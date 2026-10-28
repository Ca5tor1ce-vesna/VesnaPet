# -*- coding: utf-8 -*-
"""食物包接口: 启动时读 <桌宠目录>/dlc/foods/*.json, 把里面的食物接到 content.FOODS 后面。

目录不存在就什么都不做; 坏 JSON / 坏字段 / key 冲突只记 error.log 并跳过, 绝不影响原版。
食物包只能填数据和白名单效果名(见 EFFECTS), 不能执行代码、不能改原版食物。
JSON 格式见 README.txt「食物包」一节。
"""
import json
import re
import sys
from pathlib import Path

import content as C

# origin -> 投喂卡片里的分页名(排在原版三页后面)
ORIGINS = {"teyvat": "提瓦特扩展", "real": "现实世界", "prank": "整蛊"}
TRAITS = {None, "stew", "sweet", "cold", "drink", "spicy", "veggie", "bitter", "dark"}
# 吃后效果白名单: 名字 -> {参数: (默认, 最小, 最大)}
EFFECTS = {
    "hyper": {"sec": (12.0, 4.0, 20.0), "speed": (3.5, 2.0, 5.0)},
    "jitter": {"sec": (3.0, 1.0, 6.0)},
    "hop": {"n": (4, 2, 8)},
    "sneeze": {"delay": (1.2, 0.5, 3.0)},
    "stink": {"sec": (2.4, 1.0, 5.0)},
    "babble": {"sec": (15.0, 6.0, 25.0)},
    "burp": {"sec": (8.0, 4.0, 12.0), "n": (4, 3, 5)},
    "fly": {"sec": (10.0, 4.0, 15.0), "speed": (1.0, 0.5, 1.6)},
    "shock": {"sec": (2.5, 1.5, 4.0)},
}
FACES = ("surprised", "angry", "shy", "dizzy", "happy", "content", "cheer")
BURSTS = ("steam", "sweat", "note", "sparkle", "drop", "star", "puff")
KEY_RE = re.compile(r"^[a-z0-9_]{1,32}$")
MAX_FOODS = 64                    # 全部食物包合计上限
_installed = False
packs = []                        # [(包名, 接入的食物数)], 给日志/调试看


def pet_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _lines(v, n=30, size=40):
    if not isinstance(v, list):
        return []
    return [str(s).strip()[:size] for s in v if isinstance(s, str) and str(s).strip()][:n]


def _num(v, spec):
    d, lo, hi = spec
    try:
        x = type(d)(v)
    except (TypeError, ValueError):
        return d
    if x != x:
        return d
    return max(lo, min(hi, x))


def _effect(v):
    """{"type":"hyper","sec":10,...} 或 "hyper" -> 规整后的 dict; 不在白名单返回 None"""
    if isinstance(v, str):
        v = {"type": v}
    if not isinstance(v, dict):
        return None
    name = str(v.get("type") or "").strip().lower()
    if name not in EFFECTS:
        return None
    eff = {"type": name}
    for k, spec in EFFECTS[name].items():
        eff[k] = _num(v.get(k, spec[0]), spec)
    face = v.get("face")
    if face in FACES:
        eff["face"] = face
    burst = v.get("burst")
    if burst in BURSTS:
        eff["burst"] = burst
    return eff


def _food(raw, jp: Path, taken, log):
    pack_dir = jp.parent
    if not isinstance(raw, dict):
        raise ValueError("food 不是对象")
    key = str(raw.get("key") or "").strip()
    if not KEY_RE.match(key):
        raise ValueError(f"key 不合法: {key!r}")
    if key in taken:
        log(f"food pack: key 冲突, 跳过 {key} ({jp.name})")
        return None
    name = str(raw.get("name") or "").strip()[:16]
    if not name:
        raise ValueError(f"{key}: 缺 name")
    origin = raw.get("origin") if raw.get("origin") in ORIGINS else "teyvat"
    tier = raw.get("tier") if raw.get("tier") in C.TIER_INFO else "ok"
    trait = raw.get("trait") if raw.get("trait") in TRAITS else None
    f = dict(key=key, emoji=str(raw.get("emoji") or "🍽️")[:4], name=name,
             short=str(raw.get("short") or name).strip()[:7] or name[:7],
             region=ORIGINS[origin], tier=tier, fill=int(_num(raw.get("fill", 12), (12, 0, 40))),
             trait=trait, desc=str(raw.get("desc") or "")[:60],
             lines=_lines(raw.get("lines")) or list(C.FOOD_OK_TEXTS), refuse=_lines(raw.get("refuse")),
             origin=origin, pack=jp.name, curious=_lines(raw.get("curious")))
    icon = raw.get("icon")
    if isinstance(icon, str) and icon:
        p = (pack_dir / icon).resolve()
        if pack_dir.resolve() in p.parents and p.suffix.lower() == ".png":
            f["icon_path"] = str(p)           # 图不存在没关系: 加载时回退 assets/food 再回退 emoji
    eff = _effect(raw.get("effect"))
    if raw.get("effect") is not None and eff is None:
        log(f"food pack: {key} 的 effect 不在白名单, 忽略")
    if eff:
        f["effect"] = eff
        f["effect_lines"] = _lines(raw.get("effect_lines")) or list(f["lines"])
        f["effect_drag_lines"] = _lines(raw.get("effect_drag_lines")) or list(f["effect_lines"])
        f["effect_end_lines"] = _lines(raw.get("effect_end_lines")) or ["呼……终于好了……"]
        f["effect_caught_lines"] = _lines(raw.get("effect_caught_lines"))
        dflt_aff = -1 if origin == "prank" else 0
        f["affection"] = int(_num(raw.get("affection", dflt_aff), (dflt_aff, -5, 5)))
        f["refuse_again_sec"] = float(_num(raw.get("refuse_again_sec", 300), (300.0, 0.0, 3600.0)))
    return f


def install(log_fn=None, root: Path = None):
    """读食物包并接入 content.FOODS / FOOD_REGIONS。只做一次; 自身绝不抛异常。"""
    global _installed
    if _installed:
        return 0
    _installed = True
    log = log_fn or (lambda *a: None)
    added = 0
    try:
        d = (root or pet_dir()) / "dlc" / "foods"
        if not d.is_dir():
            return 0
        taken = {f["key"] for f in C.FOODS}
        for jp in sorted(d.glob("*.json")):
            try:
                data = json.loads(jp.read_text(encoding="utf-8-sig"))
                items = data.get("foods") if isinstance(data, dict) else None
                if not isinstance(items, list):
                    raise ValueError("缺 foods 数组")
            except Exception as e:
                log(f"food pack: 读不了 {jp.name}, 跳过", e)
                continue
            n = 0
            for raw in items:
                if added >= MAX_FOODS:
                    log(f"food pack: 超过 {MAX_FOODS} 种, 其余忽略")
                    break
                try:
                    f = _food(raw, jp, taken, log)
                except Exception as e:
                    log(f"food pack: {jp.name} 有一项食物不合法, 跳过", e)
                    continue
                if f is None:
                    continue
                C.FOODS.append(f)
                if f.get("icon_path"):
                    try:
                        import ui_kit
                        ui_kit.FOOD_ICON_EXTRA[f["key"]] = f["icon_path"]
                    except Exception as e:
                        log("food pack icon", e)
                taken.add(f["key"])
                n += 1
                added += 1
                region = f["region"]
                if not any(region in regs for _, regs in C.FOOD_REGIONS):
                    C.FOOD_REGIONS.append((region, (region,)))
            packs.append((jp.name, n))
        if added:
            # 分页按 origin 顺序: 原版三页 → 提瓦特扩展 → 现实世界 → 整蛊
            order = list(ORIGINS.values())
            base = [r for r in C.FOOD_REGIONS if r[0] not in order]
            ext = sorted((r for r in C.FOOD_REGIONS if r[0] in order), key=lambda r: order.index(r[0]))
            C.FOOD_REGIONS[:] = base + ext
    except Exception as e:
        log("food pack install", e)
    return added
