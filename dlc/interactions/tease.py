# -*- coding: utf-8 -*-
"""互动 DLC「捉弄」: 欺负欺负她。
  1. 在她脸上画画: 她睡着(或被法杖打晕)时 右键 / 托盘「互动」-> 🖌 画花脸(醒着时菜单里没有这一项)。鼠标变成一支小毛笔,
     在她身上按住拖就是画, 右键或菜单「画好了」收笔。
     画多了她会痒得动一下(「唔……」), 这时候停一停; 动完 1.2 秒内还接着画就会把她弄醒 —— 当场被抓包, 更生气。
     打晕时不会痒, 但快醒的前 3 秒她会动一下, 醒的那一刻你还在画 -> 抓包。
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
  5. 抢法杖(和头冠反着来): 按住杖头往外(离开她身子那边)一拽, 法杖到你手里(也可以菜单「🪄 抢她的法杖」), 你捏着杖身。
     法杖不挡鼠标: 点别处照常点得到; 左键点她 = 拿法杖敲她一下(乱施法), 右键点她 / 菜单「把法杖还给她」= 还给她。
     她不追: 站着伸手念咒往回叫, 每隔几秒法杖在你手里往她那边挣一下, 一次比一次猛; 离她近就被叫回去, 跑远点能撑一阵,
     念咒时你把法杖往远处挣能压住她这一轮, 不挣又离得近才会被叫回去。你拿着它左右甩(或左键点她)= 乱施法, 魔法打到她身上(开花 / 飘起来 / 被电一下 / 下雪),
     正在念的咒也被打断。挥到第三下炸了: 她被炸得灰头土脸(脸上的灰慢慢掉), 法杖还在你手里。挥到第六下她被打晕
     (X 眼、头上绕星星), 晕着的 20 秒叫不回法杖, 这时候再挥法杖也没劲了; 戳她、摸她只会哼一声, 也能把她拎走,
     右键菜单里有「画花脸」(见第 1 条)和「把法杖还给她」。
     醒过来气坏了, 下一次念咒一定把法杖叫回去。还给她她会消点气(晕着时还就悄悄塞回她手里)。拿回来后 90 秒内再伸手, 她抱紧法杖不给。心情 -3, 每挥一下 -1, 炸了再 -2, 打晕再 -3。
     法杖图 assets/wand.png; 两手空空的脸 assets/nowand.png, 没有就借被拎起来那张(那张也没拿法杖)。
达妮卡来访时(调节口 danika_script): 她脸上被画了还不知道 -> 达妮卡指出来、拿毛巾帮她擦掉, 走了以后她冲你生气;
     额头有包 -> 达妮卡问是谁弹的。
好感: 每样每天最多扣 DAILY 次(各 -1)。推事件: doodle(stage) / tiara(stage) / fake_feed(n) / flick(power) /
wand(stage: stolen / tug(n, ok) / cast(kind, n) / ko(sec) / ko_end / back(how: summon / given / silent)), 都带 memo。
她被哄着睡觉时(本体「哄她睡觉」)这些都不开; 头冠 / 法杖还在你手里时她不肯被哄(调节口 lull_ok)。
记在 <数据目录>/tease.json(每天扣过几次)。priority = -2: 别的插件先接; 画在立绘上的东西(涂鸦、小包)最后画, 盖在最上面。
只用公开接口(docs/接口规范.md)。不想要就删掉这个文件。
"""
import json
import math
import os
import random
import time
from collections import deque
from datetime import date
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (QColor, QCursor, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import QToolTip, QWidget

from stats import data_dir

ASSETS = Path(__file__).resolve().parents[2] / "assets"
DAILY = {"doodle": 2, "tiara": 2, "fake": 2, "flick": 2, "wand": 2}   # 每天最多因为这一样扣几次好感

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
DOODLE_GHOST = ["你刚才在我身子上画的!!我都看见了!!", "别以为我是魂就看不见!!……擦、擦干净!"]   # 灵魂出窍时画的
DOODLE_WIPED = ["……哼!洗干净了!", "擦、擦掉了……你给我记住!"]
GRUDGE_PET = ["哼,别碰我!你手上还有墨!", "不许摸!先把毛笔交出来!", "……(躲开)还记着呢。"]
STATUS_DRAWING = "睡得正香,浑然不知有人在她脸上作画……"
STATUS_DRAWING_KO = "晕得不省人事,浑然不知有人在她脸上作画……"
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
TIARA_NO_SLEEP = ["头冠还没还我呢!……睡什么睡!", "先把头冠还我!"]

# ----- 5. 抢法杖 -----
WAND_W = 0.30                        # 法杖(assets/wand.png)的宽 = 立绘宽的多少(和她手里拿着的一样大)
WAND_GRIP = (0.80, 0.78)             # 你捏着法杖图的哪一点(比例): 杖身下半截
WAND_TIP = (0.51, 0.26)              # 杖头宝石(比例): 发光、闪的地方
_WH_IDLE = ((0.11, 0.33), (0.45, 0.73))
_WH_UP = ((0.02, 0.25), (0.32, 0.60))   # 举起来的(开心、挥手、生气……)
_WH_MID = ((0.07, 0.28), (0.36, 0.62))  # 吓一跳、转晕
WAND_HEAD = {"happy": _WH_UP, "wave": _WH_UP, "cheer": _WH_UP, "stretch": _WH_UP, "angry": _WH_UP, "love": _WH_UP,
             "surprised": _WH_MID, "dizzy": _WH_MID, "hungry": ((0.10, 0.31), (0.69, 0.97)),
             "yawn": ((0.17, 0.36), (0.52, 0.77))}   # 各张立绘里杖头在哪(宽、高的比例); 按住这儿往外拽才算抢
WAND_HAND = (0.21, 0.60)             # 叫回来时法杖飞到哪(立绘比例)
WAND_TUG_FIRST = 2.0                 # 抢走后多久第一次念咒
WAND_TUG_GAP = 3.6                   # 两次念咒之间
WAND_TUG_SEC = 1.3                   # 一次念咒往回拽多久
WAND_TUG_K = (0.28, 0.38, 0.48, 0.56, 0.64, 0.72)   # 这一轮你不挣的话, 最多把法杖拽过全程的多少; 到不了 1
WAND_RESIST = 64.0                   # 念咒时往离开她的方向挣这么多像素, 这一轮的劲就被抵消; 后面几轮要挣得更远
WAND_REACH = 0.55                    # 法杖被拽到离她的手这么近(立绘宽的倍数)就回到她手里
WAND_RET_SEC = 0.4                   # 飞回她手里要多久
WAND_CAST_COOL = 1.3                 # 乱施法的间隔
WAND_SHAKE_PX = 18                   # 左右甩: 每一段至少挪这么多像素, 0.7 秒内来回 3 次算挥一下
WAND_BOOM_AT = 3                     # 挥到第几下炸(炸完法杖还在你手里)
WAND_KO_AT = 6                       # 挥到第几下把她打晕
WAND_KO_SEC = 20.0                   # 晕多久(这段时间叫不回法杖)
WAND_GUARD = 90.0                    # 拿回来以后这么久内再伸手, 她抱紧不给
WAND_SOOT_SEC = 25.0                 # 炸完脸上的灰多久掉干净
WAND_SPELLS = ("flower", "float", "zap", "snow")
WAND_STOLEN = ["啊!我的法杖!!", "法、法杖还我!!", "那个不能乱拿的!!"]
WAND_SUMMON = ["法杖,回来!", "……以薇斯纳之名——回来!", "回——来——!"]
WAND_TUG_FAIL = ["……唔,差一点!", "你、你别攥那么紧!", "可恶……拉不过来……"]
WAND_TUG_FIGHT = ["唔——!你别拽!!", "拉、拉不过去……!", "放手……法杖是我的!"]
WAND_CHASE = ["先把法杖还我!", "不许拿着它乱跑!"]
WAND_CAST = {"flower": ["诶?!……怎么开花了?!", "别、别乱挥!!"], "float": ["哇啊?!……放我下来!!", "飘、飘起来了?!"],
             "zap": ["呀!……麻、麻了……", "电、电到我了!!"], "snow": ["阿嚏!……好冷!!", "怎么下雪了?!……是你干的吧!"]}
WAND_BOOM = ["……咳、咳……法杖不是这么用的啦!!", "……(头发都炸起来了)……你、你!!"]
WAND_BOOM_MAD = ["……哼!再乱挥,我就把你变成青蛙!", "脸上全是灰……都怪你!快还给我!"]
WAND_KO = ["……(咚)", "呜啊……(眼前一黑)", "……星、星星……"]
WAND_KO_POKE = ["……唔……", "……(没反应)", "……呜……法杖……"]
WAND_KO_WAKE = ["……唔……你、你把我打晕了?!", "……头好晕……法杖!!马上还给我!!"]
WAND_KO_WAKE_HAS = ["……唔……头好晕……", "……诶?法杖……在我手里?……刚才发生了什么……"]   # 晕着时法杖已经还给她了
WAND_KO_STIR = ["……唔……", "……(手指动了一下)", "……嗯……星星……"]
KO_STIR_BEFORE = 3.0                 # 晕醒前这么多秒她动一下(在她脸上画画时: 这时候停笔)
WAND_BACK_SUMMON = ["哼!回来了!……果然还是听我的。", "抓到了!……不许再碰!"]
WAND_GIVEN = ["……哼,算你识相。", "(一把抱住)……不许再拿了!"]
WAND_GUARDED = ["不许碰法杖!(抱紧)", "哼,法杖不给你!"]
WAND_NO_SLEEP = ["法杖还没还我呢,睡不着!", "先把法杖还我!"]
STATUS_WAND = "两手空空地伸着手,念念有词地想把法杖叫回来……"
STATUS_WAND_TUG = "伸长了手念着咒,法杖在你手里一个劲儿往她那边挣……"
STATUS_WAND_HIT = "被乱飞的魔法弄得手忙脚乱……"
STATUS_WAND_BOOMING = "法杖在你手里滋滋地冒火星……"
STATUS_WAND_KO = "被乱飞的魔法打晕了,头上绕着一圈小星星……"
STATUS_WAND_SOOTY = "灰头土脸地伸着手,还在念咒要法杖……"
STATUS_SOOT = "头发炸得乱蓬蓬的,脸上还沾着灰……"
SOOT_SPOTS = ((0.37, 0.585, 0.045), (0.565, 0.595, 0.042), (0.46, 0.40, 0.034), (0.62, 0.35, 0.030))  # 灰: 两颊 + 刘海(x, y, 半径)

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

BUSY_HER = {"hidden", "drag", "fling", "throw", "spin", "danika", "food_fx", "edge", "frozen", "sick", "lull", "ghost"}

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


class WandWin(QWidget):
    """被抢走的法杖: 你捏着杖身(grip 那一点跟着鼠标)。不接鼠标(点击穿过去, 点得到她和别的窗口);
    窗口比法杖大一圈, 转起来、发光不会被裁掉"""
    PAD = 0.45

    def __init__(self, plug, pm, w):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
                         | Qt.WindowTransparentForInput)
        self.plug, self.pm = plug, pm
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.ww = float(w)
        self.wh = w * pm.height() / max(1, pm.width())
        pad = self.PAD * max(self.ww, self.wh)
        self.resize(int(self.ww + pad * 2), int(self.wh + pad * 2))
        self.ox, self.oy = (self.width() - self.ww) / 2, (self.height() - self.wh) / 2
        self.rot = 0.0
        self.glow = 0.0                      # 她念咒往回叫: 杖头一圈青光(0-1)
        self.flash = 0.0                     # 你挥了一下: 杖头一闪(0-1)

    def grip(self):
        return QPointF(self.ox + self.ww * WAND_GRIP[0], self.oy + self.wh * WAND_GRIP[1])

    def tip(self):
        return QPointF(self.ox + self.ww * WAND_TIP[0], self.oy + self.wh * WAND_TIP[1])

    def grip_at(self, g):
        gp = self.grip()
        self.move(int(round(g.x() - gp.x())), int(round(g.y() - gp.y())))

    def grip_global(self):
        return QPointF(self.x(), self.y()) + self.grip()

    def tip_global(self):
        return QPointF(self.x(), self.y()) + self.tip()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        g = self.grip()
        p.translate(g)
        p.rotate(self.rot)                   # 绕捏着的那一点转
        p.translate(-g)
        h = self.tip()
        if self.glow > 0.01:
            r = self.ww * (0.5 + 0.12 * self.glow)
            gr = QRadialGradient(h, r)
            gr.setColorAt(0, QColor(150, 240, 235, int(180 * self.glow)))
            gr.setColorAt(1, QColor(150, 240, 235, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(gr)
            p.drawEllipse(h, r, r)
        p.drawPixmap(QRectF(self.ox, self.oy, self.ww, self.wh), self.pm, QRectF(self.pm.rect()))
        if self.flash > 0.01:                # 星芒
            a = int(255 * self.flash)
            ln = self.ww * (0.3 + 0.5 * (1.0 - self.flash))
            gr = QRadialGradient(h, ln * 0.7)
            gr.setColorAt(0, QColor(255, 255, 235, a))
            gr.setColorAt(1, QColor(255, 220, 240, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(gr)
            p.drawEllipse(h, ln * 0.7, ln * 0.7)
            p.setPen(QPen(QColor(255, 248, 200, a), max(2.0, self.ww * 0.04), Qt.SolidLine, Qt.RoundCap))
            for ang in (0, 45, 90, 135):
                dx, dy = math.cos(math.radians(ang)) * ln, math.sin(math.radians(ang)) * ln
                k = 1.0 if ang % 90 == 0 else 0.6
                p.drawLine(QPointF(h.x() - dx * k, h.y() - dy * k), QPointF(h.x() + dx * k, h.y() + dy * k))
        p.end()



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
        # 5. 法杖
        wp = ASSETS / "wand.png"
        self.wand_pm = QPixmap(str(wp)) if wp.is_file() else None
        if self.wand_pm is not None and self.wand_pm.isNull():
            self.wand_pm = None
        self.wand = None                     # dict(mode held/follow, win, tug, tugs, casts, ret……)
        self.wand_guard = 0.0
        self.wand_hist = deque(maxlen=160)   # (t, 鼠标 x): 看你是不是在左右甩
        self.soot = 0.0                      # 炸完脸上的灰(1 -> 0)
        self.ko = None                       # 被法杖打晕了: 到这个时间(monotonic)醒; 法杖晕着时还给她也照样晕
        self.ko_stirred = False
        self.ko_stars = 0.0
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
        if self.wand is not None:
            return "wand"
        if self.charge is not None:
            return "flick"
        return None

    def state_text(self):
        if self.drawing:
            return STATUS_DRAWING_KO if self.ko is not None else STATUS_DRAWING
        if self.ko is not None and self.pet.state != "sleep":
            return STATUS_WAND_KO
        if self.tia is not None:
            return STATUS_TIARA_SAD if self.tia.get("sad") else STATUS_TIARA
        if self.wand is not None:
            wd = self.wand
            if wd.get("boom"):
                return STATUS_WAND_BOOMING
            if wd["tug"] is not None:
                return STATUS_WAND_TUG
            if time.monotonic() - wd.get("hit_at", -1e9) < 2.5:
                return STATUS_WAND_HIT
            return STATUS_WAND_SOOTY if self.soot > 0.3 else STATUS_WAND
        if self.soot > 0.3 and self.pet.state != "sleep":
            return STATUS_SOOT
        if self.doodle == "wiping":
            return STATUS_WIPING
        if self.doodle == "wearing":
            return STATUS_WEARING
        if self.bump > 0.35 and self.pet.state != "sleep":
            return STATUS_BUMP
        return None

    def expr(self, key, state):
        frames = getattr(self.pet, "frames", {})
        if self.ko is not None and state != "sleep" and "ko" in frames:   # 被打晕了: X 眼
            return "ko"
        if self.tia is not None and state != "sleep" and self._has_notiara():
            return "notiara"
        if self.wand is not None and state != "sleep":
            return "nowand" if "nowand" in frames else "held"
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
        elif self._unconscious() and p.isVisible() and not p.edge:
            items.append(("🖌", "画花脸", self.start_doodle))
        if self.doodle == "wearing" and p.state != "sleep":
            items.append(("🪞", "给她照照镜子", self.mirror))
        free = p.state != "sleep" and self._awake_free()           # 抢不了的时候(幽灵、生病、冻住……)不列
        if self.tiara_ok() and self.tia is None and self.wand is None and free:
            items.append(("👑", "抢她的头冠", self.steal_from_menu))
        if self.wand_ok() and self.wand is None and self.tia is None and free:
            items.append(("🪄", "抢她的法杖", self.steal_wand_from_menu))
        if self.wand is not None and self.wand["ret"] is None:
            items.append(("🪄", "把法杖还给她", lambda: self.wand_clicked(True)))
        return items

    def tune(self, name, value, ctx):
        if name == "lull_ok":                                     # 头冠 / 法杖还在你手里: 不肯被哄睡
            busy = self.wand is not None or self.tia is not None or self.drawing or self.charge is not None
            return False if busy else None
        if name == "lull_refuse_lines":
            return WAND_NO_SLEEP if self.wand is not None else TIARA_NO_SLEEP if self.tia is not None else None
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
        elif name == "body_marks":                            # 灵魂形态: 她回到身子里, 身子上被作弄的样子带回来
            self._body_marks(data)
        if name == "wake":
            if self.drawing:
                self.end_doodle(quiet=True)
            if self.strokes and self.doodle == "fresh" and not self.caught:
                self.doodle = "wearing"
                self.notice_at = t + random.uniform(*NOTICE_SEC)
        elif name in ("drag_start", "click", "double_click"):
            self.fpend = None

    def _body_marks(self, data):
        """灵魂形态插件推的 body_marks: 涂鸦(她看见了 -> 马上擦、记仇) / 额头的包 / 头冠掉在地上(她过去捡)"""
        p = self.pet
        strokes = [[(float(x), float(y)) for x, y in st] for st in (data.get("strokes") or []) if st]
        if strokes:
            self.end_doodle(quiet=True)
            self.strokes, self.ink, self.caught = strokes, 1.0, False
            self._cache.clear()
            if p.state == "sleep":
                self.doodle = "fresh"
            else:
                self.doodle = "wearing"
                self.notice_at = time.monotonic() + 9999
                if data.get("seen"):
                    QTimer.singleShot(1000, lambda: self.doodle == "wearing" and self._found("ghost"))
        bump = float(data.get("bump") or 0.0)
        if bump > 0.01:
            self.bump = max(self.bump, min(1.6, bump))
            self._cache.clear()
        at = data.get("tiara_at")
        if at and self.tiara_ok() and self.tia is None and self.wand is None and p.state != "sleep":
            w = TiaraWin(self, self.tiara_pm, max(40.0, p.char_w * TIARA_W))
            w.center_at(QPointF(float(at[0]), float(at[1])))
            w.show()
            now = time.monotonic()
            self.tia = dict(mode="ground", win=w, t0=now, vy=0.0, next=now + 1.5, high=0.0, hop=0.0, sad=False,
                            said=0.0)
            p.emit_event("tiara", stage="ground", memo="她回到身子里，头冠还掉在旁边地上")

    def on_pet(self):
        p = self.pet
        if self.ko is not None and p.state != "sleep":
            if not p.bubble.isVisible():
                self._say("wkopoke", WAND_KO_POKE, 1.6, None)
            return True
        if self.tia is not None or self.wand is not None:
            return True                                   # 忙着追头冠 / 叫法杖, 顾不上
        if time.monotonic() < self.grudge_until and p.state != "sleep":
            p.set_state("angry", 1.6)
            p.kick(-1.2)
            self._say("grudge", GRUDGE_PET, 2.4)
            return True
        return False

    def on_click(self, double):
        if self.ko is not None and self.pet.state != "sleep":   # 晕着: 戳一下只哼一声
            self.pet.kick(-0.6)
            if not self.pet.bubble.isVisible():
                self._say("wkopoke", WAND_KO_POKE, 1.6, None)
            return True
        if self.tia is not None and not self.tia.get("sad"):
            if not self.pet.bubble.isVisible():
                self._say("chase", TIARA_CHASE, 1.6)
            return True
        if self.wand is not None:
            wd = self.wand
            if wd["ret"] is None and wd["boom"] is None:       # 拿法杖敲她一下 = 乱施法
                if time.monotonic() - wd["cast_at"] >= WAND_CAST_COOL:
                    self._wand_cast()
                elif not self.pet.bubble.isVisible():
                    self._say("wchase", WAND_CHASE, 1.6)
            return True
        return False

    def on_context_menu(self, e):
        """拿着法杖时右键点她 = 还给她(她晕着时照常弹菜单: 画花脸 / 还法杖)"""
        wd = self.wand
        if wd is None or self.ko is not None:
            return False
        if wd["ret"] is None and wd["boom"] is None:
            self.wand_clicked(True)
        return True

    def on_mouse_press(self, e):
        p = self.pet
        if e.button() != Qt.LeftButton or self.drawing or self.tia is not None or self.wand is not None:
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
        if self._wand_grab(pos, delta):
            return True
        if (self.wand is not None or not self.tiara_ok() or self.tia is not None or self.drawing
                or not self._awake_free()):
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
    def _unconscious(self):
        """睡着, 或被法杖打晕了"""
        return self.pet.state == "sleep" or self.ko is not None

    def start_doodle(self):
        p = self.pet
        if self.drawing or not self._unconscious() or not p.isVisible() or p.edge or p.mouse_captured():
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
            p.emit_event("doodle", stage="drawn", strokes=len(self.strokes), ko=self.ko is not None,
                         memo="你趁她" + ("被打晕" if self.ko is not None else "睡着") + "，在她脸上画了画（她还不知道）（互动）")
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
        if self.wand is not None:                             # 捏着法杖时右键 = 还给她
            if e.button() == Qt.RightButton:
                self.wand_clicked(True)
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
                if self.ko is not None:                       # 打晕了: 不觉得痒
                    self.itch = 0.0
                else:
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
        if self.wand is not None:                             # 松手: 法杖还捏在手里, 跟着鼠标
            if self.wand["mode"] == "held" and e.button() == Qt.LeftButton:
                self.wand["mode"] = "follow"
                self.pet.release_mouse(self)
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
        if self.ko is not None:                               # 晕醒了, 正好看见你拿着笔
            self._ko_wake(time.monotonic(), quiet=True)
        else:
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
        elif by == "ghost":
            self._say("fghost", DOODLE_GHOST, 2.6)
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
                     memo={"caught": "你在她脸上画画时把她弄醒了，被当场抓包（互动）",
                           "ghost": "她灵魂出窍时看着你在她身子脸上画画，回到身子里马上一边擦一边记仇（互动）"}.get(
                         by, "她发现你在她脸上画了画，气坏了，一边擦一边记仇（互动）"))

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
        if self.tiara_ok() and self.tia is None and self.wand is None and self._awake_free():
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

    # ----- 5. 抢法杖 -----
    def wand_ok(self):
        return self.wand_pm is not None

    def _can_steal_wand(self):
        return (self.wand_ok() and self.wand is None and self.tia is None and not self.drawing and self.charge is None
                and self._awake_free())

    def _hand(self):
        """她手里平时拿法杖的地方(屏幕坐标)"""
        return self._glob(*WAND_HAND)

    def steal_wand_from_menu(self):
        if self._can_steal_wand():
            self._steal_wand(held=False)

    def _wand_grab(self, pos, delta):
        """按住杖头往外(离开她身子那边, 立绘里是往左)拽 -> 抢法杖; 往别的方向拖还是照常把她拎起来"""
        if not self._can_steal_wand():
            return False
        nx, ny = self._norm(pos)
        key = self.pet.stand_key() if hasattr(self.pet, "stand_key") else "idle"
        if not self._in(WAND_HEAD.get(key, _WH_IDLE), nx, ny):
            return False
        out = -delta.x() if getattr(self.pet, "face", 1.0) >= 0 else delta.x()
        if out <= 0 or out < abs(delta.y()) * 0.6:
            return False
        if time.monotonic() < self.wand_guard:                # 抱紧了: 照常被拎起来
            QTimer.singleShot(0, lambda: self._say("wguard", WAND_GUARDED, 2.0))
            return False
        self.fpend = None
        self._steal_wand(held=True)
        return True

    def _steal_wand(self, held):
        p = self.pet
        p.note_interaction()
        p.stop_walk()
        w = WandWin(self, self.wand_pm, max(36.0, p.char_w * WAND_W))
        if held:
            p.capture_mouse(self)
        w.grip_at(QPointF(QCursor.pos()))
        w.show()
        now = time.monotonic()
        self.wand = dict(mode="held" if held else "follow", win=w, t0=now, next_tug=now + WAND_TUG_FIRST, tugs=0,
                         tug=None, casts=0, cast_at=-1e9, hit_at=-1e9, last=None, boom=None, ret=None, spark=0.0)
        self.wand_hist.clear()
        p.set_state("surprised", 1.0)
        p.burst("excl", 1)
        p.sfx.play("huh")
        self._say("wstolen", WAND_STOLEN, 2.0)
        p.mood.add(-3.0)
        self._lose("wand")
        p.emit_event("wand", stage="stolen", memo="你把她的法杖抢走了，她两手空空，念咒想把它叫回来（互动）")

    def wand_clicked(self, right):
        """拿着法杖: 挥一下(左键点她) / 还给她(右键点她、菜单)"""
        wd = self.wand
        if wd is None or wd["ret"] is not None or wd["boom"] is not None:
            return
        if right:
            self._wand_return("given")
        else:
            self._wand_cast()

    def _wand_cast(self):
        wd, p = self.wand, self.pet
        t = time.monotonic()
        if wd is None or wd["ret"] is not None or wd["boom"] is not None or t - wd["cast_at"] < WAND_CAST_COOL:
            return
        wd["cast_at"] = t
        if self.ko is not None:                                 # 她晕着: 法杖也没劲了, 只闪一下
            wd["win"].flash = 0.35
            return
        wd["casts"] += 1
        wd["win"].flash = 1.0
        p.sfx.play("sparkle")
        p.note_interaction()
        if wd["casts"] == WAND_BOOM_AT:                         # 第三下: 杖在你手里抖, 然后炸
            wd["boom"] = t + 0.6
            p.emit_event("wand", stage="cast", kind="boom", n=wd["casts"],
                         memo="你又拿她的法杖乱挥，法杖在她面前炸了，她被炸得灰头土脸（互动）")
            return
        if wd["casts"] >= WAND_KO_AT:                           # 第六下: 打晕
            QTimer.singleShot(260, lambda: self.wand is wd and wd["ret"] is None and self._wand_knockout())
            p.emit_event("wand", stage="cast", kind="ko", n=wd["casts"],
                         memo="你拿她的法杖连着乱挥，最后一下把她打晕了（互动）")
            return
        kind = random.choice([k for k in WAND_SPELLS if k != wd["last"]])
        wd["last"] = kind
        QTimer.singleShot(260, lambda: self.wand is wd and wd["ret"] is None and self._wand_hit(kind))
        p.emit_event("wand", stage="cast", kind=kind, n=wd["casts"],
                     memo="你拿她的法杖乱挥了一下，魔法打到了她身上（互动）")

    def _wand_hit(self, kind):
        """乱施的魔法打到她身上"""
        p, wd = self.pet, self.wand
        t = wd["hit_at"] = time.monotonic()
        self._wand_break_tug(t)
        hp = p.head_point()
        p.stop_walk()
        p.mood.add(-1.0)
        if kind == "flower":
            p.set_state("surprised", 1.4)
            p.burst("heart", 5, at=hp)
            p.burst("sparkle", 6, at=hp)
        elif kind == "float":
            p.do_jump(True)
            p.burst("sparkle", 4, at=p.foot_point())
        elif kind == "zap":
            p.set_state("surprised", 1.4)
            p.kick(-2.0)
            p.burst("emoji", 1, at=QPointF(hp.x(), hp.y() - 8), bias=(0, -40), text="⚡")
            p.burst("sweat", 2)
        else:
            p.set_state("surprised", 1.4)
            p.burst("snow", 10, at=QPointF(hp.x(), hp.y() - p.char_h * 0.12), bias=(0, 60))
        self._say("wcast_" + kind, WAND_CAST[kind], 2.0)

    def _wand_break_tug(self, t, wait=2.0):
        """念到一半被打断: 这次不算, 缓一缓再念"""
        wd = self.wand
        if wd["tug"] is not None:
            wd["tug"] = None
            wd["win"].glow = 0.0
        wd["next_tug"] = max(wd["next_tug"], t + wait)

    def _wand_boom(self):
        """第三下: 法杖在她面前炸了, 她一脸灰; 法杖还在你手里"""
        p, wd = self.pet, self.wand
        t = time.monotonic()
        wd["boom"] = None
        wd["hit_at"] = t
        self._wand_break_tug(t, 3.4)
        hp = p.head_point()
        p.stop_walk()
        p.burst("puff", 12, at=hp, bias=(0, 0))
        p.burst("star", 6, at=hp)
        p.sfx.play("bonk")
        self.soot = 1.0
        self._cache.clear()
        p.mood.add(-2.0)
        p.set_state("dizzy", 2.4)
        self._say("wboom", WAND_BOOM, 2.6)
        QTimer.singleShot(2600, self._boom_mad)

    def _wand_knockout(self):
        """第六下: 她被打晕, WAND_KO_SEC 秒内叫不回法杖"""
        p, wd = self.pet, self.wand
        t = time.monotonic()
        self.ko, self.ko_stirred, self.ko_stars = t + WAND_KO_SEC, False, 0.0
        wd["hit_at"] = t
        self._wand_break_tug(t, WAND_KO_SEC + 1.0)
        hp = p.head_point()
        p.stop_walk()
        p.kick(-2.4)
        p.burst("star", 8, at=hp)
        p.sfx.play("bonk")
        p.set_state("dizzy", WAND_KO_SEC + 0.5)
        p.mood.add(-3.0)
        self._lose("wand")
        self._say("wko", WAND_KO, 2.4, None)
        p.emit_event("wand", stage="ko", sec=WAND_KO_SEC,
                     memo="她被你拿她的法杖打晕了，晕着的时候叫不回法杖（互动）")

    def _ko_step(self, t):
        """打晕期间: 头上绕星星; 快醒时动一下; 到时间醒(你正在她脸上画 -> 抓包)"""
        p = self.pet
        if self.ko is None:
            return
        if not p.isVisible() or p.state == "sleep":
            self.ko = None
            return
        if t >= self.ko:
            if self.drawing and self.cur is not None:         # 醒的那一刻你还在画: 抓个正着
                self._caught()
                return
            if self.drawing:
                self.end_doodle(quiet=True)
            self._ko_wake(t)
            return
        if not self.ko_stirred and t >= self.ko - KO_STIR_BEFORE:
            self.ko_stirred = True
            self.itch, self.stir_at = 0.0, t                  # 和睡着时一样: 动完还接着画 -> 醒了, 抓包
            p.kick(-0.9)
            p.tilt += random.choice((-1, 1)) * 3
            self._say("kostir", WAND_KO_STIR, 1.6, None)       # 只动这一下, 一定要让你看到
        if t >= self.ko_stars:
            self.ko_stars = t + 2.6
            p.burst("orbit", 3, bias=(0, 0))

    def _ko_wake(self, t, quiet=False):
        """晕醒了: 法杖还在你手里 -> 气坏了, 下一次念咒一定叫回去; 已经还给她了 -> 迷迷糊糊"""
        p, wd = self.pet, self.wand
        self.ko = None
        p.kick(-1.6)
        if wd is not None:
            wd["sure"] = True                             # 醒过来这一轮: 不跟你对拉, 一定叫回去
            wd["tugs"] = max(wd["tugs"], len(WAND_TUG_K) - 1)
            wd["next_tug"] = t + 2.2
            if not quiet:
                p.set_state("angry", 2.2)
                p.burst("anger", 2, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
                p.sfx.play("hmph")
                self._say("wkowake", WAND_KO_WAKE, 2.2)
            p.emit_event("wand", stage="ko_end", memo="她晕醒了，气得马上要把法杖叫回去")
        else:
            if not quiet:
                p.set_state("idle")
                self._say("wkowake2", WAND_KO_WAKE_HAS, 2.4, None)
            p.emit_event("wand", stage="ko_end", memo="她晕醒了，法杖已经在她手里")

    def _wand_return(self, how):
        """法杖飞回她手里(叫回来 / 炸了 / 你还给她), 飞到了再 _wand_back"""
        wd = self.wand
        if wd is None or wd["ret"] is not None:
            return
        self.pet.release_mouse(self)
        w = wd["win"]
        wd["ret"] = dict(how=how, t0=time.monotonic(), a=w.grip_global())
        wd["tug"] = None
        w.glow = 0.0

    def _wand_back(self, how):
        p = self.pet
        wd, self.wand = self.wand, None
        if wd is None:
            return
        p.release_mouse(self)
        try:
            wd["win"].hide()
            wd["win"].deleteLater()
        except Exception:
            pass
        self.wand_guard = time.monotonic() + WAND_GUARD
        if how == "silent":
            return
        p.stop_walk()
        if self.ko is not None:                               # 晕着时还给她: 法杖塞回手里, 她还没醒
            left = self.ko - time.monotonic()
            if left > 0.3:
                p.set_state("dizzy", left, expr="ko" if "ko" in getattr(p, "frames", {}) else None)
            p.emit_event("wand", stage="back", how=how, ko=True, memo="她晕着的时候，你把法杖塞回了她手里")
            return
        if how == "summon":
            p.set_state("happy", 2.2)
            p.burst("sparkle", 6, at=self._hand())
            self._say("wback", WAND_BACK_SUMMON, 2.6, "happy")
            memo = "她念咒把法杖叫回了手里"
        elif how == "given":
            p.set_state("content", 2.2, expr="smug" if "smug" in getattr(p, "frames", {}) else None)
            p.burst("sparkle", 3, at=self._hand())
            p.mood.add(1.5)
            self._say("wgiven", WAND_GIVEN, 2.6, None)
            memo = "你把法杖还给了她"
        else:
            memo = "她把法杖拿回来了"
        p.emit_event("wand", stage="back", how=how, memo=memo)

    def _boom_mad(self):
        p, wd = self.pet, self.wand
        if p.state == "sleep" or not p.isVisible():
            return
        if self.ko is not None or (wd is not None and (wd["ret"] is not None or wd["tug"] is not None)):
            return
        p.set_state("angry", 2.6)
        p.burst("anger", 2, at=p.head_point() + QPointF(p.char_w * 0.25, -10))
        p.sfx.play("hmph")
        self._say("wmad", WAND_BOOM_MAD, 2.8)

    def _wand_shook(self, t, x):
        """鼠标左右来回甩: 0.7 秒内来回 3 次(每段至少 WAND_SHAKE_PX)"""
        h = self.wand_hist
        h.append((t, x))
        while h and t - h[0][0] > 0.7:
            h.popleft()
        turns, last, anchor = 0, 0, None
        for _, xx in h:
            if anchor is None:
                anchor = xx
                continue
            d = xx - anchor
            if abs(d) >= WAND_SHAKE_PX:
                dirn = 1 if d > 0 else -1
                if last and dirn != last:
                    turns += 1
                last, anchor = dirn, xx
        if turns >= 3:
            h.clear()
            return True
        return False

    def _wand_step(self, t, dt):
        wd, p = self.wand, self.pet
        if wd is None:
            if self.soot > 0.0:
                old = round(self.soot, 2)
                self.soot = max(0.0, self.soot - dt / WAND_SOOT_SEC)
                if round(self.soot, 2) != old:
                    self._cache.clear()
            return
        if not p.isVisible() or p.state == "sleep":
            self._wand_back("silent")
            return
        w = wd["win"]
        w.flash = max(0.0, w.flash - dt * 2.4)
        r = wd["ret"]
        if r is not None:                                        # 飞回她手里
            u = min(1.0, (t - r["t0"]) / WAND_RET_SEC)
            e = u * u * (3 - 2 * u)
            hand = self._hand()
            w.grip_at(r["a"] + (hand - r["a"]) * e)
            w.rot = -40.0 * math.sin(math.pi * u)
            w.update()
            if u >= 1.0:
                self._wand_back(r["how"])
            return
        cur = QPointF(QCursor.pos())
        if wd["boom"] is not None:                               # 要炸了: 在你手里抖
            w.rot = 14.0 * math.sin(t * 55.0)
            w.flash = max(w.flash, 0.5 + 0.5 * math.sin(t * 30.0))
            w.grip_at(cur)
            w.update()
            if t >= wd["boom"]:
                self._wand_boom()
            return
        if self.drawing:                                         # 你在她脸上画画: 法杖先放下
            if w.isVisible():
                w.hide()
            return
        if not w.isVisible():
            w.show()
        target = cur
        tug = wd["tug"]
        if tug is not None:                                      # 她念咒往回叫: 法杖往她那儿挣
            u = (t - tug["t0"]) / WAND_TUG_SEC
            if u >= 1.0:
                wd["tug"] = None
                w.glow = 0.0
                self._say("wfail", WAND_TUG_FAIL, 1.8)
                p.emit_event("wand", stage="tug", n=wd["tugs"], ok=False)
            else:
                ramp = min(1.0, u / 0.55)
                smooth = ramp * ramp * (3 - 2 * ramp)
                hand = self._hand()
                if tug.get("sure"):
                    resist = 0.0
                else:
                    origin = tug["origin"]
                    d0 = math.hypot(origin.x() - hand.x(), origin.y() - hand.y())
                    d1 = math.hypot(cur.x() - hand.x(), cur.y() - hand.y())
                    need = WAND_RESIST * (0.75 + 0.12 * min(wd["tugs"], 6))
                    resist = min(1.0, max(0.0, d1 - d0) / need)
                pull = tug["k"] * smooth * (1.0 - resist)
                target = cur + (hand - cur) * pull
                w.glow = min(1.0, u * 3.0) * (1.0 - 0.65 * resist)
                w.rot = (6.0 + 10.0 * resist) * math.sin(t * (38.0 + 24.0 * resist))
                if resist >= 0.55 and not tug.get("fought"):
                    tug["fought"] = True
                    self._say("wfight", WAND_TUG_FIGHT, 1.4)
                if t >= wd["spark"]:
                    wd["spark"] = t + 0.25
                    p.burst("sparkle", 1, at=hand)
                d = target - hand
                if math.hypot(d.x(), d.y()) <= p.char_w * WAND_REACH:
                    w.grip_at(target)
                    p.emit_event("wand", stage="tug", n=wd["tugs"], ok=True)
                    self._wand_return("summon")
                    return
        else:
            w.rot *= 0.8
        w.grip_at(target)
        w.update()
        if tug is None and self.ko is None and t >= wd["next_tug"]:    # 再念一次咒
            sure = bool(wd.pop("sure", False))
            k = 1.0 if sure else WAND_TUG_K[min(wd["tugs"], len(WAND_TUG_K) - 1)]
            wd["tug"] = dict(t0=t, k=k, origin=QPointF(QCursor.pos()), fought=False, sure=sure)
            wd["tugs"] += 1
            wd["next_tug"] = t + WAND_TUG_SEC + WAND_TUG_GAP
            p.stop_walk()
            p.set_state("wave", WAND_TUG_SEC + 0.3)
            p.sfx.play("sparkle")
            self._say("wsummon", WAND_SUMMON, WAND_TUG_SEC + 0.5)
        if self._wand_shook(t, cur.x()):
            self._wand_cast()

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
        if not draw_ink and self.bump <= 0.01 and self.charge is None and self.soot <= 0.01:
            return None
        ck = (pm.cacheKey(), sum(len(s) for s in self.strokes), round(self.ink, 2), round(self.bump, 2),
              None if self.charge is None else int((t - self.charge["t0"]) * 12), round(self.soot, 2))
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
        if self.soot > 0.01:                                   # 炸完脸上的灰
            a = min(1.0, self.soot * 1.3)
            q.setPen(Qt.NoPen)
            for i, (sx, sy, sr) in enumerate(SOOT_SPOTS):
                for dx, dy, k in ((0.0, 0.0, 1.0), (0.6, -0.35, 0.55), (-0.5, 0.4, 0.45)):
                    c = QPointF((sx + sr * dx) * w, (sy + sr * dy) * h)
                    rr = sr * k * w
                    g = QRadialGradient(c, rr)
                    g.setColorAt(0, QColor(72, 66, 74, int(150 * a)))
                    g.setColorAt(0.6, QColor(92, 86, 94, int(95 * a)))
                    g.setColorAt(1, QColor(110, 104, 110, 0))
                    q.setBrush(g)
                    q.drawEllipse(c, rr, rr * 0.8)
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
        self._ko_step(t)
        if self.drawing and not self._unconscious():
            self.end_doodle(quiet=True)
        self._doodle_step(t)
        self._danika_step(t)
        self._tiara_step(t, dt)
        self._wand_step(t, dt)
        self._flick_step(t, dt)


def create(pet, log_fn=None):
    if not hasattr(pet, "capture_mouse"):                      # 旧本体没有接管鼠标的接口: 不加载
        return None
    return Tease(pet, log_fn)
