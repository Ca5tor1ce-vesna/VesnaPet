# -*- coding: utf-8 -*-
"""薇斯纳桌宠 (VesnaPet) —— PySide6 桌面宠物
核心表情: idle / happy / angry / sleep / surprised
扩展表情(缺图时回退): wave stretch yawn cheer dizzy look look_left eat content shy focus love
"""
import json
import math
import os
import random
import sys
import time
from collections import deque
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QColor, QCursor, QDesktopServices, QFont, QFontMetrics, QGuiApplication, QIcon,
                           QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QTransform)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

import content as C
import food_packs
import interaction_hooks
from companion import Butterfly, DanikaVisit
from effects import FxLayer, ease_out_back
from food_fx import FoodEffect
from grok_link import GrokLink, error_log_path, log_error
from live_link import LiveHub
from sounds import Sfx
from stats import Stats, data_dir
import sysidle
from mood import Mood
from ui_kit import INK, draw_gem, font, food_pixmap, shadow_image

APP_NAME = "VesnaPet"
# 打包成 exe(PyInstaller)时素材在 sys._MEIPASS 下; 源码运行时在本文件旁边
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ASSET_DIR = BASE_DIR / "assets"
CORE_STATES = ("idle", "happy", "angry", "sleep", "surprised")
EXTRA_STATES = {"wave": "happy", "stretch": "happy", "yawn": "sleep", "cheer": "happy", "dizzy": "surprised",
                "look": "idle", "look_left": "look", "eat": "happy", "content": "happy", "shy": "idle",
                "focus": "idle", "love": "happy"}
STATES = CORE_STATES + tuple(EXTRA_STATES)
PEEK_EXTRA = {"peek_happy": "peek_awake", "peek_surprised": "peek_awake"}
# 只换脸的表情: 不是新状态。状态还是右边那个(动作、计时、互动规则全照旧), 只是这会儿画这张图;
# assets 里没有这张图就照常画右边那个状态的图。谁来换: set_state(..., expr=) / stand_key 自己判断 / 插件 expr()
FACES = {"pout": "shy", "smug": "content", "hungry": "idle", "queasy": "dizzy",
         "sulk": "angry", "held": "surprised", "yuck": "angry", "wet": "angry"}
HUNGRY_FACE = 25                # 饱腹低于这个, 站着发呆时换成「饿了」那张

# ---------------- 可调参数 ----------------
SIZES = {"small": 140, "medium": 200, "large": 300}
DEFAULT_SIZE = "medium"
IDLE_SLEEP_SEC = 180
HAPPY_EVERY = (12, 28)          # 随机小动作间隔(秒)
HAPPY_DURATION = (2.0, 3.0)
BUBBLE_EVERY = (30, 60)
BUBBLE_DURATION = 3.5
SURPRISED_SEC = 1.0
WAKE_GRUMPY_SEC = 3.5           # 睡着被拖醒: 松手后不满的时长
WAKE_SPIN_ANGRY_SEC = 4.0       # 睡着被转醒: 生气时长
WAKE_SPIN_GRACE = 1.2           # 转醒后这段时间内的滚轮不计入晕度
WAKE_RUDE_COOL = 300.0          # 粗暴叫醒扣好感的冷却(秒)
SLEEP_MUMBLE_COOL = 25.0        # 梦话最小间隔(秒)
SLEEP_MUMBLE_P = 0.3            # 鼠标经过时说梦话的概率
ANGRY_SEC = 2.0
RAPID_CLICKS = 3
RAPID_WINDOW = 1.6
DRAG_THRESHOLD = 4
DRAG_STATE = "surprised"
PAD = 14
SNAP_DIST = 40
PEEK_SLEEP_SEC = 60
PEEK_SCALE = 0.74
PEEK_HIDE = 30
PEEK_TPAD = 40
PEEK_TILT = 10
PEEK_EDGES = ("left", "right", "top")
SPRING_K, SPRING_D = 180.0, 12.0  # 果冻弹簧
FLING_MIN = 900                 # 松手速度(像素/秒)超过它就"甩出去"
FLING_STICK = 1500              # 撞墙速度超过它就"咚"地贴墙探头
PET_REVERSALS = 4               # 摸头: 1.5 秒内左右来回次数
DIZZY_NOTCHES = 14              # 转圈"晕度"(滚轮格数, 会慢慢消退)达到它 -> 转晕
WALK_SPEED = 70                 # 散步速度(像素/秒)
BUTTERFLY_EVERY = (240, 540)    # 蝴蝶来访间隔(秒)
BCHASE_DELAY = 1.2              # 蝴蝶出现后多久开始追(秒)
BCHASE_RETARGET = (0.5, 0.8)    # 重新瞄准间隔(秒)
BCHASE_MAX = 12.0               # 最长追逐时长(秒)
BCHASE_SPEED = 300.0            # 追蝴蝶步速(px/s)
BCHASE_LAND_P = 0.8             # 追到后蝴蝶落头上的概率
DANIKA_EVERY = (1200, 2100)     # 达妮卡来访最短间隔(秒) ~20–35 分(约原 2.5×)
DANIKA_IDLE_P = 0.04            # idle 掷骰触发概率(约原 1/2.5)
DRAG_HOLD_SEC = 5.0             # 拖住这么久: 轻扭 + 第一句
DRAG_HOLD_HARD = 9.0            # 更用力挣扎 + 第二句
DRAG_HOLD_FURY = 13.5           # 激烈挣扎 + 第三句(仍不会自己挣脱)
DRAG_HOLD_WIND = 18.0           # 再拖: 风元素爆发(转圈+吹光标,仍不挣脱)
SNEAK_SEC = (3.2, 4.6)          # 偷吃持续时长
STARE_SEC = 4.0                 # 悬停不动多久算"盯着看"
# 离开 / 回来: 看整台电脑的键盘鼠标有多久没动(只有 Windows 读得到; 读不到就按老规矩, 她睡着算你不在)
AWAY_SEC = 600.0                # 这么久没动 = 你离开电脑了; 回来时她迎接你
SIT_BREAK_SEC = 300.0           # 这么久没动 = 起来活动过了, 久坐计时重来; 这期间也不响提醒
BACK_LONG_SEC = 7200.0          # 离开超过这么久, 用「等了你好久」那组台词
RETURN_CHEER_LV = 4             # 好感到这一级(好友)起, 你回来时她跳起来欢迎
# 被丢出去 / 闹别扭
THROW_WINDOW = 60.0             # 这段时间内连续丢她, 一次比一次生气(秒)
THROW_HARD = 2600               # 松手速度超过它算"狠狠地丢"(生气 +1 级)
WALL_BONK_MIN = 520             # 撞墙速度超过它才"咚"一下
THROW_WALL_DIZZY_SEC = 2.4      # 丢出去撞墙: 先晕这么久,再抱怨; 没撞墙不晕
SULK_SEC = 13.0                 # 第 3 次起闹别扭时长(秒), 不哄也会自己消气
SULK_CALM_CLICKS = 3            # 闹别扭时轻轻点几下(别连戳)就能哄好; 摸头/投喂立刻哄好
SULK_POKE_ADD = 3.0             # 闹别扭时连戳: 多气几秒
# 投喂
FEED_WINDOW = 150.0             # 这段时间内(秒)
FEED_MAX = 12                   # 吃了这么多份就饱了, 不再吃(最爱的能用"另一个胃"再吃一份)
FULL_HUNGER = 95                # 饱腹 >= 它也算吃饱
FOOD_REFUSE_P = 0.45            # 不爱吃的: 直接推开的概率(否则皱着脸勉强吃)
FOOD_REFUSE_WEIRD = 0.6         # 奇怪的料理: 推开的概率
DISLIKE_WINDOW = 120.0          # 这段时间内连喂 3 次讨厌的 -> 闹别扭
DISLIKE_SULK = 3
# 转圈圈
SPIN_DECAY = 0.8                # 晕度每秒消退多少格
SPIN_WOOZY = 8                  # 晕度 >= 它: "有点晕了"
DIZZY_SEC = 4.0                 # 转晕(摇摇晃晃)时长
SPIN_PRE_ANGRY_SEC = 2.4        # 这一轮停下后先晕这么久, 再生气
SPIN_REFUSE_SEC = 15.0          # 这一轮停下来之后, 这么久内拦住下一次转
QUIP_GAP = 1.1                  # 互动台词最短间隔(秒), 防止气泡刷屏
# DLC say (live 协议 v2): 允许 DLC 换的表情白名单, 以及只在这些「平静」状态下才换表情
LIVE_SAY_EXPRS = ("happy", "angry", "surprised", "shy", "love", "content", "cheer", "wave", "look", "look_left",
                  "idle", "focus")
LIVE_SAY_CALM = ("idle", "look", "look_left", "happy", "content", "shy", "wave", "love", "cheer", "surprised",
                 "focus")
LIVE_SAY_FACES = ("pout", "smug")       # DLC 也能要这两张脸(状态用 FACES 里对应的那个)

# ---------------- 活动 / 互动矩阵 ----------------
# activities() 返回她此刻在做的事(下面这些名字, 外加插件 busy() 报上来的名字)。
# 自动行为开始前查 AUTO: 表情不在白名单, 或和拦它的活动有交集, 就不做。改规则只改这张表。
# docs/接口规范.md 里的互动矩阵就是这张表; 改了这里记得同步文档。
ACTIVITIES = {
    "hidden": "隐藏着", "sleep": "睡着", "edge": "贴边探头",
    "drag": "被拖着", "fling": "甩出去/被丢, 还在飞或滑", "throw": "被丢: 从飞出去到落地抱怨完",
    "walk": "散步/走过来", "chase": "追蝴蝶", "sneak": "偷吃", "food_fx": "食物包吃后效果",
    "sulk": "闹别扭", "spin": "滚轮转圈中/转过头待发作", "dizzy": "晕着",
    "danika": "达妮卡来访", "butterfly": "蝴蝶在场", "panel": "开着面板(小屋/运势/猜拳等)",
    "focus": "专注计时(未暂停)", "link": "Grok 联动工作中", "away": "你离开电脑了(仅 Windows)",
    "plugin": "有插件的 busy() 非空",
}
AUTO = {   # 自动行为: (只在这些表情下做, None = 不限; 会拦住它的活动)
    "idle_action": (("idle",), {"hidden", "drag", "fling", "walk", "food_fx", "plugin"}),
    "danika_auto": (None, {"edge", "sulk", "danika", "butterfly", "panel", "focus", "link"}),
    "danika": (None, {"sleep", "edge", "drag", "fling", "walk", "sulk", "link"}),
    "random_bubble": (("idle", "happy"), {"hidden", "drag", "food_fx", "danika", "focus", "link", "plugin"}),
    "sneak": (("idle",), {"edge", "drag", "fling", "walk", "sulk", "danika", "butterfly", "focus", "link",
                          "plugin"}),
    "auto_butterfly": (None, {"hidden", "sleep", "drag", "food_fx", "butterfly", "focus", "plugin"}),
    "chase": (None, {"hidden", "sleep", "dizzy", "edge", "drag", "fling", "sulk", "food_fx", "danika", "panel",
                     "focus", "link", "plugin"}),
    "fall_asleep": (("idle",), {"drag", "fling", "walk"}),
    "reminder": (None, {"drag", "fling", "sulk", "danika", "focus", "plugin"}),
    "welcome_back": (None, {"hidden", "drag", "fling", "throw", "food_fx", "sulk", "danika", "focus", "link",
                            "plugin"}),
    "plugin_talk": (("idle", "look", "look_left", "content", "happy"),       # 插件主动开口(小心愿/她记得)
                    {"hidden", "sleep", "drag", "fling", "throw", "walk", "chase", "sneak", "food_fx", "sulk", "spin",
                     "dizzy", "danika", "butterfly", "panel", "focus", "link", "away", "plugin"}),
    "live_say": (None, {"sleep", "dizzy", "drag", "fling", "throw", "spin", "danika", "food_fx", "plugin"}),
}
# 插件能通过 tune() 调的参数(心情 / 好感要不要影响行为, 由插件决定; 本体只在这些决策点问一句):
# 名字 -> (类型, 下限, 上限)。插件给的值不合法就用原值; 文档 docs/接口规范.md 有同一张表。
TUNABLE = {
    "idle_gap": ("float", 3.0, 600.0),          # 下一次空闲小动作隔多少秒
    "idle_weights": ("weights", 0.0, 50.0),     # 空闲小动作各项权重 {happy look stretch hop wave walk sneak}
    "bubble_gap": ("float", 5.0, 1800.0),       # 下一次随机冒泡隔多少秒
    "bubble_pool": ("lines", None, None),       # 随机冒泡的台词池
    "sleep_after": ("float", 15.0, 3600.0),     # 多久没人理就睡着(秒); ctx: edge
    "food_refuse_p": ("float", 0.0, 1.0),       # 不爱吃 / 奇怪的东西直接推开的概率; ctx: key tier trait
    "come_ok": ("bool", None, None),            # 叫她「过来~」肯不肯来
    "come_refuse_lines": ("lines", None, None), # 不肯过来时说的那句
    "greet_lines": ("lines", None, None),       # 你离开一阵回来, 她迎接你说的那句; ctx: long(离开很久), level
    "greet_cheer": ("bool", None, None),        # 迎接时(好友起)要不要欢呼、蹦、冒爱心; False = 只挥挥手
    "status_line": ("text", 1, 20),             # 小屋头部「没事时」那句; ctx: kind(hungry|butterfly|level), level
    "drag_hold_rate": ("float", 0.0, 2.0),      # 拖着她时挣扎计时走多快(1 = 原版; 0.25 = 慢慢来); ctx: held(真实秒数), stage
    "hungry_remind": ("float", 0.0, 86400.0),   # 饿了提醒的间隔(秒), 0 = 本体不提醒(交给插件)
    "sneak_done_lines": ("lines", None, None),  # 偷吃没被发现, 吃完得意的那句的台词池
    "sneak_caught_lines": ("lines", None, None),  # 偷吃被你点到, 害羞否认的那句的台词池
}

TRAY_QSS = """
QMenu{background:#FFFFFF;border:1px solid #DCE3F1;border-radius:14px;padding:8px 6px;}
QMenu::item{padding:7px 26px 7px 14px;border-radius:9px;color:#2E3F6E;margin:1px 2px;}
QMenu::item:selected{background:#E3F7F3;color:#2C9F8F;}
QMenu::item:disabled{color:#9AA5C0;}
QMenu::separator{height:1px;background:#EDF1F8;margin:5px 10px;}
"""


# ---------------- 配置 ----------------
def config_path() -> Path:
    return data_dir() / "config.json"


class Config:
    DEFAULTS = {"x": None, "y": None, "size": DEFAULT_SIZE, "topmost": True, "mute": False, "grok_link": True,
                "peek": True, "edge": None, "edge_along": None, "edge_screen": None, "fx": True,
                "sfx": True, "walk": True, "butterfly": True, "water_min": 60, "sit_min": 90, "chime": False}

    def __init__(self, path: Path = None):
        self.path = path or config_path()
        self.data = dict(self.DEFAULTS)
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update({k: v for k, v in loaded.items() if k in self.DEFAULTS})
        except Exception:
            pass
        if self.data["size"] not in SIZES:
            self.data["size"] = DEFAULT_SIZE
        if self.data["edge"] not in PEEK_EDGES:
            self.data["edge"] = None
        if not isinstance(self.data["edge_along"], (int, float)) or isinstance(self.data["edge_along"], bool):
            self.data["edge_along"] = None
        for k in ("water_min", "sit_min"):
            if not isinstance(self.data[k], int) or isinstance(self.data[k], bool):
                self.data[k] = self.DEFAULTS[k]

    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception as e:
            print("save config failed:", e, file=sys.stderr)


# ---------------- 素材 ----------------
def _load_optional(name, ref_size):
    """可选素材: 不存在返回 None; 画布尺寸与基准不同则记日志并忽略(保证同一裁剪框不跳)"""
    p = ASSET_DIR / f"{name}.png"
    if not p.exists():
        return None
    img = QImage(str(p))
    if img.isNull():
        return None
    if img.size() != ref_size:
        log_error(f"asset {name}.png size {img.width()}x{img.height()} != {ref_size.width()}x{ref_size.height()}, ignored")
        return None
    return img.convertToFormat(QImage.Format_ARGB32)


def _resolve_fallbacks(frames, table):
    for _ in range(4):
        for s, fb in table.items():
            if s not in frames and fb in frames:
                frames[s] = frames[fb]


def load_frames():
    """返回 (frames, real): real = 真正有图(非回退)的状态集合"""
    imgs = {}
    for s in CORE_STATES:
        img = QImage(str(ASSET_DIR / f"{s}.png"))
        if img.isNull():
            raise FileNotFoundError(f"缺少素材: {ASSET_DIR / (s + '.png')}")
        imgs[s] = img.convertToFormat(QImage.Format_ARGB32)
    for s in tuple(EXTRA_STATES) + tuple(FACES):
        try:
            img = _load_optional(s, imgs["idle"].size())
            if img is not None:
                imgs[s] = img
        except Exception as e:
            log_error(f"load optional {s}", e)
    box = None
    for img in imgs.values():
        r = alpha_bbox(img)
        box = r if box is None else box.united(r)
    frames = {s: QPixmap.fromImage(img.copy(box)) for s, img in imgs.items()}
    real = set(frames)
    _resolve_fallbacks(frames, {**EXTRA_STATES, **FACES})
    return frames, real


def load_peek_frames():
    try:
        imgs = {}
        for k in ("peek_awake", "peek_sleep"):
            p = ASSET_DIR / f"{k}.png"
            if not p.exists():
                return None
            img = QImage(str(p))
            if img.isNull():
                return None
            imgs[k] = img.convertToFormat(QImage.Format_ARGB32)
        for k in PEEK_EXTRA:
            img = _load_optional(k, imgs["peek_awake"].size())
            if img is not None:
                imgs[k] = img
        box = None
        for img in imgs.values():
            r = alpha_bbox(img)
            box = r if box is None else box.united(r)
        frames = {k: QPixmap.fromImage(v.copy(box)) for k, v in imgs.items()}
        frames["_real"] = set(frames)
        _resolve_fallbacks(frames, PEEK_EXTRA)
        return frames
    except Exception as e:
        log_error("load_peek_frames", e)
        return None


def alpha_bbox(img: QImage, thr=8) -> QRect:
    img = img.convertToFormat(QImage.Format_ARGB32)
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    data = bytes(img.constBits())
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        row = data[y * bpl + 3: y * bpl + 4 * w: 4]
        if max(row) <= thr:
            continue
        xs = [i for i, a in enumerate(row) if a > thr]
        x0, x1 = min(x0, xs[0]), max(x1, xs[-1])
        y0 = min(y0, y); y1 = y
    if x1 < 0:
        return QRect(0, 0, w, h)
    return QRect(x0, y0, x1 - x0 + 1, y1 - y0 + 1)


def style_menu(m: QMenu):
    m.setWindowFlags(m.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
    m.setAttribute(Qt.WA_TranslucentBackground, True)
    m.setStyleSheet(TRAY_QSS)
    m.setFont(font(13))


# ---------------- 气泡 ----------------
class Bubble(QWidget):
    """弹出(回弹) + 打字机 + 自动换行 + 柔和阴影 + 淡出; 左上角一颗头冠同款小宝石。
    tone: normal / happy / alert / info / cool"""
    TONES = {"normal": ("#9FB0D8", "#4FC7B5", "#FFFFFF"), "happy": ("#FF9DBB", "#FF8FB1", "#FFF6F9"),
             "alert": ("#F5A660", "#F0883E", "#FFF8F0"), "info": ("#7DD6C8", "#4FC7B5", "#F4FCFA"),
             "cool": ("#7A8FA8", "#5B7C99", "#EEF3F8")}
    MAXW, M = 236, 12

    def __init__(self):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput
        super().__init__(None, flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.text, self.side, self.tone = "", "top", "normal"
        self.anchor = QPoint()
        self.tail = 11
        self.t0, self.dur = 0.0, BUBBLE_DURATION
        self._font = font(13, QFont.DemiBold)
        self._single = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)

    def _place(self, anchor: QPoint, side: str):
        w, h, m = self.width(), self.height(), self.M
        if side == "top":
            x, y = anchor.x() - w // 2, anchor.y() - h + m
        elif side == "bottom":
            x, y = anchor.x() - w // 2, anchor.y() - m
        elif side == "right":
            x, y = anchor.x() - m, anchor.y() - h // 2
        else:
            x, y = anchor.x() - w + m, anchor.y() - h // 2
        scr = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        x = max(g.left() - m + 2, min(x, g.left() + g.width() - w + m - 2))
        y = max(g.top() - m + 2, min(y, g.top() + g.height() - h + m - 2))
        self.move(x, y)

    def popup(self, text, anchor: QPoint, duration=BUBBLE_DURATION, topmost=True, side="top", tone="normal"):
        self.text, self.side, self.anchor = text, side, QPoint(anchor)
        self.tone = tone if tone in self.TONES else "normal"
        fm = QFontMetrics(self._font)
        self._single = fm.horizontalAdvance(text) <= self.MAXW
        r = fm.boundingRect(QRect(0, 0, self.MAXW, 2000), Qt.TextWordWrap, text)
        w = max(r.width() + 34, 74) + 2 * self.M
        h = r.height() + 20 + 2 * self.M
        if side in ("top", "bottom"):
            h += self.tail
        else:
            w += self.tail
        self.setWindowFlag(Qt.WindowStaysOnTopHint, topmost)
        self.resize(w, h)
        self._place(anchor, side)
        self.t0 = time.monotonic()
        self.dur = max(1.0, float(duration))
        self.show()
        self.raise_()
        self._timer.start(16)
        self.update()

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def _step(self):
        if time.monotonic() - self.t0 >= self.dur:
            self.hide()
        else:
            self.update()

    def follow(self, anchor: QPoint, side: str = None):
        if self.isVisible():
            self.anchor = QPoint(anchor)
            if side and side != self.side:
                self.side = side
            self._place(anchor, self.side)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        el = time.monotonic() - self.t0
        border, gem, fill = (QColor(c) for c in self.TONES[self.tone])
        t, m = self.tail, self.M
        l, tp, r, bt = float(m), float(m), float(self.width() - m), float(self.height() - m)
        if self.side == "top":
            bt -= t
        elif self.side == "bottom":
            tp += t
        elif self.side == "right":
            l += t
        else:
            r -= t
        body = QRectF(l, tp, r - l, bt - tp)
        cx, cy = body.center().x(), body.center().y()
        tail = QPainterPath()
        if self.side == "top":
            tail.moveTo(cx - 9, bt - 2); tail.quadTo(cx - 1, bt + 2, cx + 1, bt + t); tail.quadTo(cx + 3, bt + 2, cx + 9, bt - 2)
            tip = QPointF(cx, bt + t)
        elif self.side == "bottom":
            tail.moveTo(cx - 9, tp + 2); tail.quadTo(cx - 1, tp - 2, cx + 1, tp - t); tail.quadTo(cx + 3, tp - 2, cx + 9, tp + 2)
            tip = QPointF(cx, tp - t)
        elif self.side == "right":
            tail.moveTo(l + 2, cy - 9); tail.quadTo(l - 2, cy - 1, l - t, cy + 1); tail.quadTo(l - 2, cy + 3, l + 2, cy + 9)
            tip = QPointF(l - t, cy)
        else:
            tail.moveTo(r - 2, cy - 9); tail.quadTo(r + 2, cy - 1, r + t, cy + 1); tail.quadTo(r + 2, cy + 3, r - 2, cy + 9)
            tip = QPointF(r + t, cy)
        tail.closeSubpath()
        path = QPainterPath()
        path.addRoundedRect(body, 16, 16)
        path = path.united(tail)
        s = 0.55 + 0.45 * ease_out_back(min(1.0, el / 0.22))
        p.setOpacity(max(0.0, min(1.0, (self.dur - el) / 0.25, el / 0.08)))
        p.translate(tip); p.scale(s, s); p.translate(-tip)
        sh = shadow_image(int(body.width()), int(body.height()), 16, 10, QColor(30, 45, 90, 55))
        p.drawImage(QPointF(body.x() - 10, body.y() - 10 + 3), sh)
        g = QLinearGradient(body.topLeft(), body.bottomLeft())
        g.setColorAt(0, QColor("#FFFFFF"))
        g.setColorAt(1, fill)
        p.setPen(QPen(border, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(g)
        p.drawPath(path)
        draw_gem(p, QPointF(body.left() + 15, body.top() + 1), 5.5, gem)
        p.setPen(INK)
        p.setFont(self._font)
        n = min(len(self.text), int(el * 40) + 1)
        flags = (Qt.AlignCenter if self._single else (Qt.AlignLeft | Qt.AlignVCenter)) | Qt.TextWordWrap
        p.drawText(body.adjusted(15, 7, -15, -7), flags, self.text[:n])
        p.end()


# ---------------- Grok 联动增强 ----------------
class VesnaGrokLink(GrokLink):
    """在原联动逻辑之上, 为每类事件追加动画/粒子/气泡色调; 原模块不改动, 隐私保证不变"""
    TONE = {"perm": "alert", "err": "alert", "done": "happy", "start": "happy"}

    def _react(self, cat, state, texts, cooldown, dur=None, priority=0, bubble_dur=None):
        w = self.window
        w._next_tone = self.TONE.get(cat)
        try:
            ok = super()._react(cat, state, texts, cooldown, dur=dur, priority=priority, bubble_dur=bubble_dur)
        finally:
            w._next_tone = None
        if ok:
            try:
                w.on_link_event(cat)
            except Exception as e:
                log_error("on_link_event", e)
        return ok

    def poll(self):
        super().poll()
        try:
            busy = self.enabled and bool(self.running) and (self.active or self.inflight > 0)
            self.window.fx_badge = (self.last_cat or "other") if busy else None
        except Exception as e:
            log_error("VesnaGrokLink.poll", e)

    def stop(self):
        super().stop()
        self.window.fx_badge = None


# ---------------- 桌宠窗口 ----------------
class PetWindow(QWidget):
    quit_requested = Signal()
    AVATAR = dict(center=(0.44, 0.43), zoom=0.31)       # 圆形头像在立绘上的取景

    def __init__(self, config: Config, link_kwargs: dict = None, stats: Stats = None):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        super().__init__(None, flags)
        food_packs.install(log_error)           # 可选食物包 dlc/foods/*.json; 没有目录就什么都不做
        self.cfg = config
        self.stats = stats or Stats()
        self.sfx = Sfx(bool(self.cfg["sfx"]))
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowTitle("薇斯纳桌宠")
        self.setMouseTracking(True)
        self.setCursor(Qt.OpenHandCursor)

        self.frames, self.real_frames = load_frames()
        self.peek_frames = load_peek_frames() if self.cfg["peek"] else None
        self._codex_peek = None
        self._peek_meta = self._compute_peek_meta()
        self.edge = None
        self._edge_screen = None
        self._edge_along = None
        self._hover = False
        self.pop = 0.0
        self._reveal_until = 0.0
        self._duck_until = 0.0
        self._duck_cool = 0.0
        self._ducking = False
        self._cache = {}
        self.state = "idle"
        self._expr = self._expr_state = None      # set_state(expr=) 指定的脸, 只在那个状态里有效
        self.state_since = time.monotonic()
        self.last_interaction = time.monotonic()
        self.clicks = deque(maxlen=8)
        self._press = None
        self._dragging = False
        self.bubble = Bubble()
        self.fx = FxLayer()
        self.fx.set_topmost(self.cfg["topmost"])
        self.fx_badge = None
        self._next_tone = None
        self.link_busy = False
        self.link = None
        self.tray = None
        # 动作引擎
        self.sq = 0.0; self.sq_v = 0.0          # 果冻挤压(+拉长 / -压扁)
        self.tilt = 0.0
        self.hover_k = 0.0
        self.spin_angle = 0.0; self.spin_rem = 0.0
        self.jump_start = -1.0; self.jump_dur = 0.6; self.jump_h = 0.0; self._landed = True
        self.fling = None
        self._drag_vx = 0.0
        self._drag_samples = deque(maxlen=8)
        self._pet_hist = deque(maxlen=12); self._pet_dir = 0; self._pet_x = None; self._pet_cool = 0.0
        self._wheel_hist = deque(maxlen=30)
        self._yawned = False
        self._next_z = 0.0
        self._cursor_prev = None
        self._last_tick = time.monotonic()
        self._geo_tick = 0
        self._late_last = time.monotonic()
        # 散步 / 朝向 / 视线
        self.walk = None
        self._wpos = None
        self._walk_phase = 0.0
        self.face = 1.0; self.face_target = 1.0
        self.gaze = 0; self._gaze_want = 0; self._gaze_since = 0.0
        self._cur_last = QCursor.pos(); self._cur_moved = 0.0
        self._hover_still = 0.0; self._stare_cool = 0.0
        # 专注
        self.focus_end = None; self.focus_total = 0; self._focus_half = False
        self.focus_paused = False; self._focus_rem_paused = 0.0
        # 提醒 / 节律
        now = time.monotonic()
        self._water_last = now; self._sit_last = now
        self._chime_hour = datetime.now().hour
        self._hungry_last = now
        self._sys_idle = None             # 整台电脑多少秒没碰键盘鼠标; None = 读不到(非 Windows)
        self._away_since = None           # 你离开电脑的时刻; None = 在
        self._dodge_say = 0.0
        self._mumble_next = 0.0          # 梦话冷却
        self._wake_drag = False          # 这次拖拽是把她从睡梦里拎起来的
        self._wake_rude_last = -1e9      # 上次因粗暴叫醒扣好感
        self._spin_wake_grace = 0.0      # 转醒后的滚轮宽限期
        self._drag_hold_t0 = 0.0         # 开始拖住的时间(挣扎计时; drag_hold_rate 会让它走慢 / 走快)
        self._drag_since = 0.0           # 真正开始拖住的时间
        self._drag_rate, self._drag_rate_at = 1.0, 0.0
        self._drag_hold_stage = 0        # 0未喊 / 1轻 / 2重 / 3激烈 / 4风元素
        self._drag_hold_peak = 0         # 这次拖拽达到过的最高阶段(松手后还要用)
        self._drag_hold_fx = 0.0         # 激烈/风元素阶段特效节流
        self._sneak_until = 0.0          # 偷吃进行中(截止时刻)
        self._sneak_caught = False
        self._bchase = None              # 追蝴蝶状态
        self._bchase_land_until = 0.0    # 追到后一段时间内的落头算「追到」
        self._seen_keys = set()
        # 被丢 / 闹别扭 / 转圈
        self._throws = deque(maxlen=12)
        self._feeds = deque(maxlen=16); self._dislikes = deque(maxlen=8); self._extra_stomach_until = 0.0
        self._throw = None              # 正在飞的这一丢: dict(speed, hard, level, bonks, t_bonk)
        self._sulk_until = 0.0; self._sulk_calm = 0; self._sulk_click_t = 0.0; self._sulk_fx = 0.0; self._sulk_poke_say = 0.0
        self._spin_meter = 0.0; self._spin_stage = 0; self._spin_t = now
        self._dizzy_until = 0.0; self._dizzy_extra = 0; self._dizzy_fx = 0.0; self._stagger_t = 0.0
        self._spin_refuse_until = 0.0; self._spin_recover_at = 0.0; self._spin_recover_sure = False
        self._spin_overspin = False; self._spin_angry_done = False; self._spin_posting = False
        self._quip_until = 0.0; self._last_lines = {}
        # DLC 事件推送: LiveHub 由 PetApp 接上; 没接就是 None, emit_event 直接返回
        self._live = None; self._wake_why = None; self._spin_live = False
        self.food_fx = None; self._prank_last = {}     # 食物包: 正在进行的吃后效果 / 整蛊食物上次吃的时间
        self.mood = Mood(self.stats, emit=lambda ev, **d: self.emit_event(ev, **d),
                         away_sec=self.stats.away_hours * 3600.0)
        self._ix = interaction_hooks.load(self, log_error)   # 可选互动扩展 dlc/interactions/*.py; 没有就是空操作

        self.size_key = self.cfg["size"]
        self._apply_size(first=True)

        self.revert_timer = QTimer(self); self.revert_timer.setSingleShot(True); self.revert_timer.timeout.connect(self._revert_to_idle)
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self._tick); self.anim_timer.start(16)
        self.happy_timer = QTimer(self); self.happy_timer.setSingleShot(True); self.happy_timer.timeout.connect(self._idle_action)
        self.bubble_timer = QTimer(self); self.bubble_timer.setSingleShot(True); self.bubble_timer.timeout.connect(self._random_bubble)
        self.sleep_timer = QTimer(self); self.sleep_timer.timeout.connect(self._check_sleep); self.sleep_timer.start(1000)
        self.bfly_timer = QTimer(self); self.bfly_timer.setSingleShot(True); self.bfly_timer.timeout.connect(self._auto_butterfly)
        self._schedule_happy(); self._schedule_bubble(); self._schedule_butterfly(first=True)

        self.butterfly = Butterfly(self, log_fn=log_error)
        self.butterfly.gone.connect(self._on_bfly_gone)
        self.butterfly.caught.connect(self._on_bfly_caught)
        self.butterfly.landed.connect(self._on_bfly_landed)
        self.butterfly.dodged.connect(self._on_bfly_dodged)
        self.danika = DanikaVisit(self, bubble_cls=Bubble, asset_dir=ASSET_DIR, log_fn=log_error)
        self.danika.finished.connect(self._on_danika_finished)
        self.danika.skipped.connect(self._on_danika_skipped)
        self._danika_next = 0.0
        self._danika_test = False
        self._panels = {}
        self._build_tray_menu()
        self._restore_position()
        QTimer.singleShot(1800, self._greet)
        try:
            self.link = VesnaGrokLink(self, enabled=bool(self.cfg["grok_link"]), **(link_kwargs or {}))
        except Exception as e:
            log_error("GrokLink init", e)
            self.link = None

    # ----- 尺寸 / 缓存 -----
    def _compute_peek_meta(self):
        pf = self.peek_frames
        if not pf:
            return None
        awake = pf["peek_awake"]
        return dict(w=awake.width(), h=awake.height(), bb=alpha_bbox(awake.toImage()))

    def peek_ok(self):
        return bool(self.cfg["peek"]) and self.peek_frames is not None and self._peek_meta is not None

    def pad_top(self):
        return PAD + self.hop_room

    def _apply_size(self, first=False):
        w = SIZES[self.size_key]
        pm0 = self.frames["idle"]
        self.char_w = w
        self.char_h = round(pm0.height() * w / pm0.width())
        self.hop_room = int(self.char_h * 0.30) + 12          # 跳跃/拉长留空
        self.pad_x = PAD + int(self.char_h * 0.22)              # 倾斜不被裁切
        self.k_peek = (w / pm0.width()) * PEEK_SCALE
        if self.edge and self.peek_ok():
            pw, ph = self._peek_wh()
            if self.edge in ("left", "right"):
                self.setFixedSize(pw, ph + 2 * PEEK_TPAD)
            else:
                self.setFixedSize(pw + 2 * PEEK_TPAD, ph)
        else:
            self.setFixedSize(w + 2 * self.pad_x, self.char_h + 2 * PAD + self.hop_room)
        self._cache.clear()
        if not first:
            self._reposition_bubble()

    def _peek_wh(self):
        mt, k = self._peek_meta, self.k_peek
        if self.edge == "top":
            return round(mt["h"] * k), round(mt["w"] * k)
        return round(mt["w"] * k), round(mt["h"] * k)

    def _scaled(self, state):
        dpr = self.devicePixelRatioF() or 1.0
        key = (state, self.size_key, dpr)
        pm = self._cache.get(key)
        if pm is None:
            pm = self.frames[state].scaled(round(self.char_w * dpr), round(self.char_h * dpr), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            self._cache[key] = pm
        return pm

    def _peek_pixmap(self, key):
        dpr = self.devicePixelRatioF() or 1.0
        ck = ("peek", key, self.edge, self.size_key, dpr)
        pm = self._cache.get(ck)
        if pm is None:
            base = self.peek_frames.get(key) or self.peek_frames["peek_awake"]
            if self.edge == "right":
                base = base.transformed(QTransform().scale(-1, 1), Qt.SmoothTransformation)
            elif self.edge == "top":
                base = base.transformed(QTransform().rotate(90), Qt.SmoothTransformation)
            pw, ph = self._peek_wh()
            pm = base.scaled(round(pw * dpr), round(ph * dpr), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            self._cache[ck] = pm
        return pm

    def frame_for_codex(self, key):
        if key.startswith("peek"):
            pf = self.peek_frames or self._codex_peek
            if pf is None:
                self._codex_peek = pf = load_peek_frames()
            return pf.get(key) if pf else None
        return self.frames.get(key)

    def codex(self):
        """图鉴里列哪几格: 原来的都列; 只换脸的表情(FACES)要 assets 里真有图才列"""
        return [e for e in C.CODEX if e[0] not in FACES or e[0] in self.real_frames]

    # ----- 菜单 / 面板 -----
    def _build_tray_menu(self):
        m = QMenu()
        style_menu(m)
        self.tray_menu = m
        self.act_status = QAction("薇斯纳", m); self.act_status.setEnabled(False)
        m.addAction(self.act_status)
        m.addSeparator()
        m.addAction("🏠  打开小屋", lambda: self.open_home(0))
        play = m.addMenu("💗  互动"); style_menu(play)
        play.addAction("🤚  摸摸头", self.pet)
        self.feed_menu = play.addMenu("🍰  投喂"); style_menu(self.feed_menu)
        self.feed_menu.aboutToShow.connect(self._fill_feed_menu)
        self._fill_feed_menu()
        play.addAction("🔮  今日运势", self.open_fortune)
        play.addAction("✊  猜拳", self.open_rps)
        play.addAction("🦋  召唤蝴蝶", self.summon_butterfly)
        play.addAction("🧊  达妮卡来访", lambda: self.summon_danika(False))
        play.addAction("👣  过来~", self.come_here)
        play.addAction("🎉  放彩带", lambda: (self.note_interaction(), self.celebrate()))
        for emoji, label, fn in self._ix.menu_items():          # 互动扩展注册的菜单项; 没装就没有
            play.addAction(f"{emoji}  {label}", fn)
        focus = m.addMenu("🍅  专注"); style_menu(focus)
        for mins in (15, 25, 45, 60):
            focus.addAction(f"{mins} 分钟", lambda mins=mins: self.start_focus(mins))
        self.act_focus_pause = focus.addAction("暂停 / 继续", self.toggle_pause_focus)
        self.act_focus_stop = focus.addAction("结束计时", self.stop_focus)
        m.addAction("⚙️  设置", lambda: self.open_home(3))
        m.addSeparator()
        self.act_unpeek = m.addAction("↩️  离开边缘", lambda: self.leave_peek())
        m.addAction("👁️  显示 / 隐藏", self.toggle_visible)
        m.addAction("👋  退出", self.quit_requested.emit)
        m.aboutToShow.connect(self._on_tray_menu_show)

    def _fill_feed_menu(self):
        """托盘 → 互动 → 投喂: 按地区分组; 尝过的会标出她喜不喜欢"""
        fm = self.feed_menu
        fm.clear()
        known = sum(1 for f in C.FOODS if self.stats.food_known(f["key"]))
        hdr = fm.addAction(f"美食图鉴 {known}/{len(C.FOODS)}")
        hdr.setEnabled(False)
        fm.addSeparator()
        regions = []
        for f in C.FOODS:
            if f["region"] not in regions:
                regions.append(f["region"])
        for r in regions:
            sub = fm.addMenu(r); style_menu(sub)
            for f in C.FOODS:
                if f["region"] != r:
                    continue
                mark = ""
                if self.stats.food_known(f["key"]):
                    tname, badge, _ = C.TIER_INFO[f["tier"]]
                    mark = f"   {badge} {tname}"
                pm = food_pixmap(f["key"], 32)
                if pm is not None:
                    sub.addAction(QIcon(pm), f"{f['name']}{mark}", lambda k=f["key"]: self.feed(k))
                else:
                    sub.addAction(f"{f['emoji']}  {f['name']}{mark}", lambda k=f["key"]: self.feed(k))

    def _on_tray_menu_show(self):
        lv, name, _, _ = self.stats.level()
        txt = f"薇斯纳 · Lv.{lv} {name}"
        if self.focus_end is not None:
            rem = self.focus_remaining()
            txt += f" · 🍅 {rem // 60:02d}:{rem % 60:02d}"
        self.act_status.setText(txt)
        self.act_unpeek.setEnabled(self.edge is not None)
        run = self.focus_end is not None
        self.act_focus_pause.setEnabled(run)
        self.act_focus_stop.setEnabled(run)

    def _panel(self, name):
        p = self._panels.get(name)
        if p is None:
            import panels
            cls = {"menu": panels.ActionMenu, "home": panels.HomePanel, "fortune": panels.FortuneCard,
                   "rps": panels.RpsCard}[name]
            p = cls(self)
            self._panels[name] = p
        return p

    def contextMenuEvent(self, e):
        if self._ix.call("context_menu", e):     # 互动扩展拦下右键菜单
            e.accept()
            return
        self.note_interaction()
        self.stop_walk()
        try:
            self._panel("menu").open_at(e.globalPos())
        except Exception as ex:
            log_error("action menu", ex)
            self.tray_menu.exec(e.globalPos())

    def open_home(self, tab=0):
        self.note_interaction()
        try:
            self._panel("home").open(tab)
        except Exception as e:
            log_error("open_home", e)

    # ----- 配置项 -----
    def set_size(self, key):
        if key not in SIZES:
            return
        bottom_center = QPoint(self.x() + self.width() // 2, self.y() + self.height())
        self.size_key = key
        self.cfg["size"] = key
        self.stop_walk()
        self._apply_size()
        if self.edge:
            self._place_peek(self._edge_screen, self._edge_along)
            self._save_edge()
        else:
            self.move(bottom_center.x() - self.width() // 2, bottom_center.y() - self.height())
        self.cfg.save()
        self.kick(2.0)
        self.update()

    def set_topmost(self, on):
        self.cfg["topmost"] = bool(on)
        pos, vis = self.pos(), self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(on))
        if vis:
            self.show()
            self.move(pos)
        self.fx.set_topmost(on)
        for p in self._panels.values():
            try:
                p.set_topmost(on)
            except Exception:
                pass
        self.cfg.save()

    def set_mute(self, on):
        self.cfg["mute"] = bool(on)
        if on:
            self.bubble.hide()
        self.cfg.save()

    def set_fx(self, on):
        self.cfg["fx"] = bool(on)
        if not on:
            self.fx.clear()
        self.cfg.save()

    def set_sfx(self, on):
        self.cfg["sfx"] = bool(on)
        self.sfx.enabled = bool(on)
        if on:
            self.sfx.play("pop")
        self.cfg.save()

    def set_walk(self, on):
        self.cfg["walk"] = bool(on)
        if not on:
            self.stop_walk()
        self.cfg.save()

    def set_butterfly(self, on):
        self.cfg["butterfly"] = bool(on)
        if not on:
            self.butterfly.leave()
        else:
            self._schedule_butterfly(first=True)
        self.cfg.save()

    def set_water(self, mins):
        self.cfg["water_min"] = int(mins)
        self._water_last = time.monotonic()
        self.cfg.save()

    def set_sit(self, mins):
        self.cfg["sit_min"] = int(mins)
        self._sit_last = time.monotonic()
        self.cfg.save()

    def set_chime(self, on):
        self.cfg["chime"] = bool(on)
        self._chime_hour = datetime.now().hour
        self.cfg.save()

    def set_link(self, on):
        self.cfg["grok_link"] = bool(on)
        try:
            if self.link is not None:
                self.link.set_enabled(bool(on))
        except Exception as e:
            log_error("set_link", e)
        if not on:
            self.link_busy = False
            self.fx_badge = None
        self.cfg.save()

    def open_data_dir(self):
        try:
            d = data_dir()
            d.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))
        except Exception as e:
            log_error("open_data_dir", e)

    def reset_position(self):
        self.stop_walk()
        if self.edge:
            self.edge = None
            self._apply_size()
        self.move(*self._default_position())
        self._save_edge()
        self.cfg.save()
        self.reveal(greet=True)

    def toggle_visible(self):
        if self.isVisible():
            self.bubble.hide()
            self.fx.clear()
            self.butterfly.stop()
            self.hide()
        else:
            self.reveal(greet=False)

    def show_and_raise(self):
        self.reveal(greet=False)

    def reveal(self, greet=True):
        try:
            was_hidden = not self.isVisible()
            if self.windowState() & Qt.WindowMinimized:
                self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowNoState)
            self.setWindowOpacity(1.0)
            self._press = None
            self._dragging = False
            self.fling = None
            if was_hidden:
                self.show()
            c = QRect(self.pos(), self.size()).center()
            if not any(s.geometry().contains(c) for s in QGuiApplication.screens()) or not self._ensure_visible():
                if self.edge:
                    self.edge = None
                    self.cfg["edge"] = None
                    self._apply_size()
                self.move(*self._default_position())
                self._save_edge()
                self.cfg.save()
                self._ensure_visible()
            self.show()
            self.raise_()
            self.note_interaction()
            if greet or was_hidden:
                self._reveal_until = time.monotonic() + 4.0
                self.set_state("happy", 2.5)
                self.burst("sparkle", 10)
                self.say(random.choice(C.REVEAL_TEXTS), force=True, duration=3.5)
        except Exception as e:
            log_error("reveal", e)

    # ----- 好感 -----
    def gain(self, n, kind=None, quiet=False):
        got, up, name = self.stats.gain(n, kind)
        if got > 0 and not quiet:
            hp = self.head_point()
            self.burst("emoji", 1, at=QPointF(hp.x() + self.char_w * 0.28, hp.y() - 6), text="💗")
        if up:
            QTimer.singleShot(1500, lambda: self._level_up(name))
        return got

    def _level_up(self, name):
        self.note_interaction()
        self.emit_event("level_up", name=str(name))
        self.celebrate()
        self.burst("ring", 2)
        self.sfx.play("level")
        self.say(C.LEVEL_UP.format(name=name), force=True, duration=5.0, tone="happy")

    def mood_text(self):
        """小屋头部那句话: 正在发生什么就说什么(插件管的状态最先), 没事时和原来一样按好感说(插件可用 status_line 换)"""
        st = self.stats
        for text in self._ix.state_texts():             # 插件管的状态(超级生气、转吐……)
            return text
        acts = self.activities()
        for act, text in C.STATUS_BUSY_TEXTS:
            if act in acts:
                if act == "food_fx" and self.food_fx is not None:
                    food = self.food_fx.food                  # 用卡片上的短名, 长名放不下
                    return text.format(name=food.get("short") or food.get("name") or "奇怪的东西")
                return text
        if self.focus_end is not None:
            return "正在安静地陪你专注……"
        if self.state == "sleep":
            return "睡得正香,呼……"
        if self.state in C.STATUS_STATE_TEXTS:
            return C.STATUS_STATE_TEXTS[self.state]
        if "walk" in acts:
            return C.STATUS_WALK_TEXT
        lv = st.level()[0]
        if st.hunger < 25:
            kind, text = "hungry", "肚子咕咕叫,想吃东西~"
        elif self.butterfly.active():
            kind, text = "butterfly", "在看小蝴蝶飞来飞去~"
        else:
            kind, text = "level", ["有点害羞,还在熟悉你~", "觉得和你待着很舒服", "把你当成好朋友啦",
                                   "每天都想见到你~", "你是她最重要的人之一", "和你缔结了心之契约 ✦"][min(lv, 6) - 1]
        return self._tune("status_line", text, kind=kind, level=lv)     # 插件可以换(比如心情跌到谷底时)

    # ----- 专注计时 -----
    def start_focus(self, mins):
        self.focus_total = int(mins) * 60
        self.focus_end = time.monotonic() + self.focus_total
        self.focus_paused = False
        self._focus_half = False
        self.note_interaction()
        self.stop_walk()
        if self.state == "sleep":
            self.wake_up()
        self.set_state("wave", 1.8)
        self.sfx.play("chime")
        self.emit_event("focus_start", minutes=int(mins))
        self.say(C.FOCUS_START.format(m=mins), force=True)

    def focus_remaining(self):
        if self.focus_end is None:
            return 0
        if self.focus_paused:
            return max(0, int(math.ceil(self._focus_rem_paused)))
        return max(0, int(math.ceil(self.focus_end - time.monotonic())))

    def toggle_pause_focus(self):
        if self.focus_end is None:
            return
        if self.focus_paused:
            self.focus_end = time.monotonic() + self._focus_rem_paused
            self.focus_paused = False
            self.say("继续加油~", force=True)
        else:
            self._focus_rem_paused = max(0.0, self.focus_end - time.monotonic())
            self.focus_paused = True
            self.say(random.choice(C.FOCUS_PAUSE), force=True)
        self.sfx.play("tick")

    def stop_focus(self):
        if self.focus_end is not None:
            self.focus_end = None
            self.focus_paused = False
            self.emit_event("focus_end", minutes=self.focus_total // 60, done=False)
            self.say("计时结束啦~ 下次继续!", force=True)

    def focusing(self):
        return self.focus_end is not None and not self.focus_paused

    def _check_focus(self):
        if self.focus_end is None or self.focus_paused:
            return
        rem = self.focus_end - time.monotonic()
        if not self._focus_half and rem <= self.focus_total / 2:
            self._focus_half = True
            self.kick(2.0)
            self.say(random.choice(C.FOCUS_HALF))
        if rem <= 0:
            mins = self.focus_total // 60
            self.focus_end = None
            self.note_interaction()
            self.stats.add_focus(mins)
            self.emit_event("focus_end", minutes=mins, done=True)
            self.celebrate()
            self.sfx.play("level")
            self.say(random.choice(C.FOCUS_DONE), force=True, duration=6.0, tone="happy")
            QTimer.singleShot(2500, lambda: self.gain(max(4, round(10 * mins / 25))))

    def _update_tooltip(self):
        if not self.tray:
            return
        try:
            lv, name, _, _ = self.stats.level()
            parts = [f"薇斯纳桌宠 · Lv.{lv} {name}"]
            if self.link is not None:
                parts.append(self.link.status_text())
            if self.focus_end is not None:
                rem = self.focus_remaining()
                parts.append(f"专注:{'暂停 ' if self.focus_paused else ''}{rem // 60:02d}:{rem % 60:02d}")
            parts += self.plugin_status()              # 插件的状态行(如: 小心愿)
            self.tray.setToolTip("\n".join(parts))
        except Exception as e:
            log_error("tooltip", e)

    # ----- 今日运势 / 猜拳 -----
    def today_fortune(self):
        if self.stats.d.get("fortune_day") != date.today().isoformat():
            return None
        return C.fortune_for(date.today(), os.environ.get("USERNAME", ""))

    def open_fortune(self):
        self.note_interaction()
        today = date.today().isoformat()
        fresh = self.stats.d.get("fortune_day") != today
        data = C.fortune_for(date.today(), os.environ.get("USERNAME", ""))
        self.emit_event("fortune", tier=data["tier"], fresh=bool(fresh))
        if fresh:
            self.stats.d["fortune_day"] = today
            self.stats.touch()
            if self.state == "sleep":
                self.wake_up()
            self.set_state("wave", 1.6)
            self.burst("ring", 2)
            self.burst("sparkle", 10)
            self.sfx.play("chime")
            QTimer.singleShot(1200, lambda: self.gain(2))
            tier = data["tier"]
            good = tier in ("大吉", "中吉")
            QTimer.singleShot(1300, lambda: (self.set_state("cheer" if good else "happy", 2.2),
                                             self.say(f"是「{tier}」!" + ("太棒啦!" if good else "~"),
                                                      force=True, tone="happy")))
        try:
            self._panel("fortune").open(data, fresh)
        except Exception as e:
            log_error("fortune", e)

    def open_rps(self):
        self.note_interaction()
        if self.state == "sleep":
            self.wake_up()
        try:
            self._panel("rps").open()
        except Exception as e:
            log_error("rps", e)

    def on_rps(self, res):
        """res: 从玩家角度 win / lose / draw"""
        self.note_interaction()
        self.emit_event("rps", result=res)
        if res == "win":
            self.stats.inc("rps_win")
            self.set_state("angry", 1.6, expr="pout")
            self.sfx.play("hmph")
            self.say(random.choice(["呜……再来!", "哼,这次是我让着你~"]), force=True)
        elif res == "lose":
            self.stats.inc("rps_lose")
            self.set_state("cheer", 2.0)
            self.burst("star", 6)
            self.sfx.play("boing")
            self.say(random.choice(["耶!我赢啦~", "嘿嘿,薇斯纳最强!"]), force=True, tone="happy")
        else:
            self.stats.inc("rps_draw")
            self.set_state("surprised", 1.0)
            self.sfx.play("huh")
        self.gain(1, "rps", quiet=True)

    # ----- 投喂 -----
    def mouth_point(self) -> QPointF:
        if self.edge:
            return self.head_point()
        return QPointF(self.x() + self.width() / 2, self.y() + self.pad_top() + self.char_h * 0.6)

    def feed(self, key):
        f = C.food_by_key(key)
        if f is None:
            return
        self.note_interaction()
        self.stop_walk()
        if self.state == "sleep":
            self.wake_up("feed")
        now = time.monotonic()
        while self._feeds and now - self._feeds[0] > FEED_WINDOW:
            self._feeds.popleft()
        tier = f["tier"]
        bad = tier in ("dislike", "weird")
        # 闹别扭时: 好吃的能哄好, 讨厌的只会更生气
        if self.sulking():
            if bad:
                self._sulk_until = min(now + SULK_SEC, self._sulk_until + SULK_POKE_ADD)
                self.set_state("angry")
                self.kick(-1.4)
                self.burst("anger", 1, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
                self.sfx.play("hmph")
                self.quip(C.FOOD_SULK_WORSE_TEXTS, urgent=True, duration=3.0, tone="alert")
                self.emit_event("feed", key=key, name=f["name"], tier=tier, trait=f["trait"], reaction="sulk_worse")
                return
            self._end_sulk("food")
        # 吃太饱: 最爱的能用"另一个胃"再吃一份
        extra = False
        if self.stats.hunger >= FULL_HUNGER or len(self._feeds) >= FEED_MAX:
            if tier == "fav" and now >= self._extra_stomach_until and self.stats.hunger < 100:
                extra = True
                self._extra_stomach_until = now + FEED_WINDOW
            else:
                self.set_state("content", 2.2)
                self.kick(-1.0)
                self.burst("emoji", 1, at=self.mouth_point(), bias=(0, 0), text="🙅")
                self.say(self.pick_line(C.FULL_TEXTS), force=True, duration=3.2)
                self.emit_event("feed", key=key, name=f["name"], tier=tier, trait=f["trait"], reaction="full")
                return
        if f.get("effect"):                     # 食物包的整蛊食物: 第一次不设防, 吃过一阵内再喂就拒绝
            refuse = now - self._prank_last.get(key, -1e9) < f.get("refuse_again_sec", 300)
        else:
            refuse = bad and random.random() < self._tune("food_refuse_p",
                                                          FOOD_REFUSE_WEIRD if tier == "weird" else FOOD_REFUSE_P,
                                                          key=key, tier=tier, trait=f["trait"])
        if f.get("curious") and not self.stats.food_known(key) and not refuse:
            self.set_state("surprised", 1.8)    # 食物包的外界食物: 第一次见先好奇
            self.burst("quest", 1, at=self.head_point() + QPointF(self.char_w * 0.25, -8))
            self.say(self.pick_line(f["curious"]), force=True, duration=2.6, tone="info")
            QTimer.singleShot(1700, lambda: self._serve(f, refuse, extra))
            return
        self._serve(f, refuse, extra)

    def _serve(self, f, refuse, extra):
        if self.cfg["fx"] and self.isVisible():
            m = self.mouth_point()
            self.fx.emit("food", m.x(), m.y(), 1, text=f["emoji"], pm=food_pixmap(f["key"], 40))
            self.set_state("surprised", 0.7)
            QTimer.singleShot(720, lambda: self._eat(f, refuse, extra))
        else:
            self._eat(f, refuse, extra)

    def _eat(self, f, refuse=False, extra=False):
        key, tier, trait = f["key"], f["tier"], f["trait"]
        now = time.monotonic()
        m = self.mouth_point()
        hp = self.head_point()
        first = self.stats.taste(key, eaten=not refuse)
        self.emit_event("feed", key=key, name=f["name"], tier=tier, trait=trait,
                        reaction="refuse" if refuse else tier, first=bool(first))
        if refuse:                                          # 推开不吃
            if tier == "dislike":
                self.set_state("angry", 2.0, expr="yuck")
            else:
                self.set_state("surprised", 2.0)
            self.kick(-1.4)
            side = 1 if (QCursor.pos().x() < self.x() + self.width() / 2) else -1
            self.burst("emoji", 1, at=m, bias=(side * -520, -60), text=f["emoji"], pm=food_pixmap(key, 40))
            self.burst("puff", 5, at=m, bias=(0, 0))
            if tier == "weird":
                self.burst("quest", 1, at=hp + QPointF(self.char_w * 0.25, -8))
            self.sfx.play("hmph")
            self.say(self.pick_line(f["refuse"] or C.FOOD_REFUSE_TEXTS), force=True, duration=3.2, tone="alert")
            self._note_dislike(now)
            return
        self.stats.feed(f["fill"])
        self._feeds.append(now)
        self.sfx.play("munch")
        self.burst("crumb", 7, at=m, bias=(0, 0))
        self.kick(-1.6)
        if f.get("effect"):                                 # 食物包: 吃后效果(白名单)
            self._prank_last[key] = now
            if f.get("affection"):
                self.gain(int(f["affection"]), quiet=True)
            self.set_state("surprised", 1.2)
            self.say(self.pick_line(f["lines"]), force=True, duration=2.0, tone="alert")
            QTimer.singleShot(900, lambda: self._start_food_fx(f))
            return
        if tier == "fav":
            first_fav = not self.stats.d.get("fav_found") or first
            self.stats.d["fav_found"] = True
            self.stats.touch()
            self.set_state("love", 3.4)
            self.burst("heart", 10)
            self.burst("sparkle", 6)
            if trait == "stew":
                self.burst("steam", 5, at=m + QPointF(0, -6), bias=(0, 0))
            line = self.pick_line(C.FULL_FAV_TEXTS) if extra else self.pick_line(f["lines"])
            self.say(line, force=True, duration=4.2, tone="happy")
            self.gain(8 if first else 6, "feed")
            QTimer.singleShot(1000, self._food_hop)
            QTimer.singleShot(1500, lambda: self.sfx.play("sparkle"))
            after = C.FOOD_FAV_FIRST_TEXTS if first_fav else C.FOOD_MORE_TEXTS
            QTimer.singleShot(3600, lambda: self._food_say(after, "happy", hearts=3))
        elif tier == "like":
            self.set_state("eat", 2.8)
            if trait == "cold":
                self.burst("emoji", 2, text="❄️")
            elif trait == "stew":
                self.burst("steam", 4, at=m + QPointF(0, -6), bias=(0, 0))
            else:
                self.burst("note", 2)
            self.burst("sparkle", 4)
            self.say(self.pick_line(f["lines"] if random.random() < 0.8 else C.FOOD_LIKE_TEXTS), force=True, tone="happy")
            self.gain(5 if first else 4, "feed")
            if random.random() < 0.6:
                QTimer.singleShot(900, self._food_hop)
        elif tier == "ok":
            self.set_state("content", 2.4)
            self.burst("note", 1)
            self.say(self.pick_line(f["lines"] if random.random() < 0.75 else C.FOOD_OK_TEXTS), force=True)
            self.gain(2, "feed", quiet=True)
        elif trait == "spicy":                              # 辣!
            self.set_state("angry", 2.8, expr="yuck")
            self.burst("steam", 9, at=hp + QPointF(0, -10), bias=(0, 0))
            self.burst("emoji", 3, at=m, text="🔥")
            self.burst("sweat", 4)
            self.sfx.play("huh")
            self.say(self.pick_line(f["lines"]), force=True, tone="alert")
            QTimer.singleShot(1900, lambda: (self.burst("drop", 3), self.burst("emoji", 1, text="💧"),
                                             self.say(self.pick_line(C.FOOD_SPICY_WATER_TEXTS), force=True,
                                                      tone="alert")))
            QTimer.singleShot(4400, lambda: self._food_say(C.FOOD_SPICY_AFTER_TEXTS))
            self._note_dislike(now, quiet_until=6.0)
        elif trait == "dark":                               # 黑暗料理: 吃完头晕
            self.set_state("dizzy", 2.6, expr="queasy")
            self.burst("emoji", 1, at=hp + QPointF(0, -14), text="💀")
            self.burst("puff", 6, at=m, bias=(0, 0))
            self.sfx.play("huh")
            self.say(self.pick_line(f["lines"]), force=True, tone="alert")
            QTimer.singleShot(3200, lambda: self._food_say(C.FOOD_DARK_AFTER_TEXTS))
            self._note_dislike(now, quiet_until=5.0)
        else:                                               # 蔬菜 / 苦: 皱着脸勉强吃
            self.set_state("shy" if trait == "veggie" else "angry", 2.4, expr="yuck")
            self.burst("sweat", 3)
            if trait == "bitter":
                self.burst("anger", 1, at=hp + QPointF(self.char_w * 0.25, -10))
            self.say(self.pick_line(f["lines"] if random.random() < 0.8 else C.FOOD_DISLIKE_TEXTS), force=True)
            self._note_dislike(now)

    def _start_food_fx(self, f):
        try:
            if self.food_fx is not None:
                self.food_fx.stop("replaced")
            fx = FoodEffect(self, f, log_fn=log_error)
            if fx.start():
                self.food_fx = fx
        except Exception as e:
            log_error("food effect start", e)
            self.food_fx = None

    def _food_hop(self):
        """吃到好吃的: 原地小跳一下"""
        if self._dragging or self.fling or self.edge or not self.isVisible() or self.state == "sleep":
            return
        self.do_jump(False)
        self.burst("star", 4, at=self.foot_point(), bias=(0, -40))

    def _food_say(self, pool, tone=None, hearts=0):
        if self.sulking() or self._dragging or self.fling or not self.isVisible():
            return
        if hearts:
            self.burst("heart", hearts)
        self.say(self.pick_line(pool), force=True, duration=3.4, tone=tone)

    def _note_dislike(self, now, quiet_until=3.0):
        """短时间内连喂讨厌的: 第 2 次扣一点好感并警告, 第 3 次闹别扭"""
        while self._dislikes and now - self._dislikes[0] > DISLIKE_WINDOW:
            self._dislikes.popleft()
        self._dislikes.append(now)
        n = len(self._dislikes)
        if n >= DISLIKE_SULK:
            self._dislikes.clear()
            self.gain(-2, quiet=True)
            self.stats.inc("food_sulks")
            QTimer.singleShot(int(quiet_until * 1000) - 600,
                              lambda: (not self.sulking()) and self._start_sulk(pool=C.FOOD_SULK_TEXTS, revenge=False))
        elif n == 2:
            self.gain(-1, quiet=True)
            QTimer.singleShot(int(quiet_until * 1000), lambda: self._food_say(C.FOOD_DISLIKE_WARN_TEXTS, "alert"))

    # ----- 蝴蝶 -----
    def _schedule_butterfly(self, first=False):
        lo, hi = BUTTERFLY_EVERY
        sec = random.uniform(60, 150) if first else random.uniform(lo, hi)
        self.bfly_timer.start(int(sec * 1000))

    def _auto_butterfly(self):
        try:
            if self.cfg["butterfly"] and self.can_auto("auto_butterfly"):
                self.summon_butterfly(auto=True)
        except Exception as e:
            log_error("auto butterfly", e)
        self._schedule_butterfly()

    def summon_butterfly(self, auto=False):
        if not self.isVisible():
            return
        if self.butterfly.active():
            if not auto:
                self.say("它已经在这儿啦~", force=True)
            return
        if not auto:
            self.note_interaction()
            self.set_state("wave", 1.4)
            self.burst("sparkle", 6)
        self.butterfly.start()
        self.emit_event("butterfly", stage="come", auto=bool(auto))
        QTimer.singleShot(int(BCHASE_DELAY * 1000), self._chase_butterfly)
        QTimer.singleShot(2600, lambda: self.butterfly.mode in ("enter", "wander") and self._bchase is None
                          and self.say(random.choice(C.BUTTERFLY_SEE)))

    # ----- 追蝴蝶 -----
    def _bchase_ok(self):
        if not self.butterfly.active() or self.butterfly.mode not in ("enter", "wander", "land", "leave"):
            return False
        return bool(self.cfg["walk"]) and self.can_auto("chase")

    def _chase_butterfly(self):
        try:
            if self._bchase is not None or not self._bchase_ok():
                return
            now = time.monotonic()
            self._bchase = dict(t0=now, next=0.0, say=now + random.uniform(3.5, 5.0), lost=None)
            self.set_state(random.choice(("surprised", "happy")), 1.2)
            self.burst("excl", 1, at=self.head_point() + QPointF(self.char_w * 0.22, -14))
            self.say(random.choice(C.BUTTERFLY_CHASE_TEXTS), force=True, duration=2.4, tone="happy")
        except Exception as e:
            log_error("chase butterfly", e)

    def _end_bchase(self, why=""):
        bc, self._bchase = self._bchase, None
        if bc is None:
            return
        if self.walk is not None and self.walk.get("kind") == "chase":
            self.stop_walk()
        if why == "giveup":
            self.emit_event("butterfly", stage="giveup")
            self.set_state("shy", 2.2, expr="pout")            # 噘嘴失落, 不是生气
            self.burst("sweat", 2)
            self.say(random.choice(C.BUTTERFLY_GIVEUP_TEXTS), force=True, duration=2.8)

    def _step_bchase(self, t):
        bc = self._bchase
        if bc is None:
            return
        b = self.butterfly
        if not self._bchase_ok():
            self._end_bchase("giveup" if (not b.active() and self.isVisible() and self.state != "sleep"
                                          and not self._dragging and not self.fling) else "")
            return
        if b.mode == "sit":
            self._end_bchase("landed")
            return
        if t - bc["t0"] > BCHASE_MAX:
            self._end_bchase("giveup")
            b.leave()
            return
        if b.mode == "leave":
            if bc["lost"] is None:
                bc["lost"] = t
            elif t - bc["lost"] > 1.6:
                self._end_bchase("giveup")
                return
        hp = self.head_point()
        bp = b.pos_f
        dx = bp.x() - hp.x()
        # 追到了: 蝴蝶就在头顶附近 -> 伸手一跳, 蝴蝶大概率落下
        if (b.mode in ("enter", "wander") and abs(dx) < self.char_w * 0.35
                and -self.char_h * 1.4 < bp.y() - hp.y() < self.char_h * 0.3):
            self._end_bchase("reached")
            self.do_jump(False)
            self.set_state("cheer", 1.6)
            self.burst("sparkle", 5, at=QPointF(hp.x(), hp.y() - 16), bias=(0, 0))
            if random.random() < BCHASE_LAND_P and b.land_now(chased=True):
                self._bchase_land_until = t + 8.0
            return
        if t >= bc["next"]:
            bc["next"] = t + random.uniform(*BCHASE_RETARGET)
            g = self._screen_for_rect(self._normal_visible_rect()).availableGeometry()
            lo = g.left() - self.pad_x + 4
            hi = g.left() + g.width() - self.width() + self.pad_x - 4
            tx = max(lo, min(hi, bp.x() - self.width() / 2))
            if abs(tx - self.x()) > 8:
                self.start_walk(QPointF(tx, self.y()), kind="chase", speed=BCHASE_SPEED)
                if self.state == "idle" and random.random() < 0.5:
                    self.set_state("happy", 0.9)
        if t >= bc["say"]:
            bc["say"] = t + random.uniform(4.0, 6.0)
            if random.random() < 0.55:
                self.say(random.choice(C.BUTTERFLY_CHASE_TEXTS), force=True, duration=2.2, tone="happy")

    def _on_bfly_gone(self):
        if self._bchase is not None:
            self._end_bchase("giveup" if self.isVisible() and self.state != "sleep" else "")

    def _on_bfly_landed(self):
        self.emit_event("butterfly", stage="landed")
        if self.state in ("idle", "look", "look_left", "happy"):
            self.set_state("happy", 3.0)
        self.burst("sparkle", 4)
        if time.monotonic() < self._bchase_land_until:
            self._bchase_land_until = 0.0
            self.set_state("happy", 3.0)
            self.burst("heart", 2)
            self.say(random.choice(C.BUTTERFLY_LAND_CHASE_TEXTS), force=True, tone="happy")
        else:
            self.say(random.choice(C.BUTTERFLY_LAND))

    def _on_bfly_dodged(self):
        t = time.monotonic()
        if t > self._dodge_say:
            self._dodge_say = t + 6
            self.say(random.choice(C.BUTTERFLY_DODGE))

    def _on_bfly_caught(self):
        self.note_interaction()
        bp = self.butterfly.pos_f
        self.burst("sparkle", 14, at=bp, bias=(0, 0))
        self.burst("heart", 4, at=bp, bias=(0, 0))
        self.stats.inc("butterflies")
        self.sfx.play("sparkle")
        self.emit_event("butterfly", stage="caught")
        if self.state == "sleep":
            self.wake_up("butterfly")
        self.set_state("cheer", 2.2)
        self.say(random.choice(C.BUTTERFLY_CATCH), force=True, tone="happy")
        self.gain(4, "butterfly")

    # ----- 达妮卡来访 -----
    def summon_danika(self, auto=False):
        """低概率 idle 触发, 或托盘/菜单「测试：达妮卡来访」。"""
        if not self.isVisible():
            return False
        if self.danika.active():
            if not auto:
                self.say("达妮卡还在呢……", force=True)
            return False
        acts = self.activities()
        if not self.can_auto("danika", acts):
            if not auto:
                self.say("现在不太方便见客……", force=True)
            return False
        if "panel" in acts:
            if not auto:
                self.say("先把面板关上嘛~", force=True)
            return False
        # 手动触发无视冷却; 自动仍受 DANIKA_EVERY 约束(调用方已查)
        ok = self.danika.start()
        if ok:
            self._danika_next = time.monotonic() + random.uniform(*DANIKA_EVERY)
            self.emit_event("danika_visit", auto=bool(auto))
            self.bubble_timer.stop()
            self.happy_timer.stop()
            if not auto:
                self.note_interaction()
            try:
                self.stats.inc("danika_visits")
            except Exception:
                pass
            # 对话中点薇斯纳也可跳过
            self.set_state("look" if self.danika.side == "right" else "look_left", 2.0)
        elif not auto:
            self.say("达妮卡好像没来成……", force=True)
        return ok

    def _on_danika_finished(self):
        self.emit_event("danika_end", skipped=False)
        self._danika_next = max(self._danika_next, time.monotonic() + random.uniform(*DANIKA_EVERY))
        if not self._danika_test:
            self._schedule_happy()
            self._schedule_bubble()

    def _on_danika_skipped(self):
        self.emit_event("danika_end", skipped=True)
        self._danika_next = max(self._danika_next, time.monotonic() + random.uniform(*DANIKA_EVERY))
        if not self._danika_test:
            self._schedule_happy()
            self._schedule_bubble()

    def _run_danika_test(self):
        """`--danika-test`: 强制播一段来访, 方便截图/验收。"""
        try:
            self.show_and_raise()
            self.leave_peek()
            self.stop_walk()
            self.set_state("idle")
            # 固定短脚本, 保证 3–4 句内拍到
            script = [
                ("danika", "……茶。女皇吩咐您别再拖文书。"),
                ("vesna", "才、才没有拖!只是……风很大。"),
                ("danika", "室内没有风。请签。"),
                ("vesna", "……达妮卡好冷淡。"),
                ("danika", "冷淡能把文件交出去。告辞。"),
            ]
            self._danika_next = 0.0
            self.bubble_timer.stop()
            self.happy_timer.stop()
            self.bfly_timer.stop()
            ok = self.danika.start(script=script)
            if not ok:
                log_error("danika-test start failed")
                self.say("达妮卡测试启动失败", force=True)
                return
            # 对话结束后约 2s 退出(仅测试进程)
            def _bye():
                try:
                    from PySide6.QtWidgets import QApplication
                    QApplication.instance().quit()
                except Exception as e:
                    log_error("danika-test quit", e)
            self.danika.finished.connect(lambda: QTimer.singleShot(1800, _bye))
        except Exception as e:
            log_error("danika-test", e)

    # ----- 散步 -----
    def start_walk(self, target: QPointF = None, kind="stroll", speed=None):
        if self.edge or self._dragging or self.fling or not self.isVisible():
            return False
        if target is None:
            vis = self._normal_visible_rect()
            g = self._screen_for_rect(vis).availableGeometry()
            lo = g.left() - self.pad_x + 10
            hi = g.left() + g.width() - self.width() + self.pad_x - 10
            if hi <= lo:
                return False
            d = random.uniform(120, 380) * random.choice((-1, 1))
            tx = self.x() + d
            if tx < lo or tx > hi:
                tx = self.x() - d
            target = QPointF(max(lo, min(hi, tx)), self.y())
        self._wpos = QPointF(self.x(), self.y())
        dist = math.hypot(target.x() - self._wpos.x(), target.y() - self._wpos.y())
        if dist < 6:
            return False
        sp = speed or (WALK_SPEED if kind == "stroll" else max(240.0, dist / 3.2))
        self.walk = dict(tx=target.x(), ty=target.y(), speed=sp, kind=kind, t0=time.monotonic())
        self.revert_timer.stop()
        if self.state != "idle":
            self.set_state("idle")
        return True

    def stop_walk(self):
        if self.walk is not None:
            self.walk = None
            self.cfg["x"], self.cfg["y"] = self.x(), self.y()
            self.cfg.save()

    def come_here(self):
        self.note_interaction()
        if self.sulking():
            self._sulk_turn_away()
            self.quip(C.SULK_IGNORE_TEXTS, urgent=True)
            return
        if not self._tune("come_ok", True):            # 插件说她这会儿不肯来(比如心情很糟)
            cx = QCursor.pos().x() - (self.x() + self.width() / 2)
            self.set_state("look_left" if cx > 0 else "look", 1.6)
            self.kick(-1.0)
            self.quip(self._tune("come_refuse_lines", C.COME_REFUSE_TEXTS), urgent=True)
            self.emit_event("come_refused")
            return
        if self.edge:
            self.leave_peek()
        if self.state == "sleep":
            self.wake_up()
        cur = QCursor.pos()
        tx = cur.x() - self.width() / 2
        ty = cur.y() - (self.pad_top() + self.char_h * 0.62)
        scr = QGuiApplication.screenAt(cur) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        tx = max(g.left() - self.pad_x, min(tx, g.left() + g.width() - self.width() + self.pad_x))
        ty = max(g.top() - self.hop_room, min(ty, g.top() + g.height() - self.height() + PAD))
        if self.start_walk(QPointF(tx, ty), kind="come"):
            self.say("来啦来啦~", force=True)
        else:
            self.set_state("happy", 1.5)
            self.say(random.choice(C.COME_TEXTS), force=True)

    def _step_walk(self, t, dt):
        w = self.walk
        if self.edge or self._dragging or self.fling:
            self.walk = None
            return
        pos = self._wpos or QPointF(self.x(), self.y())
        dx, dy = w["tx"] - pos.x(), w["ty"] - pos.y()
        dist = math.hypot(dx, dy)
        if abs(dx) > 3:
            self.face_target = 1.0 if dx > 0 else -1.0
        if dist < 1.5 or t - w["t0"] > 25:
            kind = w["kind"]
            self.walk = None
            self.move(int(round(w["tx"])), int(round(w["ty"])))
            self.cfg["x"], self.cfg["y"] = self.x(), self.y()
            self.cfg.save()
            self.kick(-1.4)
            self.burst("puff", 3, at=self.foot_point(), bias=(0, 0))
            if kind == "come":
                self.set_state("happy", 2.0)
                self.burst("heart", 3)
                self.say(random.choice(C.COME_TEXTS))
            elif kind == "approach":
                self.set_state("happy", 1.6)
            elif kind == "stroll" and random.random() < 0.35:
                self.set_state(random.choice(("look", "look_left")), 1.8)
            self.emit_event("walk_end", kind=kind)
            return
        ramp = min(1.0, (t - w["t0"]) / 0.35)
        step = min(dist, w["speed"] * dt * (0.3 + 0.7 * ramp))
        pos = QPointF(pos.x() + dx / dist * step, pos.y() + dy / dist * step)
        self._wpos = pos
        self.move(int(round(pos.x())), int(round(pos.y())))
        prev = self._walk_phase
        self._walk_phase += dt * max(2.4, w["speed"] / max(40.0, self.char_w * 0.32))
        if int(prev) != int(self._walk_phase):
            self.kick(-0.5)
            if int(self._walk_phase) % 2 == 0:
                self.burst("puff", 1, at=self.foot_point(), bias=(0, 0))
        self.note_interaction()

    # ----- 位置 -----
    def _default_position(self):
        g = QGuiApplication.primaryScreen().availableGeometry()
        return g.left() + g.width() - self.width() - 40, g.top() + g.height() - self.height() - 10

    def _restore_position(self):
        try:
            edge = self.cfg["edge"]
            if edge and self.peek_ok():
                scr = self._screen_by_name(self.cfg["edge_screen"]) or self._screen_for_point(self.cfg["x"], self.cfg["y"])
                self.edge = edge
                self._edge_screen = scr
                self._apply_size()
                self._place_peek(scr, self.cfg["edge_along"])
                self.set_state("idle")
            else:
                if edge:
                    self.cfg["edge"] = None
                x, y = self.cfg["x"], self.cfg["y"]
                ok = False
                if isinstance(x, int) and isinstance(y, int):
                    r = QRect(x, y, self.width(), self.height())
                    for s in QGuiApplication.screens():
                        inter = s.availableGeometry().intersected(r)
                        if inter.width() > 60 and inter.height() > 60:
                            ok = True
                if not ok:
                    x, y = self._default_position()
                self.move(x, y)
        except Exception as e:
            log_error("restore position", e)
            self.edge = None
            self._apply_size()
            self.move(*self._default_position())
        self._ensure_visible()

    def _ensure_visible(self):
        try:
            r = QRect(self.pos(), self.size())
            for s in QGuiApplication.screens():
                inter = s.availableGeometry().intersected(r)
                if inter.width() >= min(60, r.width()) and inter.height() >= min(60, r.height()):
                    return True
            log_error(f"window off-screen at {r}, reset to default position")
            if self.edge:
                self.edge = None
                self.cfg["edge"] = None
                self._apply_size()
            self.move(*self._default_position())
            self.cfg["x"], self.cfg["y"] = self.x(), self.y()
            self.cfg.save()
            return False
        except Exception as e:
            log_error("ensure_visible", e)
            return True

    # ----- 边缘探头 -----
    def _screen_by_name(self, name):
        if not name:
            return None
        for s in QGuiApplication.screens():
            if s.name() == name:
                return s
        return None

    def _screen_for_point(self, x, y):
        if isinstance(x, int) and isinstance(y, int):
            s = QGuiApplication.screenAt(QPoint(x + 10, y + 10))
            if s:
                return s
        return QGuiApplication.primaryScreen()

    def _screen_for_rect(self, rect: QRect):
        best, area = None, -1
        for s in QGuiApplication.screens():
            i = s.geometry().intersected(rect)
            a = max(0, i.width()) * max(0, i.height())
            if a > area:
                best, area = s, a
        if best is not None and area > 0:
            return best
        c = rect.center()
        return min(QGuiApplication.screens(), key=lambda s: (s.geometry().center() - c).manhattanLength(), default=QGuiApplication.primaryScreen())

    def _edge_exposed(self, scr, edge, probe: QPoint):
        g = scr.geometry()
        if edge == "left":
            pt = QPoint(g.left() - 3, probe.y())
        elif edge == "right":
            pt = QPoint(g.left() + g.width() + 2, probe.y())
        else:
            pt = QPoint(probe.x(), g.top() - 3)
        return not any(s is not scr and s.geometry().contains(pt) for s in QGuiApplication.screens())

    def _normal_visible_rect(self, pos: QPoint = None):
        pos = pos or self.pos()
        return QRect(pos.x() + self.pad_x, pos.y() + PAD + self.hop_room, self.char_w, self.char_h)

    def _detect_edge(self):
        if not self.peek_ok():
            return None
        vis = self._normal_visible_rect()
        scr = self._screen_for_rect(vis)
        g = scr.availableGeometry()
        gl, gt = g.left(), g.top()
        gr = g.left() + g.width()
        cand = []
        d = vis.left() - gl
        if d <= SNAP_DIST and self._edge_exposed(scr, "left", vis.center()):
            cand.append((d, 0, "left"))
        d = gr - (vis.left() + vis.width())
        if d <= SNAP_DIST and self._edge_exposed(scr, "right", vis.center()):
            cand.append((d, 1, "right"))
        d = vis.top() - gt
        if d <= SNAP_DIST and self._edge_exposed(scr, "top", vis.center()):
            cand.append((d, 2, "top"))
        if not cand:
            return None
        cand.sort()
        edge = cand[0][2]
        along = vis.center().x() if edge == "top" else vis.center().y()
        return edge, scr, along

    def _place_peek(self, scr, along_win):
        scr = scr or QGuiApplication.primaryScreen()
        self._edge_screen = scr
        g = scr.availableGeometry()
        W, H = self.width(), self.height()
        gl, gt, gw, gh = g.left(), g.top(), g.width(), g.height()
        if self.edge in ("left", "right"):
            y = int(along_win) if along_win is not None else gt + (gh - H) // 2
            y = max(gt, min(y, gt + gh - H))
            x = gl if self.edge == "left" else gl + gw - W
            self._edge_along = y
        else:
            x = int(along_win) if along_win is not None else gl + (gw - W) // 2
            x = max(gl, min(x, gl + gw - W))
            y = gt
            self._edge_along = x
        self.move(x, y)

    def _save_edge(self):
        self.cfg["edge"] = self.edge
        self.cfg["edge_along"] = self._edge_along if self.edge else None
        self.cfg["edge_screen"] = self._edge_screen.name() if (self.edge and self._edge_screen) else None
        self.cfg["x"], self.cfg["y"] = self.x(), self.y()

    def enter_peek(self, edge, scr, center_along):
        try:
            if edge not in PEEK_EDGES or not self.peek_ok():
                return False
            self.walk = None
            self.edge = edge
            self._edge_screen = scr
            self.pop = 0.0
            self.tilt = 0.0; self.spin_rem = 0.0; self.spin_angle = 0.0
            self._apply_size()
            half = (self.height() if edge in ("left", "right") else self.width()) / 2
            self._place_peek(scr, None if center_along is None else center_along - half)
            self._save_edge()
            self.cfg.save()
            self.bubble.hide()
            self.set_state("idle")
            self.note_interaction()
            self._reveal_until = time.monotonic() + 1.2
            self._reposition_bubble()
            self.update()
            return True
        except Exception as e:
            log_error("enter_peek", e)
            self.edge = None
            try:
                self._apply_size()
            except Exception:
                pass
            return False

    def leave_peek(self, cursor=None):
        if not self.edge:
            return
        try:
            edge, scr = self.edge, self._edge_screen or QGuiApplication.primaryScreen()
            old = QRect(self.pos(), self.size())
            self.edge = None
            self._apply_size()
            W, H = self.width(), self.height()
            if cursor is not None:
                x, y = cursor.x() - W // 2, cursor.y() - int(H * 0.5)
            elif edge == "left":
                x, y = old.left() + 90, old.center().y() - H // 2
            elif edge == "right":
                x, y = old.left() + old.width() - W - 90, old.center().y() - H // 2
            else:
                x, y = old.center().x() - W // 2, old.top() + 90
            g = scr.availableGeometry()
            x = max(g.left() - self.pad_x, min(x, g.left() + g.width() - W + self.pad_x))
            y = max(g.top() - self.hop_room, min(y, g.top() + g.height() - H))
            self.move(x, y)
            self._save_edge()
            self.cfg.save()
            self.bubble.hide()
            self.kick(2.0)
            self.update()
        except Exception as e:
            log_error("leave_peek", e)
            self.edge = None

    def set_peek(self, on):
        self.cfg["peek"] = bool(on)
        if not on and self.edge:
            self.leave_peek()
        if on and self.peek_frames is None:
            self.peek_frames = load_peek_frames()
            self._peek_meta = self._compute_peek_meta()
        self.cfg.save()

    def _check_geometry(self):
        if self._dragging or self.fling or self.walk or not self.isVisible():
            return
        try:
            if self.edge:
                scr = self._edge_screen
                if scr is None or scr not in QGuiApplication.screens():
                    scr = self._screen_by_name(self.cfg["edge_screen"]) or self._screen_for_rect(QRect(self.pos(), self.size()))
                before = self.pos()
                self._place_peek(scr, self._edge_along)
                if self.pos() != before:
                    self._save_edge(); self.cfg.save()
            self._ensure_visible()
        except Exception as e:
            log_error("check_geometry", e)

    def bubble_side(self):
        return {"left": "right", "right": "left", "top": "bottom"}.get(self.edge, "top")

    def anchor_point(self) -> QPoint:
        if not self.edge or not self._peek_meta:
            return QPoint(self.x() + self.width() // 2, self.y() + PAD + self.hop_room)
        k = self.k_peek
        bb = self._peek_meta["bb"]
        ext = (bb.right() + 1) * k
        cy = (bb.top() + bb.bottom() / 2.0) * k
        if self.edge == "left":
            return QPoint(self.x() + int(ext) + 2, self.y() + PEEK_TPAD + int(cy))
        if self.edge == "right":
            return QPoint(self.x() + self.width() - int(ext) - 2, self.y() + PEEK_TPAD + int(cy))
        full_h = self._peek_meta["h"] * k
        return QPoint(self.x() + PEEK_TPAD + int(full_h - cy), self.y() + int(ext) + 2)

    def head_point(self) -> QPointF:
        if self.edge and self._peek_meta:
            a = self.anchor_point()
            off = {"left": (-25, 0), "right": (25, 0), "top": (0, -25)}[self.edge]
            return QPointF(a.x() + off[0], a.y() + off[1])
        return QPointF(self.x() + self.width() / 2, self.y() + PAD + self.hop_room + self.char_h * 0.18)

    def _inward_bias(self):
        return {"left": (130.0, 0.0), "right": (-130.0, 0.0), "top": (0.0, 160.0)}.get(self.edge, (0.0, 0.0))

    def _reposition_bubble(self):
        self.bubble.follow(self.anchor_point(), self.bubble_side())

    def moveEvent(self, e):
        super().moveEvent(e)
        self._reposition_bubble()

    # ----- 特效 / 动作 -----
    def burst(self, kind, n=1, at: QPointF = None, bias=None, text="", pm=None):
        if not self.cfg["fx"] or not self.isVisible():
            return
        pt = at if at is not None else self.head_point()
        self.fx.emit(kind, pt.x(), pt.y(), n, bias if bias is not None else self._inward_bias(), text, pm=pm)

    def foot_point(self) -> QPointF:
        return QPointF(self.x() + self.width() / 2, self.y() + self.height() - PAD)

    def kick(self, v):
        self.sq_v += v

    def do_jump(self, big=False):
        if self.edge:
            self._reveal_until = time.monotonic() + 2.0
            self.kick(2.5)
            self.burst("star", 6)
            return
        self.walk = None
        self.jump_start = time.monotonic()
        self.jump_dur = 0.62 if big else 0.42
        self.jump_h = self.char_h * (0.17 if big else 0.08)
        self._landed = False
        self.kick(3.0 if big else 1.8)
        if big:
            if self.state != "cheer":            # celebrate() 先换成欢呼再跳: 别把欢呼盖成 happy
                self.set_state("happy", 1.4)
            self.burst("star", 8)
            self.sfx.play("boing")
            self.say(random.choice(C.JUMP_TEXTS))

    def celebrate(self):
        self.set_state("cheer", 2.5)
        self.do_jump(True)
        self.burst("confetti", 34)
        self.burst("sparkle", 8)

    def pet(self):
        self.note_interaction()
        self.emit_event("pet", sleeping=self.state == "sleep", sulking=self.sulking())
        self._pet_cool = time.monotonic() + 2.5
        self.stop_walk()
        if self.state == "sleep":
            self.wake_by_pet()
            return
        if self._ix.call("pet"):                  # 互动扩展接管(如: 生气时哄她)
            self.stats.inc("pets")
            return
        if self.sulking():
            self.stats.inc("pets")
            self._end_sulk("pet")
            return
        self.set_state("content", 2.4)
        self.kick(-1.6)
        self.burst("heart", 6)
        self.sfx.play("pop")
        self.stats.inc("pets")
        self.say(random.choice(C.PET_TEXTS))
        self.gain(3, "pet", quiet=True)

    def on_link_event(self, cat):
        t = time.monotonic()
        if cat == "start":
            self.set_state("wave", 2.2)
            self.burst("sparkle", 10)
        elif cat in ("search", "code", "cmd", "other"):
            self.kick(1.4)
        elif cat == "perm":
            self._reveal_until = t + 5.0
            self.burst("excl", 1)
            self.kick(2.5)
        elif cat == "err":
            self.burst("sweat", 4)
            self.kick(-2.0)
        elif cat == "done":
            self.celebrate()
        elif cat == "bye":
            self.burst("heart", 5)

    def _tick(self):
        try:
            t = time.monotonic()
            dt = max(0.0, min(0.1, t - self._last_tick))
            self._last_tick = t
            # 果冻弹簧
            a = -SPRING_K * self.sq - SPRING_D * self.sq_v
            self.sq_v += a * dt
            self.sq = max(-0.25, min(0.25, self.sq + self.sq_v * dt))
            self.hover_k += ((1.0 if self._hover and not self._dragging else 0.0) - self.hover_k) * min(1.0, dt * 8)
            if self._bchase is not None:
                try:
                    self._step_bchase(t)
                except Exception as e:
                    log_error("step_bchase", e)
                    self._bchase = None
            if self.food_fx is not None:
                try:
                    self.food_fx.step(t)
                except Exception as e:
                    log_error("food effect step", e)
                    self.food_fx = None
            self._ix.step(t)
            if self.walk:
                self._step_walk(t, dt)
            else:
                self.face_target = 1.0
            self.face += (self.face_target - self.face) * min(1.0, dt * 9)
            # 倾斜: 拖拽摆锤 / 走路左右摇 / 悬停朝向鼠标
            target = 0.0
            if self._dragging:
                self._drag_vx *= math.exp(-5 * dt)
                target = max(-14.0, min(14.0, -self._drag_vx * 0.012))
                if self._drag_hold_t0:
                    if t >= self._drag_rate_at:        # 每 0.2 秒问一次插件: 挣扎计时走多快(轻轻抱着就慢)
                        self._drag_rate_at = t + 0.2
                        self._drag_rate = self._tune("drag_hold_rate", 1.0, held=round(t - self._drag_since, 1),
                                                     stage=self._drag_hold_stage)
                    if self._drag_rate != 1.0:
                        self._drag_hold_t0 = min(t, self._drag_hold_t0 + (1.0 - self._drag_rate) * dt)
                    held = t - self._drag_hold_t0
                    if held >= DRAG_HOLD_SEC:
                        # 越拖越用力挣扎, 但绝不自己挣脱/落地 — 仍由用户拖着
                        if held >= DRAG_HOLD_WIND:
                            amp, freq = 16.0, 20.0
                            stage = 4
                        elif held >= DRAG_HOLD_FURY:
                            amp, freq = 18.0, 17.5
                            stage = 3
                        elif held >= DRAG_HOLD_HARD:
                            amp, freq = 11.0, 13.0
                            stage = 2
                        else:
                            amp, freq = 5.5, 9.5
                            stage = 1
                        target += amp * math.sin(held * freq)
                        # 挣扎时更快跟上摆动(仍不挣脱), 视觉更激烈
                        self._drag_struggle_k = 26.0 if stage >= 4 else (22.0 if stage >= 2 else 16.0)
                        if stage >= 4:
                            self.sq = max(self.sq, 0.07 + 0.06 * abs(math.sin(held * 16.0)))
                            if not self.edge:
                                self.spin_rem = max(self.spin_rem, 220)
                            if self.state not in ("angry", "dizzy") and not self.sulking():
                                self.set_state("angry")
                            if t >= self._drag_hold_fx:
                                self._drag_hold_fx = t + 1.15
                                hp = self.head_point()
                                self.burst("anger", 1, at=hp + QPointF(self.char_w * 0.25, -10))
                                self.blow_at_cursor()
                                if random.random() < 0.45:
                                    self.do_jump(False)
                        elif stage >= 3:
                            self.sq = max(self.sq, 0.06 + 0.05 * abs(math.sin(held * 14.0)))
                            if self.state != "angry" and not self.sulking():
                                self.set_state("angry")
                            if t >= self._drag_hold_fx:
                                self._drag_hold_fx = t + 1.6
                                hp = self.head_point()
                                self.burst("anger", 1, at=hp + QPointF(self.char_w * 0.25, -10))
                                if random.random() < 0.55:
                                    self.burst("steam", 2, at=hp + QPointF(0, -8), bias=(0, 0))
                        elif stage >= 2 and self.state not in ("angry", "surprised") and not self.sulking():
                            self.set_state("surprised")
                        if stage > self._drag_hold_stage:
                            self._drag_hold_stage = stage
                            self._drag_hold_peak = max(self._drag_hold_peak, stage)
                            if stage == 1:
                                self.say(self.pick_line(C.DRAG_HOLD_TEXTS), force=True, duration=2.4)
                            elif stage == 2:
                                self.kick(-1.0)
                                self.say(self.pick_line(C.DRAG_HOLD_HARD_TEXTS), force=True, duration=2.6, tone="alert")
                            elif stage == 3:
                                self.kick(-1.6)
                                self.sfx.play("hmph")
                                self.say(self.pick_line(C.DRAG_HOLD_FURY_TEXTS), force=True, duration=2.8, tone="alert")
                            else:
                                self.kick(2.2)
                                self.sfx.play("whoosh")
                                self.burst("sparkle", 8)
                                self.burst("confetti", 10)
                                self.blow_at_cursor()
                                self._drag_hold_fx = t + 1.2
                                self.say(self.pick_line(C.DRAG_HOLD_WIND_TEXTS), force=True, duration=3.0, tone="alert")
            elif self.walk:
                target = 3.2 * math.sin(math.pi * self._walk_phase) + 2.0 * self.face_target
            elif self._hover and not self.edge:
                cx = QCursor.pos().x() - (self.x() + self.width() / 2)
                target = max(-5.0, min(5.0, cx / max(1, self.char_w) * 8))
            k_tilt = getattr(self, "_drag_struggle_k", 10.0) if self._dragging else 10.0
            if not self._dragging:
                self._drag_struggle_k = 10.0
            self.tilt += (target - self.tilt) * min(1.0, dt * k_tilt)
            self._drag_struggle_k = 10.0
            # 滚轮转圈(绕竖轴)
            if self.spin_rem > 0:
                step = min(self.spin_rem, 1080 * dt)
                self.spin_rem -= step
                self.spin_angle = (self.spin_angle + step) % 360
                if self.spin_rem <= 0:
                    self.spin_angle = 0.0
                    self._maybe_end_spin_session()
            elif self._spin_overspin:
                self._maybe_end_spin_session()
            if self._spin_live and self.spin_rem <= 0:
                self._spin_live = False
                self.emit_event("spin_end", meter=round(self._spin_meter, 1))
            if (self._spin_overspin and not self._spin_angry_done and not self._dragging
                    and not self.fling and self.state not in ("dizzy", "angry", "sleep")):
                self.set_state("dizzy")
            # 跳跃落地
            if not self._landed and t - self.jump_start >= self.jump_dur:
                self._landed = True
                self.kick(-2.4)
                self.burst("dust", 5, at=self.foot_point(), bias=(0, 0))
            if self.fling:
                self._step_fling(dt)
            if self.edge:
                self._step_peek(t, dt)
            else:
                self._step_gaze(t, dt)
            if self._sulk_until and t < self._sulk_until and t >= self._sulk_fx and self.state == "angry":
                self._sulk_fx = t + 2.4
                self.burst("anger", 1, at=self.head_point() + QPointF(self.char_w * random.uniform(0.15, 0.3), -10))
            if self.state == "dizzy" and t < self._dizzy_until and not self._dragging and not self.fling:
                if t >= self._dizzy_fx:
                    self._dizzy_fx = t + 1.6
                    self.burst("orbit", 2, bias=(0, 0))
                if not self.edge and t >= self._stagger_t:        # 踉踉跄跄的小碎步
                    self._stagger_t = t + random.uniform(0.45, 0.8)
                    self.kick(-0.9)
                    self.burst("puff", 2, at=self.foot_point(), bias=(0, 0))
            if self.state == "sleep" and t >= self._next_z:
                self._next_z = t + 1.5
                hp = self.head_point()
                self.burst("z", 1, at=QPointF(hp.x() + 18, hp.y() - 10))
            self.fx.badge = self.fx_badge if self.cfg["fx"] else None
            if self.fx.badge:
                if self.edge:
                    hp = self.head_point(); b = self._inward_bias()
                    self.fx.badge_pos = QPointF(hp.x() + b[0] * 0.35, hp.y() + b[1] * 0.25 - (22 if self.edge != "top" else 0))
                else:
                    self.fx.badge_pos = QPointF(self.x() + self.width() / 2 + self.char_w * 0.4, self.y() + PAD + self.hop_room + self.char_h * 0.06)
            self._update_hud()
            self.fx.step(dt, self.geometry(), alive=self.isVisible() and bool(self.cfg["fx"] or self.fx.hud))
            self.update()
        except Exception as e:
            log_error("tick", e)

    def _update_hud(self):
        if self.focus_end is None or not self.isVisible():
            self.fx.hud = None
            return
        rem = self.focus_remaining()
        self.fx.hud = dict(text=f"{rem // 60:02d}:{rem % 60:02d}", frac=1 - rem / max(1, self.focus_total),
                           paused=self.focus_paused)
        if self.edge:
            a = self.anchor_point(); b = self._inward_bias()
            self.fx.hud_pos = QPointF(a.x() + b[0] * 0.25, a.y() + (60 if self.edge != "top" else b[1] * 0.3))
        else:
            self.fx.hud_pos = QPointF(self.x() + self.width() / 2, self.y() + self.height() - PAD + 18)

    def _step_gaze(self, t, dt):
        """鼠标在旁边晃 -> 眼睛跟着看; 悬停不动太久 -> 害羞"""
        cur = QCursor.pos()
        moved = (cur - self._cur_last).manhattanLength()
        self._cur_last = cur
        if moved > 2:
            self._cur_moved = t
        want = 0
        if self.state == "idle" and not self.walk and not self._dragging and not self._hover:
            dx = cur.x() - (self.x() + self.width() / 2)
            dy = cur.y() - (self.y() + self.pad_top() + self.char_h * 0.4)
            if t - self._cur_moved < 2.2 and abs(dx) > self.char_w * 0.62 and math.hypot(dx, dy) < 760:
                want = 1 if dx > 0 else -1
        if want != self._gaze_want:
            self._gaze_want = want
            self._gaze_since = t
        elif want != self.gaze and t - self._gaze_since > (0.18 if want else 0.6):
            self.gaze = want
        # 盯着看
        if self._hover and not self._dragging and self.state == "idle":
            if moved <= 2:
                self._hover_still += dt
            else:
                self._hover_still = 0.0
            if self._hover_still > STARE_SEC and t > self._stare_cool:
                self._hover_still = 0.0
                self._stare_cool = t + 90
                self.set_state("shy", 2.8)
                self.burst("sweat", 1)
                self.say(random.choice(C.STARE_TEXTS))
        else:
            self._hover_still = 0.0

    def _step_peek(self, t, dt):
        sleeping = self.state == "sleep"
        cur = QCursor.pos()
        a = self.anchor_point()
        d = math.hypot(cur.x() - a.x(), cur.y() - a.y())
        prox = max(0.0, min(1.0, 1.0 - (d - 40) / 220.0))
        # 鼠标高速冲过来: 害羞缩回去
        if self._cursor_prev is not None and dt > 0 and not sleeping and t > self._duck_cool and not self._hover:
            pd = math.hypot(self._cursor_prev.x() - a.x(), self._cursor_prev.y() - a.y())
            speed = (pd - d) / dt
            if speed > 2200 and d < 260:
                self._duck_until = t + 1.2
                self._duck_cool = t + 8.0
                self._ducking = True
                self.kick(-2.0)
        self._cursor_prev = cur
        if self._ducking and t >= self._duck_until:
            self._ducking = False
            self._reveal_until = t + 1.5
            self.burst("quest", 1)
            if random.random() < 0.6:
                self.say(random.choice(C.SHY_TEXTS))
        full = (self.state in ("surprised", "angry", "happy", "cheer", "wave", "dizzy", "content", "eat", "love")
                or self._hover or t < self._reveal_until)
        target = 0.0 if (sleeping or t < self._duck_until) else (1.0 if full else 0.85 * prox)
        self.pop += (target - self.pop) * min(1.0, dt * (14 if t < self._duck_until else 9))

    def _step_fling(self, dt):
        vx, vy = self.fling
        nx, ny = self.x() + vx * dt, self.y() + vy * dt
        vis = self._normal_visible_rect(QPoint(int(nx), int(ny)))
        scr = self._screen_for_rect(vis)
        g = scr.availableGeometry()
        gl, gt, gr, gb = g.left(), g.top(), g.left() + g.width(), g.top() + g.height()
        hit, bounced = None, False
        impact, contact = 0.0, None             # 撞墙速度 / 撞击点(全局坐标)
        if vis.left() < gl:
            if abs(vx) > FLING_STICK and self._edge_exposed(scr, "left", vis.center()):
                hit = "left"
            impact, contact = abs(vx), QPointF(gl + 6, vis.center().y())
            nx += gl - vis.left(); vx = abs(vx) * 0.45; bounced = True
        elif vis.right() > gr:
            if abs(vx) > FLING_STICK and self._edge_exposed(scr, "right", vis.center()):
                hit = "right"
            impact, contact = abs(vx), QPointF(gr - 6, vis.center().y())
            nx -= vis.right() - gr; vx = -abs(vx) * 0.45; bounced = True
        if vis.top() < gt:
            if hit is None and abs(vy) > FLING_STICK and self._edge_exposed(scr, "top", vis.center()):
                hit = "top"
            if abs(vy) > impact:
                impact, contact = abs(vy), QPointF(vis.center().x(), gt + 6)
            ny += gt - vis.top(); vy = abs(vy) * 0.45; bounced = True
        elif vis.bottom() > gb:
            if abs(vy) > impact:
                impact, contact = abs(vy), QPointF(vis.center().x(), gb - 6)
            ny -= vis.bottom() - gb; vy = -abs(vy) * 0.45; bounced = True
        f = math.exp(-3.2 * dt)
        self.fling = [vx * f, vy * f]
        self.move(int(nx), int(ny))
        if hit and self.peek_ok():
            self.fling = None
            vis = self._normal_visible_rect()
            along = vis.center().x() if hit == "top" else vis.center().y()
            if self.enter_peek(hit, scr, along):
                self.kick(-3.0)
                self.burst("star", 7)
                self.sfx.play("boing")
                if self._throw:
                    self.stats.inc("wall_bonks")
                    self._throw_wall_dizzy()
                    self._schedule_throw_land(THROW_WALL_DIZZY_SEC + 0.35)
                else:
                    self.set_state("surprised", 1.2)
                    self.say(random.choice(C.BONK_TEXTS))
                return
        if bounced:
            self.kick(-2.2)
            self.burst("dust", 3, at=self.foot_point(), bias=(0, 0))
            if contact is not None:
                self._throw_bonk(impact, contact)
            if self._throw:
                self._throw_wall_dizzy()
        if math.hypot(*self.fling) < 70:
            self.fling = None
            self.kick(-1.8)
            self.burst("dust", 4, at=self.foot_point(), bias=(0, 0))
            self._finish_drag()
            tr = self._throw
            if tr and tr.get("dizzied"):
                remain = max(0.05, self._dizzy_until - time.monotonic())
                self._schedule_throw_land(remain + 0.2)
            else:
                self.set_state("idle")
                self._throw_land()

    # ----- 状态机 -----
    def note_interaction(self):
        self.last_interaction = time.monotonic()
        self._yawned = False

    KICKS = {"surprised": 2.4, "happy": 1.4, "angry": -1.6, "cheer": 3.0, "wave": 1.2, "dizzy": -1.2,
             "sleep": -0.8, "stretch": 3.6, "yawn": 1.0, "idle": 0.6, "look": 0.4, "look_left": 0.4,
             "eat": -1.0, "content": -1.4, "shy": -1.2, "focus": 0.5, "love": 2.6}

    def set_state(self, state, duration=None, why=None, expr=None):
        """换表情; duration 秒后回 idle(闹别扭时回 angry)。why: 从睡着换走时, wake 事件里记的醒来原因。
        expr: 这段时间画哪张脸(FACES 里的名字, 如 set_state("angry", 2.8, expr="yuck")); 状态本身照旧,
        没那张图就画状态的图。下一次 set_state 就清掉"""
        if state not in STATES:
            raise ValueError(state)
        if expr is not None and expr not in self.frames:
            raise ValueError(expr)
        self._expr, self._expr_state = expr, state
        if why is not None:
            self._wake_why = why
        prev = self.state
        self.revert_timer.stop()
        if state != prev:
            self.state = state
            self.state_since = time.monotonic()
            self.kick(self.KICKS.get(state, 0.0))
            if state == "angry":
                self.burst("anger", 1, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
            elif state == "dizzy":
                self.burst("orbit", 3, bias=(0, 0))
            if state != "idle":
                self.gaze = 0
            self.emit_event("state", **{"from": prev, "to": state})      # 事件: 状态切换 / 睡着 / 醒来(带原因)
            if state == "sleep":
                self.emit_event("sleep")
            elif prev == "sleep":
                self.emit_event("wake", why=self._wake_why or ("drag" if self._dragging else "other"))
        self._wake_why = None
        if duration:
            self.revert_timer.start(int(duration * 1000))
        self.update()

    def _revert_to_idle(self):
        if self._dragging or self.fling:
            return
        self.set_state("angry" if self.sulking() else "idle")

    def _schedule_happy(self):
        self.happy_timer.start(int(self._tune("idle_gap", random.uniform(*HAPPY_EVERY)) * 1000))

    def _schedule_bubble(self):
        self.bubble_timer.start(int(self._tune("bubble_gap", random.uniform(*BUBBLE_EVERY)) * 1000))

    def _idle_action(self):
        try:
            acts = self.activities()
            if self.can_auto("idle_action", acts):
                if (self.can_auto("danika_auto", acts) and time.monotonic() >= self._danika_next
                        and random.random() < DANIKA_IDLE_P):
                    if self.summon_danika(auto=True):
                        self._schedule_happy()
                        return
                if self.edge:
                    if random.random() < 0.55:
                        self._reveal_until = time.monotonic() + 2.5
                        self.kick(1.5)
                    else:
                        self.set_state("happy", random.uniform(*HAPPY_DURATION))
                elif self.focusing():
                    if random.random() < 0.3:
                        self.kick(1.0)
                else:
                    weights = self._tune("idle_weights", {"happy": 3, "look": 2.2, "stretch": 1.2, "hop": 1.6,
                                                          "wave": 1, "walk": 2.5, "sneak": 1.4})
                    if not self.cfg["walk"]:
                        weights["walk"] = 0                  # 设置里关了散步: 插件也改不回来
                    act = random.choices(list(weights), list(weights.values()))[0]
                    if act == "sneak":
                        self.start_sneak_eat()
                    elif act == "happy":
                        self.set_state("happy", random.uniform(*HAPPY_DURATION))
                        if random.random() < 0.35:
                            self.say(random.choice(C.HAPPY_TEXTS))
                    elif act == "look":
                        first = random.choice(("look", "look_left"))
                        other = "look_left" if first == "look" else "look"
                        self.set_state(first, 1.3)
                        QTimer.singleShot(1300, lambda: self.state == first and self.set_state(other, 1.3))
                    elif act == "stretch":
                        self.set_state("stretch", 1.6)
                        if random.random() < 0.4:
                            self.say(random.choice(C.STRETCH_TEXTS))
                    elif act == "hop":
                        self.do_jump(False)
                    elif act == "walk":
                        if self.start_walk() and random.random() < 0.25 and not self.link_busy:
                            self.say(random.choice(C.WALK_TEXTS))
                    else:
                        self.set_state("wave", 2.0)
                        self.burst("sparkle", 4)
                        if random.random() < 0.3 and not self.link_busy:
                            self.say(random.choice(C.WAVE_TEXTS))
                    if act not in ("sneak", "walk") or (self.sneaking() if act == "sneak" else self.walk is not None):
                        self.emit_event("idle_action", act=act)
        except Exception as e:
            log_error("idle_action", e)
        self._schedule_happy()

    def _random_bubble(self):
        if self.can_auto("random_bubble"):
            pool = list(C.BUBBLE_TEXTS)
            lv = self.stats.level()[0]
            for k, extra in C.BUBBLE_TEXTS_LV.items():
                if lv >= k:
                    pool += extra
            if self.stats.hunger < 30:
                pool += C.HUNGRY_TEXTS * 2
            self.say(random.choice(self._tune("bubble_pool", pool)))
        self._schedule_bubble()

    def _greet(self):
        if not self.isVisible() or self.state == "sleep":
            return
        st = self.stats
        self.set_state("wave", 2.0)
        self.say(random.choice(C.BACK_TEXTS) if st.away_hours >= 3 else C.greet_text())
        delay = 4200
        hol = C.holiday_text()
        if hol:
            QTimer.singleShot(delay, lambda: (self.burst("confetti", 18), self.say(hol, force=True, duration=4.5, tone="happy")))
            delay += 4800
        if st.new_day:
            st.new_day = False

            def checkin():
                self.burst("sparkle", 6)
                self.say(f"今天也来见我啦~ 相伴第 {st.d['days_met']} 天", duration=4.0, tone="info")
                self.gain(5)
            QTimer.singleShot(delay, checkin)

    def _check_sleep(self):
        self._geo_tick += 1
        if self._geo_tick % 5 == 0:
            self._check_geometry()
        self._check_focus()
        self._update_tooltip()
        self._check_presence()
        self._check_reminders()
        self.stats.tick(1.0)
        self.mood.tick(1.0)
        if self._geo_tick % 10 == 0:
            self.stats.save()
        now = time.monotonic()
        self._check_moods(now)
        h = datetime.now().hour
        if (h >= 23 or h < 5) and now - self._late_last > 2700 and self.state != "sleep":
            self._late_last = now
            self.say(random.choice(C.LATE_TEXTS))
        if self.food_fx is not None:
            self.note_interaction()          # 吃后效果期间不累计睡意
            return
        if not self.can_auto("fall_asleep"):
            return
        if self.focusing():
            self.note_interaction()          # 专注时她陪着你, 不睡
            return
        limit = self._tune("sleep_after", PEEK_SLEEP_SEC if self.edge else IDLE_SLEEP_SEC, edge=bool(self.edge))
        idle_for = now - self.last_interaction
        if idle_for >= limit:
            self.bubble.hide()
            self.set_state("sleep")
        elif idle_for >= limit - 4 and not self._yawned and not self.edge:
            self._yawned = True
            self.set_state("yawn", 3.0)
            self.say(random.choice(C.YAWN_TEXTS))

    def _check_presence(self):
        """每秒: 看整台电脑多久没碰键盘鼠标 -> 你离开了 / 回来了。读不到(非 Windows)就什么都不做"""
        idle = sysidle.idle_seconds()
        self._sys_idle = idle
        if idle is None:
            return
        now = time.monotonic()
        if self._away_since is None:
            if idle >= AWAY_SEC:
                self._away_since = now - idle
                self.emit_event("user_away", idle=int(idle))
        elif idle < 3.0:
            away = now - self._away_since
            self._away_since = None
            self.emit_event("user_back", away=int(away))
            self._welcome_back(away)

    def _welcome_back(self, away):
        """你离开电脑一阵又回来了: 她迎接你; 睡着就先伸个懒腰醒过来"""
        if not self.can_auto("welcome_back"):
            return
        self.note_interaction()
        self.stop_walk()
        pool = C.BACK_TEXTS if away >= BACK_LONG_SEC else C.RETURN_TEXTS
        if self.state == "sleep":
            self.set_state("stretch", 1.3, why="back")
            self.burst("sparkle", 4)
            QTimer.singleShot(1300, lambda: self.state in ("stretch", "idle") and self._greet_back(pool))
        else:
            self._greet_back(pool)

    def _greet_back(self, pool):
        if self.edge:
            self._reveal_until = time.monotonic() + 3.0
        lv = self.stats.level()[0]
        long = pool is C.BACK_TEXTS
        if pool is C.RETURN_TEXTS:                        # 短暂离开: 好感够了换成更亲近的那组话
            for k, extra in C.RETURN_TEXTS_LV.items():
                if lv >= k:
                    pool = extra
        pool = self._tune("greet_lines", pool, long=long, level=lv)
        if lv >= RETURN_CHEER_LV and self._tune("greet_cheer", True, level=lv):   # 好友起: 跳起来欢迎, 冒爱心
            self.set_state("cheer", 2.2)
            self.burst("heart", 6)
            if not self.edge:
                self.do_jump(False)
        else:
            self.set_state("wave", 2.0)
        self.burst("sparkle", 6)
        self.say(self.pick_line(pool), duration=3.5, tone="happy")

    def _check_reminders(self):
        now = time.monotonic()
        idle = self._sys_idle
        # 你不在电脑前: 久坐计时重来, 也不提醒。读得到系统空闲就看它; 读不到按老规矩, 她睡着就当你不在
        away = (self.state == "sleep") if idle is None else (idle >= SIT_BREAK_SEC)
        if away or not self.isVisible():
            self._sit_last = now
            return
        if not self.can_auto("reminder"):
            return
        # 下面的提醒在她睡着、你却在电脑前时会把她叫醒(醒来原因 reminder); 提醒完算一次互动, 免得马上又睡把气泡收掉
        wm, sm = int(self.cfg["water_min"]), int(self.cfg["sit_min"])
        if wm > 0 and now - self._water_last >= wm * 60:
            self._water_last = now
            self.emit_event("reminder", kind="water")
            self.note_interaction()
            self.set_state("wave", 1.6, why="reminder")
            self.burst("drop", 3)
            self.say(random.choice(C.WATER_TEXTS), force=True, duration=4.5, tone="info")
            return
        if sm > 0 and now - self._sit_last >= sm * 60:
            self._sit_last = now
            self.emit_event("reminder", kind="sit")
            self.note_interaction()
            self.set_state("stretch", 2.0, why="reminder")
            self.say(random.choice(C.SIT_TEXTS), force=True, duration=4.5, tone="info")
            return
        hr = datetime.now()
        if self.cfg["chime"] and hr.minute == 0 and hr.hour != self._chime_hour:
            self._chime_hour = hr.hour
            self.emit_event("reminder", kind="chime")
            if self.state == "sleep":
                self.note_interaction()
                self.set_state("idle", why="reminder")
            self.burst("note", 3)
            self.say(f"现在是 {hr.hour} 点整~", force=True, tone="info")
            return
        gap = self._tune("hungry_remind", 1200.0)
        if gap > 0 and self.stats.hunger < 25 and now - self._hungry_last > gap and self.state == "idle":
            self._hungry_last = now
            self.emit_event("reminder", kind="hungry")
            self.burst("emoji", 1, text="🍙")
            self.say(random.choice(C.HUNGRY_TEXTS) + " (右键 → 投喂)", duration=4.5)

    def say(self, text, force=False, duration=None, tone=None, src="pet"):
        if (self.cfg["mute"] and not force) or not self.isVisible():
            return
        # 达妮卡对话期间只允许 force 台词(她的对白), 避免整点/喝水气泡抢戏
        if (not force) and getattr(self, "danika", None) is not None and self.danika.active():
            return
        self.bubble.popup(text, self.anchor_point(), duration or BUBBLE_DURATION, topmost=self.cfg["topmost"],
                          side=self.bubble_side(), tone=tone or self._next_tone or "normal")
        self.emit_event("say", text=str(text), src=src)
        self._ix.call("say", str(text), src)       # 互动扩展: 台词通知(如配音); 没装就是空操作

    def wake_up(self, why="other"):
        self._wake_why = why
        self.set_state("surprised", SURPRISED_SEC)
        if random.random() < 0.7:
            self.say(random.choice(C.WAKE_TEXTS))

    def force_sleep(self):
        """设置里「立刻睡着」: 马上进入睡眠; 已睡着则说句梦话。"""
        if self.state == "sleep":
            self._mumble_next = 0.0
            self._sleep_mumble()
            return
        if self._dragging or self.fling:
            self.say("先把我放下嘛……", force=True)
            return
        try:
            if getattr(self, "danika", None) is not None and self.danika.active():
                self.danika.skip()
        except Exception as e:
            log_error("force_sleep danika", e)
        self._bchase = None
        self.stop_walk()
        self.bubble.hide()
        self.note_interaction()           # 重置 idle 计时, 醒来后不会立刻又睡
        self._yawned = False
        self.set_state("sleep")
        hp = self.head_point()
        self.burst("z", 2, at=QPointF(hp.x() + 18, hp.y() - 10))

    # ----- 偷吃 -----
    def sneaking(self):
        return time.monotonic() < self._sneak_until and not self._sneak_caught

    def start_sneak_eat(self):
        """闲着时偷偷吃一口; 没被点到就得意, 被点到就害羞否认。"""
        if not self.can_auto("sneak"):
            return False
        dur = random.uniform(*SNEAK_SEC)
        self._sneak_until = time.monotonic() + dur
        self._sneak_caught = False
        self.set_state("eat", dur)
        self.sfx.play("munch")
        self.burst("crumb", 5, at=self.mouth_point(), bias=(0, 0))
        QTimer.singleShot(int(dur * 1000) + 40, self._finish_sneak)
        return True

    def _catch_sneak(self):
        if not self.sneaking():
            return
        self._sneak_caught = True
        self._sneak_until = 0.0
        self.emit_event("sneak_caught")
        self.set_state("shy", 2.6)
        self.kick(-1.2)
        self.burst("excl", 1)
        self.burst("sweat", 2)
        self.sfx.play("huh")
        self.say(self.pick_line(self._tune("sneak_caught_lines", C.SNEAK_CAUGHT_TEXTS)), force=True, duration=2.8)

    def _finish_sneak(self):
        if self._sneak_caught or self._dragging or self.fling:
            self._sneak_until = 0.0
            return
        if time.monotonic() < self._sneak_until - 0.05:
            return
        self._sneak_until = 0.0
        if self.state not in ("eat", "idle", "content", "happy"):
            return
        self.set_state("content", 2.2, expr="smug")
        self.burst("sparkle", 3)
        self.say(self.pick_line(self._tune("sneak_done_lines", C.SNEAK_SMUG_TEXTS)), force=True, duration=2.4,
                 tone="happy")
        self.emit_event("sneak_done")

    # ----- 睡着时的互动 -----
    def _sleep_mumble(self):
        """鼠标经过睡着的她: 不醒, 偶尔嘟囔一句梦话。"""
        now = time.monotonic()
        if now < self._mumble_next:
            return
        self._mumble_next = now + SLEEP_MUMBLE_COOL
        if random.random() >= SLEEP_MUMBLE_P:
            return
        hp = self.head_point()
        self.burst("z", 2, at=QPointF(hp.x() + 18, hp.y() - 10))
        self.say(self.pick_line(C.SLEEP_MUMBLE_TEXTS), duration=2.2)

    def _wake_rude_penalty(self):
        now = time.monotonic()
        if now - self._wake_rude_last >= WAKE_RUDE_COOL:
            self._wake_rude_last = now
            self.gain(-1, quiet=True)

    def wake_by_pet(self):
        """摸头叫醒: 伸个懒腰, 开心地醒来。"""
        self.note_interaction()
        self._wake_why = "pet"
        self.clicks.clear()
        self.set_state("stretch", 1.3)
        self.burst("sparkle", 5)
        self.sfx.play("pop")
        def _happy():
            if self.state in ("stretch", "idle"):
                self.set_state("happy", 2.6)
                self.burst("heart", 5)
        QTimer.singleShot(1300, _happy)
        self.stats.inc("pets")
        self.say(self.pick_line(C.WAKE_PET_TEXTS), force=True, duration=3.2, tone="happy")
        self.gain(3, "pet", quiet=True)

    def _wake_by_drag(self):
        """睡着时被抓起来拖: 不满。"""
        self.note_interaction()
        self.clicks.clear()
        self._wake_drag = True
        self.set_state("angry")
        self.sfx.play("huh")
        self.burst("excl", 1)
        self.burst("anger", 1, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
        self.say(self.pick_line(C.WAKE_DRAG_TEXTS), force=True, duration=2.6, tone="alert")
        self._wake_rude_penalty()

    def _wake_by_spin(self, dy=0):
        """睡着时被滚轮转: 晕乎乎地生气醒来, 不计入晕度。"""
        now = time.monotonic()
        self.note_interaction()
        self._wake_why = "spin"
        self.clicks.clear()
        self._wheel_acc = 0
        self._spin_meter = 0.0
        self._spin_stage = 0
        self._spin_wake_grace = now + WAKE_SPIN_GRACE
        if not self.edge:
            self.spin_rem = min(self.spin_rem + 360, 1080)     # 被转了一圈的动画
        else:
            self._reveal_until = now + 2.0
        self.set_state("angry", WAKE_SPIN_ANGRY_SEC)
        self.burst("orbit", 2, bias=(0, 0))
        self.burst("anger", 2, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
        self.sfx.play("hmph")
        self.say(self.pick_line(C.WAKE_SPIN_TEXTS), force=True, duration=3.0, tone="alert")
        self._wake_rude_penalty()

    # ----- 台词节流 -----
    def pick_line(self, pool):
        """随机挑一句, 不和这个池子上一次说的重复"""
        last = self._last_lines.get(id(pool))
        cands = [s for s in pool if s != last] or list(pool)
        line = random.choice(cands)
        self._last_lines[id(pool)] = line
        return line

    def quip(self, pool, urgent=False, gap=QUIP_GAP, **kw):
        """互动台词: gap 秒内只说一句(urgent 无视节流); 返回说出的句子或 None"""
        now = time.monotonic()
        if not urgent and now < self._quip_until:
            return None
        self._quip_until = now + gap
        line = self.pick_line(pool)
        self.say(line, **kw)
        return line

    # ----- 被丢出去 -----
    def _throw_start(self, vx, vy):
        """松手甩出去的一瞬间: 记一次"被丢", 惊叫"""
        now = time.monotonic()
        while self._throws and now - self._throws[0] > THROW_WINDOW:
            self._throws.popleft()
        self._throws.append(now)
        speed = math.hypot(vx, vy)
        hard = speed >= THROW_HARD
        level = len(self._throws) + (1 if hard else 0)
        self._throw = dict(speed=speed, hard=hard, level=level, bonks=0, t_bonk=0.0,
                           dizzied=False, land_scheduled=False)
        self.stats.inc("throws")
        self.emit_event("throw", speed=int(speed), hard=bool(hard), level=int(level))
        if hard:
            self.set_state("surprised")
            self.spin_rem = min(self.spin_rem + 720, 1080)        # 狠狠丢: 在空中打转; 晕要等撞墙
        else:
            self.set_state("surprised")
        self.burst("excl", 1)
        self.burst("sweat", 2)
        self.quip(C.THROW_FLY_HARD_TEXTS if hard else C.THROW_FLY_TEXTS, urgent=True, duration=1.6)

    def _throw_bonk(self, impact, at: QPointF):
        """飞行中撞到屏幕边: 咚! 星星 + 音效, 第一次撞墙喊疼"""
        tr = self._throw
        now = time.monotonic()
        if tr is None or impact < WALL_BONK_MIN or now - tr["t_bonk"] < 0.25:
            return
        tr["t_bonk"] = now
        tr["bonks"] += 1
        self.emit_event("bonk", impact=int(impact))
        big = impact > FLING_STICK
        self.stats.inc("wall_bonks")
        self.kick(-3.2 if big else -2.4)
        self.burst("star", 6 if big else 4, at=at, bias=(0, 0))
        self.sfx.play("bonk")
        if tr["bonks"] == 1:
            self.burst("anger", 1, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
            self.quip(C.WALL_BONK_TEXTS, urgent=True, duration=1.6)

    def _throw_wall_dizzy(self):
        """丢出去撞到墙: 先晕一下。没撞墙不调用。"""
        tr = self._throw
        if tr is None or tr.get("dizzied"):
            return
        tr["dizzied"] = True
        self.emit_event("dizzy", why="wall")
        now = time.monotonic()
        dur = THROW_WALL_DIZZY_SEC
        self._dizzy_until = now + dur
        self._dizzy_extra = 0
        self._dizzy_fx = now + 0.35
        self._stagger_t = now + 0.3
        self._spin_recover_at = 0.0
        self._spin_recover_sure = False
        if not self.edge:
            self.spin_rem = min(self.spin_rem + 360, 1080)
        self.set_state("dizzy", dur)
        self.burst("orbit", 3, bias=(0, 0))
        self.sfx.play("whoosh")
        self.stats.inc("dizzies")
        self.quip(C.THROW_WALL_DIZZY_TEXTS, urgent=True, duration=2.2)

    def _schedule_throw_land(self, delay):
        tr = self._throw
        if tr is None or tr.get("land_scheduled"):
            return
        tr["land_scheduled"] = True
        ms = max(0, int(delay * 1000))
        if ms <= 20:
            self._throw_land()
        else:
            QTimer.singleShot(ms, self._throw_land)

    def _throw_land(self):
        """落地(或贴墙)后: 按 60 秒内被丢次数逐级生气; 第 3 次起闹别扭"""
        tr, self._throw = self._throw, None
        if tr is None or self._dragging:
            return
        self.note_interaction()
        level = tr["level"]
        self.emit_event("throw_land", level=int(level), wall=bool(tr["bonks"] or tr.get("dizzied")),
                        bonks=int(tr["bonks"]))
        if level >= 3:
            self._start_sulk(again=self.sulking())
            self.gain(-2, quiet=True)
            return
        hp = self.head_point() + QPointF(self.char_w * 0.25, -10)
        if level == 2:
            self.set_state("angry", 3.2)
            self.burst("anger", 2, at=hp)
            self.burst("steam", 4, at=self.head_point() + QPointF(0, -10), bias=(0, 0))
            self.sfx.play("hmph")
            self.gain(-1, quiet=True)
            pool = C.THROWN_HARD_TEXTS if tr["hard"] else C.THROWN_ANGRY_TEXTS
        else:
            self.set_state("angry", 2.4)
            self.burst("anger", 1, at=hp)
            pool = C.THROWN_MILD_TEXTS
        self.quip(pool, urgent=True, duration=3.2, tone="alert")

    # ----- 闹别扭 -----
    def sulking(self):
        return time.monotonic() < self._sulk_until

    def _start_sulk(self, again=False, pool=None, revenge=True):
        now = time.monotonic()
        if not again:
            self.stats.inc("sulks")
        self.emit_event("sulk", again=bool(again))
        self._sulk_until = now + SULK_SEC
        self._sulk_calm = 0
        self._sulk_fx = now + 2.4
        self.stop_walk()
        self.set_state("angry")
        self.sfx.play("hmph")
        self.burst("anger", 2, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
        self.burst("steam", 6, at=self.head_point() + QPointF(0, -10), bias=(0, 0))
        self.quip(pool or (C.SULK_AGAIN_TEXTS if again else C.SULK_START_TEXTS), urgent=True, duration=3.0, tone="alert")
        if revenge:
            QTimer.singleShot(1700, self._revenge)
        else:
            QTimer.singleShot(1500, lambda: self.sulking() and self._sulk_turn_away())

    def _revenge(self):
        """小报复: 跺两下脚, 朝鼠标吹一阵小旋风"""
        if not self.sulking() or self._dragging or self.fling or not self.isVisible():
            return
        if not self.edge:
            self.do_jump(False)
            QTimer.singleShot(460, lambda: self.sulking() and not self._dragging and not self.fling and self.do_jump(False))
            QTimer.singleShot(880, lambda: self.sulking() and self.burst("dust", 6, at=self.foot_point(), bias=(0, 0)))
        QTimer.singleShot(950, self._gust)

    def blow_at_cursor(self):
        """朝鼠标吹一小阵风(粒子+音效, 不会真的动鼠标)。拖着她的时候也能用; 插件可调。"""
        if not self.isVisible():
            return
        cur = QCursor.pos()
        hp = self.head_point()
        dx, dy = cur.x() - hp.x(), cur.y() - hp.y()
        d = math.hypot(dx, dy) or 1.0
        src = QPointF(hp.x() + dx / d * self.char_w * 0.3, hp.y() + self.char_h * 0.18)
        self.burst("gust", 10, at=src, bias=(dx / d * 340, dy / d * 340))
        self.burst("sparkle", 4, at=src, bias=(dx / d * 120, dy / d * 120))
        self.sfx.play("whoosh")
        self.kick(2.0)

    def _drag_release_wind(self):
        """拖到风元素阶段后松手: 落地再吹一下, 抱怨头发乱了。"""
        self.set_state("angry", 3.4)
        self.burst("sparkle", 6)
        if not self.edge:
            self.do_jump(False)
        QTimer.singleShot(280, self.blow_at_cursor)
        self.say(self.pick_line(C.DRAG_HOLD_WIND_DROP_TEXTS), force=True, duration=3.2, tone="alert")

    def _gust(self):
        if not self.sulking() or self._dragging or self.fling or not self.isVisible():
            return
        self.blow_at_cursor()
        self.quip(C.REVENGE_TEXTS, urgent=True, duration=2.2)

    def _sulk_turn_away(self):
        """扭头: 看向鼠标的反方向, 过一会儿又变回生气脸"""
        cx = QCursor.pos().x() - (self.x() + self.width() / 2)
        self.set_state("look_left" if cx > 0 else "look", 1.4)

    def _sulk_poke(self, rapid, calm=True):
        """闹别扭时被点: 轻轻点几下能哄好, 连戳会更生气"""
        now = time.monotonic()
        if rapid:
            self._sulk_until = min(now + SULK_SEC, self._sulk_until + SULK_POKE_ADD)
            self._sulk_calm = 0
            self.set_state("angry")
            self.kick(-1.6)
            if now >= self._sulk_poke_say:
                self._sulk_poke_say = now + 1.4
                self.quip(C.SULK_POKE_TEXTS, urgent=True)
                self.burst("anger", 1, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
                self.sfx.play("hmph")
            return
        if calm and now - self._sulk_click_t >= 0.8:
            self._sulk_click_t = now
            self._sulk_calm += 1
            if self._sulk_calm >= SULK_CALM_CLICKS:
                self._end_sulk("click")
                return
        self._sulk_turn_away()
        self.kick(-1.0)
        self.quip(C.SULK_IGNORE_TEXTS, gap=1.2)

    def _end_sulk(self, how="time"):
        """消气: 摸头(pet) / 投喂(food) / 轻轻点(click) / 时间到(time)"""
        if not self._sulk_until:
            return
        self._sulk_until = 0.0
        self._sulk_calm = 0
        self._throws.clear()
        self.emit_event("makeup", how=how)
        pool = {"pet": C.MAKEUP_PET_TEXTS, "food": C.MAKEUP_FOOD_TEXTS, "time": C.MAKEUP_TIME_TEXTS}.get(how, C.MAKEUP_TEXTS)
        self.gain(1, quiet=True)
        if how == "food":                    # 先吃, 吃完再说原谅
            QTimer.singleShot(3000, lambda: (self.burst("heart", 3), self.say(self.pick_line(pool), force=True,
                                                                               duration=3.5, tone="happy")))
            return
        self.set_state({"pet": "content", "click": "shy"}.get(how, "happy"), 2.4)
        self.burst("heart", 4)
        self.sfx.play("pop")
        self.quip(pool, urgent=True, duration=3.5, tone="happy")

    # ----- 转圈圈 -----
    def _decay_spin(self, now):
        dt = max(0.0, now - self._spin_t - 0.3)     # 连续滚动时不消退, 停下 0.3 秒后才慢慢消退
        self._spin_t = now
        self._spin_meter = max(0.0, self._spin_meter - SPIN_DECAY * dt)
        if self._spin_meter < 0.5 and now >= self._dizzy_until:
            self._spin_stage = 0

    def _spin_notches(self, n, now):
        """开心 -> 有点晕 -> 记下「转太多」. 2.4s 眩晕倒计时等这一轮停下才开始。"""
        self._decay_spin(now)
        if self._spin_posting:
            return
        if self._spin_overspin:
            if self.state != "dizzy" and not self._dragging and not self.fling:
                self.set_state("dizzy")
            return
        if now < self._dizzy_until:
            return
        self._spin_meter += n
        m = self._spin_meter
        if m >= DIZZY_NOTCHES:
            self._mark_overspin(now)
        elif m >= SPIN_WOOZY and self._spin_stage < 2:
            self._spin_stage = 2
            self.burst("orbit", 2, bias=(0, 0))
            self.burst("sweat", 1)
            self.kick(-1.0)
            self.quip(C.SPIN_WOOZY_TEXTS, urgent=True, duration=2.2)
        elif self._spin_stage < 1:
            self._spin_stage = 1
            if self.state in ("idle", "happy", "look", "look_left", "content", "wave", "surprised"):
                self.set_state("happy", 1.4)
            self.burst("sparkle", 5)
            self.quip(C.SPIN_HAPPY_TEXTS, duration=2.0)

    def _mark_overspin(self, now):
        """转太多圈: 立刻一直眩晕; 2.4s 倒计时等停下再走。"""
        self._spin_stage = 3
        self._spin_overspin = True
        self.emit_event("dizzy", why="spin")
        self._spin_angry_done = False
        self._spin_posting = False
        self._spin_recover_at = 0.0
        self._dizzy_until = now + 86400.0
        self._dizzy_fx = now + 0.8
        self._stagger_t = now + 0.4
        self.set_state("dizzy")
        self.sfx.play("whoosh")
        self.burst("orbit", 4, bias=(0, 0))
        self.burst("sweat", 2)
        self.stats.inc("dizzies")
        self.quip(C.SPIN_OVERDO_TEXTS, urgent=True, duration=2.8)

    def _start_spin_aftershock(self, now):
        """这一轮停下后: 再晕 2.4s, 然后原来的生气。"""
        self._spin_posting = True
        dur = SPIN_PRE_ANGRY_SEC
        self._dizzy_until = now + dur
        self._dizzy_fx = now
        self._stagger_t = now
        if self.state != "dizzy":
            self.set_state("dizzy")
        QTimer.singleShot(int(dur * 1000), self._spin_dizzy_then_angry)

    def _spin_dizzy_then_angry(self):
        if not self._spin_posting or self._spin_angry_done:
            return
        if self._dragging or self.fling or not self.isVisible():
            QTimer.singleShot(200, self._spin_dizzy_then_angry)
            return
        self._spin_queasy(time.monotonic())

    def _spin_queasy(self, now):
        """原来的生气效果: 怒气、想吐、扣好感。"""
        if self._spin_angry_done:
            return
        if self._ix.call("spin_queasy", now):     # 互动扩展接管(如: 转吐了)
            return
        self._spin_angry_done = True
        self._dizzy_until = 0.0
        self._dizzy_extra = 0
        self._spin_meter = 0.0
        self._spin_overspin = False
        self._spin_posting = False
        self._spin_stage = 0
        self._spin_refuse_until = now + SPIN_REFUSE_SEC
        self._spin_recover_at = self._spin_refuse_until + 0.3
        self._spin_recover_sure = True
        self.set_state("angry", 3.0)
        self.sfx.play("hmph")
        self.burst("sweat", 4)
        self.burst("anger", 2, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
        self.burst("emoji", 1, at=self.head_point() + QPointF(-self.char_w * 0.28, -6), text="😵")
        self.gain(-1, quiet=True)
        self.quip(C.SPIN_QUEASY_TEXTS, urgent=True, duration=3.0, tone="alert")

    def _maybe_end_spin_session(self):
        """圈停且没在滚: 若这轮转太多, 这时才开始 2.4s 眩晕。"""
        if not self._spin_overspin or self._spin_posting or self._spin_angry_done:
            return
        if self.spin_rem > 0 or self._dragging or self.fling:
            return
        now = time.monotonic()
        if now - self._spin_t < 0.35:
            return
        self._start_spin_aftershock(now)

    def _check_moods(self, now):
        """每秒: 闹别扭到时自己消气; 转圈拒绝窗口结束后收尾"""
        if self._sulk_until and now >= self._sulk_until and not self._dragging and not self.fling:
            if self.state == "sleep":
                self._sulk_until = 0.0
            else:
                self._end_sulk("time")
        if (self._spin_recover_at and now >= self._spin_recover_at and now >= self._spin_refuse_until
                and now >= self._dizzy_until and not self._spin_overspin and not self._spin_posting):
            self._spin_recover_at = 0.0
            self._spin_meter = 0.0
            self._spin_stage = 0
            if (self.state != "sleep" and not self._dragging and not self.fling and not self.sulking()
                    and self._spin_recover_sure):
                self.burst("sweat", 1)
                self.quip(C.SPIN_RECOVER_TEXTS, urgent=True, duration=3.0)

    # ----- 鼠标 -----
    def leaveEvent(self, e):
        self._hover = False
        self._pet_x = None
        super().leaveEvent(e)

    def enterEvent(self, e):
        self._hover = True
        if self.state == "sleep":
            self._sleep_mumble()             # 鼠标经过不再叫醒她, 偶尔说句梦话
        else:
            self.note_interaction()
        super().enterEvent(e)

    def mousePressEvent(self, e):
        if self._ix.call("mouse_press", e):      # 互动扩展(如: 拖着时右键强行浇水)
            e.accept()
            return
        if e.button() == Qt.LeftButton:
            self.note_interaction()
            if getattr(self, "danika", None) is not None and self.danika.active():
                self.danika.skip()
            if self.fling:
                self._throw = None                # 半空中接住了: 不抱怨
            self.fling = None
            self.stop_walk()
            self._bchase = None
            self._press = e.globalPosition().toPoint()
            self._win_start = self.pos()
            self._dragging = False
            self._drag_hold_t0 = 0.0
            self._drag_hold_stage = 0
            self._drag_hold_peak = 0
            self._drag_hold_fx = 0.0
            self._drag_samples.clear()
            self._drag_samples.append((time.monotonic(), self._press))
            e.accept()

    def mouseMoveEvent(self, e):
        cur = e.globalPosition().toPoint()
        if self._press is not None and (e.buttons() & Qt.LeftButton):
            delta = cur - self._press
            if not self._dragging and (abs(delta.x()) > DRAG_THRESHOLD or abs(delta.y()) > DRAG_THRESHOLD):
                self._dragging = True
                self._drag_hold_t0 = self._drag_since = time.monotonic()
                self._drag_rate, self._drag_rate_at = 1.0, 0.0
                self._drag_hold_stage = 0
                self._drag_hold_fx = 0.0
                self.setCursor(Qt.ClosedHandCursor)
                self.bubble.hide()
                was_sleep = self.state == "sleep"
                if self.edge:
                    self.leave_peek(cursor=cur)
                    self._press, self._win_start = cur, self.pos()
                    delta = QPoint(0, 0)
                self.set_state(DRAG_STATE)
                if was_sleep:
                    self._wake_by_drag()
                self.emit_event("drag_start", was_sleep=was_sleep)
            if self._dragging:
                t = time.monotonic()
                lt, lp = self._drag_samples[-1] if self._drag_samples else (t, cur)
                if t - lt > 1e-3:
                    self._drag_vx = 0.7 * self._drag_vx + 0.3 * (cur.x() - lp.x()) / (t - lt)
                self._drag_samples.append((t, cur))
                self.move(self._win_start + delta)
                self.note_interaction()
        elif not e.buttons():
            self._track_pet(e.position(), time.monotonic())

    def _track_pet(self, pos, t):
        """在头部区域左右来回划动 = 摸头"""
        head_y = (PAD + self.hop_room + self.char_h * 0.45) if not self.edge else self.height()
        if pos.y() > head_y:
            self._pet_x = None
            return
        x = pos.x()
        if self._pet_x is not None and abs(x - self._pet_x) > 6:
            d = 1 if x > self._pet_x else -1
            if self._pet_dir and d != self._pet_dir:
                self._pet_hist.append(t)
            self._pet_dir = d
            self._pet_x = x
        elif self._pet_x is None:
            self._pet_x = x
        if t >= self._pet_cool and sum(1 for s in self._pet_hist if t - s <= 1.5) >= PET_REVERSALS:
            self._pet_hist.clear()
            self.pet()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._press is None:
            return
        was_drag = self._dragging
        peak = self._drag_hold_peak
        held = (time.monotonic() - self._drag_since) if self._drag_hold_t0 else 0.0     # 真实拖了多久
        self._press = None
        self._dragging = False
        self._drag_hold_t0 = 0.0
        self._drag_hold_stage = 0
        self._drag_hold_peak = 0
        self._drag_hold_fx = 0.0
        self.setCursor(Qt.OpenHandCursor)
        self.note_interaction()
        if was_drag:
            now = time.monotonic()
            pts = [s for s in self._drag_samples if now - s[0] <= 0.09]
            if len(pts) >= 2 and pts[-1][0] - pts[0][0] > 0.01:
                span = pts[-1][0] - pts[0][0]
                vx = (pts[-1][1].x() - pts[0][1].x()) / span
                vy = (pts[-1][1].y() - pts[0][1].y()) / span
                if math.hypot(vx, vy) > FLING_MIN:
                    self._wake_drag = False          # 变成被丢: 交给原有的丢出反应
                    self.fling = [max(-4000, min(4000, vx)), max(-4000, min(4000, vy))]
                    self.sfx.play("whoosh")
                    self.emit_event("drag_end", held=round(held, 1), thrown=True)
                    self._throw_start(*self.fling)
                    return
            if self._wake_drag and not self.sulking():
                self._wake_drag = False
                self.set_state("angry", WAKE_GRUMPY_SEC)
            elif peak >= 4 and not self.sulking():
                self._drag_release_wind()
            else:
                self.set_state("angry" if self.sulking() else "idle")
            self.emit_event("drag_end", held=round(held, 1), thrown=False)
            self.kick(-1.8)
            self.burst("dust", 3, at=self.foot_point(), bias=(0, 0))
            self._finish_drag()
        else:
            self.on_click()

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self.note_interaction()
        self.emit_event("double_click")
        if self._ix.call("click", True):
            return
        now = time.monotonic()
        self.clicks.append(now)
        if self.state == "sleep":
            self.wake_up("click")
        elif self.sulking():
            self._sulk_poke(len([t for t in self.clicks if now - t <= RAPID_WINDOW]) >= RAPID_CLICKS + 1, calm=False)
        elif len([t for t in self.clicks if now - t <= RAPID_WINDOW]) >= RAPID_CLICKS + 1 or self.state == "angry":
            self.set_state("angry", ANGRY_SEC)
            self.sfx.play("hmph")
            self.say(random.choice(C.ANGRY_TEXTS))
        else:
            self.do_jump(True)
            self.stats.inc("jumps")
            self.gain(1, "jump", quiet=True)

    def wheelEvent(self, e):
        """滚轮: 转圈; 转太多只打标记; 停下后才晕 2.4s 再生气, 再 15 秒拦下一次"""
        try:
            d = e.angleDelta()
            dy = d.y() or d.x()
            if not dy:
                return
            e.accept()
            self.note_interaction()
            self.stop_walk()
            now = time.monotonic()
            if self._ix.call("wheel", e):              # 互动扩展拦下这次转圈(如: 究极生气时不让转)
                return
            if self.state == "sleep":
                self._wake_by_spin(dy)
                return
            if now < self._spin_wake_grace:              # 刚被转醒: 这一下不算晕度
                self._wheel_acc = 0
                return
            self._wheel_acc = getattr(self, "_wheel_acc", 0) + abs(dy)   # 触控板高精度滚动累积成"格"
            notches = 0
            while self._wheel_acc >= 120:
                self._wheel_acc -= 120
                notches += 1
            if not notches:
                return
            for _ in range(notches):
                self._wheel_hist.append(now)
            if self.fling or self._dragging:
                return
            if self.sulking():
                self._sulk_turn_away()
                self.quip(C.SULK_SPIN_TEXTS, gap=1.5)
                return
            if self._spin_posting:
                return
            if (not self._spin_overspin) and now < self._spin_refuse_until:
                self.kick(-1.2)
                if self.quip(C.SPIN_REFUSE_TEXTS, gap=1.6):
                    self.burst("anger", 1, at=self.head_point() + QPointF(self.char_w * 0.25, -10))
                    self.sfx.play("hmph")
                return
            if self.edge:
                self._reveal_until = now + 2.0
                self.kick(1.2 if dy > 0 else -1.2)
            else:
                if not self._spin_live:
                    self._spin_live = True
                    self.emit_event("spin_start")
                self.spin_rem = min(self.spin_rem + 360 * notches, 1080)
            self._spin_notches(notches, now)
        except Exception as ex:
            log_error("wheelEvent", ex)

    def _finish_drag(self):
        """拖拽/甩动结束: 靠近左/右/上边缘 -> 吸附探头; 否则保存位置"""
        try:
            snap = self._detect_edge()
            if snap and self.enter_peek(*snap):
                self.burst("sparkle", 5)
                return
        except Exception as e:
            log_error("finish_drag", e)
        self.cfg["edge"] = None
        self.cfg["x"], self.cfg["y"] = self.x(), self.y()
        self.cfg.save()
        self._ensure_visible()

    def on_click(self):
        now = time.monotonic()
        self.emit_event("click")
        if self._ix.call("click", False):          # 互动扩展接管(如: 究极生气时被戳)
            return
        if self.state == "sleep":
            self.clicks.clear()
            self.wake_up("click")
            return
        if self.sneaking():
            self._catch_sneak()
            return
        self.clicks.append(now)
        recent = [t for t in self.clicks if now - t <= RAPID_WINDOW]
        if self.sulking():
            self._sulk_poke(len(recent) >= RAPID_CLICKS)
            return
        if len(recent) >= RAPID_CLICKS or self.state == "angry":
            self.set_state("angry", ANGRY_SEC)
            self.sfx.play("hmph")
            self.say(random.choice(C.ANGRY_TEXTS))
        else:
            self.set_state("surprised", SURPRISED_SEC)
            self.sfx.play("huh")
            if self.edge:
                self._reveal_until = now + 1.5
                self.burst("sparkle", 4)
            if random.random() < 0.4:
                self.say(random.choice(C.SURPRISED_TEXTS))

    # ----- 绘制 -----
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        try:
            t = time.monotonic()
            if self.edge and self.peek_ok():
                key = self._paint_peek(p, t)
                real = key in self.peek_frames.get("_real", ())
            else:
                key = self._paint_stand(p, t)
                real = key in self.real_frames
            if real and key not in self._seen_keys:
                self._seen_keys.add(key)
                self._note_seen(key)
        except Exception as e:
            log_error("paintEvent", e)
        p.end()

    def _note_seen(self, key):
        if not self.stats.see(key) or key in ("idle", "peek_awake"):
            return
        name = next((n for k, n, _ in C.CODEX if k == key), None)
        if name:
            QTimer.singleShot(2600, lambda: self._say_codex(name))

    def _say_codex(self, name, tries=0):
        """图鉴解锁提示: 等她这句说完再冒, 不盖掉别的台词(最多等 30 秒)"""
        if self.bubble.isVisible() and tries < 15:
            QTimer.singleShot(2000, lambda: self._say_codex(name, tries + 1))
            return
        self.say(f"📖 图鉴解锁:「{name}」", duration=3.0, tone="info")

    def stand_key(self):
        """这一帧画哪张图: 状态本身, 或这会儿该换的脸(FACES); 插件的 expr() 最后还能再换"""
        st = self.state
        key = st
        if self._expr is not None and self._expr_state == st:
            key = self._expr
        elif st == "idle" and not self.walk:
            if self.gaze and abs(self.face) > 0.5:
                g = self.gaze * (1 if self.face > 0 else -1)
                key = "look" if g > 0 else "look_left"
            elif self.focusing():
                key = "focus"
            elif self.stats.hunger < HUNGRY_FACE:
                key = "hungry"
        elif st == "angry" and self.sulking():
            key = "sulk"
        elif st == DRAG_STATE and (self._dragging or self.fling):
            key = "held"
        if self._ix.plugins:
            k2 = self._ix.expr(key, st)
            if k2 in self.frames:
                key = k2
        return key

    def _paint_stand(self, p: QPainter, t: float):
        key = self.stand_key()
        pm = self._scaled(key)
        st = self.state
        dt = t - self.state_since
        if st == "sleep":
            breath = 1.0 + 0.022 * math.sin(2 * math.pi * t / 4.6)
            bob = 0.0
        else:
            breath = 1.0 + 0.016 * math.sin(2 * math.pi * t / 3.2)
            bob = 2.2 * math.sin(2 * math.pi * t / 4.4)
        dx, rot, sy_extra = 0.0, 0.0, 0.0
        if self.walk:
            bob = self.char_h * 0.035 * abs(math.sin(math.pi * self._walk_phase))
        elif st == "surprised":
            bob -= 9 * math.exp(-dt * 7) * abs(math.cos(dt * 14))
        elif st == "angry":
            dx = 3.0 * math.sin(dt * 40) * math.exp(-dt * 2.2)
        elif st in ("happy", "love"):
            bob -= 3.5 * abs(math.sin(2 * math.pi * dt / 0.7))
        elif st == "cheer":
            bob -= 6.0 * abs(math.sin(2 * math.pi * dt / 0.5))
        elif st == "wave":
            rot = 6.0 * math.sin(2 * math.pi * dt * 1.6)
        elif st in ("look", "look_left"):
            sgn = 1 if st == "look" else -1
            rot = 4.0 * sgn * math.sin(math.pi * min(1.0, dt / 0.6))
            dx = 3.0 * sgn * math.sin(math.pi * min(1.0, dt / 0.6))
        elif st == "dizzy":                   # 摇摇晃晃站不稳
            amp = 1.0 if t < self._dizzy_until else 0.6
            rot = amp * (9.0 * math.sin(dt * 5.2) + 3.0 * math.sin(dt * 11.0))
            dx = amp * (9.0 * math.sin(dt * 2.6) + 2.5 * math.sin(dt * 7.3))
            sy_extra = -0.02 * amp * abs(math.sin(dt * 5.2))
        elif st == "stretch":
            sy_extra = 0.07 * math.sin(math.pi * min(1.0, dt / 1.6))
        elif st == "yawn":
            sy_extra = 0.04 * math.sin(math.pi * min(1.0, dt / 3.0))
            rot = -3.0 * math.sin(math.pi * min(1.0, dt / 3.0))
        elif st == "eat":
            sy_extra = -0.025 * abs(math.sin(dt * 9))
            rot = 1.5 * math.sin(dt * 9)
        elif st == "content":
            rot = 3.0 * math.sin(dt * 3.2)
            sy_extra = -0.02 * abs(math.sin(dt * 3.2))
        elif st == "shy":
            rot = -4.0 * math.sin(math.pi * min(1.0, dt / 0.5))
            dx = -2.0 * math.sin(dt * 2.5)
        pm, ix_dx = self._ix.paint(key, pm, t)
        dx += ix_dx
        jump = 0.0
        if not self._landed:
            u = max(0.0, min(1.0, (t - self.jump_start) / self.jump_dur))
            jump = self.jump_h * 4 * u * (1 - u)
        sy = max(0.82, min(1.12, breath * (1 + self.sq) + sy_extra))
        sx = (1.0 + (1 - breath) * 0.5) * (1 - self.sq * 0.6)
        hs = 1.0 + 0.03 * self.hover_k
        sx *= hs; sy = min(1.12, sy * hs)
        sx *= math.cos(math.radians(self.spin_angle))              # 绕竖轴转圈(背面即镜像)
        sx *= self.face if abs(self.face) > 0.04 else 0.04          # 走路转身
        rot = max(-12.0, min(12.0, rot + self.tilt))
        cx = self.pad_x + self.char_w / 2 + dx
        foot_y = self.height() - PAD
        # 地面影子: 跳得越高越小越淡
        k = max(0.3, 1.0 - (jump + bob * 0.5) / max(1.0, self.char_h * 0.25))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(30, 40, 70, int(38 * k)))
        p.drawEllipse(QPointF(cx, foot_y - 1), self.char_w * 0.30 * k, 5 * k)
        p.save()
        p.translate(cx, foot_y - bob - jump)
        p.rotate(rot)
        p.scale(sx, sy)
        p.drawPixmap(QPointF(-self.char_w / 2, -self.char_h), pm)
        p.restore()
        return key

    def _peek_key(self):
        st = self.state
        if st == "sleep":
            return "peek_sleep"
        if st in ("happy", "cheer", "wave", "content", "eat", "love"):
            return "peek_happy"
        if st in ("surprised", "angry", "dizzy"):
            return "peek_surprised"
        return "peek_awake"

    def _paint_peek(self, p: QPainter, t: float):
        """探头: pop 由 _step_peek 平滑; 害羞时整个缩回墙里; 果冻挤压以墙为锚"""
        sleeping = self.state == "sleep"
        key = self._peek_key()
        pm = self._peek_pixmap(key)
        pw, ph = self._peek_wh()
        dt = t - self.state_since
        sway = 0.0 if sleeping else 2.0 * math.sin(2 * math.pi * t / 4.4)
        if self.state == "surprised":
            sway -= 5 * math.exp(-dt * 7) * abs(math.cos(dt * 14))
        elif self.state == "angry":
            sway += 3.0 * math.sin(dt * 40) * math.exp(-dt * 2.2)
        elif self.state in ("happy", "cheer", "love"):
            sway -= 3.5 * abs(math.sin(2 * math.pi * dt / 0.7))
        elif self.state == "dizzy":
            sway += 4.0 * math.sin(dt * 6)
        duck_target = 1.0 if t < self._duck_until else 0.0
        self._duck_k = getattr(self, "_duck_k", 0.0)
        self._duck_k += (duck_target - self._duck_k) * 0.25
        depth = pw if self.edge in ("left", "right") else ph
        hide = PEEK_HIDE * (1.0 - self.pop) + self._duck_k * depth * 0.45
        if self.edge == "left":
            ox, oy = -hide, PEEK_TPAD + sway
            anchor = QPointF(0, PEEK_TPAD + ph / 2)
        elif self.edge == "right":
            ox, oy = hide, PEEK_TPAD + sway
            anchor = QPointF(pw, PEEK_TPAD + ph / 2)
        else:
            ox, oy = PEEK_TPAD + sway, -hide
            anchor = QPointF(PEEK_TPAD + pw / 2, 0)
        p.save()
        s = 1.0 + 0.5 * self.sq
        if sleeping:
            s *= 1.0 + 0.012 * math.sin(2 * math.pi * t / 4.6)
        p.translate(anchor); p.scale(s, s); p.translate(-anchor)
        tilt = PEEK_TILT * (1.0 if not sleeping else -0.7) * (-1.0 if self.edge == "right" else 1.0)
        tilt *= 1.0 - 0.55 * self.pop
        p.translate(anchor); p.rotate(tilt); p.translate(-anchor)
        p.drawPixmap(QPointF(ox, oy), pm)
        p.restore()
        return key

    # ----- 插件接口 -----
    # dlc/interactions 的插件只用这一节、docs/接口规范.md 里列出的方法和字段; 下划线开头的随时可能改。
    @property
    def dragging(self):
        """正被鼠标拖着"""
        return self._dragging

    @property
    def landed(self):
        """不在跳跃的半空中"""
        return self._landed

    def activities(self):
        """她此刻在做的事: ACTIVITIES 里的名字, 加上插件 busy() 报上来的名字(此时也带 "plugin")"""
        now = time.monotonic()
        a = set()
        if not self.isVisible():
            a.add("hidden")
        if self.state == "sleep":
            a.add("sleep")
        if self.edge:
            a.add("edge")
        if self._dragging:
            a.add("drag")
        if self.fling:
            a.add("fling")
        if self._throw is not None:
            a.add("throw")
        if self.walk:
            a.add("walk")
        if self._bchase is not None:
            a.add("chase")
        if self.sneaking():
            a.add("sneak")
        if self.food_fx is not None:
            a.add("food_fx")
        if self.sulking():
            a.add("sulk")
        if self.spin_rem > 0 or self._spin_overspin or self._spin_posting:
            a.add("spin")
        if self.state == "dizzy" or now < self._dizzy_until:
            a.add("dizzy")
        if self.danika.active():
            a.add("danika")
        if self.butterfly.active():
            a.add("butterfly")
        if any(p is not None and p.isVisible() for p in self._panels.values()):
            a.add("panel")
        if self.focusing():
            a.add("focus")
        if self.link_busy:
            a.add("link")
        if self._away_since is not None:
            a.add("away")
        extra = self._ix.busy()
        if extra:
            a.update(extra)
            a.add("plugin")
        return a

    def can_auto(self, what, acts=None):
        """自动行为 what(AUTO 表里的名字)现在能不能做; acts 可传入已算好的 activities()"""
        states, blockers = AUTO[what]
        if states is not None and self.state not in states:
            return False
        return not (blockers & (self.activities() if acts is None else acts))

    def _tune(self, name, value, **ctx):
        """决策点问插件要不要调这个参数(TUNABLE 里的名字); 没插件, 或插件给的值不合法, 就用原值"""
        if not self._ix.plugins:
            return value
        kind, lo, hi = TUNABLE[name]
        v = self._ix.tune(name, value, ctx)
        if kind == "float":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
                return value
            return max(lo, min(hi, float(v)))
        if kind == "bool":
            return v if isinstance(v, bool) else value
        if kind == "weights":
            if not isinstance(v, dict):
                return value
            out = dict(value)
            for k, wv in v.items():
                if k in out and isinstance(wv, (int, float)) and not isinstance(wv, bool) and wv == wv:
                    out[k] = max(lo, min(hi, float(wv)))
            return out if sum(out.values()) > 0 else value
        if kind == "lines":
            lines = [x for x in v if isinstance(x, str) and x.strip()] if isinstance(v, (list, tuple)) else []
            return lines or value
        if kind == "text":
            return v.strip()[:hi] if isinstance(v, str) and v.strip() else value
        return value

    def plugin_status(self):
        """插件报上来的状态行(status_text), 给托盘提示和右键卡片用"""
        return self._ix.status_lines()

    def approach_cursor(self):
        """自己走到鼠标旁边(停在光标一侧, 不挡住它), 路上不说话; 到了推 walk_end(kind=approach)。
        探头 / 睡着 / 闹别扭 / 设置里关了散步 / 已经在旁边了 -> 不走。返回是否出发"""
        if self.edge or self.state == "sleep" or self.sulking() or not self.cfg["walk"]:
            return False
        cur = QCursor.pos()
        side = -1 if cur.x() > self.x() + self.width() / 2 else 1          # 停在她来的那一侧
        tx = cur.x() + side * self.char_w * 0.75 - self.width() / 2
        ty = cur.y() - (self.pad_top() + self.char_h * 0.62)
        scr = QGuiApplication.screenAt(cur) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        tx = max(g.left() - self.pad_x, min(tx, g.left() + g.width() - self.width() + self.pad_x))
        ty = max(g.top() - self.hop_room, min(ty, g.top() + g.height() - self.height() + PAD))
        if math.hypot(tx - self.x(), ty - self.y()) < self.char_w * 0.6:
            return False
        return self.start_walk(QPointF(tx, ty), kind="approach")

    def clear_sulk(self):
        """悄悄结束闹别扭(不说话、不加好感、不推 makeup); 要台词和 +1 走原版消气"""
        self._sulk_until = 0.0
        self._sulk_calm = 0
        self._throws.clear()

    def force_struggle(self, stage, since=None):
        """拖着时直接按挣扎阶段 stage(1 轻 / 2 重 / 3 激烈 / 4 风元素)抖, 不说那一阶段的台词;
        since: 从什么时刻算起(决定抖动相位, 每帧传同一个值才会连续抖)。stage 0 = 像刚拿起一样重新计时。"""
        if not self._dragging:
            return
        since = time.monotonic() if since is None else since
        if stage <= 0:
            self._drag_hold_t0 = since
            self._drag_hold_stage = 0
            return
        start = (DRAG_HOLD_SEC, DRAG_HOLD_HARD, DRAG_HOLD_FURY, DRAG_HOLD_WIND)[min(int(stage), 4) - 1]
        self._drag_hold_t0 = since - start - 0.2
        self._drag_hold_stage = 4          # 标成都喊过了: 只抖不说

    def take_over_spin(self, dizzy_sec, refuse_sec, now=None):
        """插件接管这一轮转太多的收尾(原版的「晕完生气」不再执行):
        之后 dizzy_sec 秒内算晕着, refuse_sec 秒内拦住下一次转圈, 拦完说一句缓过来了。"""
        now = time.monotonic() if now is None else now
        self._spin_angry_done = True
        self._spin_overspin = False
        self._spin_posting = False
        self._spin_meter = 0.0
        self._spin_stage = 0
        self._dizzy_extra = 0
        self._dizzy_until = now + dizzy_sec
        self._spin_refuse_until = now + refuse_sec
        self._spin_recover_at = self._spin_refuse_until + 0.3
        self._spin_recover_sure = True

    def clear_dizzy(self):
        """马上不晕了(表情不动, 要换表情另调 set_state)"""
        self._dizzy_until = 0.0

    def screen_rect(self) -> QRect:
        """她所在屏幕的可用区域(扣掉任务栏)"""
        return self._screen_for_rect(self._normal_visible_rect()).availableGeometry()

    def live_snapshot(self):
        """DLC 只读快照. 不改任何状态; 字段失败就省略, 不往外抛。"""
        now = time.monotonic()
        try:
            feeds = sum(1 for t in self._feeds if now - t <= FEED_WINDOW)
        except Exception:
            feeds = 0
        hunger = 0.0
        affection = 0.0
        level_n, level_name = 1, ""
        try:
            hunger = float(self.stats.hunger)
            affection = float(self.stats.affection)
            lv = self.stats.level()
            level_n, level_name = int(lv[0]), str(lv[1])
        except Exception:
            pass
        bubble = ""
        try:
            if self.bubble.isVisible():
                bubble = str(self.bubble.text or "")
        except Exception:
            pass
        grok = ""
        try:
            if self.link is not None:
                grok = str(self.link.status_text() or "")
        except Exception:
            pass
        return {
            "v": 1,
            "ok": True,
            "app": APP_NAME,
            "ts": time.time(),
            "state": self.state,
            "hunger": round(hunger, 2),
            "affection": round(affection, 2),
            "level": level_name,
            "level_n": level_n,
            "x": int(self.x()),
            "y": int(self.y()),
            "w": int(self.width()),
            "h": int(self.height()),
            "size": self.size_key,
            "visible": bool(self.isVisible()),
            "edge": self.edge,
            "mood": round(self.mood.value, 1),
            "mood_band": self.mood.key,
            "sleeping": self.state == "sleep",
            "dragging": bool(self._dragging),
            "spinning": self.spin_rem > 0.5,
            "dizzy": self.state == "dizzy" or now < self._dizzy_until,
            "sulking": self.sulking(),
            "focusing": self.focusing(),
            "fling": self.fling is not None,
            "walk": self.walk is not None,
            "bubble": bubble,
            "feeds_window": int(feeds),
            "full": hunger >= FULL_HUNGER or feeds >= FEED_MAX,
            "spin_refuse": now < self._spin_refuse_until,
            "link_busy": bool(self.link_busy),
            "grok": grok,
        }

    # ----- DLC 事件推送 / say (live 协议 v2) -----
    def emit_event(self, _ev, **data):
        """推一条事件给互动插件(on_event)和已订阅的 DLC。都没有就立刻返回; 绝不往外抛。
        (事件名参数叫 _ev, 好让附加字段能用 name/key 等名字)"""
        try:
            self.mood.on_event(_ev, data)             # 心情先算(可能接着推一个 "mood" 换档事件)
        except Exception as e:
            log_error("mood " + str(_ev), e)
        if self._ix.plugins:
            self._ix.event(_ev, data)
        hub = self._live
        if hub is None or not hub.subs:
            return
        try:
            hub.broadcast(_ev, data)
        except Exception as e:
            log_error("emit_event " + str(_ev), e)

    def live_say(self, text, expr=None, sec=4.0):
        """DLC 让她冒一句气泡(+可选临时表情)。成功返回 None, 否则返回错误码。
        不改好感/饱食, 不算互动; 忙的时候(睡/拖/转/丢/晕/达妮卡)不打断。"""
        if not self.isVisible():
            return "hidden"
        if self.cfg["mute"]:
            return "muted"
        if not self.can_auto("live_say"):
            return "busy"
        text = str(text or "").strip()[:60]
        if not text:
            return "empty"
        sec = max(1.0, min(8.0, float(sec)))
        face = expr if expr in LIVE_SAY_FACES else None
        state = FACES[face] if face else expr
        if (state in LIVE_SAY_EXPRS and expr in self.real_frames and not self.sulking()
                and self.state in LIVE_SAY_CALM):
            self.set_state(state, sec, expr=face)   # 临时表情: 到点由 revert_timer 回 idle(闹别扭则回 angry)
        dur = max(sec, min(8.0, 1.6 + len(text) * 0.12))
        self.say(text, force=True, duration=dur, src="dlc")
        return None

    def closeEvent(self, e):
        self.cfg["x"], self.cfg["y"] = self.x(), self.y()
        self.cfg.save()
        self.stats.save(force=True)
        self.bubble.hide()
        self.fx.clear()
        self.butterfly.stop()
        super().closeEvent(e)


# ---------------- 单实例 ----------------
def single_instance_key():
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return f"VesnaPet-{user}-single"


def try_notify_existing(key) -> bool:
    sock = QLocalSocket()
    sock.connectToServer(key)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def make_server(key, on_show):
    QLocalServer.removeServer(key)
    server = QLocalServer()
    if not server.listen(key):
        return None

    def _on_conn():
        c = server.nextPendingConnection()
        if c:
            c.waitForReadyRead(200)
            c.readAll()
            c.disconnectFromServer()
            on_show()
    server.newConnection.connect(_on_conn)
    return server


# ---------------- 应用 ----------------
class PetApp:
    def __init__(self, app: QApplication, config: Config = None, link_kwargs: dict = None, stats: Stats = None):
        self.app = app
        self.cfg = config or Config()
        self.window = PetWindow(self.cfg, link_kwargs=link_kwargs, stats=stats)
        self.window.quit_requested.connect(self.quit)
        icon = self._make_icon()
        app.setWindowIcon(icon)
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(icon, app)
            self.tray.setToolTip("薇斯纳桌宠")
            self.tray.setContextMenu(self.window.tray_menu)
            self.tray.activated.connect(self._tray_activated)
            self.tray.show()
        self.window.tray = self.tray            # 供实时 tooltip 使用
        self.window.show()
        self.live = LiveHub(self.window, log_fn=log_error)
        try:
            if self.live.start():
                self.window._live = self.live        # 事件推送(v2); 没订阅者时 emit_event 零开销
        except Exception as e:
            log_error("LiveHub init", e)

    def _make_icon(self) -> QIcon:
        ico = ASSET_DIR / "vesna.ico"
        if ico.exists():
            i = QIcon(str(ico))
            if not i.isNull():
                return i
        pm = QPixmap(str(ASSET_DIR / "idle.png"))
        pm = pm.copy(alpha_bbox(pm.toImage()))
        s = max(pm.width(), pm.height())
        sq = QPixmap(s, s); sq.fill(Qt.transparent)
        p = QPainter(sq); p.drawPixmap((s - pm.width()) // 2, (s - pm.height()) // 2, pm); p.end()
        return QIcon(sq.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger, QSystemTrayIcon.MiddleClick):
            self.window.reveal(greet=False)

    def quit(self):
        w = self.window
        self.cfg["x"], self.cfg["y"] = w.x(), w.y()
        self.cfg.save()
        w.stats.save(force=True)
        w._live = None
        try:
            if self.live is not None:
                self.live.stop()
                self.live = None
        except Exception as e:
            log_error("quit live stop", e)
        try:
            if w.link is not None:
                w.link.stop()
        except Exception as e:
            log_error("quit link stop", e)
        if self.tray:
            self.tray.hide()
        for p in list(w._panels.values()):
            try:
                p.hide()
            except Exception:
                pass
        w.butterfly.stop()
        try:
            w.danika.stop()
        except Exception:
            pass
        w.bubble.hide()
        w.fx.clear()
        w.hide()
        self.app.quit()


def _install_crash_logging():
    def hook(et, ev, tb):
        try:
            import traceback as _tb
            log_error("uncaught: " + "".join(_tb.format_exception(et, ev, tb))[-1500:])
        except Exception:
            pass
    sys.excepthook = hook
    if sys.stderr is None:
        try:
            p = error_log_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            sys.stderr = open(p, "a", encoding="utf-8", buffering=1)
        except Exception:
            pass


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    danika_test = "--danika-test" in argv
    if danika_test:
        argv = [a for a in argv if a != "--danika-test"]
    _install_crash_logging()
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    key = single_instance_key()
    if (not danika_test) and try_notify_existing(key):
        print("VesnaPet 已在运行, 退出本次启动。")
        return 0
    pet = PetApp(app)
    if danika_test:
        pet.window._danika_test = True
        # 用独立 key 避免挡住日常实例; 测试实例跳过单实例服务也可
        QTimer.singleShot(900, pet.window._run_danika_test)
    else:
        server = make_server(key, pet.window.reveal)
        if server is None:
            print("警告: 单实例服务启动失败", file=sys.stderr)
        app._single_server = server
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
