# -*- coding: utf-8 -*-
"""互动 DLC「小心愿」: 她安静待着的时候, 隔一阵(启动后 6–12 分钟, 之后 20–40 分钟)提一个小要求,
都是现成的互动: 摸摸头 / 想吃甜的 / 想吃冰的或喝凉的 / 想喝热汤 / 陪我猜拳 / 想看蝴蝶。
- 2 分钟内满足她: 专门的台词 + 爱心, 好感 +4(在那次互动原本的奖励之外)。
- 一分钟还没动静会提示一次怎么做; 到时没理她就嘟囔一句, 不扣好感。等着的心愿也显示在托盘提示和右键卡片的状态行里。
- 中途她睡着 / 隐藏 / 闹别扭 / 被强行浇水 / 你离开电脑: 心愿悄悄作废。勿扰时不提心愿。
- 每天最多 8 个; 累计次数记在 stats 的 wish_done / wish_missed。
- 推 "wish" 事件: stage = start(kind, text) / done(kind, after, gain) / miss(kind) / cancel(kind)。
测试用: 环境变量 VESNA_WISH_SEC=秒数, 把心愿间隔(含第一次)改成这么多秒。
只用公开接口(docs/接口规范.md); 满足与否靠 on_event 看事件, 能不能开口看 pet.can_auto("plugin_talk")。
"""
import os
import random
import time
from datetime import date

from PySide6.QtCore import QPointF, QTimer

ANSWER_SEC = 120.0                 # 多久内满足算数
FIRST_MIN = (6, 12)                # 启动后第一个心愿(分钟)
EVERY_MIN = (20, 40)               # 之后的间隔(分钟)
CALM_SEC = 6.0                     # 安静待着这么久才开口(刚醒 / 刚被戳完不提)
REMIND_SEC = 20.0                  # 等待中每隔这么久, 头顶冒一下心愿的小图标
DAILY_MAX = 8
GAIN = 4
FULL = 80                          # 饱腹到这儿就不许吃的心愿
CALM = ("idle", "look", "look_left", "content", "happy")   # 满足后说谢谢时, 这些表情可以换成 love
CANCEL = {"hidden", "sleep", "sulk", "away", "rage", "water_force"}               # 这些时候正等着的心愿作废
FOOD_TRAITS = {"sweet": {"sweet"}, "cold": {"cold", "drink"}, "stew": {"stew"}}

WISHES = {   # emoji: 头顶图标; label: 托盘提示/小屋里显示; delay: 满足后隔多久说谢谢(让那次互动自己的台词先说完)
    "pet": dict(emoji="🤚", label="想被摸摸头", delay=2.2, hint="(在我头上左右蹭蹭就好)",
                ask=["……头冠有点歪了,帮我摸摸头嘛?", "今天还没被摸过头呢……(偷偷看你)", "想、想被摸摸头……就一下下!"],
                done=["嘿嘿……就是这个!心愿达成~", "你真的听见了呀……嘿嘿。", "满足了!头冠也不歪了~"]),
    "sweet": dict(emoji="🍮", label="想吃甜的", delay=5.0, hint="(右键 → 投喂)",
                  ask=["好想吃甜的……杏仁豆腐、团子,什么都行!", "嘴巴想要甜甜的东西了~", "要是现在有一份甜点就好了……(小声)"],
                  done=["就是想吃甜的!你怎么知道的~", "甜甜的心愿,达成!", "嘿嘿,被你宠坏了……"]),
    "cold": dict(emoji="🍨", label="想吃冰的", delay=5.0, hint="(右键 → 投喂)",
                 ask=["想吃点冰冰凉凉的……", "有没有冰淇淋,或者凉凉的饮料呀?", "至冬人也想来一口冰的~"],
                 done=["呼——冰冰凉凉,太满足了!", "就是这个感觉!心愿达成~", "凉到心里去了,嘿嘿。"]),
    "stew": dict(emoji="🍲", label="想喝热汤", delay=5.0, hint="(右键 → 投喂)",
                 ask=["想喝一碗热乎乎的汤……", "要是有红菜汤就好了……(咕噜)", "肚子想要暖暖的东西~"],
                 done=["呼……从肚子暖到翅膀尖了~", "就是想喝这个!你最懂我了~", "热汤心愿,达成!"]),
    "rps": dict(emoji="✊", label="想猜拳", delay=2.0, hint="(右键 → 猜拳)",
                ask=["好无聊……陪我猜一局拳嘛?", "要不要来猜拳?输了不许哭哦~", "手痒了!来猜拳!"],
                done=["嘿嘿,陪我玩啦~ 心愿达成!", "你愿意陪我玩,我很开心哦。", "再来……不对,已经很满足啦~"]),
    "butterfly": dict(emoji="🦋", label="想看蝴蝶", delay=1.0, hint="(右键 → 召唤蝴蝶)",
                      ask=["好想看蝴蝶呀……能叫一只过来吗?", "今天的蝴蝶怎么还没来……", "想和蝴蝶玩~"],
                      done=["蝴蝶来啦!你是怎么做到的~", "哇,真的来了!谢谢你~", "心愿达成!……蝴蝶,别跑呀~"]),
}
HINT_LINES = ["……刚才的心愿,还算数哦。", "……还记得我的心愿吗?"]
MISS_LINES = ["……哼,算了,下次再说。", "心愿过期了……才、才没有很在意!", "没理我……那我自己想想就好啦。"]


def _test_sec():
    try:
        v = float(os.environ.get("VESNA_WISH_SEC", ""))
        if v > 0:
            return max(5.0, v)
    except ValueError:
        pass
    return None


def matches(kind, name, data):
    """事件 name/data 算不算满足了心愿 kind"""
    if kind == "pet":
        return name == "pet" and not data.get("sleeping") and not data.get("sulking")
    if kind in FOOD_TRAITS:
        return (name == "feed" and data.get("reaction") in ("fav", "like", "ok")
                and data.get("trait") in FOOD_TRAITS[kind])
    if kind == "rps":
        return name == "rps"
    if kind == "butterfly":
        return name == "butterfly" and data.get("stage") == "come" and not data.get("auto")
    return False


class Wish:
    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.test_sec = _test_sec()
        self.next_at = time.monotonic() + self._gap(first=True)
        self.cur = None            # 正在等的心愿: dict(kind, t0, hinted, next_fx, done)
        self.calm_since = None
        self.last_kind = None
        self.day, self.today = date.today().isoformat(), 0
        self._next_check = 0.0

    def _gap(self, first=False):
        if self.test_sec:
            return self.test_sec
        lo, hi = FIRST_MIN if first else EVERY_MIN
        return random.uniform(lo, hi) * 60.0

    def _above_head(self):
        p = self.pet
        hp = p.head_point()
        return QPointF(hp.x() - p.char_w * 0.26, hp.y() - 8)

    # ----- 每帧(实际每 0.5 秒看一次) -----
    def step(self, t):
        if t < self._next_check:
            return
        self._next_check = t + 0.5
        p = self.pet
        acts = p.activities()
        if p.can_auto("plugin_talk", acts):          # 安静待着、没在忙(规则在 main.AUTO)
            if self.calm_since is None:
                self.calm_since = t
        else:
            self.calm_since = None
        if self.cur is not None:
            self._wait(t, acts)
        elif t >= self.next_at and self.calm_since is not None and t - self.calm_since >= CALM_SEC:
            self._start(t)

    def _kinds(self):
        kinds = ["pet", "rps", "butterfly"]
        if self.pet.stats.hunger < FULL:
            kinds += list(FOOD_TRAITS)
        if self.last_kind in kinds:
            kinds.remove(self.last_kind)            # 不连着两次同一种
        return kinds

    def _start(self, t):
        p = self.pet
        if p.cfg["mute"] or p.bubble.isVisible():
            return
        today = date.today().isoformat()
        if today != self.day:
            self.day, self.today = today, 0
        if self.today >= DAILY_MAX:
            self.next_at = t + self._gap()
            return
        kind = random.choice(self._kinds())
        w = WISHES[kind]
        text = random.choice(w["ask"])
        self.cur = dict(kind=kind, t0=t, hinted=False, next_fx=t + REMIND_SEC, done=False)
        self.last_kind = kind
        self.today += 1
        p.set_state("shy", 2.4)
        p.burst("emoji", 1, at=self._above_head(), text=w["emoji"])
        p.say(text, duration=4.0, tone="info", src="wish")
        p.emit_event("wish", stage="start", kind=kind, text=text)

    def _end(self, t, stage):
        c, self.cur = self.cur, None
        self.next_at = t + self._gap()
        self.pet.emit_event("wish", stage=stage, kind=c["kind"])
        return c

    def _wait(self, t, acts):
        c = self.cur
        if c["done"]:
            return                                   # 已满足, 等 _fulfil 说谢谢
        p = self.pet
        if acts & CANCEL:
            self._end(t, "cancel")
            return
        free = p.can_auto("plugin_talk", acts) and not p.bubble.isVisible()
        el = t - c["t0"]
        if el >= ANSWER_SEC:
            self._end(t, "miss")
            p.stats.inc("wish_missed")
            if free:
                p.kick(-1.0)
                p.set_state("shy", 2.4, expr="pout")
                p.say(random.choice(MISS_LINES), duration=3.0, src="wish")
        elif not c["hinted"] and el >= ANSWER_SEC / 2 and free:
            c["hinted"] = True
            c["next_fx"] = t + REMIND_SEC
            p.burst("emoji", 1, at=self._above_head(), text=WISHES[c["kind"]]["emoji"])
            p.say(random.choice(HINT_LINES) + WISHES[c["kind"]]["hint"], duration=4.0, tone="info", src="wish")
        elif t >= c["next_fx"] and free:
            c["next_fx"] = t + REMIND_SEC
            p.burst("emoji", 1, at=self._above_head(), text=WISHES[c["kind"]]["emoji"])

    def status_text(self):
        """托盘提示 / 右键卡片状态行: 正在等的心愿和剩余时间"""
        c = self.cur
        if c is None or c["done"]:
            return None
        w = WISHES[c["kind"]]
        left = max(0, int(ANSWER_SEC - (time.monotonic() - c["t0"])))
        return f"{w['emoji']} 小心愿:{w['label']}(还剩 {left} 秒)"

    # ----- 事件 -----
    def on_event(self, name, data):
        c = self.cur
        if c is None or c["done"]:
            return
        if matches(c["kind"], name, data):
            c["done"] = True
            QTimer.singleShot(int(WISHES[c["kind"]]["delay"] * 1000), self._fulfil)
        elif c["kind"] == "butterfly" and name == "butterfly" and data.get("stage") == "come":
            self._end(time.monotonic(), "cancel")    # 蝴蝶自己飞来了: 不算你的, 这个心愿也不用了

    def _fulfil(self):
        if self.cur is None:
            return
        p = self.pet
        now = time.monotonic()
        kind, after = self.cur["kind"], round(now - self.cur["t0"], 1)
        self.cur = None
        self.next_at = now + self._gap()
        p.stats.inc("wish_done")
        got = p.gain(GAIN)
        p.emit_event("wish", stage="done", kind=kind, after=after, gain=got)
        if not p.isVisible() or p.state == "sleep" or p.sulking():
            return
        if p.state in CALM + ("eat", "love", "shy", "cheer", "wave") and not p.dragging and p.food_fx is None:
            p.set_state("love", 2.6)
        p.burst("heart", 6)
        p.burst("sparkle", 4)
        p.sfx.play("sparkle")
        p.say(random.choice(WISHES[kind]["done"]), force=True, duration=3.2, tone="happy", src="wish")


def create(pet, log_fn=None):
    return Wish(pet, log_fn)
