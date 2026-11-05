# -*- coding: utf-8 -*-
"""互动 DLC「灵魂形态」: 她整个人变成半透明的小幽灵 —— 不是死了, 是灵魂出窍的魔法事故; 碰不到她, 她也碰不到你。
怎么变成:
  - 魂被滚轮转断、往天上飘(本体), UNCAUGHT_SEC 秒还没去抓住 -> 身子也跟着飘出来, 整个人变成幽灵;
  - DARK_WINDOW 秒内吃下第三份黑暗料理 -> 魂回不去了, 干脆整个人飘出来;
  - 设置「扩展」-> 👻 灵魂形态(测试)。
什么样: 现有每张表情都调成青白、半透明, 下半截化成一缕雾(不用新图); 离地飘着、上下浮(本体 lift 钩子), 脚下没有影子。
越来越淡: 浓度从 1 往下掉, GHOST_SEC 秒掉完(晴天快一半, 附在鼠标上时慢一半, 藏起来时不掉);
  淡到 FAINT_AT 她开始慌, 掉到 0 打个喷嚏回到身体里。
互动(本体原来的效果都不做):
  - 戳她: 手指穿过去, 她打个寒颤咯咯笑; 2.5 秒内连戳 3 下, 她嗖地飘到一边。
  - 摸头: 摸不到。她把头凑到你的光标上, 小声说「……摸不到你。」
  - 拖她: 抓不住; 按着不放, 她跟着你的鼠标飘(像牵风筝), 松手就停在那儿。
  - 滚轮: 转起来轻飘飘的, 不会晕。
  - 浇水: 水从她身上穿过去(water 插件), 她得意。
  - 喂她: 吃不了, 闻香 —— 吃的飞到嘴边, 香气被她吸进去: 浓度 +SMELL_GAIN、心情 +2; 冰的没香味, 她很失望;
    她最爱吃的那种(fav): 顺着香味回到身体里。不涨饱腹、不算投喂。
  - 附在鼠标上: 她时不时自己钻进你的光标(或菜单「👻 附到鼠标上」), 光标旁边跟着一个小幽灵, 你走到哪她跟到哪;
    使劲左右甩鼠标 = 把她甩晕甩出来; POSSESS_SEC 秒后她玩够了自己出来(菜单「👻 从鼠标里出来」也行)。
  - 吓你: 鼠标从远处凑近她时, 偶尔「哇!」一声。
  - 达妮卡来访: 看不见她, 对着空气交代公务, 薇斯纳在旁边拼命挥手。
  - 哄睡(灵魂不用睡觉)、自己犯困睡着、捉弄插件的那些都不开; 被强行弄睡着(设置「立刻睡着」)就回到身体里。
推事件 ghost(stage: start(why: soul dark manual) / smell(key, fav, cold) / possess / unpossess(why) / end(why)), 都带 memo。
不存档: 关掉再开就回到身体里了。priority = 8: 比生病、哄她、捉弄、温柔先接戳和摸头。只用公开接口(docs/接口规范.md)。
不想要就删掉这个文件。
"""
import math
import random
import time
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

GHOST_SEC = 240.0                    # 浓度从 1 掉到 0 要多久(秒)
SUN_FASTER = 1.5                     # 晴天掉得快
POSSESS_SLOWER = 0.5                 # 附在鼠标上时掉得慢
FAINT_AT = 0.3                       # 淡到这儿她开始慌
SMELL_GAIN = 0.25                    # 闻到香味, 浓度回来这么多
UNCAUGHT_SEC = 25.0                  # 魂被转断往天上飘, 这么久没抓住 -> 整个人变成幽灵
DARK_WINDOW = 240.0                  # 这段时间里吃第三份黑暗料理 -> 变成幽灵
LIFT = 0.13                          # 离地多高(立绘高的倍数)
BOB = 0.03                           # 上下浮多少
ALPHA = (0.30, 0.80)                 # 最淡 / 最浓时的不透明度
TINT = QColor(175, 228, 248, 125)    # 青白
TAIL = 0.58                          # 从立绘这个高度往下渐渐化成雾
POSSESS_SEC = 14.0
POSSESS_GAP = (45.0, 100.0)          # 隔多久自己钻进鼠标一次
CURSOR_W = 0.42                      # 光标旁边那个小幽灵的宽(立绘宽的倍数)
SHAKE_PX = 22                        # 左右甩: 每一段至少挪这么多像素, 0.7 秒内来回 3 次
KITE_SPEED = 520.0                   # 牵着飘的速度(像素/秒)
POKE_DODGE = 3                       # 2.5 秒内戳这么多下, 她嗖地躲开
BOO_COOL, BOO_P = 50.0, 0.4          # 吓你: 冷却 / 概率
IDLE_GAP = (25.0, 45.0)              # 自己嘀咕一句的间隔

GHOST_START = {"soul": ["……诶?身子……也跟着飘起来了?!", "魂没被抓住……我、我整个人都变成幽灵了?!"],
               "dark": ["……那个黑乎乎的……把我整个人都吃没了?!", "呜……这次魂回不去了,干脆整个人飘出来了!"],
               "manual": ["……诶?我、我怎么透明了?!", "身子好轻……我变成幽灵了?!"]}
GHOST_IDLE = ["轻飘飘的~", "……原来飘着是这种感觉。", "嘿嘿,没有影子了。", "(试着穿过屏幕边)……唔,过不去嘛。", "……好安静啊。"]
GHOST_POKE = ["嘻嘻,穿过去了~", "好凉……你的手指好凉!", "(打了个寒颤)……痒!", "戳不到戳不到~"]
GHOST_DODGE = ["嗖——!抓不到~", "别戳啦!(飘走)"]
GHOST_PET = ["……摸不到你。", "(把头凑到你的光标上)……就当是摸到了吧。", "……好想快点回去,这样就能摸到你了。"]
GHOST_KITE = ["诶诶?跟、跟着你飘了~", "像风筝一样~"]
GHOST_SPIN = ["呼——转起来轻飘飘的,一点都不晕~", "嘿嘿,幽灵才不会晕~"]
GHOST_WET = ["嘿嘿,水从我身上穿过去了~", "浇不湿~浇不湿~"]
GHOST_SMELL = ["(吸——)……好香……", "闻着就像吃到了一样~", "(把香气吸了进去)……身子好像浓了一点。"]
GHOST_SMELL_COLD = ["……冰的,一点香味都没有……", "闻不到……冰的东西没味道。"]
GHOST_SMELL_FAV = ["……这个味道……!", "是、是我最喜欢的……!(跟着香味飘了过去)"]
GHOST_POSSESS = ["嘿嘿,借你的鼠标坐坐~", "钻进去咯~"]
GHOST_UNPOSSESS = {"time": ["玩够了~(从鼠标里飘出来)", "呼,出来透透气~"], "shaken": ["甩、甩晕了……!", "哇啊——别甩啦!!"],
                   "menu": ["好嘛好嘛,出来就是了~"], "feed": ["闻、闻到了!(从鼠标里钻出来)"]}
GHOST_BOO = ["哇!!", "嘿!!"]
GHOST_BOO_AFTER = ["嘿嘿,吓到了吧~", "……你怎么一点都不怕啊。"]
GHOST_FAINT = ["……我、我是不是要散了?!", "身子……越来越淡了……快想想办法……"]
GHOST_BACK = {"faded": ["阿嚏!……诶?回、回来了?", "……呼,身子又沉了。回来了!"],
              "smell": ["……回来了!果然还是要吃到嘴里才行!", "被香味拽回来了~……那个,可以真的给我吃一口吗?"],
              "sleep": []}
GHOST_NO_SLEEP = ["灵魂不用睡觉啦……", "飘着呢,睡不着~"]
GHOST_DANIKA = [("danika", "……薇斯纳大人?"), ("vesna", "我在这儿!!就在你面前!!"),
                ("danika", "……奇怪。刚才明明听见了声音。"), ("vesna", "达妮卡!!看我!!看这里!!"),
                ("danika", "……文件我先放桌上了。告辞。"), ("vesna", "……呜。谁都看不见我……")]
STATUS = "整个人变成了魂,半透明地飘在半空,身后拖着一缕雾……"
STATUS_FAINT = "魂淡得快看不见了,慌慌张张地想抓住点什么……"
STATUS_POSSESS = "魂钻进了你的鼠标里,你走到哪她跟到哪……"
STATUS_KITE = "魂像只小风筝,跟着你的手飘……"
MEMO_START = {"soul": "她的魂被转断了没人抓住，整个人跟着飘了出来，变成了半透明的幽灵",
              "dark": "她连吃了三份黑暗料理，整个人变成了半透明的幽灵",
              "manual": "她变成了半透明的幽灵"}
MEMO_END = {"faded": "幽灵状态的她越来越淡，打了个喷嚏，回到了身体里",
            "smell": "她顺着最爱吃的东西的香味，回到了身体里",
            "sleep": "她睡着了，灵魂回到了身体里", "manual": "她回到了身体里"}


def _pick(pool, last=None):
    c = [x for x in pool if x != last] or list(pool)
    return random.choice(c)


class CursorGhost(QWidget):
    """附在鼠标上: 光标右下角跟着一个小幽灵。不接鼠标(点击穿过去)"""

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
                         | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.pm = None
        self.dw = self.dh = 0.0
        self.bob = 0.0
        self.rot = 0.0

    def set_pm(self, pm, w):
        if pm is None or pm.isNull():
            return
        self.pm = pm
        dpr = pm.devicePixelRatio() or 1.0
        self.dw = float(w)
        self.dh = w * (pm.height() / dpr) / max(1.0, pm.width() / dpr)
        size = (int(self.dw * 1.25) + 8, int(self.dh * 1.25) + 8)
        if (self.width(), self.height()) != size:
            self.resize(*size)

    def paintEvent(self, _):
        if self.pm is None:
            return
        q = QPainter(self)
        q.setRenderHint(QPainter.SmoothPixmapTransform, True)
        q.translate(self.width() / 2, self.height() / 2 + self.bob)
        q.rotate(self.rot)
        q.drawPixmap(QRectF(-self.dw / 2, -self.dh / 2, self.dw, self.dh), self.pm, QRectF(self.pm.rect()))
        q.end()


class Ghost:
    priority = 8

    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.active = False
        self.why = None
        self.amt = 1.0                       # 浓度(1 -> 0)
        self.faint_said = False
        self.weather = None
        self.possess = None                  # 附在鼠标上: dict(t0, until, win, hist)
        self.kite = None                     # 被你牵着飘: dict(next)
        self.pokes = []
        self.fall_at = None                  # 本体的魂被转断(她倒下)的时间
        self.darks = []                      # 最近吃下黑暗料理的时间
        self.next_idle = self.next_possess = self.next_wisp = 0.0
        self.boo_cool = 0.0
        self.cur_d = None                    # 上一帧鼠标离她多远(立绘宽的倍数)
        self.say_cool = 0.0
        self._last = {}
        self._cache = {}
        self._blank_pm = None
        self._ghost_pm = None
        self._t = time.monotonic()

    # ----- 小工具 -----
    def _line(self, key, pool):
        line = _pick(pool, self._last.get(key))
        self._last[key] = line
        return line

    def _say(self, key, pool, dur=2.4, tone=None, throttle=0.0):
        t = time.monotonic()
        if not pool or (throttle and (t < self.say_cool or self.pet.bubble.isVisible())):
            return
        self.say_cool = t + throttle
        self.pet.say(self._line(key, pool), force=True, duration=dur, tone=tone, src="ghost")

    def _free(self):
        """没在附身、没被牵着、没别的事: 能自己嘀咕 / 吓你 / 钻鼠标"""
        p = self.pet
        return (self.possess is None and self.kite is None and p.isVisible() and not p.dragging and p.walk is None
                and not p.bubble.isVisible() and p.state in ("idle", "content", "look", "look_left", "happy")
                and not p.danika.active())

    # ----- 变成 / 变回来 -----
    def start(self, why="manual"):
        p = self.pet
        if self.active or not p.isVisible() or p.state == "sleep":
            return False
        if p.soul_active():
            p.soul_dismiss()                 # 魂和身子一起飘出来: 不再是「魂在外面」
        p.stop_walk()
        now = time.monotonic()
        self.active, self.why = True, why
        self.amt, self.faint_said = 1.0, False
        self.pokes.clear()
        self.fall_at = None
        self.next_idle = now + random.uniform(*IDLE_GAP)
        self.next_possess = now + random.uniform(*POSSESS_GAP)
        self.boo_cool = now + 20.0
        self._cache.clear()
        p.set_state("surprised", 1.4)
        p.kick(-1.6)
        p.burst("sparkle", 8)
        p.sfx.play("whoosh")
        self._say("start", GHOST_START.get(why) or GHOST_START["manual"], 2.8, "alert")
        p.emit_event("ghost", stage="start", why=why, memo=MEMO_START.get(why, MEMO_START["manual"]))
        return True

    def end(self, why="manual"):
        if not self.active:
            return
        p = self.pet
        self._unpossess("silent")
        if self.kite is not None:
            self.kite = None
            p.release_mouse(self)
        self.active = False
        self._cache.clear()
        self._ghost_pm = None
        if why in ("faded", "smell") and p.isVisible() and p.state != "sleep":
            p.stop_walk()
            p.kick(-1.8)
            p.burst("puff", 6, at=p.head_point(), bias=(0, 0))
            p.sfx.play("pop")
            p.set_state("surprised", 1.2)
            p.mood.add(3.0)
            QTimer.singleShot(900, lambda: self._say("back_" + why, GHOST_BACK[why], 2.8, "happy"))
        p.emit_event("ghost", stage="end", why=why, memo=MEMO_END.get(why, MEMO_END["manual"]))

    # ----- 附在鼠标上 -----
    def possess_me(self):
        p = self.pet
        if not self.active or self.possess is not None or self.kite is not None or not p.isVisible():
            return
        p.stop_walk()
        self._say("poss", GHOST_POSSESS, 1.6, "happy")
        QTimer.singleShot(700, self._enter_cursor)

    def _enter_cursor(self):
        p = self.pet
        if not self.active or self.possess is not None or not p.isVisible():
            return
        t = time.monotonic()
        self.possess = dict(t0=t, until=t + POSSESS_SEC, win=CursorGhost(), hist=deque(maxlen=160))
        p.burst("sparkle", 5)
        p.sfx.play("whoosh")
        p.emit_event("ghost", stage="possess", memo="变成幽灵的她钻进了你的鼠标里，跟着你的光标到处跑（互动）")

    def unpossess_me(self):
        self._unpossess("menu")

    def _unpossess(self, why):
        ps, self.possess = self.possess, None
        if ps is None:
            return
        try:
            ps["win"].hide()
            ps["win"].deleteLater()
        except Exception:
            pass
        self.next_possess = time.monotonic() + random.uniform(*POSSESS_GAP)
        if why == "silent":
            return
        p = self.pet
        p.kick(-1.2)
        p.burst("sparkle", 4)
        if why == "shaken":
            p.set_state("dizzy", 1.8)
        self._say("unposs_" + why, GHOST_UNPOSSESS.get(why) or GHOST_UNPOSSESS["menu"], 2.2,
                  "alert" if why == "shaken" else "happy")
        p.emit_event("ghost", stage="unpossess", why=why,
                     memo="你使劲甩鼠标，把她从光标里甩了出来，她晕乎乎的（互动）" if why == "shaken"
                     else "她从你的鼠标里飘了出来")

    def _shook(self, hist, t, x):
        """鼠标左右来回甩: 0.7 秒内来回 3 次(每段至少 SHAKE_PX)"""
        hist.append((t, x))
        while hist and t - hist[0][0] > 0.7:
            hist.popleft()
        turns, last, anchor = 0, 0, None
        for _, xx in hist:
            if anchor is None:
                anchor = xx
                continue
            d = xx - anchor
            if abs(d) >= SHAKE_PX:
                dirn = 1 if d > 0 else -1
                if last and dirn != last:
                    turns += 1
                last, anchor = dirn, xx
        if turns >= 3:
            hist.clear()
            return True
        return False

    # ----- 钩子 -----
    def busy(self):
        return "ghost" if self.active else None

    def state_text(self):
        if not self.active:
            return None
        if self.possess is not None:
            return STATUS_POSSESS
        if self.kite is not None:
            return STATUS_KITE
        return STATUS_FAINT if self.amt <= FAINT_AT else STATUS

    def status_text(self):
        if not self.active:
            return None
        return f"👻 灵魂出窍中 · 还剩 {max(0, int(round(self.amt * 100)))}%"

    def lift(self, t):
        if not self.active or self.possess is not None:
            return 0.0
        return self.pet.char_h * (LIFT + BOB * math.sin(t * 1.8))

    def paint(self, key, pm, t):
        if not self.active:
            return None
        a = round(ALPHA[0] + (ALPHA[1] - ALPHA[0]) * max(0.0, min(1.0, self.amt)), 2)
        ck = (pm.cacheKey(), a)
        out = self._cache.get(ck)
        if out is None:
            if len(self._cache) > 16:
                self._cache.clear()
            out = self._ghostify(pm, a)
            self._cache[ck] = out
        self._ghost_pm = out
        if self.possess is not None:                           # 钻进鼠标里了: 原地空着
            return self._blank(pm), 0.0
        return out, 0.0

    def _ghostify(self, pm, a):
        dpr = pm.devicePixelRatio() or 1.0
        out = QPixmap(pm.size())
        out.setDevicePixelRatio(dpr)
        out.fill(Qt.transparent)
        w, h = pm.width() / dpr, pm.height() / dpr
        q = QPainter(out)
        q.setOpacity(a)
        q.drawPixmap(QPointF(0, 0), pm)
        q.setOpacity(1.0)
        q.setCompositionMode(QPainter.CompositionMode_SourceAtop)      # 只染有画的地方: 青白
        q.fillRect(QRectF(0, 0, w, h), TINT)
        q.setCompositionMode(QPainter.CompositionMode_DestinationIn)   # 下半截化成雾
        g = QLinearGradient(0, h * TAIL, 0, h)
        g.setColorAt(0, QColor(0, 0, 0, 255))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        q.fillRect(QRectF(0, 0, w, h), g)
        q.end()
        return out

    def _blank(self, pm):
        b = self._blank_pm
        if b is None or b.size() != pm.size():
            b = QPixmap(pm.size())
            b.setDevicePixelRatio(pm.devicePixelRatio() or 1.0)
            b.fill(Qt.transparent)
            self._blank_pm = b
        return b

    def on_click(self, double):
        if not self.active:
            return False
        if self.possess is not None:
            return True
        p = self.pet
        t = time.monotonic()
        p.note_interaction()
        self.pokes = [x for x in self.pokes if t - x < 2.5] + [t]
        if len(self.pokes) >= POKE_DODGE:
            self.pokes.clear()
            self._dodge()
            return True
        p.kick(-0.8)
        p.tilt += random.choice((-1, 1)) * 4
        self._say("poke", GHOST_POKE, 1.8, throttle=0.8)
        return True

    def _dodge(self):
        """连戳: 嗖地飘到一边"""
        p = self.pet
        r = p.screen_rect()
        d = p.char_w * 1.4 * random.choice((-1, 1))
        lo, hi = r.left() - p.pad_x, r.left() + r.width() - p.width() + p.pad_x
        x = p.x() + d
        if x < lo or x > hi:
            x = p.x() - d
        x = max(lo, min(hi, x))
        p.burst("sparkle", 3)
        if p.start_walk(QPointF(x, p.y()), kind="ghost", speed=900.0):
            self._say("dodge", GHOST_DODGE, 1.8)

    def on_pet(self):
        if not self.active:
            return False
        if self.possess is not None:
            return True
        p = self.pet
        p.note_interaction()
        p.set_state("content", 1.8)
        p.tilt += 5
        self._say("pet", GHOST_PET, 2.6, throttle=2.5)
        return True

    def on_drag_begin(self, pos, delta):
        if not self.active:
            return False
        if self.possess is None:                               # 抓不住: 按着不放, 她跟着你的鼠标飘
            self.pet.capture_mouse(self)
            self.kite = dict(next=0.0)
            self._say("kite", GHOST_KITE, 2.0, throttle=8.0)
        return True

    def on_capture_press(self, e):
        if self.kite is None:
            self.pet.release_mouse(self)

    def on_capture_move(self, e):
        pass

    def on_capture_release(self, e):
        if self.kite is not None:
            self.kite = None
        self.pet.release_mouse(self)

    def on_wheel(self, e):
        if not self.active:
            return False
        p = self.pet
        if self.possess is None:
            p.spin_rem = min(p.spin_rem + 360, 720)
            self._say("spin", GHOST_SPIN, 2.0, throttle=3.0)
        return True

    def on_feed(self, food):
        if not self.active:
            return False
        p = self.pet
        p.note_interaction()
        if self.possess is not None:
            self._unpossess("feed")
        p.stop_walk()
        p.food_fly(food.get("key"))
        QTimer.singleShot(650, lambda: self.active and self._smell(food))
        return True

    def _smell(self, food):
        """闻香: 吃不进嘴, 把香气吸进去"""
        p = self.pet
        key = food.get("key")
        fav = food.get("tier") == "fav"
        mp = p.mouth_point()
        if food.get("trait") == "cold" and not fav:
            p.set_state("shy", 1.8)
            self._say("cold", GHOST_SMELL_COLD, 2.4)
            p.emit_event("ghost", stage="smell", key=key, fav=False, cold=True,
                         memo="你拿冰的东西给变成幽灵的她闻，一点香味都没有，她很失望")
            return
        p.burst("steam", 5, at=mp, bias=(0, -50))
        p.burst("sparkle", 3, at=mp)
        if fav:
            p.set_state("happy", 1.8)
            self._say("fav", GHOST_SMELL_FAV, 2.2, "happy")
            p.emit_event("ghost", stage="smell", key=key, fav=True, cold=False,
                         memo="你拿她最爱吃的东西给她闻，她顺着香味飘回了身体里")
            QTimer.singleShot(1600, lambda: self.active and self.end("smell"))
            return
        self.amt = min(1.0, self.amt + SMELL_GAIN)
        if self.amt > FAINT_AT:
            self.faint_said = False
        p.set_state("content", 1.8)
        p.mood.add(2.0, cat="ghost_smell")
        self._say("smell", GHOST_SMELL, 2.4, "happy")
        p.emit_event("ghost", stage="smell", key=key, fav=False, cold=False,
                     memo="你拿吃的给变成幽灵的她闻，她把香气吸了进去")

    def menu_items(self):
        if not self.active:
            return []
        if self.possess is not None:
            return [("👻", "从鼠标里出来", self.unpossess_me)]
        return [("👻", "附到鼠标上", self.possess_me)]

    def settings_rows(self):
        from ui_kit import Segmented
        seg = Segmented([(0, "正常"), (1, "灵魂")], 1 if self.active else 0, None, h=26, px=11)
        seg.changed.connect(lambda v: self.start("manual") if int(v) else self.end("manual"))

        def sync():
            seg.set_value(1 if self.active else 0)
        return [dict(key="ghost", emoji="👻", title="灵魂形态(测试)", desc="", control=seg, sync=sync)]

    def tune(self, name, value, ctx):
        if not self.active:
            return None
        if name == "danika_script":
            return list(GHOST_DANIKA) if value is None else None        # 达妮卡看不见她
        if name == "sleep_after":
            return 3600.0                                               # 灵魂不犯困
        if name == "lull_ok":
            return False
        if name == "lull_refuse_lines":
            return GHOST_NO_SLEEP
        if name == "butterfly_ok":
            return False
        return None

    def on_event(self, name, data):
        t = time.monotonic()
        if name == "weather":
            self.weather = data.get("kind")
        elif name == "soul":
            stage = data.get("stage")
            if stage == "fall" and data.get("why") != "sick":         # 魂被滚轮转断了: 等你去抓
                self.fall_at = t
            elif stage == "back":
                self.fall_at = None
        elif name == "feed" and not self.active and data.get("trait") == "dark" \
                and data.get("reaction") not in ("refuse", "full", "sulk_worse"):
            self.darks = [x for x in self.darks if t - x < DARK_WINDOW] + [t]
            if len(self.darks) >= 3:
                self.darks.clear()
                QTimer.singleShot(2400, lambda: self.start("dark"))
        elif name == "watered" and self.active and data.get("through"):
            QTimer.singleShot(600, lambda: self.active and self._say("wet", GHOST_WET, 2.2, "happy"))
        elif name == "sleep" and self.active:                          # 被强行弄睡着: 回到身体里
            self.end("sleep")

    # ----- 每帧 -----
    def step(self, t):
        dt = min(0.25, max(0.0, t - self._t))
        self._t = t
        p = self.pet
        if not self.active:
            if self.fall_at is not None and t - self.fall_at >= UNCAUGHT_SEC:
                self.fall_at = None
                if p.soul_active():
                    self.start("soul")
            return
        if not p.isVisible():
            return
        rate = 1.0 / GHOST_SEC
        if self.weather == "sunny":
            rate *= SUN_FASTER
        if self.possess is not None:
            rate *= POSSESS_SLOWER
        self.amt -= rate * dt
        if self.amt <= 0.0:
            self.end("faded")
            return
        if self.amt <= FAINT_AT and not self.faint_said:
            self.faint_said = True
            if self.possess is None:
                p.set_state("surprised", 1.4)
            self._say("faint", GHOST_FAINT, 2.8, "alert")
        ps = self.possess
        if ps is not None:                                             # 跟着光标
            c = QPointF(QCursor.pos())
            w = ps["win"]
            w.set_pm(self._ghost_pm, p.char_w * CURSOR_W)
            w.bob = 3.0 * math.sin(t * 3.0)
            w.rot = 6.0 * math.sin(t * 1.7)
            w.move(int(c.x() + 10), int(c.y() + 6))
            if not w.isVisible():
                w.show()
            w.update()
            if self._shook(ps["hist"], t, c.x()):
                self._unpossess("shaken")
            elif t >= ps["until"]:
                self._unpossess("time")
            return
        if self.kite is not None:                                      # 牵着飘
            if t >= self.kite["next"]:
                self.kite["next"] = t + 0.12
                self._kite_to(QPointF(QCursor.pos()))
            return
        if t >= self.next_wisp:                                        # 身后飘出的小光点
            self.next_wisp = t + random.uniform(0.9, 1.8)
            f = p.foot_point()
            p.burst("sparkle", 1, at=QPointF(f.x() + random.uniform(-0.15, 0.15) * p.char_w, f.y() - p.char_h * 0.2),
                    bias=(0, -30))
        self._boo_step(t)
        if not self._free():
            return
        if t >= self.next_possess:
            self.possess_me()
        elif t >= self.next_idle:
            self.next_idle = t + random.uniform(*IDLE_GAP)
            self._say("idle", GHOST_IDLE, 2.4)

    def _kite_to(self, c):
        p = self.pet
        r = p.screen_rect()
        tx = c.x() - p.width() / 2 + p.char_w * 0.35
        ty = c.y() - p.height() * 0.55
        tx = max(r.left() - p.pad_x, min(tx, r.left() + r.width() - p.width() + p.pad_x))
        ty = max(r.top() - p.char_h * 0.3, min(ty, r.top() + r.height() - p.height() + p.char_h * 0.1))
        cur = p.walk if isinstance(p.walk, dict) else None
        if cur is not None and abs(cur.get("tx", 1e9) - tx) < 16 and abs(cur.get("ty", 1e9) - ty) < 16:
            return
        if math.hypot(tx - p.x(), ty - p.y()) > 8:
            p.start_walk(QPointF(tx, ty), kind="ghost", speed=KITE_SPEED)

    def _boo_step(self, t):
        """鼠标从远处凑近她: 偶尔「哇!」"""
        p = self.pet
        c = QPointF(QCursor.pos())
        center = QPointF(p.x() + p.width() / 2, p.y() + p.height() / 2)
        d = math.hypot(c.x() - center.x(), c.y() - center.y()) / max(1.0, float(p.char_w))
        prev, self.cur_d = self.cur_d, d
        if prev is None or not (prev > 1.8 and d < 1.0) or t < self.boo_cool or not self._free():
            return
        self.boo_cool = t + BOO_COOL
        if random.random() >= BOO_P:
            return
        p.set_state("cheer", 1.2)
        p.kick(-2.0)
        p.burst("emoji", 1, at=QPointF(p.head_point().x(), p.head_point().y() - 10), bias=(0, -30), text="👻")
        self._say("boo", GHOST_BOO, 1.2, "alert")
        QTimer.singleShot(1400, lambda: self.active and self._say("boo2", GHOST_BOO_AFTER, 2.4, "happy"))


def create(pet, log_fn=None):
    if not hasattr(pet, "soul_dismiss"):                       # 旧本体: 没有收魂的接口
        return None
    return Ghost(pet, log_fn)
