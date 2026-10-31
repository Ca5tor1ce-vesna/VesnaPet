# -*- coding: utf-8 -*-
"""互动 DLC「浇水」: 右键菜单 / 托盘「互动」多一个「💧 浇水」。
- 头顶上方冒出水壶, 往下浇约 1 秒(现有 sweat/drop 粒子)。
- 醒着且不忙: 往左/右快速闪开, 水落空; 冒一句台词。不扣好感, 冷却 5 秒。
- 睡着: 浇个正着, 水花 + 一抖, 醒来生气(原版 angry 表情, comfort 插件可以哄), 好感 -1。
- 忙(被拖/被丢/吃后效果/吐/达妮卡/探头/转圈): 只冒一句「现在不行!」。
「强行浇水」: 左键拖着她时按右键(或滚轮按下) -> 躲不开, 浇 1.5 秒, 她拼命挣扎(原版挣扎抖动, 台词换成浇水的);
  松手后「究极生气」45 秒: 生气脸 + 红色泛光 + 怒气粒子, 偶尔跺脚, 一连串台词, 好感 -3;
  期间摸头被拍开(不加好感, 也挡住 comfort 插件), 连续摸 5 次才哄好(+2)。3 分钟内不能再强行浇。
  期间戳她(单击/双击)不走原版的「别戳啦」: 第 1 下瞪你, 第 2 下扭头不理, 3–4 下警告, 第 5 下起跺脚朝你吹风(4 秒一次);
  每戳一下多气 4 秒(剩余最多回到 45 秒); 摸到一半又戳 = 前功尽弃, 摸头次数清零。推 "rage_poke"。
  拖着时的右键菜单被拦下(只拦拖着的时候)。
台词来源标 src="water", 语音插件不会播。推 "watered"(dodged, asleep, forced)。
"""
import random
import time

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBitmap, QColor, QCursor, QPainter, QPixmap, QRegion

COOLDOWN = 5.0
POUR = 1.0
DODGE_LINES = ["想浇我?没门!", "哼,我又不是花!", "差点就…才没有差点!", "风仙的速度可不是盖的~", "浇不到~浇不到~",
               "你当我是蒙德的风车菊吗!", "嘿,往哪儿浇呢?"]
WET_LINES = ["呜哇!!谁、谁浇的水!", "我的头发…你给我等着!", "冷冷冷!!翅膀全湿了!", "呜…好梦全泡汤了…你赔我!"]
BUSY_LINES = ["现在不行!", "等、等一下啦!"]
FORCE_SEC = 1.5
FORCE_COOLDOWN = 180.0
RAGE_SEC = 45.0
RAGE_PETS = 5
FORCE_LINES = ["放、放开我!!", "住手——!!", "咕噜噜…呸!别浇了!", "呜哇啊——翅膀进水了!!"]
RAGE_LINES = ["你完了!!", "我要告诉达妮卡!", "头发全湿了…绝对不原谅你!", "哼!!记大过!记十个大过!",
              "这笔账我会用风元素慢慢算!", "不许看我!我现在超级生气!", "呜…发型全毁了…都怪你!"]
SLAP_LINES = ["别碰我!", "走开!", "哼!别想摸摸头就混过去!", "手拿开!"]
CALM_LINE = "…就、就这一次!下次绝对不饶你!"
AGAIN_LINES = ["你还想来?!", "想都别想!!"]
NOSPIN_LINES = ["别想转我！"]
NOSPIN_GAP = 4.0
POKE_ADD = 4.0                 # 究极生气时每戳一下多气几秒(剩余最多回到 RAGE_SEC)
POKE_BLOW_AT = 5               # 戳到第几下起会还手(跺脚 + 朝你吹风)
POKE_BLOW_GAP = 4.0            # 还手最短间隔
POKE_SAY_GAP = 1.0             # 连戳时台词最短间隔(太快的只有动作)
POKE_LINES = ["还戳?!我现在超级生气!", "戳什么戳!头发还湿着呢!", "别碰我!水还在往下滴!", "哼!戳一下记一笔!"]
POKE_TURN_LINES = ["哼!(扭头)", "不看你!不看你!", "……(背过身去)"]
POKE_WARN_LINES = ["你是嫌我还不够生气吗?!", "再戳……再戳我就真的吹飞你!", "小本本已经写不下了!!", "我数到三……一!二!"]
POKE_BLOW_LINES = ["风元素——看招!!", "说了别戳!吹飞你!", "呼——!给我离远点!", "这是你自找的!"]
POKE_UNDO_LINES = ["刚有一点点消气……你又戳!", "前功尽弃!重新哄!", "哼,刚才摸的都不算了!"]
BUSY = {"drag", "fling", "throw", "food_fx", "edge", "spin", "danika", "vomit"}   # 这些时候浇不了


class Water:
    priority = 10                  # 究极生气时先于 comfort 接管摸头

    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.cool_until = 0.0
        self.job = None            # dict(kind, t0, spout(QPointF), ...)
        self.force = None          # 强行浇水进行中: dict(t0, next, say)
        self.force_cool = 0.0
        self.rage_pending = False
        self.rage = None           # 究极生气: dict(t0, next_fx, next_say, next_stomp, pets, pokes, ...)
        self._glow_cache = {}
        self.nospin_next = 0.0

    def expr(self, key, state):
        """被浇 / 超级生气这段时间, 生气的脸换成湿漉漉那张(assets 里没有 wet.png 就照常)"""
        if (self.rage is not None or self.force is not None) and state == "angry":
            return "wet"
        return None

    def state_text(self):
        """小屋头部那句话"""
        if self.force is not None:
            return "被迫洗了个澡……抗议无效"
        if self.rage is not None or self.rage_pending:
            return "头发还在滴水,火气倒是很旺"
        return None

    def busy(self):
        if self.force is not None:
            return "water_force"
        if self.rage is not None or self.rage_pending:
            return "rage"
        return "water" if self.job is not None else None

    # ----- 强行浇水 -----
    def on_mouse_press(self, e):
        p = self.pet
        if not p.dragging or e.button() not in (Qt.RightButton, Qt.MiddleButton):
            return False
        now = time.monotonic()
        if self.force is not None:
            return True
        if now < self.force_cool:
            self._say(AGAIN_LINES, 2.0)
            return True
        self.force_cool = now + FORCE_COOLDOWN
        self.job = None
        hp = p.head_point()
        p.burst("emoji", 1, at=QPointF(hp.x() + 30, hp.y() - p.char_h * 0.35), bias=(0, 0), text="🚿")
        p.sfx.play("whoosh")
        self.force = dict(t0=now, next=now, say=now + 0.15)
        p.gain(-3, quiet=True)
        p.emit_event("watered", dodged=False, asleep=p.state == "sleep", forced=True)
        p.set_state("angry", why="water")
        return True

    def on_context_menu(self, e):
        return bool(self.pet.dragging or self.force is not None)     # 拖着时不弹菜单

    def _step_force(self, t):
        p = self.pet
        f = self.force
        el = t - f["t0"]
        if el < FORCE_SEC and p.dragging:
            p.force_struggle(3, since=f["t0"])     # 原版「激烈挣扎」的抖法, 只抖不说话
            if t >= f["next"]:
                f["next"] = t + 0.04
                hp = p.head_point()
                p.burst("sweat", 4, at=QPointF(hp.x() + random.uniform(-20, 20), hp.y() - 30), bias=(0, 0))
                if random.random() < 0.35:
                    p.burst("drop", 2, at=hp, bias=(0, 0))
                    p.burst("puff", 2, at=hp, bias=(0, 0))
            if t >= f["say"]:
                f["say"] = t + 0.75
                self._say(FORCE_LINES, 0.9)
            if p.state != "angry":
                p.set_state("angry")
            return
        # 浇完(或提前松手)
        p.force_struggle(0, since=t)               # 回到刚拿起: 原版挣扎重新计时(没在拖则无事)
        self.force = None
        self.rage_pending = True

    # ----- 究极生气 -----
    def _start_rage(self, t):
        p = self.pet
        self.rage_pending = False
        self.rage = dict(t0=t, next_fx=t, next_say=t + 0.2, next_stomp=t + 2.0, pets=0,
                         pokes=0, poke_say=0.0, next_blow=0.0, turn_until=0.0)
        p.set_state("angry")
        p.sfx.play("hmph")
        p.burst("anger", 3, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
        p.burst("steam", 6, at=p.head_point(), bias=(0, 0))

    def _step_rage(self, t):
        p = self.pet
        r = self.rage
        if t - r["t0"] >= RAGE_SEC:
            self.rage = None
            if p.state == "angry" and not p.dragging:
                p.set_state("idle")
                p.burst("sweat", 1)
            return
        if p.dragging or p.fling is not None:
            return
        if p.state not in ("angry", "sleep") and t >= r["turn_until"]:     # 扭头那一下不拉回来
            p.set_state("angry")
        if t >= r["next_fx"]:
            r["next_fx"] = t + random.uniform(1.2, 2.0)
            p.burst("anger", 1, at=p.head_point() + QPointF(p.char_w * random.uniform(0.15, 0.3), -10))
            if random.random() < 0.4:
                p.burst("steam", 3, at=p.head_point(), bias=(0, 0))
        if t >= r["next_stomp"]:
            r["next_stomp"] = t + random.uniform(4.0, 7.0)
            if p.landed and not p.edge:
                p.do_jump(False)
                p.burst("dust", 4, at=p.foot_point(), bias=(0, 0))
            else:
                p.kick(-2.0)
        if t >= r["next_say"]:
            r["next_say"] = t + random.uniform(3.5, 5.5)
            self._say(RAGE_LINES, 3.0)

    def on_click(self, double):
        """究极生气中被戳: 不走原版「别戳啦」。越戳越气, 摸到一半又戳就前功尽弃, 戳多了会还手。"""
        r = self.rage
        if r is None:
            return False
        p = self.pet
        now = time.monotonic()
        r["pokes"] += 1
        r["t0"] = min(now, r["t0"] + POKE_ADD)          # 多气几秒, 剩余不超过 RAGE_SEC
        r["next_say"] = max(r["next_say"], now + 3.0)   # 自言自语往后推, 别和回嘴叠在一起
        n, undo, blew = r["pokes"], r["pets"] > 0, False
        talk = now >= r["poke_say"]
        if undo:                                        # 哄到一半又戳
            r["pets"] = 0
            self._glare(r, hard=True)
            pool = POKE_UNDO_LINES
            talk = True
        elif n >= POKE_BLOW_AT and now >= r["next_blow"]:
            r["next_blow"] = now + POKE_BLOW_GAP
            blew = True
            self._glare(r, hard=True)
            if p.landed and not p.edge:
                p.do_jump(False)
            p.blow_at_cursor()
            pool = POKE_BLOW_LINES
            talk = True
        elif n == 2:
            self._turn_away(r, now)
            pool = POKE_TURN_LINES
        else:
            self._glare(r, hard=n >= 3)
            pool = POKE_WARN_LINES if n >= 3 else POKE_LINES
        if talk:
            r["poke_say"] = now + POKE_SAY_GAP
            self._say(pool, 2.4)
        p.emit_event("rage_poke", pokes=n, double=bool(double), undo=undo, blew=blew)
        return True

    def _glare(self, r, hard=False):
        """猛地转回来瞪你"""
        p = self.pet
        r["turn_until"] = 0.0
        if p.state != "angry":
            p.set_state("angry")
        p.kick(-2.4 if hard else -1.6)
        p.burst("anger", 2 if hard else 1, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
        if hard:
            p.burst("steam", 3, at=p.head_point(), bias=(0, 0))
        p.sfx.play("hmph")

    def _turn_away(self, r, now):
        """扭头背对鼠标, 1.2 秒后再转回来生气"""
        p = self.pet
        cx = QCursor.pos().x() - (p.x() + p.width() / 2)
        r["turn_until"] = now + 1.2
        p.set_state("look_left" if cx > 0 else "look", 1.2)
        p.kick(-1.0)
        p.burst("anger", 1, at=p.head_point() + QPointF(p.char_w * 0.25, -10))

    def on_wheel(self, e):
        """究极生气中(含刚松手待发作)不许转圈: 吃掉滚轮, 不转不攒晕度; 偶尔顶一句。"""
        if self.rage is None and not self.rage_pending:
            return False
        p = self.pet
        p.spin_rem = 0.0
        p.spin_angle = 0.0
        now = time.monotonic()
        if now >= self.nospin_next:
            self.nospin_next = now + NOSPIN_GAP
            p.kick(-1.6)
            p.burst("anger", 1, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
            self._say(NOSPIN_LINES, 1.8)
        return True

    def on_pet(self):
        if self.rage is None and self.force is None and not self.rage_pending:
            return False
        p = self.pet
        if self.rage is None:
            return True
        r = self.rage
        r["pets"] += 1
        if r["pets"] >= RAGE_PETS:
            self.rage = None
            p.set_state("shy", 3.0)
            p.burst("heart", 3)
            p.gain(2, quiet=True)
            p.say(CALM_LINE, force=True, duration=3.4, tone="happy", src="water")
            p.emit_event("comforted", was_sulking=False, after=round(time.monotonic() - r["t0"], 1), gain=2,
                         rage=True)
            return True
        p.kick(-2.2)                               # 拍开你的手
        p.burst("anger", 1, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
        p.sfx.play("hmph")
        self._say(SLAP_LINES, 1.8)
        return True

    def paint(self, key, pm, t):
        if self.rage is None and self.force is None:
            return None
        a = 60 + int(30 * abs(__import__("math").sin(t * 3)))
        a = a // 10 * 10
        ck = (pm.cacheKey(), a)
        out = self._glow_cache.get(ck)
        if out is None:
            if len(self._glow_cache) > 24:
                self._glow_cache.clear()
            out = QPixmap(pm)
            q = QPainter(out)
            mask = QBitmap.fromImage(pm.toImage().createAlphaMask(Qt.ThresholdAlphaDither))
            q.setClipRegion(QRegion(mask))
            q.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            q.fillRect(out.rect(), QColor(235, 40, 40, a))
            q.end()
            out.setDevicePixelRatio(pm.devicePixelRatio())
            self._glow_cache[ck] = out
        dx = random.uniform(-1.5, 1.5) if self.force is not None else 0.0
        return out, dx

    def menu_items(self):
        return [("💧", "浇水", self.water)]

    # ----- 判断 -----
    def _busy(self):
        return bool(self.pet.activities() & BUSY)

    def _say(self, pool, dur=2.6, tone="alert"):
        self.pet.say(self.pet.pick_line(pool), force=True, duration=dur, tone=tone, src="water")

    # ----- 入口 -----
    def water(self):
        p = self.pet
        now = time.monotonic()
        if self.job is not None or now < self.cool_until or not p.isVisible():
            return
        if self.rage is not None or self.force is not None:
            self._say(SLAP_LINES, 1.8)
            return
        p.note_interaction()
        if self._busy():
            self._say(BUSY_LINES, 1.8)
            return
        asleep = p.state == "sleep"
        p.stop_walk()
        hp = p.head_point()
        spout = QPointF(hp.x() + p.char_w * 0.12, hp.y() - p.char_h * 0.32)
        p.burst("emoji", 1, at=QPointF(spout.x() + 14, spout.y() - 6), bias=(0, 0), text="🚿")
        self.job = dict(asleep=asleep, t0=now, spout=spout, next=now, moved=False)
        self.cool_until = now + COOLDOWN
        if not asleep:                                # 醒着: 稍等一下就闪开
            self.job["dodge_at"] = now + 0.18
        p.sfx.play("whoosh")

    # ----- 每帧 -----
    def step(self, t):
        if self.force is not None:
            self._step_force(t)
        if self.rage_pending and not self.pet.dragging and self.pet.fling is None:
            self._start_rage(t)
        if self.rage is not None:
            self._step_rage(t)
        j = self.job
        if j is None:
            return
        p = self.pet
        el = t - j["t0"]
        if el < POUR and t >= j["next"]:              # 水流
            j["next"] = t + 0.05
            s = j["spout"]
            p.burst("sweat", 2, at=QPointF(s.x() + random.uniform(-6, 6), s.y()), bias=(0, 0))
        if not j["asleep"]:
            if not j["moved"] and t >= j["dodge_at"]:
                j["moved"] = True
                if p.dragging or p.fling is not None:           # 这时被抓/被丢: 算了
                    self.job = None
                    return
                self._start_dodge()
            if j.get("dodge"):
                self._step_dodge(t)
            if el >= POUR + 0.1 and not j.get("dodge"):
                self.job = None
        else:
            if el >= 0.45 and not j.get("hit"):
                j["hit"] = True
                self._hit()
            if el >= POUR + 0.1:
                self.job = None

    def _start_dodge(self):
        p = self.pet
        g = p.screen_rect()
        dist = p.char_w * random.uniform(1.1, 1.5)
        lo = g.left() - p.pad_x + 4
        hi = g.left() + g.width() - p.width() + p.pad_x - 4
        side = random.choice((-1, 1))
        if p.x() + side * dist < lo or p.x() + side * dist > hi:
            side = -side
        tx = max(lo, min(hi, p.x() + side * dist))
        self.job["dodge"] = dict(t0=time.monotonic(), x0=p.x(), tx=tx, y=p.y())
        p.set_state("surprised", 1.0)
        p.kick(2.4)
        p.burst("dust", 4, at=p.foot_point(), bias=(0, 0))

    def _step_dodge(self, t):
        p = self.pet
        d = self.job["dodge"]
        if p.dragging or p.fling is not None:
            self.job = None
            return
        u = min(1.0, (t - d["t0"]) / 0.22)
        e = 1 - (1 - u) ** 3
        p.move(int(d["x0"] + (d["tx"] - d["x0"]) * e), int(d["y"]))
        p.tilt = 8.0 * (1 if d["tx"] > d["x0"] else -1) * (1 - u)
        if u >= 1.0 and not d.get("done"):
            d["done"] = True
            p.set_state("happy", 1.6)
            p.burst("sparkle", 3)
            self._say(DODGE_LINES, 2.6, tone="normal")
            p.emit_event("watered", dodged=True, asleep=False)
            j = self.job
            if time.monotonic() - j["t0"] >= POUR:
                self.job = None
            else:
                j["dodge"] = None

    def _hit(self):
        p = self.pet
        hp = p.head_point()
        p.burst("sweat", 8, at=hp, bias=(0, 0))       # 水花
        p.burst("drop", 3, at=hp, bias=(0, 0))
        p.burst("puff", 3, at=hp, bias=(0, 0))
        p.set_state("surprised", 0.5, why="water")
        p.kick(4.0)
        p.tilt += random.choice((-1, 1)) * 6
        p.gain(-1, quiet=True)

        def angry():
            if p.state == "sleep" or p.dragging or p.fling is not None:
                return
            p.set_state("angry", 3.0, expr="wet")
            p.sfx.play("hmph")
            p.burst("anger", 2, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
            self._say(WET_LINES, 3.0)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, angry)
        p.emit_event("watered", dodged=False, asleep=True)


def create(pet, log_fn=None):
    return Water(pet, log_fn)
