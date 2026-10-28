# -*- coding: utf-8 -*-
"""连接桌宠 live 管道。
LiveClient: 旧写法, 阻塞式 get (在轮询线程里用), 桌宠没开时返回 None。
LiveSub:    v2 订阅客户端, 全靠 QLocalSocket 信号(非阻塞), 收事件推送 + 发 say。
            旧版桌宠不认 subscribe 时 supported=False, 调用方退回快照 diff。
"""
import json
import os
import time
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalSocket

PROTO_V = 1


def live_key():
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return f"VesnaPet-{user}-live"


def _dumps(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


class LiveClient:
    def __init__(self, timeout_ms=250, key=None):
        self.timeout_ms = int(timeout_ms)
        self.key = key or live_key()
        self.sock = None

    def connected(self):
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

    def get(self):
        if not self.connected() and not self.connect():
            return None
        try:
            self.sock.write(_dumps({"v": PROTO_V, "cmd": "get"}))
            if not self.sock.waitForBytesWritten(self.timeout_ms):
                self.close()
                return None
            deadline = time.monotonic() + self.timeout_ms / 1000.0
            buf = bytearray()
            while time.monotonic() < deadline:
                wait = max(1, int((deadline - time.monotonic()) * 1000))
                if self.sock.waitForReadyRead(wait):
                    buf.extend(bytes(self.sock.readAll()))
                    nl = buf.find(b"\n")
                    if nl >= 0:
                        obj = json.loads(bytes(buf[:nl]).decode("utf-8", "replace"))
                        return obj if isinstance(obj, dict) else None
            self.close()
            return None
        except Exception:
            self.close()
            return None


class LiveSub(QObject):
    """订阅客户端(主线程用)。连上 → ping → subscribe; 一行一个 JSON;
    断线 2 秒自动重连; 桌宠不在时安静重试, 不报错。"""
    event = Signal(dict)            # 推送事件 {"v":2,"ev":...}
    status = Signal(bool)           # True=订阅成功; False=断开 / 旧版桌宠不支持

    RETRY_MS = 2000
    OLD_RETRY_MS = 15000            # 旧版桌宠: 慢一点再探, 等用户升级/重启桌宠
    MAX_BUF = 256 * 1024

    def __init__(self, parent=None, key=None):
        super().__init__(parent)
        self.key = key or live_key()
        self.sock = None
        self.buf = bytearray()
        self.subscribed = False
        self.supported = None       # None 未知 / True 支持 v2 / False 旧版桌宠
        self.caps = set()
        self._pending = deque()     # 已发出、还没收到回应的命令(桌宠按顺序回)
        self._stopped = False
        self._retry = QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.timeout.connect(self._connect)

    # ----- 生命周期 -----
    def start(self):
        self._stopped = False
        self._connect()

    def stop(self):
        self._stopped = True
        self._retry.stop()
        self._teardown()

    def _teardown(self):
        s, self.sock = self.sock, None
        self.buf.clear()
        self._pending.clear()
        was = self.subscribed
        self.subscribed = False
        if s is not None:
            for sig in (s.connected, s.readyRead, s.disconnected, s.errorOccurred):
                try:
                    sig.disconnect()
                except Exception:
                    pass
            try:
                s.abort()
            except Exception:
                pass
            s.deleteLater()
        if was:
            self.status.emit(False)

    def _schedule(self, ms=None):
        if not self._stopped:
            self._retry.start(int(ms or self.RETRY_MS))

    def _connect(self):
        if self._stopped:
            return
        self._teardown()
        s = QLocalSocket(self)
        self.sock = s
        s.connected.connect(self._on_connected)
        s.readyRead.connect(self._on_read)
        s.disconnected.connect(self._on_gone)
        s.errorOccurred.connect(lambda _e: self._on_gone())
        s.connectToServer(self.key)          # 异步; 结果走 connected / errorOccurred

    def _on_gone(self):
        if self.sock is None:
            return
        self._teardown()
        self._schedule(self.OLD_RETRY_MS if self.supported is False else self.RETRY_MS)

    def _send(self, obj, tag):
        s = self.sock
        if s is None or s.state() != QLocalSocket.ConnectedState:
            return False
        s.write(_dumps(obj))
        self._pending.append(tag)
        return True

    def _on_connected(self):
        self._send({"v": PROTO_V, "cmd": "ping"}, "ping")
        self._send({"v": 2, "cmd": "subscribe"}, "subscribe")

    # ----- 读 -----
    def _on_read(self):
        s = self.sock
        if s is None:
            return
        try:
            self.buf.extend(bytes(s.readAll()))
            if len(self.buf) > self.MAX_BUF:
                self._on_gone()
                return
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    return
                line = bytes(self.buf[:nl])
                del self.buf[:nl + 1]
                try:
                    obj = json.loads(line.decode("utf-8", "replace"))
                except Exception:
                    continue
                if isinstance(obj, dict):
                    self._handle(obj)
                if self.sock is None:
                    return
        except Exception:
            self._on_gone()

    def _handle(self, obj):
        if "ev" in obj:
            if self.subscribed:
                self.event.emit(obj)
            return
        tag = self._pending.popleft() if self._pending else ""
        if tag == "ping":
            caps = obj.get("caps")
            self.caps = set(caps) if isinstance(caps, list) else set()
        elif tag == "subscribe":
            if obj.get("ok") and obj.get("subscribed"):
                self.supported = True
                self.subscribed = True
                self.status.emit(True)
            else:
                # 旧版桌宠: 不认 subscribe。断开, 由调用方退回快照 diff; 过一阵再探
                self.supported = False
                self._teardown()
                self._schedule(self.OLD_RETRY_MS)
        # say 的回应(ok / busy / rate)静默忽略

    # ----- 写 -----
    def can_say(self):
        return self.subscribed and "say" in self.caps

    def say(self, text, expr=None, sec=4):
        """让她在桌面上冒一句气泡。发出去就返回 True; 不在线/不支持返回 False。结果不等。"""
        if not self.can_say():
            return False
        obj = {"v": 2, "cmd": "say", "text": str(text)[:60], "sec": sec}
        if expr:
            obj["expr"] = expr
        return self._send(obj, "say")
