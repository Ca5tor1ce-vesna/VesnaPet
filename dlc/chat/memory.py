# -*- coding: utf-8 -*-
"""长期记忆 + 自动压缩旧对话。压缩过程不出现在聊天窗。"""
import json
import os
import re
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

KEEP_RECENT = 10          # 压缩后仍原样保留的最近消息条数（user+assistant）
COMPRESS_AT = 20          # 达到这么多条就压缩更早的部分
FACT_CAP = 24

COMPRESS_SYS = """你是对话记忆整理器，不是薇斯纳。只输出一个 JSON 对象，不要 markdown。
格式：
{"facts":["短句", "..."],"summary":"一段连续的中文摘要"}
要求：
- facts：对以后对话仍有用的稳定信息。用第三人称短句。例如「指挥官名叫……」「指挥官在做……」「约定……」「不喜欢……」。不要写语气词。最多 24 条。新信息优先；和旧事实冲突时留最新。
- summary：把「旧摘要 + 被折叠的对话」收成 180 字以内的一段话，让薇斯纳下次还能接上。保留未完成的事和情绪变化。丢掉重复闲聊和一次性玩笑。
- 不要编造对话里没出现的内容。"""


def memory_path() -> Path:
    root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(root) / "VesnaDLC" / "memory.json"


def _blank():
    return {"facts": [], "summary": "", "recent": [], "updated": 0.0}


def load():
    data = _blank()
    p = memory_path()
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            facts = loaded.get("facts") or []
            data["facts"] = [str(x).strip() for x in facts if str(x).strip()][:FACT_CAP]
            data["summary"] = str(loaded.get("summary") or "").strip()
            recent = loaded.get("recent") or []
            out = []
            for item in recent:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    role, text = str(item[0]), str(item[1]).strip()
                    if role in ("user", "assistant") and text:
                        out.append((role, text))
            data["recent"] = out[-KEEP_RECENT:]
            data["updated"] = float(loaded.get("updated") or 0)
    except Exception:
        pass
    return data


def save(data):
    p = memory_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "facts": list(data.get("facts") or [])[:FACT_CAP],
        "summary": str(data.get("summary") or ""),
        "recent": [list(x) for x in (data.get("recent") or [])][-KEEP_RECENT:],
        "updated": time.time(),
    }
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def merge_facts(old, new):
    seen = []
    for item in list(new or []) + list(old or []):
        s = str(item).strip()
        if s and s not in seen:
            seen.append(s)
    return seen[:FACT_CAP]


def memory_block(data) -> str:
    facts = data.get("facts") or []
    summary = (data.get("summary") or "").strip()
    if not facts and not summary:
        return ""
    parts = ["【长期记忆，用户看不见】下面是你和指挥官以前相处留下的笔记。当作你记得的事来用，不要宣读清单，不要说「根据记忆」。"]
    if facts:
        parts.append("稳定印象：")
        parts.extend(f"- {x}" for x in facts)
    if summary:
        parts.append("更早的对话收成：" + summary)
    return "\n".join(parts)


def _parse_json(text: str):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


class CompressJob(QThread):
    finished_ok = Signal(object)
    finished_fail = Signal()

    def __init__(self, cfg, old_messages, memory, parent=None):
        super().__init__(parent)
        self.cfg = dict(cfg)
        self.old_messages = list(old_messages)
        self.memory = dict(memory)

    def run(self):
        try:
            from openai import OpenAI
        except Exception:
            self.finished_fail.emit()
            return
        key = (self.cfg.get("api_key") or "").strip()
        model = (self.cfg.get("model") or "").strip()
        if not key or not model or not self.old_messages:
            self.finished_fail.emit()
            return
        lines = []
        old_sum = (self.memory.get("summary") or "").strip()
        if old_sum:
            lines.append("已有摘要：\n" + old_sum)
        old_facts = self.memory.get("facts") or []
        if old_facts:
            lines.append("已有事实：\n" + "\n".join(f"- {x}" for x in old_facts))
        lines.append("需要折叠的对话：")
        for role, text in self.old_messages:
            who = "指挥官" if role == "user" else "薇斯纳"
            lines.append(f"{who}：{text}")
        try:
            kw = {"api_key": key}
            base = (self.cfg.get("base_url") or "").strip().rstrip("/")
            if base:
                kw["base_url"] = base
            client = OpenAI(**kw)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": COMPRESS_SYS},
                    {"role": "user", "content": "\n".join(lines)},
                ],
                stream=False,
                temperature=0.2,
            )
            content = ""
            if resp.choices:
                content = (resp.choices[0].message.content or "").strip()
            obj = _parse_json(content)
            if not obj:
                self.finished_fail.emit()
                return
            facts = obj.get("facts") if isinstance(obj.get("facts"), list) else []
            summary = str(obj.get("summary") or "").strip()
            if not summary and not facts:
                self.finished_fail.emit()
                return
            out = {
                "facts": merge_facts(self.memory.get("facts"), facts),
                "summary": summary or (self.memory.get("summary") or ""),
                "recent": self.memory.get("recent") or [],
            }
            self.finished_ok.emit(out)
        except Exception:
            traceback.print_exc()
            self.finished_fail.emit()
