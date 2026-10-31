# -*- coding: utf-8 -*-
import traceback

from PySide6.QtCore import QThread, Signal

from persona import PERSONA


def _client(cfg):
    from openai import OpenAI
    import httpx
    kw = {"api_key": (cfg.get("api_key") or "").strip()}
    base = (cfg.get("base_url") or "").strip().rstrip("/")
    if base:
        kw["base_url"] = base
    # MIMO 偶发十几秒才出首包；默认 connect=5 会重试后变成 Request timed out
    kw["timeout"] = httpx.Timeout(connect=30.0, read=180.0, write=60.0, pool=60.0)
    kw["max_retries"] = 2
    return OpenAI(**kw)


class ChatJob(QThread):
    delta = Signal(str)
    done = Signal()
    fail = Signal(str)

    def __init__(self, cfg, history, user_text, hidden, memory_text, parent=None):
        super().__init__(parent)
        self.cfg = dict(cfg)
        self.history = list(history)
        self.user_text = user_text
        self.hidden = hidden or ""
        self.memory_text = memory_text or ""

    def run(self):
        try:
            from openai import OpenAI  # noqa: F401
        except Exception:
            self.fail.emit("还没装 openai 库，先关掉窗口，用 run.bat 启动一次。")
            return
        key = (self.cfg.get("api_key") or "").strip()
        if not key:
            self.fail.emit("还没有 API Key。点右上角设置填一下。")
            return
        model = (self.cfg.get("model") or "").strip()
        if not model:
            self.fail.emit("还没有填模型名。")
            return
        messages = [{"role": "system", "content": PERSONA}]
        if self.memory_text:
            messages.append({"role": "system", "content": self.memory_text})
        for role, text in self.history:
            if role in ("user", "assistant") and text:
                messages.append({"role": role, "content": text})
        if self.hidden:
            messages.append({"role": "system", "content": self.hidden})
        messages.append({"role": "user", "content": self.user_text})
        try:
            client = _client(self.cfg)
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=0.85,
            )
            for chunk in stream:
                if self.isInterruptionRequested():
                    break
                if not chunk.choices:
                    continue
                piece = chunk.choices[0].delta.content
                if piece:
                    self.delta.emit(piece)
            self.done.emit()
        except Exception as e:
            msg = str(e).strip() or e.__class__.__name__
            self.fail.emit(msg[:400])
            traceback.print_exc()
