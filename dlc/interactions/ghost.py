# -*- coding: utf-8 -*-
"""互动 DLC「灵魂形态」: 她整个人变成半透明的小幽灵 —— 不是死了, 是灵魂出窍的魔法事故; 碰不到她, 她也碰不到你。
怎么变成:
  - 魂被滚轮转断、往天上飘(本体), UNCAUGHT_SEC 秒还没去抓住 -> 魂离开身子, 变成幽灵;
  - DARK_WINDOW 秒内吃下第三份黑暗料理 -> 魂回不去了, 干脆飘出来;
  - 设置「扩展」-> 👻 灵魂形态(测试);
  - 别的插件推事件 ghost_request(why, hold, status, memo, body): 比如生病 DLC —— 重病魂飘上天时没塞回去就送医院,
    身子被接走, 魂落在桌面上。hold 秒内回不去: 不会淡没、最爱吃的香味也引不回去; 那个插件推 ghost_release 时才回到身子里
    (安安静静, 台词归它)。body=False: 身子不在桌面上(在医院)。
身子: 平时她的身子侧躺在原地(X 眼), 是一个单独的小窗(和雪人一样): 可以拖走藏起来, 点它她会急。
  淡没了 / 闻着最爱吃的香味要回去时, 魂飘回身子那儿再钻进去(身子被你拖到哪, 她就飘到哪)。
什么样: 现有每张表情都调成青白、半透明, 下半截化成一缕雾(不用新图); 离地飘着、上下浮(本体 lift 钩子), 脚下没有影子。
越来越淡: 浓度从 1 往下掉, GHOST_SEC 秒掉完(晴天快一半, 附在鼠标上时慢一半, 藏起来、散开时不掉);
  淡到 FAINT_AT 她开始慌, 掉到 0 打个喷嚏回到身子里。
互动(本体原来的效果都不做):
  - 戳她: 手指穿过去, 她打个寒颤咯咯笑; 2.5 秒内连戳 3 下, 她嗖地飘到一边。
  - 弹脑门(按住额头 0.3 秒再松手): 弹空了, 她反过来朝你的光标弹一下, 冒个小火花。
  - 摸头: 摸不到。她把头凑到你的光标上, 小声说「……摸不到你。」
  - 拖她: 没有重量, 抓不住、甩不出去; 按着不放, 她跟着你的鼠标飘(像牵风筝), 松手就停在那儿。
  - 滚轮: 转起来不晕, 但越转越像一团雾; 转太多(MIST_STEP 一格)就散了, 碎成 ORBS 个光点散在屏幕上,
    一个个点回来把她拼好; SCATTER_AUTO 秒没人管, 光点自己慢慢飘回来。
  - 浇水: 水从她身上穿过去(water 插件), 她得意。
  - 喂她: 吃不了, 闻香 —— 吃的飞到嘴边, 香气被她吸进去: 浓度 +SMELL_GAIN、心情 +2; 冰的没香味, 她很失望;
    她最爱吃的那种(fav): 顺着香味回到身子里。不涨饱腹、不算投喂。
  - 附在鼠标上: 她时不时自己钻进你的光标(或菜单「👻 附到鼠标上」), 光标旁边跟着一个小幽灵, 你走到哪她跟到哪;
    使劲左右甩鼠标 = 把她甩晕甩出来; POSSESS_SEC 秒后她玩够了自己出来(菜单「👻 从鼠标里出来」也行)。
  - 钻进东西里: 别的插件推 ghost_enter(where, sec, status) 让她钻进去(天气 DLC: 雪人自己转头、蹦), ghost_exit(where) 出来。
  - 火炉(火炉 DLC 推的 stove 事件): 靠近炉火, 热气把她往上托, 整个人映成青色的鬼火。
  - 吓你: 鼠标从远处凑近她时, 偶尔「哇!」一声。
  - 达妮卡来访: 看不见她, 对着空气交代公务, 薇斯纳在旁边拼命挥手。
  - 哄睡(灵魂不用睡觉)、自己犯困睡着、捉弄插件的那些都不开; 被强行弄睡着(设置「立刻睡着」)就回到身子里。
推事件 ghost(stage: start(why, hold) / smell(key, fav, cold) / flick / possess / unpossess(why) / scatter / reform /
enter(where) / exit(where) / body(what: moved poked) / end(why: faded smell sleep manual release)), 都带 memo。
收事件 ghost_request / ghost_release / ghost_enter / ghost_exit(见上), 还有火炉 DLC 的 stove。
不存档: 关掉再开就回到身子里了。priority = 8: 比生病、哄她、捉弄、温柔先接戳和摸头。只用公开接口(docs/接口规范.md)。
不想要就删掉这个文件。
"""
import math
import random
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

ASSETS = Path(__file__).resolve().parents[2] / "assets"
GHOST_SEC = 240.0                    # 浓度从 1 掉到 0 要多久(秒)
SUN_FASTER = 1.5                     # 晴天掉得快
POSSESS_SLOWER = 0.5                 # 附在鼠标上时掉得慢
FAINT_AT = 0.3                       # 淡到这儿她开始慌
SMELL_GAIN = 0.25                    # 闻到香味, 浓度回来这么多
UNCAUGHT_SEC = 25.0                  # 魂被转断往天上飘, 这么久没抓住 -> 变成幽灵
DARK_WINDOW = 240.0                  # 这段时间里吃第三份黑暗料理 -> 变成幽灵
LIFT = 0.13                          # 离地多高(立绘高的倍数)
BOB = 0.03                           # 上下浮多少
HEAT_LIFT = 0.10                     # 炉火的热气再往上托多少
ALPHA = (0.30, 0.80)                 # 最淡 / 最浓时的不透明度
TINT = QColor(175, 228, 248, 125)    # 青白
FIRE_TINT = QColor(40, 225, 200, 165)  # 靠近炉火: 青色的鬼火
TAIL = 0.58                          # 从立绘这个高度往下渐渐化成雾
POSSESS_SEC = 14.0
POSSESS_GAP = (45.0, 100.0)          # 隔多久自己钻进鼠标一次
CURSOR_W = 0.42                      # 光标旁边那个小幽灵的宽(立绘宽的倍数)
SHAKE_PX = 22                        # 左右甩: 每一段至少挪这么多像素, 0.7 秒内来回 3 次
KITE_SPEED = 520.0                   # 牵着飘的速度(像素/秒)
HOME_SPEED = 650.0                   # 飘回身子的速度
POKE_DODGE = 3                       # 2.5 秒内戳这么多下, 她嗖地躲开
FLICK_ZONE = ((0.36, 0.66), (0.26, 0.48))   # 额头(和捉弄插件一样): 按住 0.3 秒再松手 = 弹脑门
FLICK_HOLD = 0.3
MIST_STEP = 0.2                      # 滚轮一格, 雾气 +这么多; 到 1 就散成光点
MIST_FADE = 0.2                      # 不转了雾气每秒散掉这么多
ORBS = 5                             # 散成几个光点
ORB_SIZE = 44
ORB_DIST = (160.0, 420.0)            # 光点散出去多远(像素)
SCATTER_AUTO = 60.0                  # 散开这么久没人管, 光点自己一个个飘回来
ORB_AUTO_GAP = 3.0                   # 自己飘回来时, 每隔这么久回来一个
BODY_TILT = 78.0                     # 身子侧躺的角度(和本体魂被转断时倒下一样)
BOO_COOL, BOO_P = 50.0, 0.4          # 吓你: 冷却 / 概率
IDLE_GAP = (25.0, 45.0)              # 自己嘀咕一句的间隔

GHOST_START = {"soul": ["……诶?魂……整个飘出来了?!身子还躺在那儿……", "魂没被抓住……我、我变成幽灵了?!"],
               "dark": ["……那个黑乎乎的……把我的魂整个吃出来了?!", "呜……这次魂回不去了,干脆飘出来了!"],
               "manual": ["……诶?我、我怎么透明了?!", "身子好轻……我变成幽灵了?!"],
               "hospital": ["……身子被抬走了……我、我还在这儿啊!", "等等!把我也带上——!(魂被落下了)"]}
GHOST_IDLE = ["轻飘飘的~", "……原来飘着是这种感觉。", "嘿嘿,没有影子了。", "(试着穿过屏幕边)……唔,过不去嘛。", "……好安静啊。"]
GHOST_POKE = ["嘻嘻,穿过去了~", "好凉……你的手指好凉!", "(打了个寒颤)……痒!", "戳不到戳不到~"]
GHOST_DODGE = ["嗖——!抓不到~", "别戳啦!(飘走)"]
GHOST_FLICK = ["弹空啦~换我!(啪)", "嘿嘿,轮到我了——(朝你的光标弹了一下)", "弹不到我~看招!"]
GHOST_PET = ["……摸不到你。", "(把头凑到你的光标上)……就当是摸到了吧。", "……好想快点回去,这样就能摸到你了。"]
GHOST_KITE = ["诶诶?跟、跟着你飘了~", "像风筝一样~"]
GHOST_SPIN = ["呼——转起来轻飘飘的,一点都不晕~", "嘿嘿,幽灵才不会晕~"]
GHOST_MISTY = ["……再、再转就要散了!", "身子……变成雾了……"]
GHOST_SCATTER = ["呜哇——转、转散了!!", "……散、散成好几块了……快把我拼回来!"]
GHOST_ORB = ["……(一个光点飞回来了)", "还差几块……", "再来一块!"]
GHOST_REFORM = ["呼……拼回来了!……别再转啦!", "终于完整了……刚才好可怕……"]
GHOST_SCATTER_FEED = ["……先、先把我拼回来嘛……", "(光点们闻了闻)……拼好了再说!"]
GHOST_WET = ["嘿嘿,水从我身上穿过去了~", "浇不湿~浇不湿~"]
GHOST_SMELL = ["(吸——)……好香……", "闻着就像吃到了一样~", "(把香气吸了进去)……身子好像浓了一点。"]
GHOST_SMELL_COLD = ["……冰的,一点香味都没有……", "闻不到……冰的东西没味道。"]
GHOST_SMELL_FAV = ["……这个味道……!", "是、是我最喜欢的……!(跟着香味飘回身子那儿)"]
GHOST_SMELL_HELD = ["……闻到了……可是身子不在这儿,回不去……", "好香……等我回去了,再真的给我吃一口吧……"]
GHOST_POSSESS = ["嘿嘿,借你的鼠标坐坐~", "钻进去咯~"]
GHOST_UNPOSSESS = {"time": ["玩够了~(从鼠标里飘出来)", "呼,出来透透气~"], "shaken": ["甩、甩晕了……!", "哇啊——别甩啦!!"],
                   "menu": ["好嘛好嘛,出来就是了~"], "feed": ["闻、闻到了!(从鼠标里钻出来)"]}
GHOST_EXIT = ["呼~从{where}里钻出来了!", "嘿嘿,{where}里面好挤~"]
GHOST_BODY_POKE = ["那、那是我的身子!别戳!", "喂!别碰我的身子!", "……(身子被戳了一下,魂这边打了个哆嗦)"]
GHOST_BODY_MOVED = ["诶!我的身子!别拖走!", "你、你把我的身子藏哪去了?!", "……回头我得去那边找身子了。"]
GHOST_STOVE = ["呜哇,热气把我往上托——……诶?变、变成青色的了?!", "火炉边好暖……整个人都映成青色了~"]
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
STATUS_SCATTER = "魂被转散了,碎成几个光点散在屏幕上……"
STATUS_HOME = "魂慢悠悠地飘回身子那儿……"
STATUS_HELD = "身子不在这儿,魂一个人在桌面上飘着,等着回去……"
STATUS_FIRE = "魂被炉火的热气托着,映成了青色的鬼火……"
MEMO_START = {"soul": "她的魂被转断了没人抓住，魂离开了身子，变成了半透明的幽灵，身子侧躺在原地",
              "dark": "她连吃了三份黑暗料理，魂飘了出来变成了半透明的幽灵，身子侧躺在原地",
              "manual": "她变成了半透明的幽灵，身子侧躺在原地"}
MEMO_END = {"faded": "幽灵状态的她越来越淡，飘回身子里，打了个喷嚏醒过来",
            "smell": "她顺着最爱吃的东西的香味，飘回了身子里",
            "sleep": "她睡着了，灵魂回到了身子里", "manual": "她回到了身子里", "release": "她的魂回到了身子里"}


def _pick(pool, last=None):
    c = [x for x in pool if x != last] or list(pool)
    return random.choice(c)


def _tool_window(w, click_through):
    flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
    if click_through:
        flags |= Qt.WindowTransparentForInput
    w.setWindowFlags(flags)
    w.setAttribute(Qt.WA_TranslucentBackground, True)
    w.setAttribute(Qt.WA_ShowWithoutActivating, True)
    if click_through:
        w.setAttribute(Qt.WA_TransparentForMouseEvents, True)


class CursorGhost(QWidget):
    """附在鼠标上: 光标右下角跟着一个小幽灵。不接鼠标(点击穿过去)"""

    def __init__(self):
        super().__init__(None)
        _tool_window(self, True)
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


class BodyWin(QWidget):
    """魂飘出来以后留在地上的身子: 侧躺着、X 眼。能拖走(藏起来), 点一下她会急"""

    def __init__(self, plug, pm, cw, ch, side):
        super().__init__(None)
        _tool_window(self, False)
        self.plug, self.pm = plug, pm
        self.cw, self.ch, self.side = float(cw), float(ch), side
        a = math.radians(BODY_TILT * side)
        pts = [(x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))
               for x, y in ((-cw / 2, -ch), (cw / 2, -ch), (cw / 2, 0.0), (-cw / 2, 0.0))]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        m = 8
        self.resize(int(max(xs) - min(xs)) + 2 * m, int(max(ys) - min(ys)) + 2 * m)
        self.pivot = QPointF(m - min(xs), m - min(ys))      # 脚底(转的那一点)在窗口里的位置
        self.shake_until = 0.0
        self.drag_off = self.press_g = None
        self.moved = False
        self.setCursor(Qt.OpenHandCursor)

    def foot(self):
        """身子的脚底(屏幕坐标)"""
        return QPointF(self.x(), self.y()) + self.pivot

    def place_foot(self, f):
        self.move(int(round(f.x() - self.pivot.x())), int(round(f.y() - self.pivot.y())))

    def paintEvent(self, _):
        q = QPainter(self)
        q.setRenderHint(QPainter.SmoothPixmapTransform, True)
        q.setRenderHint(QPainter.Antialiasing, True)
        jit = 2.0 * math.sin(time.monotonic() * 60.0) if time.monotonic() < self.shake_until else 0.0
        q.setPen(Qt.NoPen)                                   # 地上的影子
        q.setBrush(QColor(30, 40, 70, 38))
        q.drawEllipse(QPointF(self.pivot.x() + self.side * self.ch * 0.45, self.pivot.y() - 2), self.ch * 0.5, 6)
        q.translate(self.pivot.x() + jit, self.pivot.y())
        q.rotate(BODY_TILT * self.side)
        q.drawPixmap(QRectF(-self.cw / 2, -self.ch, self.cw, self.ch), self.pm, QRectF(self.pm.rect()))
        q.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.press_g = e.globalPosition().toPoint()
            self.drag_off = self.press_g - self.frameGeometry().topLeft()
            self.moved = False
            self.setCursor(Qt.ClosedHandCursor)
        e.accept()

    def mouseMoveEvent(self, e):
        if self.drag_off is not None and e.buttons() & Qt.LeftButton:
            if (e.globalPosition().toPoint() - self.press_g).manhattanLength() > 4:
                self.moved = True
            self.move(e.globalPosition().toPoint() - self.drag_off)
        e.accept()

    def mouseReleaseEvent(self, e):
        if self.drag_off is not None:
            self.plug.body_moved() if self.moved else self.plug.body_poked()
        self.drag_off = None
        self.setCursor(Qt.OpenHandCursor)
        e.accept()

    def contextMenuEvent(self, e):
        e.accept()


class Orb(QWidget):
    """转散了的一个光点: 点一下飞回她那儿"""

    def __init__(self, plug, size):
        super().__init__(None)
        _tool_window(self, False)
        self.plug = plug
        self.resize(size, size)
        self.ph = random.uniform(0, math.tau)
        self.fly = None                                      # 飞回去: dict(t0, a, b)
        self.base = None                                     # 散开时待的地方(左上角)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, _):
        q = QPainter(self)
        q.setRenderHint(QPainter.Antialiasing, True)
        w = self.width()
        k = 0.85 + 0.15 * math.sin(time.monotonic() * 4.0 + self.ph)
        c = QPointF(w / 2, w / 2)
        g = QRadialGradient(c, w / 2 * k)
        g.setColorAt(0, QColor(255, 255, 255, 240))
        g.setColorAt(0.35, QColor(190, 240, 255, 200))
        g.setColorAt(1, QColor(150, 220, 250, 0))
        q.setPen(Qt.NoPen)
        q.setBrush(g)
        q.drawEllipse(c, w / 2 * k, w / 2 * k)
        q.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.plug.orb_clicked(self)
        e.accept()

    def contextMenuEvent(self, e):
        e.accept()


class Ghost:
    priority = 8

    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.active = False
        self.why = None
        self.hold_until = None               # 回不去到什么时候(墙上时间); 这之前不会淡没、香味也引不回去
        self.hold_status = None
        self.amt = 1.0                       # 浓度(1 -> 0)
        self.faint_said = False
        self.weather = None
        self.possess = None                  # 附在鼠标上: dict(t0, until, win, hist)
        self.kite = None                     # 被你牵着飘: dict(next)
        self.inside = None                   # 钻进东西里: dict(where, until, status)
        self.scatter = None                  # 散成光点: dict(orbs, got, t0, next_auto)
        self.home = None                     # 飘回身子: dict(why, t0)
        self.body = None                     # 地上的身子(BodyWin)
        self.mist = 0.0                      # 转出来的雾气(0-1)
        self.mist_t = 0.0
        self.heat = 0.0                      # 炉火的热气(0-1)
        self.heat_said = False
        self.stove_rect = None
        self.fpress = None                   # 按住额头: (t0, 窗口坐标)
        self.pokes = []
        self.fall_at = None                  # 本体的魂被转断(她倒下)的时间
        self.darks = []                      # 最近吃下黑暗料理的时间
        self.next_idle = self.next_possess = self.next_wisp = 0.0
        self.boo_cool = 0.0
        self.cur_d = None                    # 上一帧鼠标离她多远(立绘宽的倍数)
        self.say_cool = self.body_cool = 0.0
        self._last = {}
        self._cache = {}
        self._blank_pm = None
        self._ghost_pm = None
        self._body_pm = None
        self._t = time.monotonic()

    # ----- 小工具 -----
    def _line(self, key, pool):
        line = _pick(pool, self._last.get(key))
        self._last[key] = line
        return line

    def _say(self, key, pool, dur=2.4, tone=None, throttle=0.0, fmt=None):
        t = time.monotonic()
        if not pool or (throttle and (t < self.say_cool or self.pet.bubble.isVisible())):
            return
        self.say_cool = t + throttle
        line = self._line(key, pool)
        self.pet.say(line.format(**fmt) if fmt else line, force=True, duration=dur, tone=tone, src="ghost")

    def _held(self):
        return self.hold_until is not None and time.time() < self.hold_until

    def _away(self):
        """她这会儿不在原地(钻进鼠标 / 钻进东西 / 散开了 / 正飘回身子)"""
        return self.possess is not None or self.inside is not None or self.scatter is not None or self.home is not None

    def _free(self):
        """没在忙别的: 能自己嘀咕 / 吓你 / 钻鼠标"""
        p = self.pet
        return (not self._away() and self.kite is None and p.isVisible() and not p.dragging and p.walk is None
                and not p.bubble.isVisible() and p.state in ("idle", "content", "look", "look_left", "happy")
                and not p.danika.active())

    def _norm(self, pos):
        """她窗口里的一个点 -> 立绘里的比例坐标(飘起来的高度算进去; 走路转身时立绘是镜像的)"""
        p = self.pet
        up = self.lift(time.monotonic())
        nx = (pos.x() - p.pad_x) / max(1.0, float(p.char_w))
        ny = (pos.y() + up - p.pad_top()) / max(1.0, float(p.char_h))
        if getattr(p, "face", 1.0) < 0:
            nx = 1.0 - nx
        return nx, ny

    # ----- 变成 / 变回来 -----
    def start(self, why="manual", hold=None, status=None, memo=None, body=True):
        p = self.pet
        if self.active:                      # 已经是幽灵了: 只是这回回不去了
            if hold:
                self.hold_until, self.hold_status, self.why = time.time() + float(hold), status, why
                p.emit_event("ghost", stage="start", why=why, hold=float(hold), memo=memo or MEMO_START.get(why, ""))
            return True
        if not p.isVisible() or p.state == "sleep":
            return False
        if p.soul_active():
            p.soul_dismiss()                 # 魂整个离开了身子: 不再是「魂在外面晃」
        p.stop_walk()
        now = time.monotonic()
        self.active, self.why = True, why
        self.hold_until = time.time() + float(hold) if hold else None
        self.hold_status = status
        self.amt, self.faint_said = 1.0, False
        self.mist = self.heat = 0.0
        self.heat_said = False
        self.pokes.clear()
        self.fall_at = None
        self.next_idle = now + random.uniform(*IDLE_GAP)
        self.next_possess = now + random.uniform(*POSSESS_GAP)
        self.boo_cool = now + 20.0
        self._cache.clear()
        if body:
            self._drop_body()
        p.set_state("surprised", 1.4)
        p.kick(-1.6)
        p.burst("sparkle", 8)
        p.sfx.play("whoosh")
        self._say("start", GHOST_START.get(why) or GHOST_START["manual"], 2.8, "alert")
        p.emit_event("ghost", stage="start", why=why, hold=float(hold or 0.0),
                     memo=memo or MEMO_START.get(why, MEMO_START["manual"]))
        return True

    def end(self, why="manual"):
        """回到身子里。淡没了 / 闻着香味: 先飘回身子那儿再钻进去; 别的(设置里关、睡着、放回来)马上回去"""
        if not self.active or self.home is not None:
            return
        p = self.pet
        self._unpossess("silent")
        self._exit_inside(quiet=True)
        self._gather_all()
        if self.kite is not None:
            self.kite = None
            p.release_mouse(self)
        b = self.body
        if b is not None and why in ("faded", "smell") and p.isVisible():
            f = p.foot_point()
            off = QPointF(f.x() - p.x(), f.y() - p.y())
            target = b.foot() - off
            if math.hypot(target.x() - p.x(), target.y() - p.y()) > 8 and \
                    p.start_walk(target, kind="ghost_home", speed=HOME_SPEED):
                self.home = dict(why=why, t0=time.monotonic())
                return
        self._finish(why)

    def _finish(self, why):
        p = self.pet
        self.home = None
        self._remove_body()
        self.active = False
        self.hold_until = self.hold_status = None
        self.mist = self.heat = 0.0
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

    # ----- 地上的身子 -----
    def _body_pixmap(self):
        if self._body_pm is None:
            for name in ("ko", "dizzy", "idle"):
                f = ASSETS / f"{name}.png"
                pm = QPixmap(str(f)) if f.is_file() else QPixmap()
                if not pm.isNull():
                    self._body_pm = self.pet.fit_sprite(pm)
                    break
        return self._body_pm

    def _drop_body(self):
        p = self.pet
        pm = self._body_pixmap()
        if pm is None:
            return
        r = p.screen_rect()
        f = p.foot_point()
        side = 1 if f.x() + p.char_h < r.left() + r.width() else -1        # 倒向有地方的那一侧
        b = BodyWin(self, pm, p.char_w, p.char_h, side)
        b.place_foot(f)
        b.show()
        self.body = b

    def _remove_body(self):
        b, self.body = self.body, None
        if b is not None:
            try:
                b.hide()
                b.deleteLater()
            except Exception:
                pass

    def body_poked(self):
        b, p = self.body, self.pet
        if b is None:
            return
        b.shake_until = time.monotonic() + 0.35
        b.update()
        p.note_interaction()
        if not self._away():
            p.kick(-1.0)
        if time.monotonic() >= self.body_cool:                     # 身子被碰: 一定要说出来(不等别的气泡)
            self.body_cool = time.monotonic() + 1.0
            self._say("bpoke", GHOST_BODY_POKE, 2.2, "alert")
        p.emit_event("ghost", stage="body", what="poked", memo="你戳了戳她留在地上的身子，她的魂急了（互动）")

    def body_moved(self):
        b, p = self.body, self.pet
        if b is None:
            return
        p.note_interaction()
        f = b.foot()
        d = math.hypot(f.x() - p.foot_point().x(), f.y() - p.foot_point().y()) / max(1.0, float(p.char_w))
        if d > 2.0 and time.monotonic() >= self.body_cool:
            self.body_cool = time.monotonic() + 1.0
            self._say("bmove", GHOST_BODY_MOVED, 2.4, "alert")
        p.emit_event("ghost", stage="body", what="moved", far=round(d, 1),
                     memo="你把她留在地上的身子拖走藏了起来（互动）" if d > 2.0 else None)

    # ----- 附在鼠标上 -----
    def possess_me(self):
        p = self.pet
        if not self.active or self._away() or self.kite is not None or not p.isVisible():
            return
        p.stop_walk()
        self._say("poss", GHOST_POSSESS, 1.6, "happy")
        QTimer.singleShot(700, self._enter_cursor)

    def _enter_cursor(self):
        p = self.pet
        if not self.active or self._away() or not p.isVisible():
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

    # ----- 钻进东西里(别的插件请她进去) -----
    def _enter_inside(self, where, sec, status, memo):
        p = self.pet
        if not self.active or self._away() or self.kite is not None or not p.isVisible():
            return
        p.stop_walk()
        self.inside = dict(where=where, until=time.monotonic() + max(1.0, sec) + 2.0, status=status)
        p.burst("sparkle", 5)
        p.sfx.play("whoosh")
        p.emit_event("ghost", stage="enter", where=where, memo=memo or f"变成幽灵的她钻进了{where}里（互动）")

    def _exit_inside(self, quiet=False):
        ins, self.inside = self.inside, None
        if ins is None:
            return
        p = self.pet
        if not quiet:
            p.kick(-1.2)
            p.burst("sparkle", 4)
            self._say("exit", GHOST_EXIT, 2.2, "happy", fmt=dict(where=ins["where"]))
        p.emit_event("ghost", stage="exit", where=ins["where"], memo=f"她从{ins['where']}里钻了出来")

    # ----- 转散了 -----
    def _scatter_now(self):
        p = self.pet
        self._unpossess("silent")
        if self.kite is not None:
            self.kite = None
            p.release_mouse(self)
        p.stop_walk()
        r = p.screen_rect()
        c = QPointF(p.x() + p.width() / 2, p.y() + p.height() / 2)
        orbs = []
        for i in range(ORBS):
            a = math.tau * i / ORBS + random.uniform(-0.4, 0.4)
            d = random.uniform(*ORB_DIST)
            x = min(max(c.x() + math.cos(a) * d, r.left() + 10), r.left() + r.width() - ORB_SIZE - 10)
            y = min(max(c.y() + math.sin(a) * d * 0.7, r.top() + 10), r.top() + r.height() - ORB_SIZE - 10)
            o = Orb(self, ORB_SIZE)
            o.base = QPointF(x, y)
            o.move(int(x), int(y))
            o.show()
            orbs.append(o)
        t = time.monotonic()
        self.scatter = dict(orbs=orbs, got=0, t0=t, next_auto=t + SCATTER_AUTO)
        self.mist = 1.0
        p.burst("sparkle", 10, at=c, bias=(0, 0))
        p.sfx.play("whoosh")
        self._say("scatter", GHOST_SCATTER, 2.8, "alert")
        p.emit_event("ghost", stage="scatter", n=ORBS, memo="你把变成幽灵的她转散了，她碎成几个光点散在屏幕上（互动）")

    def orb_clicked(self, orb):
        sc = self.scatter
        if sc is None or orb.fly is not None or orb not in sc["orbs"]:
            return
        self.pet.note_interaction()
        self._fly_orb(orb)

    def _fly_orb(self, orb):
        p = self.pet
        b = QPointF(p.x() + p.width() / 2 - orb.width() / 2, p.y() + p.height() / 2 - orb.height() / 2)
        orb.fly = dict(t0=time.monotonic(), a=QPointF(orb.x(), orb.y()), b=b)
        p.sfx.play("tick")

    def _orb_home(self, orb):
        sc, p = self.scatter, self.pet
        try:
            sc["orbs"].remove(orb)
            orb.hide()
            orb.deleteLater()
        except Exception:
            pass
        sc["got"] += 1
        self.mist = max(0.0, 1.0 - sc["got"] / float(ORBS))
        self._cache.clear()
        p.burst("sparkle", 3)
        if not sc["orbs"]:
            self._reform()
        elif sc["got"] in (1, ORBS - 1):
            self._say("orb", GHOST_ORB, 1.6, throttle=0.5)

    def _reform(self):
        p = self.pet
        self.scatter = None
        self.mist, self.mist_t = 0.0, time.monotonic()
        self._cache.clear()
        p.kick(-1.6)
        p.burst("sparkle", 8)
        p.sfx.play("pop")
        p.set_state("happy", 1.6)
        self._say("reform", GHOST_REFORM, 2.6, "happy")
        p.emit_event("ghost", stage="reform", memo="散成光点的她被拼了回来")

    def _gather_all(self):
        """马上收掉所有光点(结束 / 回身子时)"""
        sc, self.scatter = self.scatter, None
        if sc is None:
            return
        for o in sc["orbs"]:
            try:
                o.hide()
                o.deleteLater()
            except Exception:
                pass
        self.mist = 0.0

    def _scatter_step(self, t):
        sc = self.scatter
        for o in list(sc["orbs"]):
            if o.fly is not None:
                u = min(1.0, (t - o.fly["t0"]) / 0.45)
                e = u * u * (3 - 2 * u)
                pos = o.fly["a"] + (o.fly["b"] - o.fly["a"]) * e
                o.move(int(pos.x()), int(pos.y()))
                if u >= 1.0:
                    self._orb_home(o)
                    if self.scatter is None:
                        return
            else:
                o.move(int(o.base.x() + 3 * math.sin(t * 1.3 + o.ph)), int(o.base.y() + 4 * math.sin(t * 1.7 + o.ph)))
                o.update()
        if t >= sc["next_auto"]:                                      # 没人管: 光点自己一个个飘回来
            sc["next_auto"] = t + ORB_AUTO_GAP
            waiting = [o for o in sc["orbs"] if o.fly is None]
            if waiting:
                self._fly_orb(waiting[0])

    # ----- 钩子 -----
    def busy(self):
        return "ghost" if self.active else None

    def state_text(self):
        if not self.active:
            return None
        if self.home is not None:
            return STATUS_HOME
        if self.scatter is not None:
            return STATUS_SCATTER
        if self.inside is not None:
            return self.inside.get("status") or STATUS_POSSESS
        if self.possess is not None:
            return STATUS_POSSESS
        if self.kite is not None:
            return STATUS_KITE
        if self._held():
            return self.hold_status or STATUS_HELD
        if self.heat > 0.5:
            return STATUS_FIRE
        return STATUS_FAINT if self.amt <= FAINT_AT else STATUS

    def status_text(self):
        if not self.active:
            return None
        if self._held():
            left = max(0, int(self.hold_until - time.time()))
            return f"👻 灵魂出窍中 · 还要 {left // 60}:{left % 60:02d} 才回得去"
        return f"👻 灵魂出窍中 · 还剩 {max(0, int(round(self.amt * 100)))}%"

    def lift(self, t):
        if not self.active or self.possess is not None or self.inside is not None or self.scatter is not None:
            return 0.0
        ch = self.pet.char_h
        up = LIFT + BOB * math.sin(t * 1.8)
        if self.heat > 0.01:                                           # 炉火的热气往上托, 一抖一抖的
            up += self.heat * (HEAT_LIFT + 0.015 * math.sin(t * 9.0))
        return ch * up

    def paint(self, key, pm, t):
        if not self.active:
            return None
        a = ALPHA[0] + (ALPHA[1] - ALPHA[0]) * max(0.0, min(1.0, self.amt))
        a = round(a * (1.0 - 0.55 * self.mist), 2)                      # 转成雾: 更淡
        heat = round(self.heat * 5) / 5.0
        ck = (pm.cacheKey(), a, heat)
        out = self._cache.get(ck)
        if out is None:
            if len(self._cache) > 24:
                self._cache.clear()
            out = self._ghostify(pm, a, heat)
            self._cache[ck] = out
        self._ghost_pm = out
        if self.possess is not None or self.inside is not None or self.scatter is not None:   # 不在原地: 空着
            return self._blank(pm), 0.0
        return out, 0.0

    def _ghostify(self, pm, a, heat):
        dpr = pm.devicePixelRatio() or 1.0
        out = QPixmap(pm.size())
        out.setDevicePixelRatio(dpr)
        out.fill(Qt.transparent)
        w, h = pm.width() / dpr, pm.height() / dpr
        tint = QColor(TINT)
        if heat > 0:                                                   # 靠近炉火: 青色的鬼火
            tint = QColor(int(TINT.red() + (FIRE_TINT.red() - TINT.red()) * heat),
                          int(TINT.green() + (FIRE_TINT.green() - TINT.green()) * heat),
                          int(TINT.blue() + (FIRE_TINT.blue() - TINT.blue()) * heat),
                          int(TINT.alpha() + (FIRE_TINT.alpha() - TINT.alpha()) * heat))
        q = QPainter(out)
        q.setOpacity(a)
        q.drawPixmap(QPointF(0, 0), pm)
        q.setOpacity(1.0)
        q.setCompositionMode(QPainter.CompositionMode_SourceAtop)      # 只染有画的地方
        q.fillRect(QRectF(0, 0, w, h), tint)
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

    def on_mouse_press(self, e):
        if not self.active or self._away() or e.button() != Qt.LeftButton:
            return False
        nx, ny = self._norm(e.position())
        (x0, x1), (y0, y1) = FLICK_ZONE
        self.fpress = (time.monotonic(), (nx, ny)) if (x0 <= nx <= x1 and y0 <= ny <= y1) else None
        return False

    def on_click(self, double):
        if not self.active:
            return False
        if self._away():
            return True
        p = self.pet
        t = time.monotonic()
        p.note_interaction()
        fp, self.fpress = self.fpress, None
        if fp is not None and t - fp[0] >= FLICK_HOLD:                  # 按住额头再松手: 弹空了, 她弹回来
            self._flick_back()
            return True
        self.pokes = [x for x in self.pokes if t - x < 2.5] + [t]
        if len(self.pokes) >= POKE_DODGE:
            self.pokes.clear()
            self._dodge()
            return True
        p.kick(-0.8)
        p.tilt += random.choice((-1, 1)) * 4
        self._say("poke", GHOST_POKE, 1.8, throttle=0.8)
        return True

    def _flick_back(self):
        p = self.pet
        c = QPointF(QCursor.pos())
        p.kick(-1.6)
        p.set_state("cheer", 1.0)
        p.burst("star", 3, at=c, bias=(0, 0))
        p.burst("sparkle", 4, at=c, bias=(0, 0))
        p.sfx.play("tick")
        self._say("flick", GHOST_FLICK, 2.2, "happy")
        p.emit_event("ghost", stage="flick", memo="你想弹变成幽灵的她脑门，手指穿了过去；她反过来朝你的光标弹了一下（互动）")

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
        if self._away():
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
        self.fpress = None
        if not self._away():                                           # 抓不住: 按着不放, 她跟着你的鼠标飘
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
        if self._away():
            return True
        try:
            n = max(1, int(round(abs(e.angleDelta().y() or e.angleDelta().x()) / 120.0)))
        except Exception:
            n = 1
        p.spin_rem = min(p.spin_rem + 360, 720)
        self.mist = min(1.0, self.mist + MIST_STEP * n)
        self.mist_t = time.monotonic()
        if self.mist >= 1.0:
            self._scatter_now()
        elif self.mist >= 0.55:
            self._say("misty", GHOST_MISTY, 1.8, "alert", throttle=1.5)
        else:
            self._say("spin", GHOST_SPIN, 2.0, throttle=3.0)
        return True

    def on_feed(self, food):
        if not self.active:
            return False
        p = self.pet
        p.note_interaction()
        if self.scatter is not None or self.home is not None:
            self._say("sfeed", GHOST_SCATTER_FEED, 2.2, throttle=1.5)
            return True
        if self.possess is not None:
            self._unpossess("feed")
        self._exit_inside()
        p.stop_walk()
        p.food_fly(food.get("key"))
        QTimer.singleShot(650, lambda: self.active and self.home is None and self._smell(food))
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
        if fav and self._held():                                   # 身子不在这儿: 引不回去
            self.amt = min(1.0, self.amt + SMELL_GAIN)
            p.set_state("content", 1.8)
            self._say("held", GHOST_SMELL_HELD, 2.6)
            p.emit_event("ghost", stage="smell", key=key, fav=True, cold=False, held=True,
                         memo="你拿她最爱吃的东西给她闻，可她的身子不在这儿，回不去")
            return
        if fav:
            p.set_state("happy", 1.8)
            self._say("fav", GHOST_SMELL_FAV, 2.2, "happy")
            p.emit_event("ghost", stage="smell", key=key, fav=True, cold=False,
                         memo="你拿她最爱吃的东西给她闻，她顺着香味飘回了身子里")
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
        if not self.active or self.scatter is not None or self.home is not None or self.inside is not None:
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
        if name == "ghost_request":                                   # 别的插件: 让她变成幽灵(回不去 hold 秒)
            self.start(str(data.get("why") or "manual"), hold=data.get("hold"), status=data.get("status"),
                       memo=data.get("memo"), body=bool(data.get("body", True)))
        elif name == "ghost_release":                                # 别的插件: 可以回身子里了
            if self.active:
                self.end("release")
        elif name == "ghost_enter":                                  # 别的插件: 请她钻进某样东西里
            self._enter_inside(str(data.get("where") or "那里"), float(data.get("sec") or 10.0), data.get("status"),
                               data.get("memo"))
        elif name == "ghost_exit":
            if self.inside is not None and data.get("where") in (None, self.inside["where"]):
                self._exit_inside()
        elif name == "walk_end" and data.get("kind") == "ghost_home" and self.home is not None:
            self._finish(self.home["why"])
        elif name == "stove":                                        # 火炉 DLC: 火炉在哪
            stage = data.get("stage")
            if stage in ("place", "move") and data.get("rect"):
                try:
                    self.stove_rect = QRect(*[int(v) for v in data["rect"]])
                except Exception:
                    self.stove_rect = None
            elif stage == "remove":
                self.stove_rect = None
        elif name == "weather":
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
        elif name == "sleep" and self.active:                          # 被强行弄睡着: 回到身子里
            self.home = None
            self.end("sleep")

    # ----- 每帧 -----
    def _stove_near(self):
        r, p = self.stove_rect, self.pet
        if r is None or not p.isVisible():
            return False
        body = QRect(int(p.x() + p.pad_x), int(p.y() + p.pad_top()), int(p.char_w), int(p.char_h))
        m = int(p.char_w * 0.5)
        return body.adjusted(-m, -int(p.char_h * 0.2), m, int(p.char_h * 0.2)).intersects(r)

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
        for w in (self.body, *(self.scatter["orbs"] if self.scatter else ())):   # 她藏起来时, 身子、光点也藏
            if w is not None and w.isVisible() != p.isVisible():
                w.setVisible(p.isVisible())
        if not p.isVisible():
            return
        if self.home is not None:                                      # 飘回身子: 到了(walk_end)或走不动了就算到
            if p.walk is None or t - self.home["t0"] > 6.0:
                self._finish(self.home["why"])
            return
        if self.body is not None:
            self.body.update()
        if self.scatter is not None:
            self._scatter_step(t)
            return
        if self.mist > 0 and t - self.mist_t > 1.0:                    # 不转了: 雾气慢慢散掉
            self.mist = max(0.0, self.mist - MIST_FADE * dt)
        near = self._stove_near() and not self._away()
        self.heat = min(1.0, self.heat + dt * 1.5) if near else max(0.0, self.heat - dt * 1.0)
        if self.heat > 0.6 and not self.heat_said:
            self.heat_said = True
            self._say("stove", GHOST_STOVE, 2.8, "alert")
            p.emit_event("ghost", stage="stove", memo="火炉的热气把变成幽灵的她往上托，她被映成了青色的鬼火")
        elif self.heat < 0.15:
            self.heat_said = False
        rate = 0.0 if (self._held() or self.inside is not None) else 1.0 / GHOST_SEC   # 回不去 / 钻在东西里时不淡
        if self.hold_until is not None and not self._held():           # 等的时间到了(没人来接): 照常慢慢淡
            self.hold_until = self.hold_status = None
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
            if not self._away():
                p.set_state("surprised", 1.4)
            self._say("faint", GHOST_FAINT, 2.8, "alert")
        if self.inside is not None:
            if t >= self.inside["until"]:                              # 叫她进去的那个插件忘了叫她出来
                self._exit_inside()
            return
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
