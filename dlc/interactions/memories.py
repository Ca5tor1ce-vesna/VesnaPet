# -*- coding: utf-8 -*-
"""互动 DLC「她记得」: 记下每天发生了什么, 偶尔提起来, 像是记得你们之间的事。
- 每天第一次安静下来时(启动 1.5 分钟后), 说一句「昨天 / 上次」的事: 被丢了几次、摸了几次头、
  喂了几次什么、陪你专注了多久、猜拳谁赢……挑一件那天真发生过的。
- 之后偶尔(启动 25–45 分钟后第一次, 之后 40–90 分钟)说一句累计的事: 一共喂过几次某样菜、撞过几次墙、
  帮她实现了几个心愿、认识几天了……同一类 7 天内不重复。
- 一天最多 3 句(含「昨天」那句); 勿扰时不说; 有小心愿在等时不插嘴。
- 只记次数, 存 <数据目录>/memories.json, 保留最近 8 天; 当天说过几句也记在里面, 重启不会重说。
测试用: 环境变量 VESNA_MEMO_SEC=秒数, 把开口前的等待和间隔都改成这么多秒。
只用公开接口(docs/接口规范.md): 记账靠 on_event, 累计数靠 pet.stats, 能不能开口看 pet.can_auto("plugin_talk")。
"""
import json
import os
import random
import time
from datetime import date, timedelta

import content as C
from stats import data_dir

KEEP_DAYS = 8
DAILY_MAX = 3
RECAP_DELAY = 90.0                 # 启动后多久才说「昨天」(先让问候/签到说完)
LIFE_FIRST_MIN = (25, 45)
LIFE_EVERY_MIN = (40, 90)
REPEAT_DAYS = 7                    # 同一类累计的话, 这么多天内不重复
CALM_SEC = 6.0
SAVE_GAP = 15.0
EATEN = ("fav", "like", "ok", "dislike", "weird")
FX = {"angry": ("anger", 1), "happy": ("sparkle", 4), "cheer": ("sparkle", 6), "love": ("heart", 4),
      "content": ("heart", 2), "shy": ("sweat", 1), "surprised": ("excl", 1)}


def _test_sec():
    try:
        v = float(os.environ.get("VESNA_MEMO_SEC", ""))
        if v > 0:
            return max(3.0, v)
    except ValueError:
        pass
    return None


def recap_lines(day, word):
    """那一天的计数 -> 可以说的话 [(表情, 台词)]; word 是「昨天」或「上次」"""
    out = []
    n = day.get("throw", 0)
    if n >= 3:
        out.append(("angry", f"{word}被你丢了 {n} 次……小本本上都记着呢!"))
    if day.get("water", 0):
        out.append(("angry", f"{word}你还拿水浇我……这笔账还没算完!"))
    if day.get("vomit", 0):
        out.append(("angry", f"{word}被你转到吐了……今天不许转!"))
    n = day.get("pet", 0)
    if n >= 8:
        out.append(("happy", f"{word}你摸了我 {n} 次头……嘿嘿,今天呢?"))
    foods = day.get("food") or {}
    if foods:
        key = max(foods, key=lambda k: foods[k])
        if foods[key] >= 2:
            name = (day.get("names") or {}).get(key) or key
            out.append(("happy", f"{word}喂了我 {foods[key]} 次{name}~ 还想吃!"))
    n = day.get("focus", 0)
    if n >= 50:
        out.append(("cheer", f"{word}陪你专注了 {n} 分钟,好厉害!"))
    w, lo = day.get("rps_win", 0), day.get("rps_lose", 0)
    if w + lo >= 3 and w != lo:
        out.append(("angry", f"{word}猜拳你赢了 {w} 局……今天我要赢回来!") if w > lo
                   else ("happy", f"{word}猜拳我赢了 {lo} 局,嘿嘿~"))
    n = day.get("wish", 0)
    if n >= 2:
        out.append(("love", f"{word}你帮我实现了 {n} 个小心愿~"))
    n = day.get("sulk", 0)
    if n >= 2:
        out.append(("shy", f"{word}我闹了 {n} 次别扭……才、才不全是我的错!"))
    n = day.get("bfly", 0)
    if n >= 2:
        out.append(("happy", f"{word}我们一起抓了 {n} 只蝴蝶~"))
    return out


def life_lines(stats):
    """累计计数 -> 可以说的话 [(类别, 表情, 台词)]"""
    out = []
    best, best_n = None, 0
    for f in C.FOODS:
        n = stats.food_count(f["key"])
        if n > best_n:
            best, best_n = f, n
    if best is not None and best_n >= 10:
        out.append(("food", "happy", f"你已经喂过我 {best_n} 次{best['name']}啦~ 吃不腻!"))
    n = stats.count("pets")
    if n >= 50:
        out.append(("pets", "content", f"被你摸了 {n} 次头了……头冠都被摸亮了~"))
    n = stats.count("throws")
    if n >= 10:
        out.append(("throws", "angry", f"你一共丢过我 {n} 次!小本本都快写满了!"))
    n = stats.count("wall_bonks")
    if n >= 5:
        out.append(("bonks", "surprised", f"我已经撞了 {n} 次墙……墙上都快有我的形状了!"))
    n = stats.count("focus_minutes")
    if n >= 120:
        out.append(("focus", "cheer", f"我们一起专注了 {n // 60} 个小时了哦!"))
    n = stats.count("wish_done")
    if n >= 5:
        out.append(("wish", "love", f"你已经帮我实现 {n} 个小心愿了……谢谢你~"))
    n = stats.count("days_met")
    if n >= 7:
        out.append(("days", "shy", f"认识你已经 {n} 天了呢……时间过得好快。"))
    w, lo = stats.count("rps_win"), stats.count("rps_lose")
    if w + lo >= 10 and w != lo:
        out.append(("rps", "angry", f"猜拳你总共赢了我 {w} 局……不公平!") if w > lo
                   else ("rps", "happy", f"猜拳我总共赢了 {lo} 局!嘿嘿~"))
    n = stats.count("butterflies")
    if n >= 10:
        out.append(("bfly", "happy", f"我们一共抓过 {n} 只蝴蝶了~"))
    return out


class Memories:
    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.path = data_dir() / "memories.json"
        self.d = {"days": {}, "said": {}, "talk": {"day": "", "n": 0, "recap": False}}
        try:
            v = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(v, dict):
                for k in ("days", "said", "talk"):
                    if isinstance(v.get(k), dict):
                        self.d[k] = v[k]
        except FileNotFoundError:
            pass
        except Exception as e:
            if log_fn:
                log_fn("memories load", e)
        talk = self.d["talk"]
        try:
            self.d["talk"] = {"day": str(talk.get("day") or ""), "n": int(talk.get("n") or 0),
                              "recap": bool(talk.get("recap"))}
        except (TypeError, ValueError):
            self.d["talk"] = {"day": "", "n": 0, "recap": False}
        self.test_sec = _test_sec()
        now = time.monotonic()
        self.recap_at = now + (self.test_sec or RECAP_DELAY)
        self.life_at = now + self._gap(LIFE_FIRST_MIN)
        self.calm_since = None
        self.wish_pending = False
        self.dirty = False
        self._last_save = now
        self._next_check = 0.0

    def _gap(self, rng):
        return self.test_sec or random.uniform(*rng) * 60.0

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.d, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
            self.dirty = False
        except Exception as e:
            if self.log:
                self.log("memories save", e)

    # ----- 记账 -----
    def _today(self):
        today = date.today().isoformat()
        days = self.d["days"]
        if not isinstance(days.get(today), dict):
            days[today] = {}
            for k in sorted(days)[:-KEEP_DAYS]:
                del days[k]
        return days[today]

    def _add(self, key, n=1):
        day = self._today()
        day[key] = int(day.get(key, 0)) + n
        self.dirty = True

    def on_event(self, name, data):
        if name == "wish":
            self.wish_pending = data.get("stage") == "start"
            if data.get("stage") == "done":
                self._add("wish")
        elif name == "pet" and not data.get("sleeping"):
            self._add("pet")
        elif name == "feed" and data.get("reaction") in EATEN and data.get("key"):
            day = self._today()
            foods = day.setdefault("food", {})
            foods[data["key"]] = int(foods.get(data["key"], 0)) + 1
            day.setdefault("names", {})[data["key"]] = str(data.get("name") or data["key"])
            self.dirty = True
        elif name == "throw":
            self._add("throw")
        elif name == "watered" and (data.get("forced") or not data.get("dodged")):
            self._add("water")
        elif name == "vomit":
            self._add("vomit")
        elif name == "sulk" and not data.get("again"):
            self._add("sulk")
        elif name == "butterfly" and data.get("stage") == "caught":
            self._add("bfly")
        elif name == "focus_end" and data.get("done"):
            self._add("focus", int(data.get("minutes") or 0))
        elif name == "rps" and data.get("result") in ("win", "lose"):
            self._add("rps_" + data["result"])

    # ----- 开口 -----
    def step(self, t):
        if t < self._next_check:
            return
        self._next_check = t + 0.5
        if self.dirty and t - self._last_save >= SAVE_GAP:
            self._last_save = t
            self._save()
        p = self.pet
        if p.can_auto("plugin_talk"):
            if self.calm_since is None:
                self.calm_since = t
        else:
            self.calm_since = None
        if (self.calm_since is None or t - self.calm_since < CALM_SEC or self.wish_pending
                or p.cfg["mute"] or p.bubble.isVisible()):
            return
        talk = self.d["talk"]
        today = date.today().isoformat()
        if talk.get("day") != today:
            talk.clear()
            talk.update(day=today, n=0, recap=False)
            self.dirty = True
        if talk["n"] >= DAILY_MAX:
            return
        if not talk["recap"] and t >= self.recap_at:
            talk["recap"] = True
            self.dirty = True
            line = self._recap(today)
            if line:
                self._speak(*line, kind="recap")
            return
        if t >= self.life_at:
            self.life_at = t + self._gap(LIFE_EVERY_MIN)
            line = self._life(today)
            if line:
                self._speak(*line, kind="life")

    def _recap(self, today):
        days = [k for k, v in self.d["days"].items() if k < today and isinstance(v, dict) and v]
        if not days:
            return None
        last = max(days)
        yday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
        cands = recap_lines(self.d["days"][last], "昨天" if last == yday else "上次")
        return random.choice(cands) if cands else None

    def _life(self, today):
        said = self.d["said"]
        cutoff = (date.fromisoformat(today) - timedelta(days=REPEAT_DAYS)).isoformat()
        cands = [c for c in life_lines(self.pet.stats) if said.get(c[0], "") <= cutoff]
        if not cands:
            return None
        cat, expr, text = random.choice(cands)
        said[cat] = today
        return expr, text

    def _speak(self, expr, text, kind):
        p = self.pet
        talk = self.d["talk"]
        talk["n"] += 1
        self.dirty = True
        if expr in ("angry", "happy", "cheer", "love", "content", "shy", "surprised"):
            p.set_state(expr, 2.4)
        kind_fx = FX.get(expr)
        if kind_fx:
            p.burst(kind_fx[0], kind_fx[1])
        p.say(text, duration=4.0, tone="info" if kind == "recap" else "normal", src="memo")
        p.emit_event("memory", kind=kind, text=text)


def create(pet, log_fn=None):
    return Memories(pet, log_fn)
