# -*- coding: utf-8 -*-
"""薇斯纳 UI 组件: 配色取自角色(薄荷绿/冬契藏青/星辉金/樱花粉), 全部 QPainter 自绘。"""
import math
import sys
import time
from pathlib import Path

from PySide6.QtCore import (QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt,
                            QVariantAnimation, Signal)
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QGuiApplication, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import QAbstractButton, QWidget

# ---------------- 配色 ----------------
INK = QColor("#2E3F6E")
INK2 = QColor("#5B6A92")
MUTED = QColor("#9AA5C0")
LINE = QColor(46, 63, 110, 26)
MINT = QColor("#4FC7B5")
MINT_D = QColor("#2C9F8F")
MINT_L = QColor("#E3F7F3")
PINK = QColor("#FF8FB1")
PINK_D = QColor("#E2557F")
PINK_L = QColor("#FFE9F0")
GOLD = QColor("#F5C451")
GOLD_D = QColor("#D99A1E")
GOLD_L = QColor("#FFF5DA")
LAV = QColor("#B6A4F5")
SKY = QColor("#7CC8F5")
CARD = QColor("#FFFFFF")
CARD2 = QColor("#F7FBFF")
ORANGE = QColor("#F0883E")

FAMILIES = ["Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Segoe UI", "sans-serif"]
EMOJI_FAMILIES = ["Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji"] + FAMILIES


def font(px=13, weight=QFont.Normal):
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPixelSize(int(px))
    f.setWeight(weight)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def emoji_font(px=20):
    f = QFont()
    f.setFamilies(EMOJI_FAMILIES)
    f.setPixelSize(int(px))
    return f


# 食物图标 assets/food/food_<key>.png (256×256 透明); 找不到就返回 None, 调用方退回 emoji
FOOD_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets" / "food"
_food_pix = {}
FOOD_ICON_EXTRA = {}     # key -> 食物包里的图标路径(优先于 assets/food), 由 food_packs 登记


def food_pixmap(key, size):
    """平滑缩放到 size 逻辑像素(按屏幕 DPR 出高清图); 缺图/坏图返回 None。结果缓存。"""
    try:
        app = QGuiApplication.instance()
        dpr = max(1.0, float(app.devicePixelRatio())) if app is not None else 1.0
    except Exception:
        dpr = 1.0
    ck = (key, int(size), dpr)
    if ck not in _food_pix:
        pm = None
        try:
            src = QPixmap()
            for p in (FOOD_ICON_EXTRA.get(key), FOOD_DIR / f"food_{key}.png"):
                if p and Path(p).exists():
                    src = QPixmap(str(p))
                    if not src.isNull():
                        break
            if not src.isNull():
                px = max(1, int(round(size * dpr)))
                pm = src.scaled(px, px, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pm.setDevicePixelRatio(dpr)
        except Exception:
            pm = None
        _food_pix[ck] = pm
    return _food_pix[ck]


def mix(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t), int(a.alpha() + (b.alpha() - a.alpha()) * t))


def alpha(c: QColor, a: int) -> QColor:
    c = QColor(c)
    c.setAlpha(a)
    return c


def ease_out_back(x):
    c1 = 1.70158
    x = max(0.0, min(1.0, x)) - 1.0
    return 1 + (c1 + 1) * x ** 3 + c1 * x ** 2


# ---------------- 阴影 ----------------
_SHADOW_CACHE = {}


def shadow_image(w, h, radius, blur=14, color=QColor(30, 45, 90, 70)):
    """模糊圆角矩形阴影(缩小再放大 = 便宜的高斯近似)"""
    key = (w, h, radius, blur, color.rgba())
    img = _SHADOW_CACHE.get(key)
    if img is not None:
        return img
    W, H = w + blur * 2, h + blur * 2
    s = 0.2
    small = QImage(max(1, int(W * s)), max(1, int(H * s)), QImage.Format_ARGB32_Premultiplied)
    small.fill(Qt.transparent)
    p = QPainter(small)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(QRectF(blur * s, blur * s, w * s, h * s), radius * s, radius * s)
    p.end()
    mid = small.scaled(int(W * 0.45), int(H * 0.45), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    img = mid.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    if len(_SHADOW_CACHE) > 64:
        _SHADOW_CACHE.clear()
    _SHADOW_CACHE[key] = img
    return img


def draw_card(p: QPainter, rect: QRectF, radius=18, blur=16, tint=None, border=LINE, shadow=QColor(30, 45, 90, 60)):
    img = shadow_image(int(rect.width()), int(rect.height()), radius, blur, shadow)
    p.drawImage(QPointF(rect.x() - blur, rect.y() - blur + 4), img)
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0, tint or CARD2)
    g.setColorAt(0.35, CARD)
    g.setColorAt(1, CARD)
    p.setPen(QPen(border, 1))
    p.setBrush(g)
    p.drawRoundedRect(rect, radius, radius)


def gem_path(c: QPointF, r: float) -> QPainterPath:
    """菱形宝石(呼应头冠宝石)"""
    path = QPainterPath()
    path.moveTo(c.x(), c.y() - r)
    path.lineTo(c.x() + r * 0.72, c.y())
    path.lineTo(c.x(), c.y() + r)
    path.lineTo(c.x() - r * 0.72, c.y())
    path.closeSubpath()
    return path


def draw_gem(p: QPainter, c: QPointF, r: float, color=MINT):
    p.save()
    p.setPen(QPen(color.darker(135), max(1.0, r * 0.16)))
    g = QLinearGradient(QPointF(c.x(), c.y() - r), QPointF(c.x(), c.y() + r))
    g.setColorAt(0, color.lighter(150))
    g.setColorAt(1, color)
    p.setBrush(g)
    p.drawPath(gem_path(c, r))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 190))
    p.drawPath(gem_path(QPointF(c.x() - r * 0.18, c.y() - r * 0.3), r * 0.28))
    p.restore()


def sparkle_path(c: QPointF, r: float) -> QPainterPath:
    path = QPainterPath()
    for i in range(8):
        rr = r if i % 2 == 0 else r * 0.24
        a = -math.pi / 2 + i * math.pi / 4
        pt = QPointF(c.x() + math.cos(a) * rr, c.y() + math.sin(a) * rr)
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    path.closeSubpath()
    return path


def butterfly_path(w: float, flap: float = 1.0) -> tuple:
    """返回 (上翅, 下翅) 路径, 以身体中心为原点; flap ∈ [0.15, 1] 为翅膀横向展开度"""
    up = QPainterPath()
    up.moveTo(0, -1)
    up.cubicTo(w * 0.35 * flap, -w * 0.95, w * 1.05 * flap, -w * 0.75, w * 0.92 * flap, -w * 0.18)
    up.cubicTo(w * 0.85 * flap, w * 0.05, w * 0.3 * flap, w * 0.02, 0, 0)
    lo = QPainterPath()
    lo.moveTo(0, 0)
    lo.cubicTo(w * 0.45 * flap, w * 0.05, w * 0.8 * flap, w * 0.35, w * 0.55 * flap, w * 0.68)
    lo.cubicTo(w * 0.35 * flap, w * 0.85, w * 0.08 * flap, w * 0.45, 0, 0.5)
    return up, lo


def draw_butterfly(p: QPainter, c: QPointF, w: float, flap: float, colors=(PINK, MINT), outline=INK, white_rim=True):
    up, lo = butterfly_path(w, flap)
    p.save()
    p.translate(c)
    for sx in (1, -1):
        p.save()
        p.scale(sx, 1)
        for path, col in ((lo, colors[1]), (up, colors[0])):
            if white_rim:
                p.setPen(QPen(QColor("white"), max(2.0, w * 0.22), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(QColor("white"))
                p.drawPath(path)
            g = QRadialGradient(QPointF(0, 0), w * 1.1)
            g.setColorAt(0, QColor(255, 255, 255))
            g.setColorAt(0.35, col.lighter(115))
            g.setColorAt(1, col)
            p.setPen(QPen(outline, max(1.0, w * 0.07), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(g)
            p.drawPath(path)
        p.restore()
    p.setPen(Qt.NoPen)
    p.setBrush(outline)
    p.drawRoundedRect(QRectF(-w * 0.07, -w * 0.42, w * 0.14, w * 0.9), w * 0.07, w * 0.07)
    p.setPen(QPen(outline, max(1.0, w * 0.05), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(0, -w * 0.4), QPointF(-w * 0.22, -w * 0.72))
    p.drawLine(QPointF(0, -w * 0.4), QPointF(w * 0.22, -w * 0.72))
    p.restore()


# ---------------- 动画小工具 ----------------
class Anim:
    """把 0..1 的值平滑地动画到目标, 驱动 widget.update()"""

    def __init__(self, widget, ms=160, curve=QEasingCurve.OutCubic):
        self.v = 0.0
        self._w = widget
        self._a = QVariantAnimation(widget)
        self._a.setDuration(ms)
        self._a.setEasingCurve(curve)
        self._a.valueChanged.connect(self._set)

    def _set(self, v):
        self.v = float(v)
        self._w.update()

    def to(self, target):
        self._a.stop()
        self._a.setStartValue(self.v)
        self._a.setEndValue(float(target))
        self._a.start()

    def jump(self, v):
        self._a.stop()
        self.v = float(v)


# ---------------- 卡片窗口 ----------------
class CardWindow(QWidget):
    """无边框圆角卡片(带柔和阴影), 头部可拖动, 淡入+上浮出现"""
    closed = Signal()
    M = 18           # 阴影留白

    def __init__(self, w, h, title="", topmost=True, popup=False, drag_h=56):
        flags = Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        flags |= (Qt.Popup if popup else Qt.Tool)
        if topmost and not popup:
            flags |= Qt.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.title = title
        self._drag_h = drag_h
        self._drag = None
        self.resize(w + 2 * self.M, h + 2 * self.M)
        self._show_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._show_anim.setDuration(170)
        self._show_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pos_anim = QPropertyAnimation(self, b"pos", self)
        self._pos_anim.setDuration(240)
        self._pos_anim.setEasingCurve(QEasingCurve.OutBack)
        self.radius = 20
        self.tint = CARD2

    def body(self) -> QRectF:
        return QRectF(self.M, self.M, self.width() - 2 * self.M, self.height() - 2 * self.M)

    def content_rect(self) -> QRect:
        b = self.body().toRect()
        return b.adjusted(16, self._drag_h, -16, -14)

    def set_topmost(self, on):
        if self.windowFlags() & Qt.Popup:
            return
        vis = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(on))
        if vis:
            self.show()

    def popup_at(self, pos: QPoint):
        """pos = 卡片主体左上角(全局); 自动夹在屏幕内"""
        x, y = pos.x() - self.M, pos.y() - self.M
        scr = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        x = max(g.left() - self.M + 4, min(x, g.left() + g.width() - self.width() + self.M - 4))
        y = max(g.top() - self.M + 4, min(y, g.top() + g.height() - self.height() + self.M - 4))
        self.setWindowOpacity(0.0)
        self.move(x, y + 10)
        self.show()
        self.raise_()
        self._show_anim.stop()
        self._show_anim.setStartValue(0.0)
        self._show_anim.setEndValue(1.0)
        self._show_anim.start()
        self._pos_anim.stop()
        self._pos_anim.setStartValue(QPoint(x, y + 10))
        self._pos_anim.setEndValue(QPoint(x, y))
        self._pos_anim.start()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.closed.emit()

    def paint_bg(self, p: QPainter):
        draw_card(p, self.body(), self.radius, 16, self.tint)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        self.paint_bg(p)
        self.paint_content(p)
        p.end()

    def paint_content(self, p: QPainter):
        pass

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < self.M + self._drag_h:
            self._drag = e.globalPosition().toPoint() - self.pos()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag)
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag = None
        super().mouseReleaseEvent(e)


class CloseButton(QAbstractButton):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self._h = Anim(self, 120)

    def enterEvent(self, e):
        self._h.to(1)

    def leaveEvent(self, e):
        self._h.to(0)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self._h.v
        p.setPen(Qt.NoPen)
        p.setBrush(mix(QColor(46, 63, 110, 14), PINK_L, k))
        p.drawEllipse(QRectF(2, 2, 24, 24))
        p.setPen(QPen(mix(INK2, PINK_D, k), 2, Qt.SolidLine, Qt.RoundCap))
        p.translate(14, 14)
        p.rotate(90 * k)
        p.drawLine(QPointF(-4.5, -4.5), QPointF(4.5, 4.5))
        p.drawLine(QPointF(4.5, -4.5), QPointF(-4.5, 4.5))
        p.end()


# ---------------- 按钮 ----------------
class Button(QAbstractButton):
    """kind: primary(薄荷) / pink / soft(浅底) / ghost(描边) / danger"""
    STYLES = {
        "primary": (MINT, MINT_D, QColor("white")),
        "pink": (PINK, PINK_D, QColor("white")),
        "gold": (GOLD, GOLD_D, QColor("#5A3D00")),
        "soft": (QColor("#EEF2FA"), QColor("#DEE5F3"), INK),
        "ghost": (QColor(255, 255, 255, 0), MINT_L, INK2),
        "danger": (QColor("#FFF0F0"), QColor("#FFDCDC"), QColor("#D9534F")),
    }

    def __init__(self, text, parent=None, kind="primary", icon="", h=34, px=13):
        super().__init__(parent)
        self.setText(text)
        self.kind = kind
        self.icon = icon
        self.px = px
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(h)
        fm = QFontMetrics(font(px, QFont.DemiBold))
        w = fm.horizontalAdvance(text) + 30 + (22 if icon else 0)
        self.setMinimumWidth(w)
        self._h = Anim(self, 140)
        self._p = Anim(self, 90)

    def sizeHint(self):
        return QSize(self.minimumWidth(), self.height())

    def enterEvent(self, e):
        self._h.to(1)
        if callable(getattr(self, "on_hover", None)):
            self.on_hover(True)

    def leaveEvent(self, e):
        self._h.to(0)
        if callable(getattr(self, "on_hover", None)):
            self.on_hover(False)

    def mousePressEvent(self, e):
        self._p.to(1)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._p.to(0)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        base, hov, fg = self.STYLES.get(self.kind, self.STYLES["primary"])
        k, pk = self._h.v, self._p.v
        r = QRectF(self.rect()).adjusted(1, 1 + pk, -1, -1)
        rad = r.height() / 2
        if not self.isEnabled():
            p.setOpacity(0.45)
        if self.kind in ("primary", "pink", "gold"):
            p.setPen(Qt.NoPen)
            p.setBrush(alpha(hov, int(60 * (1 - pk))))
            p.drawRoundedRect(r.translated(0, 2.5 - pk), rad, rad)
            g = QLinearGradient(r.topLeft(), r.bottomLeft())
            g.setColorAt(0, mix(base.lighter(112), hov, k * 0.3))
            g.setColorAt(1, mix(base, hov, k * 0.6))
            p.setBrush(g)
            p.drawRoundedRect(r, rad, rad)
            p.setPen(QPen(QColor(255, 255, 255, 90), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), rad - 1, rad - 1)
        elif self.kind == "ghost":
            p.setPen(QPen(mix(QColor(46, 63, 110, 40), MINT, k), 1.2))
            p.setBrush(mix(base, hov, k))
            p.drawRoundedRect(r, rad, rad)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(mix(base, hov, k))
            p.drawRoundedRect(r, rad, rad)
        p.setPen(fg if self.kind != "ghost" else mix(INK2, MINT_D, k))
        p.setFont(font(self.px, QFont.DemiBold))
        if self.icon:
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(self.text())
            total = tw + 22
            x0 = r.center().x() - total / 2
            p.setFont(emoji_font(self.px + 2))
            p.drawText(QRectF(x0, r.top(), 20, r.height()), Qt.AlignCenter, self.icon)
            p.setFont(font(self.px, QFont.DemiBold))
            p.drawText(QRectF(x0 + 22, r.top(), tw + 2, r.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        else:
            p.drawText(r, Qt.AlignCenter, self.text())
        p.end()


class IconTile(QAbstractButton):
    """emoji 图标 + 文字的方块按钮(悬停上浮, 底色变薄荷)"""

    def __init__(self, emoji, text, parent=None, size=(64, 70), tint=MINT_L, badge="", sub=""):
        super().__init__(parent)
        self.emoji, self.label, self.tint, self.badge, self.sub = emoji, text, tint, badge, sub
        self.pixmap = None          # 有图就画图(如食物图标), 否则画 emoji
        self.setFixedSize(*size)
        self.setCursor(Qt.PointingHandCursor)
        self._h = Anim(self, 150)
        self._p = Anim(self, 80)

    def enterEvent(self, e):
        self._h.to(1)
        if callable(getattr(self, "on_hover", None)):
            self.on_hover(True)

    def leaveEvent(self, e):
        self._h.to(0)
        if callable(getattr(self, "on_hover", None)):
            self.on_hover(False)

    def mousePressEvent(self, e):
        self._p.to(1)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._p.to(0)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k, pk = self._h.v, self._p.v
        W = self.width()
        if not self.isEnabled():
            p.setOpacity(0.4)
        lift = -2.0 * k + 1.0 * pk
        isz = min(W - 14, 44)
        box = QRectF((W - isz) / 2, 4 + lift, isz, isz)
        p.setPen(Qt.NoPen)
        if k > 0.01:
            p.setBrush(alpha(MINT_D, int(40 * k)))
            p.drawRoundedRect(box.translated(0, 3), 14, 14)
        g = QLinearGradient(box.topLeft(), box.bottomLeft())
        g.setColorAt(0, mix(QColor("#F5F7FC"), self.tint.lighter(104), k))
        g.setColorAt(1, mix(QColor("#EDF1F9"), self.tint, k))
        p.setBrush(g)
        p.drawRoundedRect(box, 14, 14)
        p.setPen(QPen(QColor(255, 255, 255, 200), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        p.setFont(emoji_font(int(isz * 0.5)))
        p.setPen(INK)
        p.save()
        c = box.center()
        s = 1.0 + 0.08 * k - 0.06 * pk
        p.translate(c)
        p.scale(s, s)
        if self.pixmap is not None and not self.pixmap.isNull():
            d = isz + 8                               # 比底框略大一点, 像盛在盘子上
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.drawPixmap(QRectF(-d / 2, -d / 2 - 1, d, d), self.pixmap, QRectF(self.pixmap.rect()))
        else:
            p.drawText(QRectF(-isz / 2, -isz / 2, isz, isz), Qt.AlignCenter, self.emoji)
        p.restore()
        if self.badge:
            p.setFont(emoji_font(11))
            p.drawText(QRectF(box.right() - 14, box.top() - 4, 18, 18), Qt.AlignCenter, self.badge)
        px = 12
        while px > 9 and QFontMetrics(font(px, QFont.DemiBold)).horizontalAdvance(self.label) > W - 2:
            px -= 1                                   # 名字太长就缩小一点
        p.setFont(font(px, QFont.DemiBold))
        p.setPen(mix(INK2, MINT_D, k))
        ty = box.bottom() + 3
        p.drawText(QRectF(-4, ty, W + 8, 16), Qt.AlignHCenter | Qt.AlignTop, self.label)
        if self.sub:
            p.setFont(font(10, QFont.Normal))
            p.setPen(getattr(self, "sub_color", None) or MUTED)
            p.drawText(QRectF(0, ty + 15, W, 14), Qt.AlignHCenter | Qt.AlignTop, self.sub)
        p.end()


class Toggle(QAbstractButton):
    def __init__(self, parent=None, checked=False, color=MINT):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(42, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.color = color
        self._k = Anim(self, 180, QEasingCurve.OutBack)
        self._k.jump(1.0 if checked else 0.0)
        self.toggled.connect(lambda on: self._k.to(1.0 if on else 0.0))

    def set_silent(self, on):
        self.blockSignals(True)
        self.setChecked(bool(on))
        self.blockSignals(False)
        self._k.jump(1.0 if on else 0.0)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = max(0.0, min(1.0, self._k.v))
        r = QRectF(1, 2, 40, 20)
        p.setPen(Qt.NoPen)
        p.setBrush(mix(QColor("#DCE2EE"), self.color, k))
        p.drawRoundedRect(r, 10, 10)
        x = 3 + 20 * self._k.v
        p.setBrush(QColor(20, 30, 60, 40))
        p.drawEllipse(QRectF(x, 5, 16, 16))
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, 4, 16, 16))
        if k > 0.5:
            p.setPen(QPen(alpha(self.color, int(255 * (k - 0.5) * 2)), 1.6, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x + 5, 12.2), QPointF(x + 7.3, 14.4))
            p.drawLine(QPointF(x + 7.3, 14.4), QPointF(x + 11.2, 9.6))
        p.end()


class Segmented(QWidget):
    """分段选择(滑块指示), options: [(key, label)]"""
    changed = Signal(object)

    def __init__(self, options, current=None, parent=None, h=28, px=12):
        super().__init__(parent)
        self.options = list(options)
        self.idx = 0
        for i, (k, _) in enumerate(self.options):
            if k == current:
                self.idx = i
        self.px = px
        fm = QFontMetrics(font(px, QFont.DemiBold))
        self.seg_w = max(fm.horizontalAdvance(l) for _, l in self.options) + 22
        self.setFixedSize(self.seg_w * len(self.options) + 6, h)
        self.setCursor(Qt.PointingHandCursor)
        self._x = Anim(self, 220, QEasingCurve.OutBack)
        self._x.jump(self.idx)
        self._hover = -1
        self.setMouseTracking(True)

    def value(self):
        return self.options[self.idx][0]

    def set_value(self, key):
        for i, (k, _) in enumerate(self.options):
            if k == key:
                self.idx = i
                self._x.jump(i)
                self.update()

    def mouseMoveEvent(self, e):
        h = int((e.position().x() - 3) // self.seg_w)
        if h != self._hover:
            self._hover = h
            self.update()

    def leaveEvent(self, e):
        self._hover = -1
        self.update()

    def mousePressEvent(self, e):
        i = int((e.position().x() - 3) // self.seg_w)
        if 0 <= i < len(self.options) and i != self.idx:
            self.idx = i
            self._x.to(i)
            self.changed.emit(self.options[i][0])

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        H = self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#EEF2FA"))
        p.drawRoundedRect(QRectF(0, 0, self.width(), H), H / 2, H / 2)
        x = 3 + self._x.v * self.seg_w
        p.setBrush(QColor(30, 45, 90, 25))
        p.drawRoundedRect(QRectF(x, 4, self.seg_w, H - 6), (H - 6) / 2, (H - 6) / 2)
        p.setBrush(QColor("white"))
        p.drawRoundedRect(QRectF(x, 3, self.seg_w, H - 6), (H - 6) / 2, (H - 6) / 2)
        p.setFont(font(self.px, QFont.DemiBold))
        for i, (_, label) in enumerate(self.options):
            r = QRectF(3 + i * self.seg_w, 0, self.seg_w, H)
            p.setPen(MINT_D if i == self.idx else (INK if i == self._hover else INK2))
            p.drawText(r, Qt.AlignCenter, label)
        p.end()


class Bar(QWidget):
    """渐变进度条; 值变化时平滑过渡"""

    def __init__(self, parent=None, colors=(MINT, PINK), h=10, value=0.0):
        super().__init__(parent)
        self.colors = colors
        self.setFixedHeight(h)
        self._v = Anim(self, 500)
        self._v.jump(value)

    def set_value(self, v, animate=True):
        v = max(0.0, min(1.0, float(v)))
        if animate:
            self._v.to(v)
        else:
            self._v.jump(v)
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        H = self.height()
        r = QRectF(0, 0, self.width(), H)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#EDF1F8"))
        p.drawRoundedRect(r, H / 2, H / 2)
        w = max(H, self.width() * self._v.v) if self._v.v > 0.001 else 0
        if w:
            fr = QRectF(0, 0, w, H)
            g = QLinearGradient(fr.topLeft(), fr.topRight())
            g.setColorAt(0, self.colors[0])
            g.setColorAt(1, self.colors[1])
            p.setBrush(g)
            p.drawRoundedRect(fr, H / 2, H / 2)
            p.setBrush(QColor(255, 255, 255, 80))
            p.drawRoundedRect(QRectF(2, 1.5, max(0, w - 4), H * 0.38), H * 0.2, H * 0.2)
        p.end()


class Ring(QWidget):
    """圆环进度(专注计时)"""

    def __init__(self, parent=None, d=180):
        super().__init__(parent)
        self.setFixedSize(d, d)
        self.frac = 0.0
        self.big = "25:00"
        self.small = "准备好了吗"
        self.colors = (MINT, LAV)
        self.running = False

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        d = self.width()
        pw = d * 0.075
        r = QRectF(pw, pw, d - 2 * pw, d - 2 * pw)
        p.setPen(QPen(QColor("#EDF1F8"), pw, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(r)
        if self.frac > 0.0005:
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, self.colors[0])
            g.setColorAt(1, self.colors[1])
            p.setPen(QPen(g, pw, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(r, 90 * 16, -int(360 * 16 * min(1.0, self.frac)))
            a = math.radians(90 - 360 * self.frac)
            c = r.center()
            dot = QPointF(c.x() + math.cos(a) * r.width() / 2, c.y() - math.sin(a) * r.height() / 2)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("white"))
            p.drawEllipse(dot, pw * 0.32, pw * 0.32)
        # 中心: 小宝石 + 时间
        c = r.center()
        if self.running:
            t = time.monotonic()
            draw_gem(p, QPointF(c.x(), c.y() - d * 0.25 + 2 * math.sin(t * 2.4)), d * 0.04, MINT)
        else:
            draw_gem(p, QPointF(c.x(), c.y() - d * 0.25), d * 0.04, MUTED)
        p.setPen(INK)
        p.setFont(font(int(d * 0.2), QFont.Bold))
        p.drawText(QRectF(0, c.y() - d * 0.16, d, d * 0.26), Qt.AlignCenter, self.big)
        p.setPen(INK2)
        p.setFont(font(max(11, int(d * 0.07)), QFont.Normal))
        p.drawText(QRectF(0, c.y() + d * 0.11, d, d * 0.12), Qt.AlignCenter, self.small)
        p.end()


class Tabs(QWidget):
    """胶囊标签页, 指示条滑动"""
    changed = Signal(int)

    def __init__(self, labels, parent=None, h=34):
        super().__init__(parent)
        self.labels = list(labels)
        self.idx = 0
        self.setFixedHeight(h)
        self.setCursor(Qt.PointingHandCursor)
        self._x = Anim(self, 260, QEasingCurve.OutBack)
        self._hover = -1
        self.setMouseTracking(True)

    def _seg(self):
        return self.width() / max(1, len(self.labels))

    def set_index(self, i, animate=True):
        if 0 <= i < len(self.labels):
            self.idx = i
            self._x.to(i) if animate else (self._x.jump(i), self.update())
            self.changed.emit(i)

    def mousePressEvent(self, e):
        i = int(e.position().x() // self._seg())
        if i != self.idx:
            self.set_index(i)

    def mouseMoveEvent(self, e):
        h = int(e.position().x() // self._seg())
        if h != self._hover:
            self._hover = h
            self.update()

    def leaveEvent(self, e):
        self._hover = -1
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        H, sw = self.height(), self._seg()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#EEF2FA"))
        p.drawRoundedRect(QRectF(0, 0, self.width(), H), H / 2, H / 2)
        x = self._x.v * sw
        r = QRectF(x + 3, 3, sw - 6, H - 6)
        p.setBrush(QColor(30, 45, 90, 22))
        p.drawRoundedRect(r.translated(0, 1.5), r.height() / 2, r.height() / 2)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor("#FFFFFF"))
        g.setColorAt(1, QColor("#F7FFFD"))
        p.setBrush(g)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setFont(font(13, QFont.DemiBold))
        for i, l in enumerate(self.labels):
            rr = QRectF(i * sw, 0, sw, H)
            p.setPen(MINT_D if i == self.idx else (INK if i == self._hover else INK2))
            p.drawText(rr, Qt.AlignCenter, l)
        p.end()


class Label(QWidget):
    """轻量文字(可选 emoji 前缀), 避免 QLabel 的样式表"""

    def __init__(self, text="", parent=None, px=13, color=INK, weight=QFont.Normal, align=Qt.AlignLeft | Qt.AlignVCenter,
                 h=None, wrap=False):
        super().__init__(parent)
        self.text, self.px, self.color, self.weight, self.align, self.wrap = text, px, color, weight, align, wrap
        fm = QFontMetrics(font(px, weight))
        self.setFixedHeight(h or fm.height() + 4)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_text(self, t):
        if t != self.text:
            self.text = t
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setPen(self.color)
        p.setFont(font(self.px, self.weight))
        flags = self.align | (Qt.TextWordWrap if self.wrap else 0)
        p.drawText(self.rect(), flags, self.text)
        p.end()


def face_avatar(src: QPixmap, d: int, dpr: float = 1.0, ring=MINT, center=(0.45, 0.47), zoom=0.38) -> QPixmap:
    """从立绘裁圆形头像; center/zoom 为相对原图(已裁 alpha 框)比例"""
    D = int(d * dpr)
    out = QPixmap(D, D)
    out.fill(Qt.transparent)
    if src is None or src.isNull():
        return out
    w, h = src.width(), src.height()
    side = min(w, h) * zoom * 2
    cx, cy = w * center[0], h * center[1]
    sr = QRectF(cx - side / 2, cy - side / 2, side, side)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    rim = max(2.0, D * 0.05)
    g = QLinearGradient(0, 0, D, D)
    g.setColorAt(0, ring.lighter(120))
    g.setColorAt(1, PINK)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawEllipse(QRectF(0, 0, D, D))
    p.setBrush(QColor("#FFF8EE"))
    inner = QRectF(rim, rim, D - 2 * rim, D - 2 * rim)
    p.drawEllipse(inner)
    clip = QPainterPath()
    clip.addEllipse(inner)
    p.setClipPath(clip)
    p.drawPixmap(inner, src, sr)
    p.end()
    out.setDevicePixelRatio(dpr)
    return out
