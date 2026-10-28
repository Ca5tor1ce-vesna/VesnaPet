# -*- coding: utf-8 -*-
"""互动 DLC「哄她」: 她生气(被丢/转晕后/转吐后/闹别扭…)起 30 秒内摸头 -> 别扭地消气。
生气提前结束, 1-2 句傲娇台词, 好感 +2(原版 gain), 推 "comforted" 事件。每次生气只能哄一次;
接管期间原版摸头的效果(+3 好感 / 闹别扭消气 +1)不执行, 不叠加。
"""
import random
import time

from PySide6.QtCore import QPointF, QTimer

WINDOW = 30.0
LINES = ["哼…这次就原谅你。", "下、下不为例!", "…就、就摸一下而已哦。", "别以为摸摸头我就不生气了…好吧,不气了。",
         "哼,看在你这么诚恳的份上。"]
LINES2 = ["…不许笑!", "再有下次我真的不理你了。", "我才没有消气…只是累了而已。"]


class Comfort:
    def __init__(self, pet, log_fn=None):
        self.pet = pet
        self.t0 = 0.0            # 这次生气开始的时间; 0 = 当前没有可哄的生气
        self.done = False        # 这次生气已经被哄过
        self.was_angry = False

    def _angry_now(self):
        p = self.pet
        return p.state == "angry" or p.sulking()

    def step(self, t):
        a = self._angry_now()
        if a and not self.was_angry and (self.done or not self.t0 or t - self.t0 > WINDOW):
            self.t0, self.done = t, False          # 新的一次生气
        self.was_angry = a
        if self.t0 and t - self.t0 > WINDOW and not a:
            self.t0 = 0.0

    def on_pet(self):
        p = self.pet
        now = time.monotonic()
        self.step(now)
        if not self.t0 or self.done or now - self.t0 > WINDOW:
            return False
        if p._dragging or p.fling:
            return False
        self.done = True
        sulk = p.sulking()
        if sulk:                                   # 原版 _end_sulk 的收尾, 但不加它的 +1
            p._sulk_until = 0.0
            p._sulk_calm = 0
            p._throws.clear()
        p.set_state("shy", 2.6)
        p.kick(-1.2)
        p.burst("heart", 3)
        p.burst("sweat", 1)
        p.sfx.play("pop")
        got = p.gain(2, quiet=True)
        hp = p.head_point()
        p.burst("emoji", 1, at=QPointF(hp.x() + p.char_w * 0.28, hp.y() - 6), text="💗")
        p.say(random.choice(LINES), force=True, duration=2.6, tone="happy")
        if random.random() < 0.6:
            QTimer.singleShot(2700, lambda: p.isVisible() and p.state != "sleep" and
                              p.say(random.choice(LINES2), force=True, duration=2.4, tone="normal"))
        p.emit_event("comforted", was_sulking=bool(sulk), after=round(now - self.t0, 1), gain=got)
        return True


def create(pet, log_fn=None):
    return Comfort(pet, log_fn)
