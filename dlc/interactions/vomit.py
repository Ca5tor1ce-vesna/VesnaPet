# -*- coding: utf-8 -*-
"""互动 DLC: 转圈转到最晕(转太多 -> 晕完)时, 先干呕再吐, 约 3.6 秒。
吐完: 饱食度 -20(最低 0), 好感 -1, 推 "vomit" 事件; 之后 60 秒内再转只晕不吐(走原版生气逻辑)。
图: 同目录 vomit_pre.png / vomit.png (每次触发时重新检查, 放进来就能用); 缺图 -> 晕眩立绘泛绿 + 抖动。
地上不留任何东西(只有短暂粒子)。
"""
import math
import random
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBitmap, QColor, QPainter, QPixmap, QRegion

HERE = Path(__file__).resolve().parent
PRE_SEC = 1.4          # 干呕前摇
VOMIT_SEC = 2.2        # 吐
COOLDOWN = 60.0        # 吐完这么久内只晕不吐
HUNGER_DROP = 20.0
PRE_LINES = ["呕……等、等一下……", "唔……胃、胃里……", "别看我……呕……"]
VOMIT_LINES = ["呜…都怪你…", "笨蛋!都说了别转了!", "我、我才没有吐……是你看错了!", "哼…这笔账记下了…",
               "呜呜…早饭全没了…", "下次再转我就咬你!"]
END_LINES = ["……不理你了。", "哼!赔我零食!", "头还在转……都怪你啦。"]


class VomitFx:
    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.active = False
        self.t0 = 0.0
        self.stage = 0           # 0 前摇 1 吐
        self.cool_until = 0.0
        self.penalized = False
        self.next_say = 0.0
        self.next_fx = 0.0
        self.said = 0
        self._img = {}           # name -> QPixmap | None
        self._cache = {}

    # ---- 图 ----
    def _load_imgs(self):
        self._img.clear(); self._cache.clear()
        for n in ("vomit_pre", "vomit"):
            f = HERE / (n + ".png")
            pm = QPixmap(str(f)) if f.is_file() else QPixmap()
            self._img[n] = None if pm.isNull() else pm

    def _sized(self, name, ref):
        src = self._img.get(name)
        if src is None:
            return None
        ck = (name, ref.width(), ref.height(), ref.devicePixelRatio())
        pm = self._cache.get(ck)
        if pm is None:
            pm = src.scaled(ref.width(), ref.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pm.setDevicePixelRatio(ref.devicePixelRatio())
            self._cache[ck] = pm
        return pm

    def _green(self, ref, a):
        ck = ("green", ref.cacheKey(), a)
        pm = self._cache.get(ck)
        if pm is None:
            pm = QPixmap(ref)
            p = QPainter(pm)
            # 只给不透明部分上色(立绘边缘的半透明光晕不染, 免得出现绿框)
            mask = QBitmap.fromImage(ref.toImage().createAlphaMask(Qt.ThresholdAlphaDither))
            p.setClipRegion(QRegion(mask))
            p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            p.fillRect(pm.rect(), QColor(90, 200, 70, a))
            p.end()
            pm.setDevicePixelRatio(ref.devicePixelRatio())
            self._cache[ck] = pm
        return pm

    # ---- 钩子 ----
    def busy(self):
        return "vomit" if self.active else None

    def state_text(self):
        """小屋头部那句话"""
        if not self.active:
            return None
        return "脸色发青,胃在翻跟头……" if self.stage == 0 else "……这一幕请你忘掉"

    def on_spin_queasy(self, now):
        p = self.pet
        if self.active or now < self.cool_until:
            return False
        if p.state == "sleep" or p.dragging or p.fling or not p.isVisible():
            return False
        self._load_imgs()
        self.active, self.t0, self.stage, self.penalized, self.said = True, now, 0, False, 0
        # 接管原版的转圈收尾: 不再走「晕完生气」, 吐的过程中滚轮被拦住
        p.take_over_spin(PRE_SEC + VOMIT_SEC + 0.2, PRE_SEC + VOMIT_SEC + 15.0, now)
        try:
            p.stop_walk()
        except Exception:
            pass
        if p.state != "dizzy":
            p.set_state("dizzy")
        p.kick(-1.4)
        p.burst("sweat", 2)
        p.say(random.choice(PRE_LINES), force=True, duration=1.4, tone="alert")
        self.next_say = now + PRE_SEC + 0.15
        self.next_fx = now + 0.3
        return True

    def step(self, t):
        if not self.active:
            return
        p = self.pet
        el = t - self.t0
        if p.dragging or p.fling or p.state == "sleep" or not p.isVisible():
            self._finish(t, interrupted=True)
            return
        if p.state != "dizzy":
            p.set_state("dizzy")
        if self.stage == 0 and el >= PRE_SEC:
            self.stage = 1
            self._penalize()
            p.kick(-2.2)
            p.sfx.play("hmph")
        if t >= self.next_fx:
            hp = p.head_point()
            mouth = QPointF(hp.x() + p.char_w * 0.06, hp.y() + p.char_h * 0.12)
            if self.stage == 0:
                self.next_fx = t + 0.45
                p.kick(-1.0)
                p.burst("sweat", 1)
            else:
                self.next_fx = t + 0.3
                p.kick(-0.8)
                p.burst("drop", 2, at=mouth)
        if self.stage == 1 and t >= self.next_say and self.said < 2:
            self.said += 1
            self.next_say = t + 1.1
            p.say(p.pick_line(VOMIT_LINES), force=True, duration=1.3, tone="alert")
        if el >= PRE_SEC + VOMIT_SEC:
            self._finish(t)

    def paint(self, key, pm, t):
        if not self.active:
            return None
        el = t - self.t0
        name = "vomit_pre" if self.stage == 0 else "vomit"
        img = self._sized(name, pm)
        if self.stage == 0:
            dx = 2.5 * math.sin(el * 38)                       # 干呕: 细抖
        else:
            dx = 4.0 * math.sin(el * 26) * (0.6 + 0.4 * abs(math.sin(el * 3)))
        if img is not None:
            return img, dx
        a = 70 if self.stage == 0 else 110                     # 缺图: 晕眩立绘泛绿
        return self._green(pm, a), dx

    # ---- 内部 ----
    def _penalize(self):
        if self.penalized:
            return
        self.penalized = True
        p = self.pet
        before = float(p.stats.hunger)
        after = p.stats.add_hunger(-HUNGER_DROP)
        p.gain(-1, quiet=True)
        p.stats.inc("vomits")
        try:
            p.stats.save()
        except Exception:
            pass
        p.emit_event("vomit", why="spin", hunger_drop=round(before - after, 1), hunger=round(after, 1),
                     affection_drop=1)

    def _finish(self, t, interrupted=False):
        if not self.active:
            return
        self.active = False
        self._cache.clear()
        p = self.pet
        if self.penalized:
            self.cool_until = t + COOLDOWN
        p.clear_dizzy()
        if not interrupted:
            p.set_state("angry", 2.6)
            p.burst("anger", 1, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
            p.say(random.choice(END_LINES), force=True, duration=2.4, tone="alert")
        p.update()


def create(pet, log_fn=None):
    return VomitFx(pet, log_fn)
