# -*- coding: utf-8 -*-
"""互动 DLC「捉弄」: 欺负欺负她。
  1. 在她脸上画画: 她睡着时 右键 / 托盘「互动」-> 🖌 画花脸(醒着时菜单里没有这一项)。鼠标变成一支小毛笔,
     在她身上按住拖就是画, 右键或菜单「画好了」收笔。
     画多了她会痒得动一下(「唔……」), 这时候停一停; 动完 1.2 秒内还接着画就会把她弄醒 —— 当场被抓包, 更生气。
     醒了她不知道, 顶着一脸涂鸦到处晃; 过几分钟自己发现, 或者你给她「🪞 照照镜子」: 先愣住, 再炸毛, 一边擦一边记仇
     (5 分钟内摸头会被拍开)。心情 -6(被抓包 -8)。
  2. 抢头冠: 按住她的头冠往上一扯, 头冠就到你手里了(也可以菜单「👑 抢她的头冠」, 头冠跟着鼠标, 点一下扔掉)。
     她捂着头追: 跑到底下蹦起来够, 够得着就抢回去; 你举得太高她只能原地蹦, 十几秒够不着就蹲下委屈。
     松手头冠掉在地上, 她跑过去捡起来戴好。抢回来后 90 秒内再伸手, 她会护住头冠。心情 -3。
     要 assets/notiara.png(没戴头冠、捂着头的那张脸)才开; 头冠本身是 assets/tiara.png。
  3. 假装喂她: 按住 Ctrl 再点吃的。吃的飞到嘴边又被你抽走, 她「啊呜」咬了个空。连骗三次她就学乖了:
     10 分钟内再 Ctrl 喂她不上当; 这段时间真喂她, 她也要先眯眼确认一下才吃。心情 -2。
  4. 弹脑门: 按住她额头别动, 0.3 秒后开始蓄力(她会紧张), 松手「啪」一下 —— 蓄得越久越疼, 额头鼓起一个小包, 慢慢消。
     30 秒内弹三下, 她会捂住额头半分钟不让弹。心情 -1.5 ~ -4。要 assets/ouch.png(揉额头), 没有就借委屈那张。
达妮卡来访时(调节口 danika_script): 她脸上被画了还不知道 -> 达妮卡指出来、拿毛巾帮她擦掉, 走了以后她冲你生气;
     额头有包 -> 达妮卡问是谁弹的。
好感: 每样每天最多扣 DAILY 次(各 -1)。推事件: doodle(stage) / tiara(stage) / fake_feed(n) / flick(power), 都带 memo。
记在 <数据目录>/tease.json(每天扣过几次)。priority = -2: 别的插件先接; 画在立绘上的东西(涂鸦、小包)最后画, 盖在最上面。
只用公开接口(docs/接口规范.md)。不想要就删掉这个文件。
"""
import json
import math
import os
import random
import time
from datetime import date
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (QColor, QCursor, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import QToolTip, QWidget

from stats import data_dir

ASSETS = Path(__file__).resolve().parents[2] / "assets"
DAILY = {"doodle": 2, "tiara": 2, "fake": 2, "flick": 2}       # 每天最多因为这一样扣几次好感

# ----- 1. 在脸上画画 -----
INK = QColor(34, 34, 46)
INK_W = 0.013                       # 笔画粗细(立绘宽的倍数)
ITCH_STIR = 0.75                    # 画了这么长(立绘宽的倍数, 累计)她就痒得动一下
STIR_GRACE = 1.2                    # 她动了以后这么多秒内还接着画 -> 醒了, 当场抓包
NOTICE_SEC = (150.0, 300.0)         # 醒来后过多久自己发现
WIPE_SEC = 2.6                      # 擦掉要多久
GRUDGE_SEC = 300.0                  # 记仇: 这段时间摸头会被拍开
DOODLE_STIR = ["唔……", "……嗯……痒……", "……(皱了皱鼻子)"]
DOODLE_CAUGHT = ["……嗯?你、你手里拿的什么?!", "!!你在我脸上画什么!!", "……毛笔?!……我的脸!!"]
DOODLE_SELF = ["……脸上怎么黏黏的?", "……?(摸了摸脸, 看了看手)", "……手上怎么有墨……"]
DOODLE_MIRROR = ["……镜子?给我干嘛……", "嗯?照镜子?"]
DOODLE_FOUND = ["!!!这、这是什么!!", "我的脸——!!你画了什么!!", "胡、胡子?!你给我站住!!"]
DOODLE_WIPED = ["……哼!洗干净了!", "擦、擦掉了……你给我记住!"]
GRUDGE_PET = ["哼,别碰我!你手上还有墨!", "不许摸!先把毛笔交出来!", "……(躲开)还记着呢。"]
STATUS_DRAWING = "睡得正香,浑然不知有人在她脸上作画……"
STATUS_WEARING = "顶着一脸涂鸦,自己还浑然不觉……"
STATUS_WIPING = "使劲擦着脸,一边擦一边瞪你……"

# ----- 2. 抢头冠 -----
TIARA_ZONE = ((0.22, 0.72), (-0.05, 0.30))     # 头冠在立绘里的范围(宽、高的比例)
TIARA_W = 0.43                       # 头冠的宽 = 立绘宽的多少
TIARA_REACH = 0.55                   # 蹦起来能够到头顶上方多高(立绘高的倍数)
TIARA_GIVEUP = 12.0                  # 举高了够不着这么久, 她就蹲下委屈
TIARA_GUARD = 90.0                   # 抢回来以后这么久内再伸手, 她护住头冠
TIARA_STOLEN = ["啊!我的头冠!!", "还、还给我!!", "呀——!头冠!"]
TIARA_CHASE = ["还给我!", "别跑!", "那是我的!!"]
TIARA_HIGH = ["够、够不着……", "你、你举那么高干嘛!", "跳……跳不上去……"]
TIARA_SAD = ["呜……我的头冠……", "……不要了啦……(蹲下)"]
TIARA_BACK_QUICK = ["哼!抢回来了!", "抓到了!不许再抢!"]
TIARA_BACK_SLOW = ["……终于拿回来了……", "呼……还好没丢。"]
TIARA_PICKUP = ["(捡起来,拍拍灰)……哼。", "找到了!……下次不许扔!"]
TIARA_GUARDED = ["不许碰!(护住头冠)", "哼,头冠不给你!"]
STATUS_TIARA = "捂着脑袋追头冠……"
STATUS_TIARA_SAD = "蹲在地上,眼巴巴地看着头冠……"

# ----- 3. 假装喂 -----
FAKE_WINDOW = 1800.0                 # 这段时间里骗了几次
FAKE_WISE = 3                        # 骗到第几次她学乖
DISTRUST_SEC = 600.0
FAKE_BITE = ["……诶?吃的呢?", "啊呜——……咦?", "……(咬了个空)"]
FAKE_FIRST = ["你、你骗我!", "……坏人!"]
FAKE_AGAIN = ["哼!又耍我!", "我的、我的点心呢!!", "还来?!"]
FAKE_WISE_LINE = ["……哼,记住你了。下次不上当!", "第三次了!我全都记下来了!"]
FAKE_NOPE = ["哼,我才不上当。", "……我看着呢。", "同一招对我没用了!"]
FAKE_SUSPECT = ["……这次是真的吧?", "……(眯眼)不会又抽回去吧?"]

# ----- 4. 弹脑门 -----
FLICK_ZONE = ((0.36, 0.66), (0.26, 0.48))
FLICK_HOLD = 0.3                     # 按住不动这么久开始蓄力
FLICK_FULL = 1.3                     # 蓄满要多久
FLICK_SPOT = (0.57, 0.40)            # 小包长在哪儿(立绘里的比例)
FLICK_GUARD = (3, 30.0, 30.0)        # 30 秒内弹 3 下 -> 捂住额头 30 秒
FLICK_CHARGE = ["……你、你想干嘛?", "……(手指头对着我额头……)", "等、等一下——"]
FLICK_HIT = (["哎呀!", "唔!"], ["痛!干嘛弹我!", "呜……好痛!"], ["痛痛痛——!!", "呜哇!!肿、肿起来了!!"])
FLICK_GUARDED = ["不许再弹了!(捂住额头)", "哼,额头不给你!"]
FLICK_CANCEL = ["……呼?不弹了?", "……吓死我了。"]
STATUS_BUMP = "额头上鼓着个小包,时不时摸一下……"

BUSY_HER = {"hidden", "drag", "fling", "throw", "spin", "danika", "food_fx", "edge", "frozen", "sick"}

# ----- 达妮卡来访时: 脸上被画了 / 额头有包 -----
DANIKA_DOODLE = [("danika", "……薇斯纳大人。您脸上。"), ("vesna", "脸上?……有什么吗?"),
                 ("danika", "……有人在您脸上画了画。"), ("vesna", "诶?!……我、我的脸——!"),
                 ("danika", "别动。……擦掉了。"), ("danika", "下次睡觉记得锁门。告辞。")]
DANIKA_WIPE_LINE = 4                 # 第 5 句(「擦掉了」)开始的时候擦
DANIKA_BUMP = [("danika", "……额头怎么肿了。"), ("vesna", "……被、被弹的!"), ("danika", "谁弹的。"),
               ("vesna", "哼……就是那个人!"), ("danika", "……我记下了。告辞。")]
DANIKA_AFTER = ["……你!在我脸上画了画还不告诉我!!", "达妮卡都看见了!……你给我等着!"]


def _brush_cursor():
    """画画时的鼠标: 一支小毛笔(木杆 + 银箍 + 黑笔头), 笔尖就是落笔的点"""
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    q = QPainter(pm)
    q.setRenderHint(QPainter.Antialiasing, True)
    q.setPen(QPen(QColor(255, 255, 255), 8, Qt.SolidLine, Qt.RoundCap))     # 白边: 深色桌面上也看得见
    q.drawLine(QPointF(27, 5), QPointF(12, 20))
    q.setPen(QPen(QColor(70, 46, 30), 6, Qt.SolidLine, Qt.RoundCap))
    q.drawLine(QPointF(27, 5), QPointF(12, 20))
    q.setPen(QPen(QColor(200, 146, 88), 3.6, Qt.SolidLine, Qt.RoundCap))
    q.drawLine(QPointF(27, 5), QPointF(12, 20))
    q.setPen(QPen(QColor(168, 178, 198), 5, Qt.SolidLine, Qt.FlatCap))      # 银箍
    q.drawLine(QPointF(14, 18), QPointF(11, 21))
    tip = QPainterPath(QPointF(12.5, 18.5))                                  # 笔头
    tip.quadTo(QPointF(5.5, 20.5), QPointF(2, 30))
    tip.quadTo(QPointF(9.5, 26.5), QPointF(13.5, 21.5))
    tip.closeSubpath()
    q.setPen(QPen(QColor(255, 255, 255), 1.3))
    q.setBrush(QColor(INK))
    q.drawPath(tip)
    q.end()
    return QCursor(pm, 2, 29)


def _pick(pool, last=None):
    c = [x for x in pool if x != last] or list(pool)
    return random.choice(c)


class TiaraWin(QWidget):
    """被抢走的头冠: 跟着鼠标 / 掉在地上; 跟着鼠标时点一下 = 扔掉"""

    def __init__(self, plug, pm, w):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.plug, self.pm = plug, pm
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        h = w * pm.height() / max(1, pm.width())
        self.resize(int(w), int(h))
        self.setCursor(Qt.ClosedHandCursor)
        self.rot = 0.0

    def center_at(self, c):
        self.move(int(c.x() - self.width() / 2), int(c.y() - self.height() / 2))

    def center(self):
        return QPointF(self.x() + self.width() / 2, self.y() + self.height() / 2)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(self.rot)
        p.translate(-self.width() / 2, -self.height() / 2)
        p.drawPixmap(QRectF(0, 0, self.width(), self.height()), self.pm, QRectF(self.pm.rect()))
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.plug.tiara_clicked()
        e.accept()


class Tease:
    priority = -2

    def __init__(self, pet, log_fn=None):
        self.pet, self.log = pet, log_fn
        self.path = data_dir() / "tease.json"
        self.store = self._load()
        self._last = {}
        self._cache = {}
        # 1. 画脸
        self.drawing = False
        self.strokes, self.cur = [], None
        self.doodle = None                   # None / fresh(她睡着) / wearing(醒着还不知道) / wiping
        self.ink = 1.0
        self.itch, self.stir_at = 0.0, -1e9
        self.notice_at = self.wipe_t0 = 0.0
        self.grudge_until = 0.0
        self.caught = False
        self._brush = None                   # 毛笔光标(第一次画时才做)
        # 2. 头冠
        tp = ASSETS / "tiara.png"
        self.tiara_pm = QPixmap(str(tp)) if tp.is_file() else None
        if self.tiara_pm is not None and self.tiara_pm.isNull():
            self.tiara_pm = None
        self.tia = None
        self.tia_guard = 0.0
        # 3. 假装喂
        self.fakes, self.distrust_until = [], 0.0
        # 4. 弹脑门
        self.fpend, self.charge = None, None
        self.bump, self.bump_t = 0.0, 0.0
        self.flicks, self.flick_guard = [], 0.0
        self.dvisit = None                   # 达妮卡这次来是冲着涂鸦 / 小包: dict(kind, asked, t0, wiped)
        self.quiet_wipe = False              # 达妮卡帮她擦的: 擦完不自己嘟囔

    # ----- 存档 / 小工具 -----
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
                self.log("tease save", e)

    def _lose(self, kind):
        """扣 1 点好感(每样每天有上限)"""
        today = date.today().isoformat()
        if self.store.get("day") != today:
            self.store["day"], self.store["counts"] = today, {}
        c = self.store.setdefault("counts", {})
        if c.get(kind, 0) >= DAILY[kind]:
            return
        c[kind] = c.get(kind, 0) + 1
        self._save()
        self.pet.gain(-1, quiet=True)

    def _line(self, key, pool):
        line = _pick(pool, self._last.get(key))
        self._last[key] = line
        return line

    def _say(self, key, pool, dur=2.6, tone="alert"):
        self.pet.say(self._line(key, pool), force=True, duration=dur, tone=tone, src="tease")

    def _awake_free(self):
        p = self.pet
        return (p.isVisible() and p.state != "sleep" and not (p.activities() & BUSY_HER)
                and not p.soul_active())

    def _norm(self, pos):
        """她窗口里的一个点 -> 立绘里的比例坐标(走路转身时立绘是镜像的)"""
        p = self.pet
        nx = (pos.x() - p.pad_x) / max(1.0, float(p.char_w))
        ny = (pos.y() - p.pad_top()) / max(1.0, float(p.char_h))
        if getattr(p, "face", 1.0) < 0:
            nx = 1.0 - nx
        return nx, ny

    def _glob(self, nx, ny):
        """立绘里的比例坐标 -> 屏幕坐标"""
        p = self.pet
        if getattr(p, "face", 1.0) < 0:
            nx = 1.0 - nx
        return QPointF(p.x() + p.pad_x + nx * p.char_w, p.y() + p.pad_top() + ny * p.char_h)

    @staticmethod
    def _in(zone, nx, ny):
        (x0, x1), (y0, y1) = zone
        return x0 <= nx <= x1 and y0 <= ny <= y1

    # ----- 钩子 -----
    def busy(self):
        if self.drawing:
            return "doodle"
        if self.tia is not None:
            return "tiara"
        if self.charge is not None:
            return "flick"
        return None

    def state_text(self):
        if self.drawing:
            return STATUS_DRAWING
        if self.tia is not None:
            return STATUS_TIARA_SAD if self.tia.get("sad") else STATUS_TIARA
        if self.doodle == "wiping":
            return STATUS_WIPING
        if self.doodle == "wearing":
            return STATUS_WEARING
        if self.bump > 0.35 and self.pet.state != "sleep":
            return STATUS_BUMP
        return None

    def expr(self, key, state):
        if self.tia is not None and state != "sleep" and self._has_notiara():
            return "notiara"
        return None

    def _has_notiara(self):
        return "notiara" in getattr(self.pet, "real_frames", ())

    def tiara_ok(self):
        return self.tiara_pm is not None and self._has_notiara()

    def menu_items(self):
        p = self.pet
        items = []
        if self.drawing:
            items.append(("✅", "画好了", self.end_doodle))
        elif p.state == "sleep" and p.isVisible() and not p.edge:
            items.append(("🖌", "画花脸", self.start_doodle))
        if self.doodle == "wearing" and p.state != "sleep":
            items.append(("🪞", "给她照照镜子", self.mirror))
        if self.tiara_ok() and self.tia is None and p.state != "sleep":
            items.append(("👑", "抢她的头冠", self.steal_from_menu))
        return items

    def tune(self, name, value, ctx):
        if name != "danika_script" or value is not None:          # 别的插件(生病……)已经换了就不抢
            return None
        p = self.pet
        if self.doodle == "wearing" and self.strokes and p.state != "sleep":
            self.dvisit = dict(kind="doodle", asked=time.monotonic(), t0=None, wiped=False)
            return list(DANIKA_DOODLE)
        if self.bump > 0.35 and p.state != "sleep":
            self.dvisit = dict(kind="bump", asked=time.monotonic(), t0=None, wiped=False)
            return list(DANIKA_BUMP)
        return None

    def _danika_step(self, t):
        dv = self.dvisit
        if dv is None:
            return
        if dv["t0"] is None:
            if t - dv["asked"] > 1.0:                             # 问了剧本但没来成
                self.dvisit = None
            return
        d = self.pet.danika                                     # 进场多久 + 每句多久(和达妮卡那边一样算)
        wipe_at = getattr(d, "ENTER_SEC", 1.15) + DANIKA_WIPE_LINE * getattr(d, "LINE_SEC", 3.6) * 0.95
        if dv["kind"] == "doodle" and not dv["wiped"] and t - dv["t0"] >= wipe_at and self.doodle == "wearing":
            dv["wiped"] = True                                     # 达妮卡拿毛巾擦掉
            self.doodle, self.wipe_t0, self.quiet_wipe = "wiping", t, True
            self.pet.burst("sparkle", 3, at=self.pet.head_point())

    def _danika_after(self, skipped):
        dv, self.dvisit = self.dvisit, None
        p = self.pet
        if dv is None or dv["kind"] != "doodle" or not dv["wiped"]:
            return
        t = time.monotonic()
        p.mood.add(-6.0)
        self._lose("doodle")
        self.grudge_until = t + GRUDGE_SEC
        p.emit_event("doodle", stage="found", by="danika",
                     memo="达妮卡来访时指出她脸上被画了画，帮她擦掉了；她知道是你画的，很生气（互动）")

        def mad():
            if p.state == "sleep" or not p.isVisible():
                return
            p.set_state("angry", 3.0)
            p.burst("anger", 2, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
            p.sfx.play("hmph")
            self._say("dafter", DANIKA_AFTER, 3.0)
        QTimer.singleShot(700, mad)

    def on_event(self, name, data):
        t = time.monotonic()
        if name == "danika_visit" and data.get("custom") and self.dvisit is not None and self.dvisit["t0"] is None:
            self.dvisit["t0"] = t
        elif name == "danika_end":
            self._danika_after(bool(data.get("skipped")))
        if name == "wake":
            if self.drawing:
                self.end_doodle(quiet=True)
            if self.strokes and self.doodle == "fresh" and not self.caught:
                self.doodle = "wearing"
                self.notice_at = t + random.uniform(*NOTICE_SEC)
        elif name in ("drag_start", "click", "double_click"):
            self.fpend = None

    def on_pet(self):
        p = self.pet
        if self.tia is not None:
            return True                                   # 忙着追头冠, 顾不上
        if time.monotonic() < self.grudge_until and p.state != "sleep":
            p.set_state("angry", 1.6)
            p.kick(-1.2)
            self._say("grudge", GRUDGE_PET, 2.4)
            return True
        return False

    def on_click(self, double):
        if self.tia is not None and not self.tia.get("sad"):
            if not self.pet.bubble.isVisible():
                self._say("chase", TIARA_CHASE, 1.6)
            return True
        return False

    def on_mouse_press(self, e):
        p = self.pet
        if e.button() != Qt.LeftButton or self.drawing or self.tia is not None:
            return False
        nx, ny = self._norm(e.position())
        if self._in(FLICK_ZONE, nx, ny) and self._awake_free() and not p.sulking():
            if time.monotonic() < self.flick_guard:           # 捂着额头呢
                p.set_state("shy", 1.6)
                p.kick(-1.0)
                self._say("fguard", FLICK_GUARDED, 2.0)
                return True
            self.fpend = dict(t0=time.monotonic(), gpos=QCursor.pos(), n=(nx, ny))
        return False

    def on_drag_begin(self, pos, delta):
        p = self.pet
        if not self.tiara_ok() or self.tia is not None or self.drawing or not self._awake_free():
            return False
        nx, ny = self._norm(pos)
        if not self._in(TIARA_ZONE, nx, ny) or delta.y() >= 0 or -delta.y() < abs(delta.x()) * 0.8:
            return False
        if time.monotonic() < self.tia_guard:                 # 护住头冠: 照常被拎起来
            QTimer.singleShot(0, lambda: self._say("tguard", TIARA_GUARDED, 2.0))
            return False
        self.fpend = None
        self._steal(held=True)
        return True

    # ----- 1. 在她脸上画画 -----
    def start_doodle(self):
        p = self.pet
        if self.drawing or p.state != "sleep" or not p.isVisible() or p.edge or p.mouse_captured():
            return
        self.drawing = True
        self.caught = False
        self.session = 0                     # 这次画了几笔
        self.itch, self.stir_at = 0.0, -1e9
        if self.doodle not in (None, "fresh"):
            self.strokes, self.doodle = [], None
        p.capture_mouse(self)
        if self._brush is None:
            self._brush = _brush_cursor()
        p.setCursor(self._brush)
        QToolTip.showText(QCursor.pos(), "在她身上按住拖动 = 画\n右键 = 收笔", None, QRect(), 4000)

    def end_doodle(self, quiet=False):
        if not self.drawing:
            return
        p = self.pet
        self.drawing, self.cur = False, None
        p.release_mouse(self)
        self.strokes = [s for s in self.strokes if len(s) >= 1]
        if self.session and not self.caught:
            p.emit_event("doodle", stage="drawn", strokes=len(self.strokes),
                         memo="你趁她睡着，在她脸上画了画（她还不知道）（互动）")
        if self.strokes and p.state != "sleep" and self.doodle == "fresh" and not self.caught:
            self.doodle = "wearing"
            self.notice_at = time.monotonic() + random.uniform(*NOTICE_SEC)

    def on_capture_press(self, e):
        if self.drawing:
            if e.button() == Qt.RightButton:
                self.end_doodle()
                return
            if e.button() == Qt.LeftButton:
                if time.monotonic() - self.stir_at < STIR_GRACE:
                    self._caught()
                    return
                nx, ny = self._norm(e.position())
                self.cur = [(nx, ny)]
                self.strokes.append(self.cur)
                self.session += 1
                if self.doodle is None:
                    self.doodle, self.ink = "fresh", 1.0
                self._cache.clear()
            return
        if self.charge is None and self.tia is None:
            self.pet.release_mouse(self)

    def on_capture_move(self, e):
        t = time.monotonic()
        if self.drawing:
            if self.cur is None or not (e.buttons() & Qt.LeftButton):
                return
            nx, ny = self._norm(e.position())
            lx, ly = self.cur[-1]
            d = math.hypot(nx - lx, ny - ly)
            if d < 0.006:
                return
            if t - self.stir_at < STIR_GRACE and t - self.stir_at > 0.15:
                self._caught()
                return
            self.cur.append((nx, ny))
            self._cache.clear()
            self.itch += d
            if self.itch >= ITCH_STIR:
                self._stir(t)
            return
        if self.charge is not None:
            g = QCursor.pos() - self.charge["gpos"]
            if abs(g.x()) + abs(g.y()) > 26:                  # 蓄力时挪开了: 不弹了
                self.charge = None
                self.pet.release_mouse(self)
                self.pet.set_state("idle")
                self._say("fcancel", FLICK_CANCEL, 1.8, None)
            return
        if self.tia is not None and self.tia["mode"] == "held":
            self.tia["win"].center_at(QPointF(QCursor.pos()) + QPointF(0, self.tia["win"].height() * 0.25))

    def on_capture_release(self, e):
        if self.drawing:
            if e.button() == Qt.LeftButton:
                if self.cur is not None and len(self.cur) == 1:
                    self.cur.append((self.cur[0][0] + 0.002, self.cur[0][1]))   # 点一下 = 一个点
                self.cur = None
                self._cache.clear()
            return
        if self.charge is not None:
            self._flick()
            return
        if self.tia is not None and self.tia["mode"] == "held":
            self._drop()
            return
        self.pet.release_mouse(self)

    def _stir(self, t):
        """画得痒了: 动一下(这时候停笔就没事)"""
        p = self.pet
        self.itch, self.stir_at = 0.0, t
        p.kick(-0.9)
        p.tilt += random.choice((-1, 1)) * 3
        if not p.bubble.isVisible():
            self._say("stir", DOODLE_STIR, 1.4, None)

    def _caught(self):
        """动完还接着画: 醒了, 当场抓包"""
        p = self.pet
        self.caught = True
        self.end_doodle(quiet=True)
        if self.strokes:
            self.doodle = "fresh"
        p.wake_up("doodle")
        QTimer.singleShot(250, lambda: self._found("caught"))

    def mirror(self):
        p = self.pet
        if self.doodle != "wearing" or not self._awake_free():
            return
        p.note_interaction()
        p.set_state("surprised", 1.2)
        self._say("mirror", DOODLE_MIRROR, 1.4, None)
        QTimer.singleShot(1300, lambda: self._found("mirror"))

    def _found(self, by):
        """发现脸上被画了: 愣住 -> 炸毛 -> 擦"""
        p = self.pet
        if not self.strokes or self.doodle == "wiping":
            return
        self.doodle = "wiping"
        t = time.monotonic()
        self.wipe_t0 = t + 1.6
        p.stop_walk()
        p.set_state("surprised", 0.8)
        p.burst("excl", 1, at=p.head_point() + QPointF(p.char_w * 0.22, -12))
        p.sfx.play("huh")
        if by == "caught":
            self._say("caught", DOODLE_CAUGHT, 2.6)
        else:
            self._say("found", DOODLE_FOUND, 2.6)

        def mad():
            if p.state == "sleep" or not p.isVisible():
                return
            p.set_state("angry", 3.4)
            p.burst("anger", 2, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
            p.sfx.play("hmph")
        QTimer.singleShot(800, mad)
        p.mood.add(-8.0 if by == "caught" else -6.0)
        self._lose("doodle")
        self.grudge_until = t + GRUDGE_SEC
        p.emit_event("doodle", stage="found", by=by,
                     memo="她发现你在她脸上画了画，气坏了，一边擦一边记仇（互动）" if by != "caught"
                     else "你在她脸上画画时把她弄醒了，被当场抓包（互动）")

    def _doodle_step(self, t):
        p = self.pet
        if self.doodle == "wearing" and t >= self.notice_at and self._awake_free() and not p.bubble.isVisible() \
                and p.state in ("idle", "look", "look_left", "content", "happy"):
            self._say("self", DOODLE_SELF, 2.2, None)
            QTimer.singleShot(2000, lambda: self._found("self"))
            self.notice_at = t + 9999
        elif self.doodle == "wiping" and t >= self.wipe_t0:
            u = (t - self.wipe_t0) / WIPE_SEC
            if int(u * 8) != int((u - 0.05) * 8):
                p.kick(-0.7)                                  # 一下一下擦
            self.ink = max(0.0, 1.0 - u)
            self._cache.clear()
            if u >= 1.0:
                self.strokes, self.doodle, self.ink = [], None, 1.0
                if p.state != "sleep" and p.isVisible() and not self.quiet_wipe:
                    self._say("wiped", DOODLE_WIPED, 2.4)
                self.quiet_wipe = False

    # ----- 2. 抢头冠 -----
    def steal_from_menu(self):
        if self.tiara_ok() and self.tia is None and self._awake_free():
            self._steal(held=False)

    def _steal(self, held):
        p = self.pet
        p.note_interaction()
        p.stop_walk()
        w = TiaraWin(self, self.tiara_pm, max(40.0, p.char_w * TIARA_W))
        if held:
            p.capture_mouse(self)
            w.center_at(QPointF(QCursor.pos()) + QPointF(0, w.height() * 0.25))
        else:
            w.center_at(QPointF(QCursor.pos()))
        w.show()
        now = time.monotonic()
        self.tia = dict(mode="held" if held else "follow", win=w, t0=now, vy=0.0, next=now + 0.6, high=0.0,
                        hop=0.0, sad=False, said=0.0)
        p.set_state("surprised", 0.8)
        p.sfx.play("huh")
        self._say("stolen", TIARA_STOLEN, 2.0)
        p.mood.add(-3.0)
        self._lose("tiara")
        p.emit_event("tiara", stage="stolen", memo="你把她的头冠抢走了，她捂着头追你（互动）")

    def tiara_clicked(self):
        if self.tia is not None and self.tia["mode"] == "follow":
            self._drop()

    def _drop(self):
        tia = self.tia
        if tia is None:
            return
        self.pet.release_mouse(self)
        tia["mode"] = "drop"
        tia["vy"] = 0.0
        tia["sad"] = False
        tia["next"] = time.monotonic() + 0.4

    def _tiara_back(self, how):
        p = self.pet
        tia, self.tia = self.tia, None
        if tia is None:
            return
        p.release_mouse(self)
        try:
            tia["win"].hide()
            tia["win"].deleteLater()
        except Exception:
            pass
        self.tia_guard = time.monotonic() + TIARA_GUARD
        if how == "silent":
            return
        p.stop_walk()
        p.burst("sparkle", 4, at=p.head_point())
        if how == "snatch":
            quick = time.monotonic() - tia["t0"] < 8.0
            p.set_state("angry" if quick else "content", 2.4)
            self._say("back", TIARA_BACK_QUICK if quick else TIARA_BACK_SLOW, 2.6, "alert" if quick else None)
        else:
            p.set_state("content", 2.0)
            self._say("pickup", TIARA_PICKUP, 2.6, None)
        p.emit_event("tiara", stage="back", how=how,
                     memo="她把头冠抢回来了" if how == "snatch" else "她把掉在地上的头冠捡回来戴好了")

    def _tiara_step(self, t, dt):
        tia, p = self.tia, self.pet
        if tia is None:
            return
        if not p.isVisible() or p.state == "sleep":
            self._tiara_back("silent")
            return
        w = tia["win"]
        foot = p.foot_point().y()                                # 她脚下 = 地面
        if tia["mode"] == "follow":
            w.center_at(QPointF(QCursor.pos()))
        elif tia["mode"] == "drop":
            tia["vy"] += 1900.0 * dt
            c = w.center()
            ny = c.y() + tia["vy"] * dt
            floor = foot - w.height() / 2
            if ny >= floor:
                ny = floor
                tia["mode"] = "ground"
                w.rot = 0.0
                p.sfx.play("tick")
            else:
                w.rot += 420.0 * dt                           # 一边掉一边转
            w.update()
            w.center_at(QPointF(c.x(), ny))
        if t < tia["next"] or p.dragging or p.fling is not None:
            return
        tia["next"] = t + 0.2
        c = w.center()
        me = p.x() + p.width() / 2
        dx = c.x() - me
        near = abs(dx) <= p.char_w * 0.32
        if tia["mode"] in ("drop", "ground"):
            tia["sad"] = False
            if tia["mode"] == "ground" and near:
                self._tiara_back("pickup")
            elif not near and p.walk is None:
                p.start_walk(QPointF(c.x() - p.width() / 2, p.y()), kind="tiara", speed=320)
            return
        if tia["sad"]:                                         # 蹲着委屈: 举低了才又追
            head = p.y() + p.pad_top()
            if c.y() >= head - p.char_h * TIARA_REACH * 0.8 and near:
                tia["sad"] = False
            return
        if not near:
            tx = c.x() - p.width() / 2
            cur = p.walk.get("tx") if isinstance(p.walk, dict) else None
            if cur is None or abs(cur - tx) > 40:                # 头冠挪远了就改道
                p.start_walk(QPointF(tx, p.y()), kind="tiara", speed=320)
            if t - tia["said"] > 3.5 and not p.bubble.isVisible():
                tia["said"] = t
                self._say("chase", TIARA_CHASE, 1.6)
            return
        p.stop_walk()
        head = p.y() + p.pad_top()
        reach = head - p.char_h * TIARA_REACH
        if c.y() >= reach:                                     # 够得着: 蹦起来抢回去
            p.do_jump(True)
            QTimer.singleShot(260, lambda: self.tia is not None and self.tia["mode"] in ("held", "follow")
                              and self._tiara_back("snatch"))
            tia["next"] = t + 0.6
            return
        tia["high"] += 0.2                                      # 太高了: 原地蹦
        if t >= tia["hop"]:
            tia["hop"] = t + 0.9
            p.do_jump(False)
            if t - tia["said"] > 3.0 and not p.bubble.isVisible():
                tia["said"] = t
                self._say("high", TIARA_HIGH, 1.8)
        if tia["high"] >= TIARA_GIVEUP:
            tia["sad"], tia["high"] = True, 0.0
            p.set_state("shy", 3.0)
            p.burst("drop", 2, at=p.head_point() + QPointF(0, p.char_h * 0.2))
            self._say("sad", TIARA_SAD, 3.0, None)

    # ----- 3. 假装喂 -----
    def on_feed(self, food):
        p = self.pet
        t = time.monotonic()
        ctrl = bool(QGuiApplication.keyboardModifiers() & Qt.ControlModifier)
        if p.state == "sleep" or p.sulking() or not p.isVisible() or p.edge or food.get("effect"):
            return False
        key = food.get("key")
        if not ctrl:
            if t < self.distrust_until and self._awake_free():     # 学乖了: 真喂也先确认一下
                p.stop_walk()
                p.set_state("shy", 1.3)
                self._say("suspect", FAKE_SUSPECT, 1.6, None)
                self.distrust_until -= 120.0
                QTimer.singleShot(1300, lambda: p.feed(key, ask=False))
                return True
            return False
        if not self._awake_free():
            return False
        p.note_interaction()
        p.stop_walk()
        if t < self.distrust_until:                            # 不上当了
            p.set_state("content", 1.8, expr="smug" if "smug" in p.frames else None)
            self._say("nope", FAKE_NOPE, 2.2, None)
            return True
        self.fakes = [x for x in self.fakes if t - x < FAKE_WINDOW] + [t]
        n = len(self.fakes)
        p.food_fly(key, yank=True)
        QTimer.singleShot(420, lambda: p.state != "sleep" and p.set_state("eat", 0.7))
        QTimer.singleShot(560, lambda: p.sfx.play("munch"))

        def miss():
            if p.state == "sleep" or p.dragging:
                return
            p.set_state("surprised", 0.9)
            p.burst("quest", 1, at=p.head_point() + QPointF(p.char_w * 0.25, -8))
            self._say("bite", FAKE_BITE, 1.2, None)

        def mad():
            if p.state == "sleep" or p.dragging:
                return
            if n >= 2:
                p.set_state("angry", 2.4)
                self._say("again", FAKE_AGAIN, 2.4)
            else:
                p.set_state("shy", 2.4, expr="pout" if "pout" in p.frames else None)
                self._say("first", FAKE_FIRST, 2.4)
            if n >= FAKE_WISE:
                self.distrust_until = time.monotonic() + DISTRUST_SEC
                QTimer.singleShot(2600, lambda: self._say("wise", FAKE_WISE_LINE, 2.6, None))
        QTimer.singleShot(1000, miss)
        QTimer.singleShot(2000, mad)
        p.mood.add(-2.0)
        if n >= 2:
            self._lose("fake")
        p.emit_event("fake_feed", key=key, n=n, memo=f"你假装喂她{food.get('name', '吃的')}，到嘴边又抽走了（互动）")
        return True

    # ----- 4. 弹脑门 -----
    def _flick_step(self, t, dt):
        p = self.pet
        fp = self.fpend
        if fp is not None:
            g = QCursor.pos() - fp["gpos"]
            if not p.press_pending() or abs(g.x()) + abs(g.y()) > 5 or not self._awake_free():
                self.fpend = None
            elif t - fp["t0"] >= FLICK_HOLD:
                self.fpend = None
                p.capture_mouse(self)
                self.charge = dict(t0=t, gpos=fp["gpos"], n=fp["n"], shake=0.0)
                p.stop_walk()
                p.set_state("shy", FLICK_FULL + 3.0)
                p.burst("sweat", 1, at=p.head_point())
                self._say("charge", FLICK_CHARGE, 1.8, None)
        ch = self.charge
        if ch is not None:
            self._cache.clear()
            if t - ch["t0"] >= FLICK_FULL and t >= ch["shake"]:      # 蓄满了: 吓得发抖
                ch["shake"] = t + 0.12
                p.kick(random.choice((-1, 1)) * 0.8)
        if self.bump > 0 and t - self.bump_t > 6.0:
            self.bump = max(0.0, self.bump - dt / 45.0)                # 约 45 秒消一级
            self._cache.clear()

    def _flick(self):
        p = self.pet
        ch, self.charge = self.charge, None
        p.release_mouse(self)
        t = time.monotonic()
        pw = max(0.15, min(1.0, (t - ch["t0"]) / FLICK_FULL))
        p.sfx.play("bonk")
        p.kick(-(2.0 + 3.0 * pw))
        p.tilt += random.choice((-1, 1)) * (5 + 9 * pw)
        self.bump = min(1.6, self.bump + 0.45 + 0.6 * pw)
        self.bump_t = t
        self._cache.clear()
        hit = self._glob(*FLICK_SPOT)
        p.burst("star", 2 + int(3 * pw), at=hit, bias=(0, 0))
        if pw > 0.4:
            p.burst("drop", 1 + int(2 * pw), at=self._glob(0.42, 0.52))
        lvl = 0 if pw < 0.35 else (1 if pw < 0.75 else 2)
        p.set_state("angry" if lvl == 2 else "shy", 2.4, expr="ouch" if "ouch" in p.frames else None)
        self._say("hit%d" % lvl, FLICK_HIT[lvl], 2.0)
        p.mood.add(-(1.5 + 2.5 * pw))
        if pw >= 0.7:
            self._lose("flick")
        n, win, guard = FLICK_GUARD
        self.flicks = [x for x in self.flicks if t - x < win] + [t]
        if len(self.flicks) >= n:
            self.flicks = []
            self.flick_guard = t + guard
        p.emit_event("flick", power=round(pw, 2),
                     memo="你蓄力弹了她脑门一下，额头鼓起一个小包（互动）" if pw >= 0.5 else "你弹了她脑门一下（互动）")

    # ----- 画在立绘上: 涂鸦、小包、蓄力圈 -----
    def paint(self, key, pm, t):
        draw_ink = bool(self.strokes) and self.ink > 0.01
        if not draw_ink and self.bump <= 0.01 and self.charge is None:
            return None
        ck = (pm.cacheKey(), sum(len(s) for s in self.strokes), round(self.ink, 2), round(self.bump, 2),
              None if self.charge is None else int((t - self.charge["t0"]) * 12))
        out = self._cache.get(ck)
        if out is not None:
            return out, 0.0
        if len(self._cache) > 12:
            self._cache.clear()
        out = QPixmap(pm)
        dpr = pm.devicePixelRatio() or 1.0
        w, h = pm.width() / dpr, pm.height() / dpr
        q = QPainter(out)
        q.setRenderHint(QPainter.Antialiasing, True)
        if self.bump > 0.01 and key not in ("notiara", "ouch"):  # 额头的小包(捂着头 / 揉额头那两张, 手正盖着, 不画)
            bx, by = FLICK_SPOT
            r = w * (0.022 + 0.022 * min(1.6, self.bump))
            a = min(1.0, self.bump * 1.4)
            g = QRadialGradient(QPointF(bx * w, by * h), r)
            g.setColorAt(0, QColor(255, 120, 130, int(230 * a)))
            g.setColorAt(0.65, QColor(250, 140, 150, int(200 * a)))
            g.setColorAt(1, QColor(250, 160, 170, 0))
            q.setPen(Qt.NoPen)
            q.setBrush(g)
            q.drawEllipse(QPointF(bx * w, by * h), r, r * 0.85)
            q.setBrush(QColor(255, 255, 255, int(170 * a)))
            q.drawEllipse(QPointF(bx * w - r * 0.3, by * h - r * 0.3), r * 0.22, r * 0.16)
        if draw_ink:
            col = QColor(INK)
            col.setAlphaF(0.92 * self.ink)
            pen = QPen(col, max(1.6, w * INK_W))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            q.setPen(pen)
            q.setBrush(Qt.NoBrush)
            for s in self.strokes:
                if len(s) < 2:
                    continue
                path = QPainterPath(QPointF(s[0][0] * w, s[0][1] * h))
                for x, y in s[1:]:
                    path.lineTo(QPointF(x * w, y * h))
                q.drawPath(path)
        if self.charge is not None:                            # 蓄力圈: 越蓄越满
            nx, ny = self.charge["n"]
            u = min(1.0, (t - self.charge["t0"]) / FLICK_FULL)
            c = QPointF(nx * w, ny * h)
            r = w * 0.06
            q.setPen(QPen(QColor(255, 255, 255, 200), max(2.0, w * 0.012)))
            q.setBrush(Qt.NoBrush)
            q.drawEllipse(c, r, r)
            q.setPen(QPen(QColor(240, 90, 90, 230), max(2.0, w * 0.012), Qt.SolidLine, Qt.RoundCap))
            q.drawArc(QRectF(c.x() - r, c.y() - r, r * 2, r * 2), 90 * 16, int(-360 * 16 * u))
        q.end()
        out.setDevicePixelRatio(dpr)
        self._cache[ck] = out
        return out, 0.0

    def step(self, t):
        dt = min(0.1, t - getattr(self, "_t", t))
        self._t = t
        if self.drawing and self.pet.state != "sleep":
            self.end_doodle(quiet=True)
        self._doodle_step(t)
        self._danika_step(t)
        self._tiara_step(t, dt)
        self._flick_step(t, dt)


def create(pet, log_fn=None):
    if not hasattr(pet, "capture_mouse"):                      # 旧本体没有接管鼠标的接口: 不加载
        return None
    return Tease(pet, log_fn)
