# -*- coding: utf-8 -*-
"""心情值(本体)。本体只负责算、存、显示, 不拿它改她的行为;
要不要因为心情改行为, 由插件通过 tune() 决定(见 docs/接口规范.md)。
- -100..100, 五档: 超开心 / 不错 / 平平 / 有点低落 / 很糟; 换档有回差, 换档时推 "mood" 事件(band, value, old)。
- 她身上的事件 -> 心情加减(event_delta)。好的互动 10 分钟内重复打折(第 n 次只算 1/n), 坏的不打折;
  饿着的时候吃到东西, 开心翻 1.5 倍。
- 不理她会慢慢回到「平常」: 偏离的部分 45 分钟减半, 关掉期间也算。
  平常心情跟好感等级走(Lv.1 是 +5, Lv.6 是 +30); 饱腹低于 25 时往下拉, 饿扁了低 20。
- 存在 stats.json 的 "mood"。
"""
import math
import time

LO, HI = -100.0, 100.0
HALF_LIFE = 45 * 60.0              # 偏离平常的部分多久减半(秒)
BASE_BY_LV = {1: 5.0, 2: 10.0, 3: 15.0, 4: 20.0, 5: 25.0, 6: 30.0}
HUNGRY_AT = 25.0                   # 饱腹低于它, 平常心情往下拉
HUNGRY_PULL = 0.8                  # 每低 1 点拉多少(饱腹 0 时 -20)
HUNGRY_MEAL_BONUS = 1.5            # 饿着吃到东西, 开心乘这个
REPEAT_WINDOW = 600.0              # 好的互动这段时间内重复: 第 n 次只算 1/n
HYST = 6.0                         # 换档回差
BANDS = [   # (下限, key, 名字, emoji), 从高到低
    (60.0, "great", "超开心", "😆"),
    (25.0, "good", "不错", "😊"),
    (-15.0, "ok", "平平", "🙂"),
    (-50.0, "low", "有点低落", "😕"),
    (-1e9, "bad", "很糟", "😣"),
]
FEED = {"fav": 10, "like": 6, "ok": 2, "dislike": -5, "weird": -4, "refuse": -3, "sulk_worse": -6}
RPS = {"lose": 4, "draw": 1, "win": -1}            # 从你的角度: 你输了她开心
BFLY = {"caught": 5, "landed": 3, "giveup": -1}
WAKE = {"drag": -5, "spin": -5, "pet": 2, "back": 3}


def event_delta(name, d):
    """事件 -> (类别, 心情变化); 不影响心情返回 (None, 0)"""
    if name == "pet":
        return "pet", 2.0 if d.get("sleeping") else (1.0 if d.get("sulking") else 4.0)
    if name == "feed":
        return "feed", float(FEED.get(d.get("reaction"), 0))
    if name == "wish":
        return "wish", {"done": 8.0, "miss": -3.0}.get(d.get("stage"), 0.0)
    if name == "rps":
        return "rps", float(RPS.get(d.get("result"), 0))
    if name == "butterfly":
        return "bfly", float(BFLY.get(d.get("stage"), 0))
    if name == "throw":
        return "throw", -10.0 if d.get("hard") else -6.0
    if name == "bonk":
        return "bonk", -2.0
    if name == "dizzy":
        return "dizzy", -4.0 if d.get("why") == "spin" else -2.0
    if name == "vomit":
        return "vomit", -12.0
    if name == "watered":
        if d.get("forced"):
            return "water", -15.0
        return ("water", 2.0) if d.get("dodged") else ("water", -8.0)
    if name == "rage_poke":
        return "poke", -2.0
    if name in ("comforted", "makeup"):
        return "comfort", 6.0 if name == "comforted" else 5.0
    if name == "sulk":
        return "sulk", -8.0
    if name == "sneak_caught":
        return "sneak", -1.0
    if name == "companion_bonus":
        return "company", 4.0
    if name == "level_up":
        return "level", 10.0
    if name == "focus_end" and d.get("done"):
        return "focus", 6.0
    if name == "food_effect_start":
        return "prank", -4.0
    if name == "wake":
        return "wake", float(WAKE.get(d.get("why"), 0))
    if name == "user_back":
        return "back", 4.0 if (d.get("away") or 0) >= 1800 else 1.0
    if name == "fortune" and d.get("fresh"):
        return "fortune", 3.0 if d.get("tier") in ("大吉", "中吉") else 0.0
    if name == "double_click":
        return "jump", 1.0
    return None, 0.0


def band_of(m):
    for i, b in enumerate(BANDS):
        if m >= b[0]:
            return i
    return len(BANDS) - 1


class Mood:
    def __init__(self, stats, emit=None, away_sec=0.0):
        self.stats = stats
        self.emit = emit or (lambda *a, **k: None)
        v = stats.d.get("mood")
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v:
            self.value = self._settle(max(LO, min(HI, float(v))), max(0.0, float(away_sec)))
        else:
            self.value = self.base()
        self.band = band_of(self.value)
        self.recent = {}                   # 类别 -> [时刻...], 算重复打折
        self._store()

    # ----- 读 -----
    @property
    def key(self):
        return BANDS[self.band][1]

    @property
    def name(self):
        return BANDS[self.band][2]

    @property
    def emoji(self):
        return BANDS[self.band][3]

    def frac(self):
        return (self.value - LO) / (HI - LO)

    def base(self):
        """平常心情: 好感越高越好, 饿了往下拉"""
        try:
            b = BASE_BY_LV.get(int(self.stats.level()[0]), 5.0)
            h = float(self.stats.hunger)
        except Exception:
            return 5.0
        return b - max(0.0, HUNGRY_AT - h) * HUNGRY_PULL

    # ----- 变化 -----
    def _settle(self, m, dt):
        base = self.base()
        return base + (m - base) * math.pow(0.5, dt / HALF_LIFE)

    def tick(self, dt):
        self.value = self._settle(self.value, dt)
        self._store()
        self._update_band()

    def add(self, delta, cat=None):
        """心情 +delta。给了 cat 且是正数时, 同类 10 分钟内重复打折。返回实际加了多少"""
        delta = float(delta)
        if cat and delta > 0:
            now = time.monotonic()
            hist = [t for t in self.recent.get(cat, ()) if now - t < REPEAT_WINDOW]
            hist.append(now)
            self.recent[cat] = hist
            delta /= len(hist)
        old = self.value
        self.value = max(LO, min(HI, self.value + delta))
        self._store()
        self._update_band()
        return self.value - old

    def on_event(self, name, data):
        cat, delta = event_delta(name, data)
        if not cat or not delta:
            return
        if cat == "feed" and delta > 0 and self.stats.hunger < HUNGRY_AT:
            delta *= HUNGRY_MEAL_BONUS
        self.add(delta, cat)

    def _store(self):
        self.stats.d["mood"] = round(self.value, 2)
        self.stats.touch()

    def _update_band(self):
        i = band_of(self.value)
        if i == self.band:
            return
        lo = BANDS[self.band][0]
        hi = BANDS[self.band - 1][0] if self.band > 0 else 1e9
        if lo - HYST <= self.value < hi + HYST:          # 还在回差里: 不换档
            return
        old, self.band = self.band, i
        self.emit("mood", band=self.key, value=round(self.value), old=BANDS[old][1])
