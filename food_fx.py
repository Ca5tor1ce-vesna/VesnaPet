# -*- coding: utf-8 -*-
"""吃后效果(白名单, 给食物包用): hyper 亢奋乱跑 / jitter 发抖 / hop 连跳 / sneeze 喷嚏 / stink 熏晕再生气 / babble 胡言乱语 / burp 打嗝 / fly 满屏乱飞 / shock 电击口香糖。

由 PetWindow._tick 每帧调用 step(t)。只用桌宠已有的公开动作(set_state / say / start_walk / do_jump / burst ...)。
睡着、被丢、被滚轮转、隐藏、(非 hyper 时)被拖 都会打断效果; 打断时不再说结束台词。
"""
import random
import time

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QBitmap, QColor, QPainter, QPixmap, QRegion


class FoodEffect:
    DEFAULT_FACE = {"hyper": "surprised", "jitter": "shy", "hop": "happy", "sneeze": "surprised", "stink": "dizzy", "babble": "dizzy", "burp": "shy", "fly": "surprised", "shock": "surprised"}

    def __init__(self, pet, food, log_fn=None):
        self.pet, self.food = pet, food
        self.eff = dict(food.get("effect") or {})
        self.kind = self.eff.get("type")
        self.face = self.eff.get("face") or self.DEFAULT_FACE.get(self.kind, "surprised")
        self.log = log_fn
        self.t0 = self.last = time.monotonic()
        self.run = 0.0                 # 已经「跑」过的时间(被拖住时不计)
        self.next_say = 0.0
        self.next_kick = 0.0
        self.stage = 0
        self.leg = 0
        self.active = False

    # ----- 工具 -----
    def _line(self, pool_key):
        pool = self.food.get(pool_key) or self.food.get("effect_lines") or self.food.get("lines") or ["……"]
        return self.pet.pick_line(pool)

    def _say(self, pool_key, dur=2.0, tone="alert"):
        self.pet.say(self._line(pool_key), force=True, duration=dur, tone=tone)

    def _burst(self, n=2):
        b = self.eff.get("burst")
        if b:
            hp = self.pet.head_point()
            self.pet.burst(b, n, at=QPointF(hp.x(), hp.y() - 8), bias=(0, 0) if b == "steam" else None)

    def _emit(self, name, **kw):
        self.pet.emit_event(name, key=self.food["key"], name=self.food["name"], effect=self.kind, **kw)

    # ----- 生命周期 -----
    def start(self):
        p = self.pet
        if p.state == "sleep" or p._dragging or p.fling is not None or not p.isVisible():
            return False
        now = time.monotonic()
        self.t0 = self.last = now
        self.active = True
        p.stop_walk()
        p._bchase = None
        if self.kind == "stink":
            sec = float(self.eff.get("sec", 2.4))
            p._dizzy_until = now + sec
            p._dizzy_fx = now + 0.2
            p._stagger_t = now + 0.3
            p.set_state("dizzy")
            p.burst("puff", 6, at=p.head_point(), bias=(0, 0))
        else:
            p.set_state(self.face)
        if self.kind == "burp":
            n = int(self.eff.get("n", 4))
            sec = float(self.eff.get("sec", 8.0))
            gap = (sec - 1.6) / n                  # 最后留 ~1.6 秒说收尾
            self._burps = sorted(0.6 + gap * i + random.uniform(0.0, gap * 0.6) for i in range(n))
        if self.kind == "fly":
            self._fly_start()
        if self.kind == "shock":
            if p._feeds:                           # 不是食物: 不计入「吃了几份」(FEED_MAX)
                p._feeds.pop()
            self._glow = _ShockFlash(self)
            hub = getattr(p, "_ix", None)
            if hub is not None and hasattr(hub, "plugins"):
                hub.plugins.append(self._glow)
        if self.kind == "babble":
            self._decks = {}
            self._dragged = False
            self._glow = _RainbowGlow(self)
            hub = getattr(p, "_ix", None)
            if hub is not None and hasattr(hub, "plugins"):
                hub.plugins.append(self._glow)
        self._burst(3)
        self._spark = 0.0
        self._say("effect_lines", 2.2)
        self.next_say = now + random.uniform(1.5, 2.5)
        self._emit("food_effect_start")
        return True

    def stop(self, why="done"):
        if not self.active:
            return
        self.active = False
        p = self.pet
        if p.food_fx is self:
            p.food_fx = None
        glow = getattr(self, "_glow", None)
        if glow is not None:
            self._glow = None
            hub = getattr(p, "_ix", None)
            if hub is not None and glow in getattr(hub, "plugins", ()):
                hub.plugins.remove(glow)
        try:
            if self.kind == "hyper" and p.walk is not None and p.walk.get("kind") == "hyper":
                p.stop_walk()
            if self.kind == "fly":
                self._fly_cleanup(why)
            if why == "done" and self.kind in ("fly", "shock"):
                pass                               # fly 的落地/晕/台词在 _step_fly 里做完了
            elif why == "done":
                if self.kind == "stink":       # 熏晕之后: 原来的「生气」
                    p._dizzy_until = 0.0
                    p.set_state("angry", 2.6)
                    p.sfx.play("hmph")
                    p.burst("anger", 2, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
                    self._say("effect_end_lines", 3.0)
                else:
                    p.set_state("idle")
                    p.burst("sweat", 2)
                    self._say("effect_end_lines", 3.0, tone=None)
            elif self.kind == "stink" and p.state == "dizzy" and not p._spin_overspin:
                p._dizzy_until = 0.0
        finally:
            self._emit("food_effect_end", why=why)

    def _interrupted(self):
        p = self.pet
        if p.state == "sleep" or not p.isVisible():
            return "sleep" if p.state == "sleep" else "hidden"
        if p.fling is not None or p._throw is not None:
            return "throw"
        if p._spin_live or p._spin_overspin:
            return "spin"
        if p._dragging and self.kind not in ("hyper", "babble", "burp", "shock"):
            return "drag"
        return None

    def step(self, t):
        if not self.active:
            return
        why = self._interrupted()
        if why:
            self.stop(why)
            return
        dt = max(0.0, min(0.1, t - self.last))
        self.last = t
        getattr(self, "_step_" + self.kind)(t, dt)

    # ----- 各效果 -----
    def _step_hyper(self, t, dt):
        p = self.pet
        if p._dragging:                          # 被拖住: 不计时, 继续嚷嚷
            if t >= self.next_say:
                self.next_say = t + random.uniform(1.5, 2.5)
                p.say(self._line("effect_drag_lines"), force=True, duration=1.8, tone="alert")
                p.kick(-1.2)
            return
        self.run += dt
        if self.run >= float(self.eff.get("sec", 12.0)):
            self.stop("done")
            return
        if p.edge:                               # 松手吸到墙边: 跳出来接着跑
            p.leave_peek()
            return
        if p.walk is None:
            self._new_leg()
        elif p.state != self.face and p.state not in ("angry", "surprised"):
            p.set_state(self.face)
        if t >= self.next_say:
            self.next_say = t + random.uniform(1.5, 2.5)
            p.say(self._line("effect_lines"), force=True, duration=1.8, tone="alert")
            self._burst(2)

    def _new_leg(self):
        p = self.pet
        vis = p._normal_visible_rect()
        g = p._screen_for_rect(vis).availableGeometry()
        lo = g.left() - p.pad_x + 10
        hi = g.left() + g.width() - p.width() + p.pad_x - 10
        if hi <= lo:
            return
        self.leg += 1
        # 左右来回: 交替往两边跑, 每段 35%–90% 屏宽
        span = (hi - lo) * random.uniform(0.35, 0.9)
        go_right = (self.leg % 2 == 1) if p.x() < (lo + hi) / 2 else (self.leg % 2 == 0)
        tx = p.x() + span if go_right else p.x() - span
        tx = max(lo, min(hi, tx))
        if abs(tx - p.x()) < 40:
            tx = lo if p.x() > (lo + hi) / 2 else hi
        speed = 70.0 * float(self.eff.get("speed", 3.5)) * random.uniform(0.9, 1.25)
        if p.start_walk(QPointF(tx, p.y()), kind="hyper", speed=speed):
            p.set_state(self.face)

    def _step_jitter(self, t, dt):
        p = self.pet
        if t - self.t0 >= float(self.eff.get("sec", 3.0)):
            self.stop("done")
            return
        if t >= self.next_kick:
            self.next_kick = t + 0.09
            p.kick(random.choice((-1, 1)) * random.uniform(1.0, 1.8))
            p.tilt += random.uniform(-4.0, 4.0)
        if t >= self.next_say:
            self.next_say = t + random.uniform(1.5, 2.5)
            p.say(self._line("effect_lines"), force=True, duration=1.8, tone="alert")
            self._burst(1)

    def _step_hop(self, t, dt):
        p = self.pet
        n = int(self.eff.get("n", 4))
        if self.stage >= n:
            if t >= self.next_kick + 0.5:
                self.stop("done")
            return
        if t >= self.next_kick and p._landed:
            self.next_kick = t + 0.48
            self.stage += 1
            p.do_jump(False)
            p.burst("star", 3, at=p.foot_point(), bias=(0, -40))
            self._burst(1)
            if self.stage in (2, n) or random.random() < 0.3:
                p.say(self._line("effect_lines"), force=True, duration=1.6, tone="alert")

    def _step_sneeze(self, t, dt):
        p = self.pet
        delay = float(self.eff.get("delay", 1.2))
        if self.stage == 0 and t - self.t0 >= delay:
            self.stage = 1
            self.next_kick = t
            p.kick(3.6)
            p.set_state("surprised")
            hp = p.head_point()
            p.burst("puff", 9, at=hp, bias=(0, 0))
            p.burst("drop", 2)
            p.sfx.play("huh")
            p.do_jump(False)
            p.say(self._line("effect_lines"), force=True, duration=2.0, tone="alert")
        elif self.stage == 1 and t - self.next_kick >= 1.8:
            self.stop("done")

    def _step_stink(self, t, dt):
        if t - self.t0 >= float(self.eff.get("sec", 2.4)):
            self.stop("done")
            return
        if t >= self.next_say:
            self.next_say = t + random.uniform(1.5, 2.5)
            self.pet.say(self._line("effect_lines"), force=True, duration=1.8, tone="alert")

    def _step_babble(self, t, dt):
        p = self.pet
        if t - self.t0 >= float(self.eff.get("sec", 15.0)):
            self.stop("done")
            return
        if p._dragging:
            # 被拖住: 计时照走; 压住原版「拖久了挣扎」(它按 _drag_hold_t0 计时), 免得挣扎台词/表情抢气泡
            if p._drag_hold_t0:
                p._drag_hold_t0 = t
            if not self._dragged:
                self._dragged = True
                self.next_say = min(self.next_say, t + 0.35)
        elif self._dragged:                        # 松手: 换回普通胡话
            self._dragged = False
            self.next_say = min(self.next_say, t + 0.6)
        if p.state != self.face:                   # 拖拽开始会换成惊讶脸: 拉回晕乎乎的脸
            p.set_state(self.face)
        if t >= self.next_kick:                    # 轻微晃一下
            self.next_kick = t + random.uniform(0.7, 1.2)
            p.tilt += random.uniform(-3.0, 3.0)
        if t >= self.next_say:
            self.next_say = t + random.uniform(1.5, 2.5)
            name = "effect_drag_lines" if p._dragging else "effect_lines"
            deck = self._decks.setdefault(name, [])
            if not deck:                           # 洗牌抽, 一轮内不重复
                pool = self.food.get(name) or self.food.get("effect_lines") or ["……"]
                deck[:] = random.sample(pool, len(pool))
            p.say(deck.pop(), force=True, duration=1.9, tone="normal")
            if random.random() < 0.5:
                self._burst(1)


class _RainbowGlow:
    """babble 期间临时挂到 pet._ix 的画图钩子: 立绘慢慢换色泛光(淡)。效果结束就摘掉。"""
    HUES = 12

    def __init__(self, fx):
        self.fx = fx
        self._cache = {}

    def paint(self, key, pm, t):
        if not self.fx.active:
            return None
        i = int(t * 2.0) % self.HUES                  # 约 6 秒转一圈色相
        ck = (pm.cacheKey(), i)
        out = self._cache.get(ck)
        if out is None:
            if len(self._cache) > 48:
                self._cache.clear()
            out = QPixmap(pm)
            q = QPainter(out)
            mask = QBitmap.fromImage(pm.toImage().createAlphaMask(Qt.ThresholdAlphaDither))
            q.setClipRegion(QRegion(mask))
            q.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            q.fillRect(out.rect(), QColor.fromHsv(int(360 * i / self.HUES) % 360, 170, 255, 46))
            q.end()
            out.setDevicePixelRatio(pm.devicePixelRatio())
            self._cache[ck] = out
        return out, 0.0


# ----- burp / fly (挂在 FoodEffect 上) -----
def _step_burp(self, t, dt):
    p = self.pet
    el = t - self.t0
    if el >= float(self.eff.get("sec", 8.0)):
        self.stop("done")
        return
    if self._burps and el >= self._burps[0]:
        self._burps.pop(0)
        self.stage += 1
        hp = p.head_point()
        mouth = QPointF(hp.x() + p.char_w * 0.04, hp.y() + p.char_h * 0.14)
        if not p._dragging and p._landed and random.random() < 0.45:
            p.do_jump(False)                      # 嗝得跳一下
        p.kick(2.6)                               # 身体一顿
        p.tilt += random.uniform(-3.0, 3.0)
        p.burst("ring", 1, at=mouth)
        p.burst("puff", 2, at=mouth, bias=(0, -60))
        self._burst(1)
        if not p._dragging:
            p.set_state(self.face, 0.9)
        p.say(self._line("effect_lines"), force=True, duration=1.5, tone="alert")


def _fly_start(self):
    p = self.pet
    if p.edge:
        p.leave_peek()
    p.stop_walk()
    self._home = QPointF(p.pos())
    vis = p._normal_visible_rect()
    self._screen = p._screen_for_rect(vis)
    ang = random.uniform(0, 6.283)
    sp = 1500.0 * float(self.eff.get("speed", 1.0))
    import math
    self._v = [sp * math.cos(ang), -abs(sp * math.sin(ang)) - 400]
    self._pos = QPointF(p.pos())
    self._land = None                             # 落回原位阶段: (t0, from)
    self._trail = 0.0
    self._spun = False


def _fly_bounds(self):
    p = self.pet
    g = self._screen.availableGeometry()
    vis = p._normal_visible_rect(QPoint(0, 0))     # 窗口左上 -> 立绘可见区的偏移
    ox, oy = vis.left(), vis.top()
    return (g.left() - ox, g.top() - oy, g.left() + g.width() - ox - vis.width(),
            g.top() + g.height() - oy - vis.height())


def _step_fly(self, t, dt):
    import math
    p = self.pet
    sec = float(self.eff.get("sec", 10.0))
    if self._land is None and t - self.t0 >= sec:
        self._land = (t, QPointF(self._pos))
        p.tilt = 0.0
    if self._land is not None:                    # 0.7 秒滑回原位, 然后晕一下
        u = min(1.0, (t - self._land[0]) / 0.7)
        e = 1 - (1 - u) ** 3
        a, b = self._land[1], self._home
        self._pos = QPointF(a.x() + (b.x() - a.x()) * e, a.y() + (b.y() - a.y()) * e)
        p.move(int(self._pos.x()), int(self._pos.y()))
        if u >= 1.0:
            p.kick(-3.0)
            p.burst("dust", 5, at=p.foot_point(), bias=(0, 0))
            p.burst("star", 4)
            now = time.monotonic()
            p._dizzy_until = now + 2.2
            p._dizzy_fx = now
            p._stagger_t = now + 0.3
            p.set_state("dizzy", 2.4)
            self._say("effect_end_lines", 3.0, tone=None)
            self.stop("done")
        return
    l, tp, r, b = _fly_bounds(self)
    x, y = self._pos.x() + self._v[0] * dt, self._pos.y() + self._v[1] * dt
    bounced = False
    if x < l:
        x, self._v[0], bounced = l, abs(self._v[0]), True
    elif x > r:
        x, self._v[0], bounced = r, -abs(self._v[0]), True
    if y < tp:
        y, self._v[1], bounced = tp, abs(self._v[1]), True
    elif y > b:
        y, self._v[1], bounced = b, -abs(self._v[1]), True
    # 乱飞: 速度方向一直随机拐, 速率保持
    sp = math.hypot(*self._v) or 1.0
    want = 1500.0 * float(self.eff.get("speed", 1.0))
    ang = math.atan2(self._v[1], self._v[0]) + random.uniform(-2.5, 2.5) * dt
    self._v = [math.cos(ang) * want, math.sin(ang) * want]
    self._pos = QPointF(x, y)
    p.move(int(x), int(y))
    p.tilt = max(-12.0, min(12.0, self._v[0] / want * 12.0))      # 朝飞行方向倾斜
    if bounced:
        p.kick(-2.4)
        p.burst("star", 3, at=p.head_point(), bias=(0, 0))
        if not self._spun or random.random() < 0.4:
            self._spun = True
            p.spin_rem = max(p.spin_rem, 360)      # 撞边转一圈
    if t >= self._trail:                           # 彩色拖尾(粒子留在原地慢慢散)
        self._trail = t + 0.05
        c = QPointF(p._normal_visible_rect().center())
        p.burst("confetti" if random.random() < 0.5 else "sparkle", 2, at=c, bias=(-self._v[0] * 0.15, -self._v[1] * 0.15))
    if p.state != self.face and p.state != "angry":
        p.set_state(self.face)
    if t >= self.next_say:
        self.next_say = t + random.uniform(1.3, 2.0)
        p.say(self._line("effect_lines"), force=True, duration=1.6, tone="alert")


def _fly_cleanup(self, why):
    p = self.pet
    p.tilt = 0.0
    if why == "drag":                             # 被鼠标接住: 效果结束, 之后照原版拖/放/丢
        p.say(self._line("effect_caught_lines") if self.food.get("effect_caught_lines") else "呜…被、被接住了…才不是谢谢你!",
              force=True, duration=2.4, tone="alert")


FoodEffect._step_burp = _step_burp
FoodEffect._fly_start = _fly_start
FoodEffect._step_fly = _step_fly
FoodEffect._fly_cleanup = _fly_cleanup


def _step_shock(self, t, dt):
    p = self.pet
    el = t - self.t0
    sec = float(self.eff.get("sec", 2.5))
    if el >= sec:
        p.set_state("angry", 3.0)                  # 电完: 生气
        p.sfx.play("hmph")
        p.burst("anger", 2, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
        p.burst("steam", 3, at=p.head_point(), bias=(0, 0))
        self._say("effect_end_lines", 3.0)
        self.stop("done")
        return
    if self.stage == 0:                            # 一下电到: 全身一抖
        self.stage = 1
        p.kick(4.0)
        if not p._dragging and p._landed:
            p.do_jump(False)
        p.set_state("surprised")
    if t >= self.next_kick:                        # 高频抖动
        self.next_kick = t + 0.05
        p.kick(random.choice((-1, 1)) * random.uniform(1.4, 2.4))
        p.tilt += random.uniform(-6.0, 6.0)
    if t >= self._spark:
        self._spark = t + 0.18
        c = QPointF(p._normal_visible_rect().center()) if not p.edge else p.head_point()
        p.burst("star", 2, at=c + QPointF(random.uniform(-40, 40), random.uniform(-50, 30)), bias=(0, 0))
        if random.random() < 0.5:
            p.burst("sparkle", 3, at=c, bias=(0, 0))
    if el >= sec * 0.55 and p.state != "angry" and not p._dragging:
        p.set_state("angry")                       # 后半段炸毛


class _ShockFlash:
    """shock 期间临时挂到 pet._ix 的画图钩子: 专用立绘(有图时) + 白/黄闪烁 + 水平抖。
    立绘: <桌宠目录>/dlc/interactions/shocked.png, 备用 dlc/foods/sprites/shocked.png (512x512, 与其他立绘对齐); 每次触发重新检查, 缺图用当前脸。"""
    def __init__(self, fx):
        self.fx = fx
        self._cache = {}
        self._img = None
        try:
            import food_packs
            root = food_packs.pet_dir() / "dlc"
            for f in (root / "interactions" / "shocked.png", root / "foods" / "sprites" / "shocked.png"):
                if f.is_file():
                    pm = QPixmap(str(f))
                    if not pm.isNull():
                        self._img = pm
                        break
        except Exception:
            self._img = None

    def paint(self, key, pm, t):
        if not self.fx.active:
            return None
        el = t - self.fx.t0
        ph = int(el * 14) % 3                      # 0 白 1 黄 2 原色
        dx = random.uniform(-3.5, 3.5)
        if self._img is not None:                  # 专用立绘: 缩到和当前立绘一样大
            sk = ("img", pm.width(), pm.height(), pm.devicePixelRatio())
            base = self._cache.get(sk)
            if base is None:
                base = self._img.scaled(pm.width(), pm.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                base.setDevicePixelRatio(pm.devicePixelRatio())
                self._cache[sk] = base
            pm = base
        if ph == 2:
            return pm, dx
        ck = (pm.cacheKey(), ph)
        out = self._cache.get(ck)
        if out is None:
            if len(self._cache) > 24:
                self._cache = {k: v for k, v in self._cache.items() if k[0] == "img"}
            out = QPixmap(pm)
            q = QPainter(out)
            mask = QBitmap.fromImage(pm.toImage().createAlphaMask(Qt.ThresholdAlphaDither))
            q.setClipRegion(QRegion(mask))
            q.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            q.fillRect(out.rect(), QColor(255, 255, 255, 150) if ph == 0 else QColor(255, 225, 60, 130))
            q.end()
            out.setDevicePixelRatio(pm.devicePixelRatio())
            self._cache[ck] = out
        return out, dx


FoodEffect._step_shock = _step_shock
