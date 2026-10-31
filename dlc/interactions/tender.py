# -*- coding: utf-8 -*-
"""互动 DLC「温柔」: 捉弄的反面 —— 同样的手势温柔地做, 她会开心。
  1. 抱: 拖着她慢慢走、不晃 -> 挣扎慢下来(本体的 drag_hold_rate 口), 她不扑腾了, 偶尔冒爱心; 轻轻放下(不甩)会道谢。
     乱晃挣扎得更快; 抱着停在半空也会慢慢想下来。被拎醒 / 闹别扭时不算抱。
  2. 一直摸: 连着摸头(每下间隔 4.5 秒内), 第二下起有阶段: 舒服 -> 靠过来冒爱心 -> 摸太久害羞「够、够了啦」(之后 25 秒照原版)。
  3. 盖被子: 她睡着时 右键 / 托盘「互动」-> 🛏 盖小被子。身上多一条小被子; 被温柔地叫醒(不是拎醒、转醒、戳醒、浇醒)会道谢。
     下次开机会提一句。
  4. 梳头: 不按键, 在她两侧的卷发上从上往下慢慢顺 3 下。被丢 / 浇水 / 转晕 / 拎很久之后头发乱了, 梳顺她会道谢;
     闹别扭时头发乱着, 梳顺也能哄好她。头发不乱时也会舒服一下(45 秒一次)。
  5. 回应挥手: 她冲你挥手时, 2.5 秒内点她一下 = 你也挥手了, 她会高兴地蹦一下。没回应只是偶尔小声嘀咕, 不扣好感。
  6. 道晚安: 🌙 道晚安(然后关掉)。她挥手说晚安, 2.7 秒后桌宠关掉; 下次开机第一句接上(20 小时内)。
  7. 夸夸她: 💬 夸夸她。连着夸(90 秒内)越来越不好意思, 第三句转一圈「再夸我就要飞走了」, 第四句捂脸, 之后 1 分钟不让夸。
好感: 每样每天有上限(DAILY), 都是 +1(一直摸到「靠过来」那一下 +2); 摸头本身照原版 +3。心情: 本体 mood.py 的 TENDER 表。
她在忙别的(睡觉、闹别扭、生气、被丢、超级生气、转吐、达妮卡……)时, 这些手势交回原版。
推事件: carried(sec) / pet_lean / tucked / woke_tucked / combed(messy) / waved_back / goodnight / praised(n)。
记在 <数据目录>/tender.json(每天的次数、上次道晚安 / 盖被子的时间)。
priority = -1: 别的插件(哄她、超级生气、谷底……)先接。只用公开接口(docs/接口规范.md)。不想要就删掉这个文件。
"""
import json
import math
import os
import random
import time
from datetime import date, datetime

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from stats import data_dir

DAILY = {"carry": 4, "lean": 1, "tuck": 1, "comb": 3, "wave": 5, "night": 1, "praise": 3}
DRAG_STATE = "surprised"            # 本体 main.DRAG_STATE: 被拎着时的状态
BUSY = {"hidden", "drag", "fling", "throw", "spin", "danika", "food_fx", "chase", "walk", "plugin", "sulk"}

# ----- 1. 抱 -----
CARRY_SPEED = (25.0, 750.0)         # 慢慢移动: 速度在这个范围(像素/秒)
CARRY_ACC = 2600.0                  # 加速度低于这个才算稳
ROUGH_SPEED, ROUGH_ACC = 1100.0, 6000.0
CARRY_SETTLE = 1.2                  # 稳稳地抱着走这么久, 她就不扑腾了
RATE_CARRY, RATE_CARRY_STILL, RATE_SHAKE = 0.25, 0.5, 1.5
CARRY_LINES = ["……诶?是、是抱着吗……", "嗯……这样被抱着走,还挺舒服的。", "(不扑腾了)……慢点走哦。"]
CARRY_THANKS = ["……谢谢你轻轻放下我。", "到啦?嘿嘿,下次还要这样抱。", "……被抱着走的感觉,还不错。"]

# ----- 2. 一直摸 -----
PET_GAP = 4.5                       # 两下摸头间隔这么久以内, 算连着摸
PET_COOL = 25.0                     # 摸到「够了」之后这么久, 摸头照原版
PET_STAGES = [                      # (第几下起, 表情, 台词)
    (2, "content", ["呼噜噜……", "嗯~ 就是那里……", "(眯起了眼睛)"]),
    (4, "love", ["……往你手边靠一点点。", "嘿嘿……被摸得好舒服……", "(轻轻蹭了蹭你的手)"]),
    (6, "love", ["……再、再摸一会儿也不是不行。", "你今天怎么这么温柔……", "呼……要被摸化了……"]),
]
PET_LEAN = 4                        # 摸到第几下算「靠过来」(好感 +2, 每天一次)
PET_ENOUGH = 8
PET_ENOUGH_LINES = ["够、够了啦!头发要被摸成蒲公英了!", "再摸下去我就要睡着了啦……", "好、好啦!今天的份已经满了!"]

# ----- 3. 盖被子 -----
TUCK_AWAKE = ["现在还不困~ 等我睡着再盖嘛。", "诶?被子?……我还醒着呢。"]
TUCK_LINES = ["……嗯……好暖……", "(往被子里缩了缩)……嘿嘿……", "zzz……被子……香香的……"]
TUCK_AGAIN = "……(在被子里蹭了蹭)"
TUCK_THANKS = ["……被子是你盖的吗?嘿嘿,谢谢。", "睡得好香……原来是有被子呀。", "唔……醒了。被子好暖,谢谢你~"]
RUDE_WAKE = ("drag", "spin", "click", "water")
MEMORY_SEC = 20 * 3600              # 道晚安 / 盖被子之后这么久内重新打开, 第一句会提

# ----- 4. 梳头 -----
COMB_ZONE_X = (0.18, 0.5)           # 离头中心的水平距离(占 char_w)
COMB_ZONE_Y = (0.28, 1.0)           # 从头顶往下(占 char_h)
COMB_STROKE = 0.2                   # 一下至少往下顺 char_h 的这么多
COMB_STROKE_SEC = 2.0
COMB_NEED, COMB_WINDOW, COMB_COOL = 3, 6.0, 45.0
MESSY_SEC = 600.0                   # 头发乱了以后这么久内梳头算「梳顺」
COMB_MESSY = ["……头发顺了。谢、谢谢你。", "呼,总算不乱糟糟的了~", "嗯……你梳得还挺好的嘛。"]
COMB_TIDY = ["诶?帮我梳头吗……嘿嘿,好舒服。", "头发本来就很整齐啦……不过,再梳一下也行。"]
COMB_SULK = ["……看在你帮我梳头的份上,原谅你了。", "哼……头发是你弄乱的,你梳好是应该的!……谢谢。"]

# ----- 5. 回应挥手 -----
WAVE_WIN = 2.5
WAVE_MISS_P = 0.25
WAVE_BACK_LINES = ["你看到啦!嘿嘿~", "耶,你也冲我挥手了!", "嗨嗨~ 被回应了!"]
WAVE_MISS_LINES = ["……(悄悄把手放下了)", "……没看到吗。没关系~"]

# ----- 6. 道晚安 -----
QUIT_DELAY_MS = 2700
NIGHT_LINES = ["晚安~ 明天见!做个好梦哦。", "晚安……明天也要来找我哦。", "嗯,晚安!我也要去睡啦~"]
DAY_BYE_LINES = ["这么早就要走啦?……那,回头见!", "要去忙了吗?路上小心~ 回头见!"]
ASLEEP_BYE = "……嗯……晚安……(迷迷糊糊地)"

# ----- 7. 夸夸她 -----
PRAISE_GAP, PRAISE_COOL = 90.0, 60.0
PRAISE_TOPICS = ["诶?头冠好看?……这、这可是冬契的宝贝,当然好看!", "你也觉得这两个卷卷好看?每天早上要卷好久的……",
                 "翅膀?……嘿嘿,其实飞不太高啦。", "风元素很厉害?……哼哼,那当然!", "可、可爱?!……突然说这个干嘛啦。",
                 "……有我陪着你很开心吗?那、那我也很开心。"]
PRAISE_TWO = ["哼……还、还行吧。(嘴角压不住)", "你今天嘴怎么这么甜……", "再、再说一遍?……没什么!"]
PRAISE_THREE = ["……再夸我就要飞走了!", "呜哇,脸好烫……我去吹吹风!"]
PRAISE_STOP = ["别、别夸了啦!(捂脸)", "够了够了!今天的份满了!"]
PRAISE_HIDE = "……(把脸埋进披肩里)"
PRAISE_SULK = ["……夸我也没用。", "哼。(耳朵尖有点红)"]
PRAISE_ASLEEP = "……(睡梦中笑了一下)"


def _pick(pool, last=None):
    c = [x for x in pool if x != last] or list(pool)
    return random.choice(c)


class Tender:
    priority = -1

    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.path = data_dir() / "tender.json"
        self.store = self._load()
        now = time.monotonic()
        self.t_start = now
        self.drag = None                    # 这次拖拽: 速度 / 稳不稳 / 抱了多久
        self.pet_streak, self.pet_last, self.pet_cool = 0, 0.0, 0.0
        self.tucked = False
        self._blanket_cache = {}
        self.later = None                   # (最早, 最晚, 函数): 等气泡空了再说的话
        self.memory = self._memory_line()
        self.stroke, self.strokes, self.comb_cool, self.messy_until = None, [], 0.0, 0.0
        self.wave_until, self.wave_idle = 0.0, False
        self.praise_n, self.praise_last, self.praise_cool = 0, 0.0, 0.0
        self._last = {}

    # ----- 存档 -----
    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
        return {}

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.store, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception as e:
            if self.log:
                self.log("tender save", e)

    def _daily(self, kind):
        """今天这一样的好感还没到上限: 记一次, 返回 True"""
        today = date.today().isoformat()
        if self.store.get("day") != today:
            self.store["day"], self.store["counts"] = today, {}
        c = self.store.setdefault("counts", {})
        if c.get(kind, 0) >= DAILY[kind]:
            return False
        c[kind] = c.get(kind, 0) + 1
        self._save()
        return True

    def _gain(self, kind, n=1):
        if self._daily(kind):
            self.pet.gain(n, quiet=True)

    # ----- 小工具 -----
    def _line(self, key, pool):
        line = _pick(pool, self._last.get(key))
        self._last[key] = line
        return line

    def _say(self, text, dur=2.8, tone="happy"):
        self.pet.say(text, force=True, duration=dur, tone=tone, src="tender")

    def _free(self, sulk_ok=False):
        """她这会儿没在忙别的(手势交给这里)"""
        p = self.pet
        if p.state in ("sleep", "dizzy", "eat") or p.edge or not p.isVisible():
            return False
        if p.sulking():
            if not sulk_ok:
                return False
        elif p.state == "angry":
            return False
        busy = BUSY - {"sulk"} if sulk_ok else BUSY
        return not (p.activities() & busy)

    # ----- 1. 抱 -----
    def _drag_step(self, t):
        d, p = self.drag, self.pet
        dt = t - d["t"]
        if dt < 1e-3:
            return
        x, y = p.x(), p.y()
        k = min(1.0, dt * 8.0)
        vx = d["vx"] + ((x - d["x"]) / dt - d["vx"]) * k
        vy = d["vy"] + ((y - d["y"]) / dt - d["vy"]) * k
        acc = math.hypot(vx - d["vx"], vy - d["vy"]) / dt
        d["acc"] += (acc - d["acc"]) * min(1.0, dt * 4.0)
        d.update(x=x, y=y, t=t, vx=vx, vy=vy)
        speed = math.hypot(vx, vy)
        d["speed"] = speed
        rough = speed > ROUGH_SPEED or d["acc"] > ROUGH_ACC
        d["rough"] = d["rough"] + dt if rough else 0.0
        if rough:
            d["gentle"] = max(0.0, d["gentle"] - 2 * dt)
            if d["rough"] > 0.4:
                d["carried"] = False
        elif CARRY_SPEED[0] <= speed <= CARRY_SPEED[1] and d["acc"] < CARRY_ACC:
            d["gentle"] += dt
            d["carry_sec"] += dt if d["carried"] else 0.0
        if d["block"] or d["carried"] or d["gentle"] < CARRY_SETTLE or p.state != DRAG_STATE:
            if d["carried"] and t >= d["heart_at"]:
                d["heart_at"] = t + random.uniform(2.2, 3.2)
                p.burst("heart", 1)
            return
        d["carried"], d["heart_at"] = True, t + 2.5
        p.burst("heart", 2)
        if not d["said"]:
            d["said"] = True
            self._say(self._line("carry", CARRY_LINES), 2.6)

    def _drag_end(self, thrown):
        d, self.drag = self.drag, None
        p = self.pet
        if not d or d["block"] or thrown or not d["carried"] or p.state == "angry" or p.sulking():
            return
        p.set_state("shy", 2.4)
        p.burst("heart", 3)
        self._say(self._line("thanks", CARRY_THANKS), 2.8)
        self._gain("carry")
        p.emit_event("carried", sec=round(d["carry_sec"] + CARRY_SETTLE, 1))

    # ----- 3. 盖被子 -----
    def tuck(self):
        p = self.pet
        if p.state != "sleep":
            self._say(self._line("tuck_awake", TUCK_AWAKE), 2.6, "normal")
            return
        if self.tucked:
            self._say(TUCK_AGAIN, 2.2, "cool")
            return
        self.tucked = True
        self.store["last_tucked"] = time.time()
        self._save()
        p.burst("sparkle", 4)
        self._say(self._line("tuck", TUCK_LINES), 3.0, "cool")
        p.emit_event("tucked")

    def _woke(self, why):
        if not self.tucked:
            return
        self.tucked = False
        if why in RUDE_WAKE:
            return

        def thank():
            p = self.pet
            if p.state in ("sleep", "angry") or p.sulking():
                return
            p.set_state("shy", 2.4)
            p.burst("heart", 3)
            self._say(self._line("tuck_thanks", TUCK_THANKS), 3.0)
            self._gain("tuck")
            p.emit_event("woke_tucked")

        now = time.monotonic()
        self.later = (now + 2.6, now + 15.0, thank)

    def _blanket(self, pm):
        """睡着的立绘上盖一条小被子: 上沿顺着肩膀弧起来, 两边鼓出去, 翻过来的被头是波浪边, 上面撒小星星"""
        ck = pm.cacheKey()
        out = self._blanket_cache.get(ck)
        if out is not None:
            return out
        if len(self._blanket_cache) > 6:
            self._blanket_cache.clear()
        out = QPixmap(pm)
        dpr = pm.devicePixelRatio() or 1.0
        w, h = pm.width() / dpr, pm.height() / dpr
        q = QPainter(out)
        q.setRenderHint(QPainter.Antialiasing, True)
        top, side, bot = h * 0.655, h * 0.735, h * 0.995
        xl, xr = w * 0.15, w * 0.85
        body = QPainterPath()
        body.moveTo(xl, side)
        body.cubicTo(xl + w * 0.12, top - h * 0.01, xr - w * 0.12, top - h * 0.01, xr, side)
        body.cubicTo(xr + w * 0.05, side + h * 0.08, xr + w * 0.06, bot - h * 0.05, xr + w * 0.035, bot)
        body.lineTo(xl - w * 0.035, bot)
        body.cubicTo(xl - w * 0.06, bot - h * 0.05, xl - w * 0.05, side + h * 0.08, xl, side)
        body.closeSubpath()
        g = QLinearGradient(0, top, 0, bot)
        g.setColorAt(0, QColor(255, 232, 240))
        g.setColorAt(1, QColor(250, 196, 216))
        q.setPen(QPen(QColor(255, 255, 255), max(2.5, w * 0.022)))
        q.setBrush(g)
        q.drawPath(body)
        q.setPen(QPen(QColor(46, 63, 110, 170), max(1.0, w * 0.007)))
        q.setBrush(Qt.NoBrush)
        q.drawPath(body)
        q.setClipPath(body)
        rnd = random.Random(7)                                                       # 小星星
        q.setPen(Qt.NoPen)
        for i in range(14):
            sx = xl - w * 0.02 + (i % 7 + rnd.uniform(0.1, 0.9)) * (xr - xl + w * 0.04) / 7
            sy = side + h * 0.07 + (i // 7 + rnd.uniform(0.15, 0.85)) * (bot - side - h * 0.07) / 2
            r = w * rnd.uniform(0.011, 0.017)
            star = QPainterPath()
            for k in range(8):
                rr = r if k % 2 == 0 else r * 0.38
                a = math.pi / 4 * k - math.pi / 2
                pt = QPointF(sx + rr * math.cos(a), sy + rr * math.sin(a))
                star.moveTo(pt) if k == 0 else star.lineTo(pt)
            star.closeSubpath()
            q.setBrush(QColor(255, 255, 255, 235) if i % 3 else QColor(170, 232, 220, 235))
            q.drawPath(star)
        hem = QPainterPath()                                                         # 翻过来的被头, 下沿波浪
        band = h * 0.065
        hem.moveTo(xl, side)
        hem.cubicTo(xl + w * 0.12, top - h * 0.01, xr - w * 0.12, top - h * 0.01, xr, side)
        n = 9
        pts = []
        for k in range(n + 1):
            u = k / n
            x = xr - (xr - xl) * u
            y = side + band - 4 * (side - top + h * 0.004) * u * (1 - u) * 0.75
            pts.append(QPointF(x, y))
        hem.lineTo(pts[0])
        for k in range(n):
            a_, b_ = pts[k], pts[k + 1]
            mid = QPointF((a_.x() + b_.x()) / 2, (a_.y() + b_.y()) / 2 + band * 0.32)
            hem.quadTo(mid, b_)
        hem.closeSubpath()
        q.setBrush(QColor(255, 251, 246))
        q.setPen(QPen(QColor(46, 63, 110, 120), max(1.0, w * 0.005)))
        q.drawPath(hem)
        q.end()
        out.setDevicePixelRatio(dpr)
        self._blanket_cache[ck] = out
        return out

    def paint(self, key, pm, t):
        if self.tucked and key == "sleep":
            return self._blanket(pm), 0.0
        return None

    # ----- 4. 梳头 -----
    def _comb_step(self, t):
        p = self.pet
        if QGuiApplication.mouseButtons() != Qt.NoButton or not self._free(sulk_ok=True):
            self.stroke = None
            return
        c = QCursor.pos()
        hp = p.head_point()
        cw, ch = max(1.0, float(p.char_w)), max(1.0, float(p.char_h))
        rx = (c.x() - hp.x()) / cw
        ry = (c.y() - (hp.y() - 0.18 * ch)) / ch
        if not (COMB_ZONE_X[0] <= abs(rx) <= COMB_ZONE_X[1] and COMB_ZONE_Y[0] <= ry <= COMB_ZONE_Y[1]):
            self.stroke = None
            return
        side = 1 if rx > 0 else -1
        s = self.stroke
        if s is None or s["side"] != side or ry < s["last"] - 0.02 or t - s["t0"] > COMB_STROKE_SEC:
            self.stroke = dict(side=side, start=ry, last=ry, t0=t)
            return
        s["last"] = max(s["last"], ry)
        if s["last"] - s["start"] >= COMB_STROKE:
            self.strokes = [x for x in self.strokes if t - x <= COMB_WINDOW] + [t]
            self.stroke = None
            if len(self.strokes) >= COMB_NEED:
                self.strokes = []
                self._combed(t)

    def _combed(self, t):
        if t < self.comb_cool:
            return
        p = self.pet
        messy = t < self.messy_until
        sulking = p.sulking()
        if sulking and not messy:
            return                                     # 闹别扭时只有「把你弄乱的头发梳好」才算数
        self.comb_cool, self.messy_until = t + COMB_COOL, 0.0
        if sulking:
            p.clear_sulk()
            p.set_state("shy", 2.6)
            p.burst("heart", 2)
            self._say(self._line("comb_sulk", COMB_SULK), 3.0)
        else:
            p.set_state("content", 2.6)
            p.burst("sparkle", 6 if messy else 3)
            self._say(self._line("comb", COMB_MESSY if messy else COMB_TIDY), 2.8)
        if messy:
            self._gain("comb")
        p.emit_event("combed", messy=bool(messy), sulk=bool(sulking))

    # ----- 5. 回应挥手 -----
    def _wave_back(self):
        p = self.pet
        self.wave_until = 0.0
        p.note_interaction()
        p.set_state("cheer", 1.8)
        if p.landed:
            p.do_jump(False)
        p.burst("heart", 4)
        p.burst("sparkle", 4)
        self._say(self._line("wave", WAVE_BACK_LINES), 2.4)
        self._gain("wave")
        p.emit_event("waved_back")

    # ----- 6. 道晚安 -----
    def goodnight(self):
        p = self.pet
        h = datetime.now().hour
        if p.state == "sleep":
            self._say(ASLEEP_BYE, 2.6, "cool")
        else:
            p.note_interaction()
            p.set_state("wave", 2.8)
            p.burst("heart", 4)
            p.burst("sparkle", 4)
            self._say(self._line("bye", NIGHT_LINES if h >= 21 or h < 5 else DAY_BYE_LINES), 2.8)
        self.store["last_goodnight"] = time.time()
        self._save()
        self._gain("night")
        p.emit_event("goodnight")
        QTimer.singleShot(QUIT_DELAY_MS, p.quit_requested.emit)

    def _memory_line(self):
        """上次关掉前道过晚安 / 盖过被子: 这次开机第一句接上(只说一次)"""
        now = time.time()
        night = self.store.get("last_goodnight") or 0
        tuck = self.store.get("last_tucked") or 0
        if max(night, tuck) <= (self.store.get("memory_for") or 0):
            return None
        ok_n = 0 < now - night < MEMORY_SEC
        ok_t = 0 < now - tuck < MEMORY_SEC
        if not ok_n and not ok_t:
            return None
        h = datetime.now().hour
        hello = "早~ " if 5 <= h < 11 else ("嗨~ " if h < 18 else "晚上好~ ")
        if ok_n and ok_t:
            text = hello + "上次你说了晚安,还给我盖了被子……嘿嘿,睡得特别香。"
        elif ok_n:
            text = hello + "上次走之前你说了晚安……我记着呢。"
        else:
            text = hello + "上次是你给我盖的被子吧?……谢谢。"
        self.store["memory_for"] = max(night, tuck)
        return text

    # ----- 7. 夸夸她 -----
    def praise(self):
        p = self.pet
        now = time.monotonic()
        if p.state == "sleep":
            self._say(PRAISE_ASLEEP, 2.4, "cool")
            return
        p.note_interaction()
        if p.sulking():
            self._say(self._line("praise_sulk", PRAISE_SULK), 2.4, "normal")
            return
        if now < self.praise_cool:
            p.set_state("shy", 2.4)
            self._say(PRAISE_HIDE, 2.2, "normal")
            return
        n = self.praise_n + 1 if now - self.praise_last <= PRAISE_GAP else 1
        self.praise_n, self.praise_last = n, now
        if n == 1:
            p.set_state("shy", 2.8)
            p.burst("heart", 2)
            self._say(self._line("praise", PRAISE_TOPICS), 3.4)
        elif n == 2:
            p.set_state("shy", 2.8)
            p.burst("heart", 3)
            self._say(self._line("praise2", PRAISE_TWO), 3.0)
        elif n == 3:
            p.set_state("love", 3.0)
            p.burst("heart", 6)
            if not p.edge:
                p.spin_rem = max(p.spin_rem, 360.0)
            self._say(self._line("praise3", PRAISE_THREE), 3.0)
        else:
            p.set_state("shy", 3.0)
            p.kick(-1.2)
            p.burst("sweat", 1)
            self._say(self._line("praise_stop", PRAISE_STOP), 2.8)
            self.praise_n, self.praise_cool = 0, now + PRAISE_COOL
        self._gain("praise")
        p.emit_event("praised", n=n)

    # ----- 钩子 -----
    def tune(self, name, value, ctx):
        if name != "drag_hold_rate" or not self.drag or self.drag["block"]:
            return None
        d = self.drag
        d["stage"] = int(ctx.get("stage") or 0)
        if d["rough"] > 0.15:
            return RATE_SHAKE
        if d["carried"]:
            return RATE_CARRY if d["speed"] >= CARRY_SPEED[0] else RATE_CARRY_STILL
        return None

    def expr(self, key, state):
        d = self.drag
        if d and d["carried"] and not d.get("stage") and state == DRAG_STATE and self.pet.dragging:
            return "content"                           # 被抱着: 不扑腾了, 眯眼笑(开始喊「放我下来」就不笑了)
        return None

    def on_pet(self):
        """连着摸头: 第二下起换成这里的阶段; 第一下、忙的时候、刚摸够了, 都交回原版"""
        p = self.pet
        now = time.monotonic()
        if not self._free() or now < self.pet_cool:
            self.pet_streak = 0
            return False
        self.pet_streak = self.pet_streak + 1 if now - self.pet_last <= PET_GAP else 1
        self.pet_last = now
        n = self.pet_streak
        if n < PET_STAGES[0][0]:
            return False
        if n >= PET_ENOUGH:
            self.pet_streak, self.pet_cool = 0, now + PET_COOL
            p.set_state("shy", 2.8)
            p.kick(-1.4)
            p.burst("heart", 3)
            p.burst("sweat", 1)
            self._say(self._line("pet_enough", PET_ENOUGH_LINES), 3.0)
            p.gain(3, "pet", quiet=True)
            return True
        stage = [s for s in PET_STAGES if n >= s[0]][-1]
        p.set_state(stage[1], 2.8)
        p.kick(-1.0)
        p.burst("heart", min(8, 2 + n))
        self._say(self._line(f"pet{stage[0]}", stage[2]), 2.6)
        p.gain(3, "pet", quiet=True)                   # 摸头本身照原版
        if n == PET_LEAN:
            self._gain("lean", 2)
            p.emit_event("pet_lean")
        return True

    def on_click(self, double):
        if double or time.monotonic() >= self.wave_until:
            return False
        if not self._free() and self.pet.state != "wave":
            return False
        self._wave_back()
        return True

    def on_event(self, name, data):
        now = time.monotonic()
        p = self.pet
        if name == "drag_start":
            self.drag = dict(t=now, x=p.x(), y=p.y(), vx=0.0, vy=0.0, acc=0.0, speed=0.0, rough=0.0, gentle=0.0,
                             carried=False, carry_sec=0.0, said=False, heart_at=0.0,
                             block=bool(data.get("was_sleep")) or p.sulking())
        elif name == "drag_end":
            if (data.get("held") or 0) >= 9:
                self.messy_until = now + MESSY_SEC
            self._drag_end(bool(data.get("thrown")))
        elif name in ("throw", "vomit") or (name == "dizzy") or (name == "watered" and not data.get("dodged")):
            self.messy_until = now + MESSY_SEC
        elif name == "wake":
            self._woke(data.get("why"))
        elif name == "idle_action":
            self.wave_idle = data.get("act") == "wave"
        elif name == "state":
            if data.get("to") == "wave" and not p.sulking():
                self.wave_until = now + WAVE_WIN
            elif data.get("to") in ("sleep", "angry", "dizzy", DRAG_STATE) and self.wave_until:
                self.wave_until = 0.0                  # 挥手被打断了(睡着 / 生气 / 被拎起来……); 回到发呆不算
                self.wave_idle = False

    def step(self, t):
        p = self.pet
        if self.drag is not None:
            if p.dragging:
                self._drag_step(t)
            elif t - self.drag["t"] > 1.0:
                self.drag = None
        if self.tucked and p.state != "sleep":
            self.tucked = False
        if self.wave_until and t >= self.wave_until:   # 挥手没人理
            self.wave_until = 0.0
            if self.wave_idle and random.random() < WAVE_MISS_P and not p.bubble.isVisible() and not p.cfg["mute"]:
                p.say(self._line("wave_miss", WAVE_MISS_LINES), duration=2.4, tone="cool", src="tender")
            self.wave_idle = False
        if self.later and t >= self.later[0]:
            if t > self.later[1]:
                self.later = None
            elif not p.bubble.isVisible():
                fn, self.later = self.later[2], None
                fn()
        if self.memory and t - self.t_start > 12.0 and p.can_auto("plugin_talk") and not p.bubble.isVisible():
            text, self.memory = self.memory, None
            self._save()
            p.set_state("shy", 2.6)
            p.burst("heart", 2)
            self._say(text, 3.6)
        self._comb_step(t)

    def menu_items(self):
        return [("💬", "夸夸她", self.praise), ("🛏", "盖小被子", self.tuck), ("🌙", "道晚安(然后关掉)", self.goodnight)]


def create(pet, log_fn=None):
    return Tender(pet, log_fn)
