# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path

DEFAULTS = {
    "api_key": "",
    "base_url": "https://api.xiaomimimo.com/v1",
    "model": "mimo-v2.6-flash",
    "topmost": True,
    "pet_say": True,        # 回复完让她在桌面上说出来(需要新版桌宠)
}


def config_path() -> Path:
    root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(root) / "VesnaDLC" / "config.json"


def load():
    data = dict(DEFAULTS)
    p = config_path()
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            for k in DEFAULTS:
                if k in loaded:
                    data[k] = loaded[k]
    except Exception:
        pass
    data["topmost"] = bool(data.get("topmost", True))
    data["pet_say"] = bool(data.get("pet_say", True))
    data["api_key"] = str(data.get("api_key") or "")
    data["base_url"] = str(data.get("base_url") or "")
    data["model"] = str(data.get("model") or "")
    return data


def save(data):
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    out = {k: data.get(k, DEFAULTS[k]) for k in DEFAULTS}
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)
