# -*- coding: utf-8 -*-
"""Grok App 联动模块 (只读)

原理: 只读 Grok App 的工具审计日志 (audit/tool_ledger.jsonl, 只追加) 的新增行, 以及
sessions/*/messages.json 的修改时间 (仅 stat, 不读内容)。不修改任何 Grok 文件,
不读取 session-api.json, 不访问其本地接口/令牌。所有逻辑在 Qt 主线程由 QTimer 驱动,
任何异常只写 error.log, 绝不向外抛。
"""
import json
import os
import random
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

PROCESS_NAMES = ("grok-app.exe", "grok-app")
ENV_LEDGER = "VESNAPET_GROK_LEDGER"      # 覆盖 ledger 路径 (测试/自定义)
ENV_PROC = "VESNAPET_GROK_PROC"          # always / never: 覆盖进程检测

# ---------------- 触发分类 ----------------
SEARCH_TOOLS = {"search", "web_fetch", "search_tool"}
CODE_TOOLS = {"read_file", "grep", "list_dir", "search_replace", "write"}
CMD_TOOLS = {"run_terminal_command"}

TEXTS = {
    "start": ["指挥官，今天也要加油哦!", "Grok 上线啦，一起努力吧!", "指挥官早~ 我准备好啦!", "嘿嘿，今天也请多关照~"],
    "search": ["正在帮你查资料~", "搜索中，马上就有结果啦~", "让我看看网上怎么说~", "查资料查资料~"],
    "code": ["在看/改代码，我给你盯着!", "代码交给我盯着，放心~", "嗯嗯，代码有动静了!", "我在旁边看着呢~"],
    "cmd": ["在跑命令啦，要小心喔", "命令执行中，别眨眼~", "敲命令的时候要小心喔!", "终端在忙，我帮你守着~"],
    "other": ["忙着呢~", "还在忙，等一下下~", "正在处理中~"],
    "perm_ask": ["需要你确认一下权限哦!", "有权限要你点头啦!", "快来看看，需要你确认~"],
    "perm_ok": ["权限收到啦~", "授权好啦，继续~"],
    "err": ["出错啦!别急我陪着你", "哎呀出错了，不要慌，我在呢!", "报错了?深呼吸，我陪你~"],
    "done": ["做完啦~ 快来看看吧!", "完成啦!快来验收~", "搞定!辛苦啦~", "忙完啦，快来看看结果~"],
    "bye": ["拜拜~", "下次见啦~", "Grok 下班啦，拜拜~"],
}
# 类别 -> 气泡冷却(秒)
COOLDOWN = {"start": 60, "search": 6, "code": 6, "cmd": 6, "other": 12, "perm": 8, "err": 10, "done": 20, "bye": 30}


# ---------------- 日志 ----------------
def error_log_path() -> Path:
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        root = str(Path.home() / "Library" / "Application Support")
    else:
        root = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(root) / "VesnaPet" / "error.log"


_last_logged = {}


def log_error(where: str, exc: BaseException = None):
    """写 error.log; 自身绝不抛异常; 同一位置 30 秒内最多记一次, 文件超 512KB 则截断重写"""
    try:
        now = time.time()
        key = where + (type(exc).__name__ if exc else "")
        if now - _last_logged.get(key, 0) < 30:
            return
        _last_logged[key] = now
        p = error_log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.stat().st_size > 512 * 1024:
            p.write_text("", encoding="utf-8")
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {where}\n")
            if exc is not None:
                f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            f.write("\n")
    except Exception:
        pass


# ---------------- 路径 / 进程检测 ----------------
def default_ledger_path() -> Path:
    env = os.environ.get(ENV_LEDGER)
    if env:
        return Path(env)
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        root = str(Path.home() / "Library" / "Application Support")
    else:
        root = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(root) / "grokapp" / "grok-app" / "data" / "audit" / "tool_ledger.jsonl"


def _win_process_running(names=PROCESS_NAMES) -> bool:
    """Windows: 用 ToolHelp32 快照枚举进程, 纯 ctypes, 无子进程/无控制台闪窗"""
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32FirstW.restype = wintypes.BOOL
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)       # TH32CS_SNAPPROCESS
    if snap in (None, wintypes.HANDLE(-1).value):
        raise OSError("CreateToolhelp32Snapshot failed")
    wanted = {n.lower() for n in names}
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            if pe.szExeFile.lower() in wanted:
                return True
            ok = k32.Process32NextW(snap, ctypes.byref(pe))
        return False
    finally:
        k32.CloseHandle(snap)


def _proc_running(names=PROCESS_NAMES) -> bool:
    try:
        if sys.platform.startswith("win"):
            return _win_process_running(names)
        wanted = {n.lower().replace(".exe", "") for n in names}
        for d in os.scandir("/proc"):
            if d.name.isdigit():
                try:
                    with open(f"/proc/{d.name}/comm", "r") as f:
                        if f.read().strip().lower() in wanted:
                            return True
                except OSError:
                    continue
        return False
    except Exception as e:
        log_error("process detection failed", e)
        return False


def default_process_check():
    mode = os.environ.get(ENV_PROC, "").lower()
    if mode == "always":
        return lambda: True
    if mode == "never":
        return lambda: False
    return _proc_running


def classify_tool(name: str) -> str:
    n = (name or "").strip().lower()
    if n in SEARCH_TOOLS or n.startswith("web search") or n.startswith("x search"):
        return "search"
    if n in CODE_TOOLS:
        return "code"
    if n in CMD_TOOLS:
        return "cmd"
    return "other"


def classify_permission(value) -> str:
    v = str(value or "").strip().lower()
    if v.startswith("auto"):
        return "auto"            # 自动放行: 无需用户操作
    if v.startswith("allow"):
        return "ok"              # 用户已授权 (allow_session / allow_once ...)
    return "ask"                 # deny / ask / pending / 未知: 需要用户留意


def parse_ts(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


# ---------------- 联动主体 ----------------
class GrokLink(QObject):
    def __init__(self, window, enabled=True, ledger_path=None, process_check=None, sessions_dir=None,
                 now=time.monotonic, wall=time.time, poll_ms=700, proc_ms=5000, quiet_sec=8.0,
                 min_gap=2.5, max_event_age=120.0, autostart=True):
        super().__init__(window)
        self.window = window
        self.enabled = bool(enabled)
        self.ledger_path = Path(ledger_path) if ledger_path else default_ledger_path()
        self.sessions_dir = Path(sessions_dir) if sessions_dir else self.ledger_path.parent.parent / "sessions"
        self.proc_fn = process_check or default_process_check()
        self.now, self.wall = now, wall
        self.quiet_sec, self.min_gap, self.max_event_age = quiet_sec, min_gap, max_event_age
        self.poll_ms, self.proc_ms = poll_ms, proc_ms

        self.offset = None          # None=文件尚未出现
        self.ino = None
        self.running = None         # None=尚未检测
        self.active = False
        self.inflight = 0
        self.episode_events = 0
        self.last_activity = 0.0
        self.last_cat = ""
        self._last = {}
        self._last_any = -1e9
        self._msg_mtime = None
        self._tick = 0

        self.poll_timer = QTimer(self); self.poll_timer.timeout.connect(self.poll)
        self.proc_timer = QTimer(self); self.proc_timer.timeout.connect(self.check_process)
        if autostart and self.enabled:
            self.start()

    # ----- 生命周期 -----
    def start(self):
        try:
            self._reset_position()
            self._msg_mtime = self._scan_messages()
            self.poll_timer.start(self.poll_ms)
            self.proc_timer.start(self.proc_ms)
            QTimer.singleShot(1200, self.check_process)      # 窗口显示后做第一次检测
        except Exception as e:
            log_error("GrokLink.start", e)

    def stop(self):
        self.poll_timer.stop()
        self.proc_timer.stop()
        self.active = False
        self.inflight = 0
        self.window.link_busy = False

    def set_enabled(self, on: bool):
        on = bool(on)
        if on == self.enabled:
            return
        self.enabled = on
        if on:
            self.running = None
            self.start()
        else:
            self.stop()

    def _reset_position(self):
        """启动/重新启用时跳到文件末尾, 只处理之后新增的内容"""
        try:
            st = self.ledger_path.stat()
            self.offset, self.ino = st.st_size, st.st_ino
        except OSError:
            self.offset, self.ino = None, None

    # ----- 状态文本 -----
    def status_text(self) -> str:
        if not self.enabled:
            return "联动已关闭"
        if not self.running:
            return "Grok App：未检测到"
        if self.active or self.inflight > 0:
            label = {"search": "搜索", "code": "代码", "cmd": "命令", "other": "处理中"}.get(self.last_cat, "处理中")
            return f"Grok App：工作中（{label}）"
        return "Grok App：已连接 · 空闲"

    # ----- 轮询 -----
    def poll(self):
        if not self.enabled:
            return
        try:
            self._tick += 1
            for ev in self._read_new_events():
                try:
                    self.handle_event(ev)
                except Exception as e:
                    log_error("handle_event", e)
            if self._tick % 3 == 0:                     # ~2 秒一次 messages.json mtime
                m = self._scan_messages()
                if m is not None:
                    if self._msg_mtime is not None and m > self._msg_mtime + 0.001:
                        self._on_activity("msg")
                    self._msg_mtime = m
            self._check_finished()
            self.window.link_busy = bool(self.active or self.inflight > 0) and bool(self.running is not False)
            if self.active:
                self.window.note_interaction()           # 联动工作期间不入睡
        except Exception as e:
            log_error("GrokLink.poll", e)

    def _read_new_events(self):
        try:
            st = self.ledger_path.stat()
        except OSError:
            self.offset, self.ino = None, None           # 文件不存在, 等它出现后从头读
            return []
        size = st.st_size
        if self.offset is None:
            self.offset = 0                               # 启动后才出现的新文件: 从头读
            self.ino = st.st_ino
        elif size < self.offset or (self.ino and st.st_ino and st.st_ino != self.ino):
            self.offset = 0                               # 截断/轮转: 重置
            self.ino = st.st_ino
        if size <= self.offset:
            return []
        try:
            with open(self.ledger_path, "rb") as f:
                f.seek(self.offset)
                chunk = f.read(min(size - self.offset, 512 * 1024))
        except OSError:
            return []
        end = chunk.rfind(b"\n")
        if end < 0:
            if len(chunk) >= 512 * 1024:                  # 异常超长无换行: 丢弃防卡死
                self.offset += len(chunk)
            return []                                     # 半行, 等下次
        self.offset += end + 1
        events = []
        for line in chunk[:end].split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line.decode("utf-8", "replace"))
            except Exception:
                continue
            if isinstance(ev, dict):
                events.append(ev)
        return events

    def _scan_messages(self):
        """sessions/*/messages.json 的最新 mtime (只 stat)"""
        try:
            best = None
            n = 0
            for d in os.scandir(self.sessions_dir):
                n += 1
                if n > 2000:
                    break
                try:
                    t = os.stat(os.path.join(d.path, "messages.json")).st_mtime
                except OSError:
                    continue
                if best is None or t > best:
                    best = t
            return best
        except OSError:
            return None

    # ----- 事件处理 -----
    def handle_event(self, ev: dict):
        if not self.enabled:
            return
        ts = parse_ts(ev.get("ts"))
        if ts is not None and self.wall() - ts > self.max_event_age:
            return                                         # 过期事件(例如电脑休眠后追赶)
        kind = ev.get("event")
        tool = ev.get("toolName")
        if kind == "tool_start":
            cat = classify_tool(tool)
            self.inflight += 1
            self.last_cat = cat
            self._on_activity("tool")
            self._react(cat, "idle", TEXTS[cat], COOLDOWN[cat])
        elif kind == "tool_end":
            self.inflight = max(0, self.inflight - 1)
            self._on_activity("tool")
            if ev.get("outcome") == "err":
                self._react("err", "surprised", TEXTS["err"], COOLDOWN["err"], dur=1.4, priority=2, bubble_dur=4.5)
        elif kind == "permission":
            self._on_activity("perm")
            c = classify_permission(ev.get("permission"))
            if c == "ask":
                self._react("perm", "surprised", TEXTS["perm_ask"], COOLDOWN["perm"], dur=1.5, priority=2, bubble_dur=6.0)
            elif c == "ok":
                self._react("perm", "idle", TEXTS["perm_ok"], COOLDOWN["perm"])
            # auto: 只保持清醒, 不打扰

    def _on_activity(self, src):
        self.last_activity = self.now()
        if not self.active:
            self.active = True
            self.episode_events = 0
        self.episode_events += 1
        self.window.note_interaction()
        if self.window.state == "sleep":
            self.window.set_state("surprised", 0.7)       # 睡着则醒来

    def _check_finished(self):
        if not self.active:
            return
        idle_for = self.now() - self.last_activity
        if idle_for < self.quiet_sec:
            return
        if self.inflight > 0 and idle_for < 120:           # 还有工具在跑(长命令), 再等等
            return
        self.active = False
        self.inflight = 0
        n, self.episode_events = self.episode_events, 0
        if n >= 1:
            self._react("done", "happy", TEXTS["done"], COOLDOWN["done"], dur=2.5, priority=1, bubble_dur=5.0)

    # ----- 进程检测 -----
    def check_process(self):
        if not self.enabled:
            return
        try:
            r = bool(self.proc_fn())
        except Exception as e:
            log_error("process check", e)
            return
        try:
            prev = self.running
            self.running = r
            if r and not prev:
                self._react("start", "happy", TEXTS["start"], COOLDOWN["start"], dur=2.5, priority=1, bubble_dur=5.0)
            elif prev and not r:
                self.active, self.inflight, self.episode_events = False, 0, 0
                self.window.link_busy = False
                self._react("bye", "happy", TEXTS["bye"], COOLDOWN["bye"], dur=1.8, priority=1, bubble_dur=3.5)
        except Exception as e:
            log_error("check_process react", e)

    # ----- 表现 -----
    def _react(self, cat, state, texts, cooldown, dur=None, priority=0, bubble_dur=None):
        w = self.window
        try:
            if w._dragging or not w.isVisible():
                return False
            now = self.now()
            if now - self._last.get(cat, -1e9) < cooldown:
                return False
            if priority < 1 and now - self._last_any < self.min_gap:
                return False
            self._last[cat] = now
            self._last_any = now
            w.note_interaction()
            # 表情: 用户刚触发的惊讶/生气不被低优先级联动打断
            if w.state == "sleep":
                if state == "idle":
                    w.set_state("surprised", 0.7)
                else:
                    w.set_state(state, dur)
            elif state == "idle":
                if w.state == "happy":
                    w.set_state("idle")
            elif w.state in ("surprised", "angry") and priority < 2:
                pass
            else:
                w.set_state(state, dur)
            w.say(random.choice(texts), duration=bubble_dur)
            return True
        except Exception as e:
            log_error("GrokLink._react", e)
            return False
