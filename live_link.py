# -*- coding: utf-8 -*-
"""DLC 状态协议 (v1 只读 + v2 事件推送/冒气泡)

桌宠自己跑; DLC 装不装、连不连都不影响她。监听失败就关掉本模块, 记一行 error.log。

套接字名: VesnaPet-{USERNAME}-live
  与单实例管道 VesnaPet-{user}-single 分开, 互不干扰。

传输: UTF-8, 一行一个 JSON。没有喂食/改好感/改饱食命令。

客户端 -> 桌宠:
  {"v":1,"cmd":"ping"}
  {"v":1,"cmd":"get"}
  {"v":2,"cmd":"subscribe"}                       (v2) 本连接之后收事件推送
  {"v":2,"cmd":"say","text":"...","expr":"happy","sec":4}   (v2) 让她头顶冒一句气泡
  也接受纯文本 ping / get / subscribe 加换行 (方便手工测)。

桌宠 -> 客户端:
  ping: {"v":1,"ok":true,"pong":true,"proto":2,"caps":["get","subscribe","say"]}
  get:  {"v":1,"ok":true, ...快照字段}            (v1 字段都在; 后来只加不改, 如 mood / mood_band)
  subscribe: {"v":2,"ok":true,"subscribed":true}
  say:  {"v":2,"ok":true}  或  {"v":2,"ok":false,"err":"rate"|"busy"|"muted"|"hidden"|"empty"}
  未知: {"v":1,"ok":false,"err":"unknown"}
  事件(仅已订阅的连接): {"v":2,"ev":"<名>","t":<unix秒>, ...附加字段}

say 规则:
  text 截断到 60 字; expr 只认白名单表情(SAY_EXPRS 且 assets 里真有图), 不认识就忽略;
  另外认 pout(委屈) / smug(偷笑) 两张「只换脸」的(main.LIVE_SAY_FACES), 同样要真有图;
  sec 夹在 1–8 秒, 表情到时自动回到原状态(走 set_state 的临时表情计时器);
  每连接最小间隔 1.2 秒, 超频回 rate; 她在睡觉/被拖/被转/被丢/晕/达妮卡来访时回 busy, 不打断。
  say 不改好感、饱食, 也不算一次互动(不重置睡觉计时)。

事件名(附加字段):
  click / double_click / pet(sleeping, sulking)
  drag_start(was_sleep) / drag_end(held, thrown)
  throw(speed, hard, level) / bonk(impact) / throw_land(level, wall, bonks)
  spin_start / spin_end(meter) / dizzy(why: spin|wall)
  feed(key, name, tier, trait, reaction, first)
     reaction: fav|like|ok|dislike|weird 吃下去的档次 / refuse 推开 / full 吃饱不吃 / sulk_worse 闹别扭时喂讨厌的
  sleep / wake(why: pet|drag|spin|click|feed|butterfly|water|back|reminder|other)
  state(from, to) / say(text, src: pet|dlc)
  idle_action(act: happy|look|stretch|hop|wave|walk|sneak) / sneak_caught
  sulk(again) / makeup(how) / level_up(name)
  danika_visit(auto) / danika_end(skipped)
  butterfly(stage: come|caught|landed|giveup, auto)
  food_effect_start(key, name, effect) / food_effect_end(key, name, effect, why: done|sleep|hidden|throw|spin|drag)
  rps(result: win|lose|draw, 从你的角度) / fortune(tier, fresh)
  focus_start(minutes) / focus_end(minutes, done) / reminder(kind: water|sit|chime|hungry)
  user_away(idle) / user_back(away)   你离开电脑 / 回来(只有 Windows 有)
  mood(band: great|good|ok|low|bad, value, old)   心情换档 / walk_end(kind: stroll|come|approach) / come_refused
  sneak_done   偷吃没被发现、吃完了
  插件发的: watered(dodged, asleep, forced) / comforted(was_sulking, after, gain) / companion_bonus(count, gain, minutes)
     / vomit(why, hunger_drop, hunger, affection_drop) / wish(stage: start|done|miss|cancel, kind, ...)
     / rage_poke(pokes, double, undo, blew) / memory(kind: recap|life, text) / approach(why: hungry|company)
     / weak_hop(hunger)
  同一套事件也会通知互动插件(on_event); 完整说明和字段见 docs/接口规范.md。

同时最多 4 个连接; 单行最多 4KB; 写缓冲超过 64KB 则断开(推送也一样, 慢客户端会被断开)。
桌宠端不用 waitFor*, 不阻塞 16ms 主循环。
"""
import json
import os
import sys
import time

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket

PROTO_V = 1
PROTO_V2 = 2
CAPS = ["get", "subscribe", "say"]
MAX_CLIENTS = 4
MAX_LINE = 4096
MAX_BUF = 8192
MAX_WRITE = 64 * 1024
SAY_GAP = 1.2           # 每连接 say 最小间隔(秒)
SAY_MAX = 60            # say 文本最多字数


def live_key() -> str:
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return f"VesnaPet-{user}-live"


def _ok(extra=None, v=PROTO_V):
    d = {"v": v, "ok": True}
    if extra:
        d.update(extra)
    return d


def _err(msg, v=PROTO_V):
    return {"v": v, "ok": False, "err": str(msg)}


def _dumps(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


class _Conn:
    """一个客户端连接: 读缓冲 + 是否订阅 + 上次 say 时间"""
    __slots__ = ("sock", "buf", "sub", "say_t")

    def __init__(self, sock):
        self.sock = sock
        self.buf = bytearray()
        self.sub = False
        self.say_t = -1e9


class LiveHub(QObject):
    """桌宠侧监听。DLC 不在时它只是空转。"""

    def __init__(self, window, log_fn=None, key=None):
        super().__init__(window)
        self.window = window
        self.log_fn = log_fn
        self.key = key or live_key()
        self.server = None
        self._clients = []          # list[_Conn]
        self.subs = 0               # 已订阅连接数; 0 时 broadcast 立刻返回

    def _log(self, where, exc=None):
        fn = self.log_fn
        if fn is None:
            return
        try:
            fn(where, exc) if exc is not None else fn(where)
        except Exception:
            pass

    def start(self) -> bool:
        try:
            QLocalServer.removeServer(self.key)
            server = QLocalServer(self)
            server.setMaxPendingConnections(MAX_CLIENTS)
            if not server.listen(self.key):
                self._log("LiveHub.listen failed: " + (server.errorString() or self.key))
                server.deleteLater()
                return False
            server.newConnection.connect(self._on_conn)
            self.server = server
            return True
        except Exception as e:
            self._log("LiveHub.start", e)
            self.server = None
            return False

    def stop(self):
        try:
            for c in list(self._clients):
                self._drop(c.sock)
            self._clients.clear()
            self.subs = 0
            if self.server is not None:
                self.server.close()
                QLocalServer.removeServer(self.key)
                self.server.deleteLater()
                self.server = None
        except Exception as e:
            self._log("LiveHub.stop", e)

    def _on_conn(self):
        try:
            if self.server is None:
                return
            sock = self.server.nextPendingConnection()
            if sock is None:
                return
            if len(self._clients) >= MAX_CLIENTS:
                try:
                    sock.write(_dumps(_err("busy")))
                except Exception:
                    pass
                sock.disconnectFromServer()
                sock.deleteLater()
                return
            self._clients.append(_Conn(sock))
            sock.readyRead.connect(lambda s=sock: self._on_read(s))
            sock.disconnected.connect(lambda s=sock: self._drop(s))
            sock.errorOccurred.connect(lambda _e, s=sock: self._drop(s))
            if sock.bytesAvailable():
                self._on_read(sock)
        except Exception as e:
            self._log("LiveHub._on_conn", e)

    def _find(self, sock):
        for i, c in enumerate(self._clients):
            if c.sock is sock:
                return i, c
        return None, None

    def _recount(self):
        self.subs = sum(1 for c in self._clients if c.sub)

    def _drop(self, sock):
        try:
            idx, _ = self._find(sock)
            if idx is not None:
                self._clients.pop(idx)
                self._recount()
            try:
                sock.readyRead.disconnect()
            except Exception:
                pass
            try:
                sock.disconnected.disconnect()
            except Exception:
                pass
            try:
                sock.errorOccurred.disconnect()
            except Exception:
                pass
            if sock.state() != QLocalSocket.UnconnectedState:
                sock.disconnectFromServer()
            sock.deleteLater()
        except Exception as e:
            self._log("LiveHub._drop", e)

    def _on_read(self, sock):
        try:
            idx, conn = self._find(sock)
            if conn is None:
                return
            buf = conn.buf
            chunk = bytes(sock.readAll())
            if not chunk:
                return
            buf.extend(chunk)
            if len(buf) > MAX_BUF:
                self._drop(sock)
                return
            while True:
                nl = buf.find(b"\n")
                if nl < 0:
                    if len(buf) > MAX_LINE:
                        self._drop(sock)
                    return
                line = bytes(buf[:nl])
                del buf[:nl + 1]
                if len(line) > MAX_LINE:
                    self._reply(sock, _err("too_long"))
                    continue
                self._handle_line(conn, line)
                if self._find(sock)[1] is None:
                    return              # 处理中被断开
        except Exception as e:
            self._log("LiveHub._on_read", e)
            self._drop(sock)

    def _handle_line(self, conn, raw: bytes):
        sock = conn.sock
        text = raw.decode("utf-8", "replace").strip()
        if not text:
            return
        cmd = "get"
        obj = {}
        if text[:1] == "{":
            try:
                obj = json.loads(text)
            except Exception:
                self._reply(sock, _err("bad_json"))
                return
            if not isinstance(obj, dict):
                self._reply(sock, _err("bad_json"))
                return
            cmd = str(obj.get("cmd") or "get").strip().lower()
        else:
            cmd = text.split()[0].strip().lower()
        if cmd in ("ping", "hi"):
            self._reply(sock, _ok({"pong": True, "proto": PROTO_V2, "caps": list(CAPS)}))
            return
        if cmd in ("get", "snapshot", "state"):
            self._reply(sock, self._snapshot())
            return
        if cmd in ("subscribe", "sub"):
            conn.sub = True
            self._recount()
            self._reply(sock, _ok({"subscribed": True}, v=PROTO_V2))
            return
        if cmd == "say":
            self._reply(sock, self._say(conn, obj))
            return
        self._reply(sock, _err("unknown"))

    def _say(self, conn, obj):
        """v2 say: 节流 + 截断在这里做; 能不能说、换不换表情交给 window.live_say"""
        try:
            now = time.monotonic()
            if now - conn.say_t < SAY_GAP:
                return _err("rate", v=PROTO_V2)
            text = str(obj.get("text") or "").strip()[:SAY_MAX]
            if not text:
                return _err("empty", v=PROTO_V2)
            fn = getattr(self.window, "live_say", None)
            if not callable(fn):
                return _err("unknown", v=PROTO_V2)
            expr = obj.get("expr")
            expr = str(expr).strip().lower() if isinstance(expr, str) else None
            try:
                sec = float(obj.get("sec", 4))
            except (TypeError, ValueError):
                sec = 4.0
            sec = max(1.0, min(8.0, sec if sec == sec else 4.0))
            bad = fn(text, expr, sec)
            if bad:
                return _err(bad, v=PROTO_V2)
            conn.say_t = now
            return _ok(v=PROTO_V2)
        except Exception as e:
            self._log("LiveHub._say", e)
            return _err("busy", v=PROTO_V2)

    def broadcast(self, name, data=None):
        """推一条事件给所有已订阅连接。没订阅者就立刻返回; 任何异常只记 error.log。"""
        if not self.subs:
            return
        try:
            ev = {"v": PROTO_V2, "ev": str(name), "t": round(time.time(), 3)}
            if data:
                for k, v in data.items():
                    if k not in ev:
                        ev[k] = v
            try:
                line = _dumps(ev)
            except (TypeError, ValueError):
                line = _dumps({k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
                               for k, v in ev.items()})
            for c in list(self._clients):
                if not c.sub:
                    continue
                s = c.sock
                if s.bytesToWrite() > MAX_WRITE:
                    self._drop(s)           # 读得太慢的客户端: 断开, 不攒内存
                    continue
                s.write(line)
        except Exception as e:
            self._log("LiveHub.broadcast", e)

    def _snapshot(self):
        try:
            fn = getattr(self.window, "live_snapshot", None)
            if not callable(fn):
                return _err("no_snapshot")
            data = fn()
            if not isinstance(data, dict):
                return _err("bad_snapshot")
            data.setdefault("v", PROTO_V)
            data.setdefault("ok", True)
            return data
        except Exception as e:
            self._log("LiveHub._snapshot", e)
            return _err("busy")

    def _reply(self, sock, obj):
        try:
            if sock.bytesToWrite() > MAX_WRITE:
                self._drop(sock)
                return
            sock.write(_dumps(obj))
        except Exception as e:
            self._log("LiveHub._reply", e)
            self._drop(sock)


class LiveClient:
    """给 DLC 用。桌宠没开时 connect() 返回 False, 不要当异常。"""

    def __init__(self, timeout_ms=400, key=None):
        self.timeout_ms = int(timeout_ms)
        self.key = key or live_key()
        self.sock = None

    def connected(self) -> bool:
        s = self.sock
        return s is not None and s.state() == QLocalSocket.ConnectedState

    def connect(self) -> bool:
        self.close()
        s = QLocalSocket()
        s.connectToServer(self.key)
        if not s.waitForConnected(self.timeout_ms):
            s.deleteLater()
            return False
        self.sock = s
        return True

    def close(self):
        s = self.sock
        self.sock = None
        if s is None:
            return
        try:
            s.disconnectFromServer()
        except Exception:
            pass
        s.deleteLater()

    def ask(self, cmd="get"):
        """成功返回 dict; 桌宠不在或超时返回 None。"""
        if not self.connected() and not self.connect():
            return None
        try:
            self.sock.write(_dumps({"v": PROTO_V, "cmd": cmd}))
            if not self.sock.waitForBytesWritten(self.timeout_ms):
                self.close()
                return None
            deadline = time.monotonic() + self.timeout_ms / 1000.0
            buf = bytearray()
            while time.monotonic() < deadline:
                if self.sock.waitForReadyRead(max(1, int((deadline - time.monotonic()) * 1000))):
                    buf.extend(bytes(self.sock.readAll()))
                    nl = buf.find(b"\n")
                    if nl >= 0:
                        line = bytes(buf[:nl]).decode("utf-8", "replace")
                        obj = json.loads(line)
                        return obj if isinstance(obj, dict) else None
            self.close()
            return None
        except Exception:
            self.close()
            return None

    def ping(self):
        return self.ask("ping")

    def get(self):
        return self.ask("get")


def probe():
    """命令行烟测: python live_link.py  → 打印快照或 'offline'。"""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    c = LiveClient()
    data = c.get()
    c.close()
    if data is None:
        print("offline")
        return 1
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if data.get("ok") else 2


if __name__ == "__main__":
    sys.exit(probe())
