# -*- coding: utf-8 -*-
"""互动 DLC「陪伴奖励」: 桌宠显示着、她醒着的时间累计满 1 小时(隐藏/睡觉时暂停), 等她不忙时说一句别扭的话,
好感 +1(原版 gain), 一天最多 3 次, 推 "companion_bonus" 事件。
计数存 <数据目录>/companion_time.json(跨天清零)。测试用: 环境变量 VESNA_COMPANION_SEC=秒数 缩短 1 小时。
"""
import json
import os
import random
from datetime import date

from stats import data_dir

DAILY_MAX = 3
CALM = ("idle", "look", "look_left", "content", "happy")
BUSY = {"drag", "fling", "walk", "sulk", "food_fx", "link", "spin", "danika", "plugin"}
LINES = ["你…一直在啊。", "陪了这么久,也、也不是很开心啦。", "哼,一个小时了…你都不嫌我烦吗?",
         "…谢谢你一直开着我。才、才不是想说这个!", "这么久都在,算你有点良心。"]


def _need_sec():
    try:
        v = float(os.environ.get("VESNA_COMPANION_SEC", ""))
        if v > 0:
            return max(5.0, v)
    except ValueError:
        pass
    return 3600.0


class CompanionTime:
    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.path = data_dir() / "companion_time.json"
        self.need = _need_sec()
        self.acc = 0.0
        self.last = None
        self.d = {"day": date.today().isoformat(), "count": 0}
        try:
            v = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(v, dict) and isinstance(v.get("count"), int) and isinstance(v.get("day"), str):
                self.d = {"day": v["day"], "count": max(0, v["count"])}
        except FileNotFoundError:
            pass
        except Exception as e:
            if log_fn:
                log_fn("companion_time load", e)
        self._roll()

    def _roll(self):
        today = date.today().isoformat()
        if self.d["day"] != today:
            self.d = {"day": today, "count": 0}

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.d, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except Exception as e:
            if self.log:
                self.log("companion_time save", e)

    def _busy(self):
        p = self.pet
        return p.state not in CALM or bool(p.activities() & BUSY)

    def step(self, t):
        p = self.pet
        dt = 0.0 if self.last is None else max(0.0, min(1.0, t - self.last))
        self.last = t
        if not p.isVisible() or p.state == "sleep":
            return                                   # 隐藏 / 睡觉: 暂停计时
        self.acc += dt
        if self.acc < self.need or self._busy():
            return
        self.acc = 0.0
        self._roll()
        if self.d["count"] >= DAILY_MAX:
            return
        self.d["count"] += 1
        self._save()
        got = p.gain(1)
        p.set_state("shy", 2.6)
        p.burst("heart", 2)
        p.say(random.choice(LINES), duration=3.4, tone="happy")   # 静音时不冒泡, 好感照加
        p.emit_event("companion_bonus", count=self.d["count"], gain=got, minutes=round(self.need / 60, 1))


def create(pet, log_fn=None):
    return CompanionTime(pet, log_fn)
