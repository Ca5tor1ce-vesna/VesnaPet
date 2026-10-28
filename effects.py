# -*- coding: utf-8 -*-
"""VesnaPet 程序化特效层: 粒子(爱心/星星/彩纸/汗滴/zZ/!?/怒气/尘土/眩晕星/小旋风/音符/emoji/魔法阵...)
+ Grok 工作徽章 + 专注计时 HUD。独立的透明、鼠标穿透小窗, 跟随桌宠; 没有内容时自动隐藏。"""
import math
import random

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

INK = QColor("#34487A")
PINK = ("#FF6F91", "#FF8FAB", "#FF5C8A")
GOLD = ("#FFD24D", "#FFC24B", "#FFE98A")
CONFETTI = ("#FF6F91", "#FFC75F", "#7BD389", "#5EC8F2", "#B39CFF", "#FF9671")
MAX_PARTICLES = 180
FAMILIES = ["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "sans-serif"]
EMOJI = ["Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji"] + FAMILIES


def ease_out_back(x):
    c1 = 1.70158
    x = max(0.0, min(1.0, x)) - 1.0
    return 1 + (c1 + 1) * x ** 3 + c1 * x ** 2


def _star_path(r, n=5, inner=0.45):
    path = QPainterPath()
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * inner
        a = -math.pi / 2 + i * math.pi / n
        pt = QPointF(math.cos(a) * rr, math.sin(a) * rr)
        if i == 0:
            path.moveTo(pt)
        else:
            path.lineTo(pt)
    path.closeSubpath()
    return path


def _heart_path(s):
    path = QPainterPath()
    path.moveTo(0, s * 0.45)
    path.cubicTo(-s * 1.1, -s * 0.25, -s * 0.5, -s * 1.0, 0, -s * 0.42)
    path.cubicTo(s * 0.5, -s * 1.0, s * 1.1, -s * 0.25, 0, s * 0.45)
    path.closeSubpath()
    return path


def _drop_path(s):
    path = QPainterPath()
    path.moveTo(0, -s)
    path.cubicTo(s * 0.9, 0, s * 0.8, s, 0, s)
    path.cubicTo(-s * 0.8, s, -s * 0.9, 0, 0, -s)
    return path


def _font(px, bold=True, emoji=False):
    f = QFont()
    f.setFamilies(EMOJI if emoji else FAMILIES)
    f.setPixelSize(max(6, int(px)))
    f.setBold(bold)
    return f


def _outlined_text(p, text, px, color):
    path = QPainterPath()
    path.addText(0, 0, _font(px), text)
    path.translate(-path.boundingRect().center())
    p.setPen(QPen(QColor("white"), 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPath(path)


def _draw_pm(p, pm, d):
    """以原点为中心平滑画一张 d×d 逻辑像素的图(食物图标)"""
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    p.drawPixmap(QRectF(-d / 2, -d / 2, d, d), pm, QRectF(pm.rect()))


class Particle:
    __slots__ = ("kind", "x", "y", "vx", "vy", "g", "drag", "life", "age", "size", "color",
                 "rot", "vrot", "cx", "cy", "r", "ang", "w", "text", "sx", "sy", "tx", "ty", "pm")

    def __init__(self, kind, x, y, **kw):
        self.kind, self.x, self.y = kind, x, y
        self.vx = self.vy = self.g = self.drag = 0.0
        self.life, self.age, self.size = 1.0, 0.0, 8.0
        self.color = QColor(INK)
        self.rot = self.vrot = 0.0
        self.cx = self.cy = self.r = self.ang = self.w = 0.0
        self.text = ""
        self.sx = self.sy = self.tx = self.ty = 0.0
        self.pm = None               # 可选图片(食物图标); 有就画图, 没有就画 text
        for k, v in kw.items():
            setattr(self, k, v)


def _spawn(kind, x, y, bias, text=""):
    R = random.uniform
    bx, by = bias
    if kind == "note":
        return Particle(kind, x + R(-16, 16), y, vx=R(-20, 20) + bx * 0.2, vy=R(-70, -50), life=R(1.3, 1.8),
                        size=R(14, 18), color=QColor(random.choice(("#34487A", "#E2557F", "#2C9F8F"))),
                        text=random.choice(("\u266a", "\u266b")))
    if kind == "emoji":
        return Particle(kind, x + R(-10, 10), y, vx=R(-18, 18) + bx * 0.2, vy=R(-60, -40), life=R(1.4, 1.8),
                        size=R(18, 22), text=text or "\u2728", vrot=R(-30, 30))
    if kind == "food":
        # (x, y) = 嘴的位置; 从头顶上方抛进嘴里
        return Particle(kind, x, y - 120, sx=x + R(-30, 30), sy=y - 130, tx=x, ty=y, life=0.75, size=30,
                        text=text or "\U0001F370")
    if kind == "crumb":
        return Particle(kind, x + R(-10, 10), y + R(-4, 4), vx=R(-60, 60), vy=R(-120, -40), g=520, life=R(0.5, 0.8),
                        size=R(1.8, 3.2), color=QColor(random.choice(("#E8B86A", "#F4D8A0", "#C98A4A"))))
    if kind == "steam":
        return Particle(kind, x + R(-26, 26), y, vx=R(-12, 12), vy=R(-60, -35), drag=0.6, life=R(0.9, 1.4),
                        size=R(6, 10), color=QColor(255, 255, 255))
    if kind == "ring":
        return Particle(kind, x, y, life=1.1, size=R(10, 14),
                        color=QColor(random.choice(("#4FC7B5", "#F5C451", "#FF8FB1"))))
    if kind == "drop":
        return Particle(kind, x + R(-6, 6), y, vx=R(-10, 10), vy=R(-40, -30), g=60, life=1.4, size=9,
                        color=QColor("#7CC8F5"))
    if kind == "puff":
        return Particle(kind, x + R(-6, 6), y, vx=R(-50, 50), vy=R(-12, -3), drag=4.0, life=R(0.3, 0.45),
                        size=R(2.5, 4.5), color=QColor(185, 188, 205))
    if kind == "heart":
        return Particle(kind, x + R(-14, 14), y + R(-6, 6), vx=R(-25, 25) + bx * 0.3, vy=R(-95, -60) + by * 0.3,
                        g=-8, life=R(1.1, 1.6), size=R(6, 10), color=QColor(random.choice(PINK)), vrot=R(-40, 40))
    if kind in ("sparkle", "star"):
        a, sp = R(0, 2 * math.pi), R(70, 170)
        return Particle(kind, x, y, vx=math.cos(a) * sp + bx, vy=math.sin(a) * sp + by, drag=3.5,
                        life=R(0.5, 0.9), size=R(4, 8) if kind == "sparkle" else R(5, 9),
                        color=QColor(random.choice(GOLD)), vrot=R(-180, 180))
    if kind == "confetti":
        return Particle(kind, x + R(-10, 10), y, vx=R(-200, 200) + bx, vy=R(-380, -220) + by, g=560, drag=1.2,
                        life=R(1.4, 2.0), size=R(4, 7), color=QColor(random.choice(CONFETTI)),
                        rot=R(0, 360), vrot=R(-540, 540))
    if kind == "sweat":
        return Particle(kind, x + R(-8, 8), y, vx=R(-50, 50) + bx * 0.2, vy=R(-70, -40), g=320, life=0.9,
                        size=R(5, 7), color=QColor("#6EC6F5"))
    if kind == "z":
        return Particle(kind, x, y, vx=R(10, 22) + bx * 0.1, vy=R(-30, -22), life=2.2, size=R(9, 12))
    if kind == "excl":
        return Particle(kind, x, y, life=1.4, size=18, color=QColor("#F07A3C"))
    if kind == "quest":
        return Particle(kind, x, y, life=1.3, size=17, color=QColor(INK))
    if kind == "anger":
        return Particle(kind, x, y, life=1.1, size=11, color=QColor("#E5484D"))
    if kind == "dust":
        return Particle(kind, x + R(-12, 12), y, vx=R(-80, 80), vy=R(-18, -4), drag=3.0, life=R(0.4, 0.6),
                        size=R(4, 7), color=QColor(170, 170, 185))
    if kind == "gust":
        # 小旋风: bias = 吹出去的方向*速度
        sp = math.hypot(bx, by) or 1.0
        return Particle(kind, x + R(-12, 12), y + R(-26, 26), vx=bx * R(0.75, 1.3), vy=by * R(0.75, 1.3) + R(-25, 25),
                        drag=1.4, life=R(0.7, 1.0), size=R(16, 28), rot=math.degrees(math.atan2(by, bx)) if sp else 0.0,
                        color=QColor(random.choice(("#4FC7B5", "#7FDCCB", "#A8E6DA"))))
    if kind == "orbit":
        return Particle(kind, x, y, cx=x, cy=y, r=R(30, 42), ang=R(0, 2 * math.pi), w=R(4, 6), life=3.0,
                        size=R(5, 7), color=QColor(random.choice(GOLD)))
    return None


class FxLayer(QWidget):
    MARGIN = 150

    def __init__(self):
        flags = (Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                 | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        super().__init__(None, flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.parts = []
        self.badge = None            # None / "search" / "code" / "cmd" / "other"
        self.badge_pos = QPointF()
        self.hud = None              # None / dict(text, frac, paused)
        self.hud_pos = QPointF()
        self.clock = 0.0
        self._topmost = True

    def set_topmost(self, on):
        on = bool(on)
        if on != self._topmost:
            self._topmost = on
            vis = self.isVisible()
            self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
            if vis:
                self.show()

    def emit(self, kind, x, y, n=1, bias=(0.0, 0.0), text="", pm=None):
        for _ in range(int(n)):
            p = _spawn(kind, float(x), float(y), bias, text)
            if p is not None:
                if pm is not None and kind in ("food", "emoji"):
                    p.pm = pm
                self.parts.append(p)
        if len(self.parts) > MAX_PARTICLES:
            del self.parts[:len(self.parts) - MAX_PARTICLES]

    def clear(self):
        self.parts.clear()
        self.badge = None
        self.hud = None
        self.hide()

    def step(self, dt, host: QRect, alive=True):
        if not alive:
            if self.isVisible() or self.parts:
                self.clear()
            return
        self.clock += dt
        for p in self.parts:
            p.age += dt
            if p.kind == "orbit":
                p.ang += p.w * dt
                p.x = p.cx + math.cos(p.ang) * p.r
                p.y = p.cy + math.sin(p.ang) * p.r * 0.35
            elif p.kind == "food":
                u = min(1.0, p.age / p.life)
                p.x = p.sx + (p.tx - p.sx) * u
                p.y = p.sy + (p.ty - p.sy) * u * u - 26 * math.sin(math.pi * u)
            else:
                p.vy += p.g * dt
                if p.drag:
                    f = math.exp(-p.drag * dt)
                    p.vx *= f
                    p.vy *= f
                p.x += p.vx * dt
                p.y += p.vy * dt
            p.rot += p.vrot * dt
        self.parts = [p for p in self.parts if p.age < p.life]
        if self.parts or self.badge or self.hud:
            m = self.MARGIN
            g = host.adjusted(-m, -m, m, m)
            if self.geometry() != g:
                self.setGeometry(g)
            if not self.isVisible():
                self.show()
                self.raise_()
            self.update()
        elif self.isVisible():
            self.hide()

    # ----- 绘制 -----
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.translate(-self.x(), -self.y())          # 粒子使用全局坐标
        for part in self.parts:
            try:
                self._paint_particle(p, part)
            except Exception:
                pass
        if self.badge:
            try:
                self._paint_badge(p, self.badge, self.badge_pos)
            except Exception:
                pass
        if self.hud:
            try:
                self._paint_hud(p, self.hud, self.hud_pos)
            except Exception:
                pass
        p.end()

    def _paint_particle(self, p, q):
        k = q.age / q.life
        alpha = 1.0 if k < 0.6 else max(0.0, (1 - k) / 0.4)
        pop = 0.3 + 0.7 * ease_out_back(min(1.0, q.age / 0.16))
        p.save()
        p.setOpacity(alpha)
        p.translate(q.x, q.y)
        kind = q.kind
        if kind == "heart":
            p.rotate(q.rot)
            p.scale(pop, pop)
            p.setPen(QPen(q.color.darker(125), 1.2))
            p.setBrush(q.color)
            p.drawPath(_heart_path(q.size))
        elif kind in ("sparkle", "star", "orbit"):
            p.rotate(q.rot)
            p.scale(pop, pop)
            if kind == "sparkle":
                p.setPen(Qt.NoPen)
                p.setBrush(q.color)
                p.drawPath(_star_path(q.size, 4, 0.3))
            else:
                p.setPen(QPen(QColor("#C98A12"), 1.0))
                p.setBrush(q.color)
                p.drawPath(_star_path(q.size))
        elif kind == "confetti":
            p.rotate(q.rot)
            p.scale(1.0, abs(math.cos(q.age * 9)) + 0.15)
            p.setPen(Qt.NoPen)
            p.setBrush(q.color)
            p.drawRect(QRectF(-q.size / 2, -q.size / 4, q.size, q.size / 2))
        elif kind == "sweat":
            p.setPen(QPen(QColor("#3A8FC7"), 1.0))
            p.setBrush(q.color)
            p.drawPath(_drop_path(q.size))
        elif kind == "z":
            p.scale(pop, pop)
            _outlined_text(p, "z", q.size * (1 + 0.5 * k), QColor(INK))
        elif kind in ("excl", "quest"):
            bounce = -6 * abs(math.sin(q.age * 9)) * math.exp(-q.age * 2)
            p.translate(0, bounce)
            p.scale(pop, pop)
            _outlined_text(p, "!" if kind == "excl" else "?", q.size, q.color)
        elif kind == "anger":
            s = q.size * pop * (1 + 0.15 * math.sin(q.age * 20))
            p.setPen(QPen(q.color, 2.6, Qt.SolidLine, Qt.RoundCap))
            for a in (0, 90, 180, 270):
                p.save()
                p.rotate(a + 45)
                path = QPainterPath()
                path.moveTo(s * 0.25, s * 0.9)
                path.quadTo(s * 0.3, s * 0.3, s * 0.9, s * 0.25)
                p.drawPath(path)
                p.restore()
        elif kind == "gust":
            p.rotate(q.rot)
            s = q.size * (0.7 + 0.6 * k)
            p.setPen(QPen(q.color, 2.4, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.moveTo(-s, 0)
            path.cubicTo(-s * 0.3, -s * 0.05, s * 0.35, -s * 0.05, s * 0.55, -s * 0.32)
            path.cubicTo(s * 0.75, -s * 0.6, s * 0.3, -s * 0.72, s * 0.22, -s * 0.42)
            p.drawPath(path)
            p.setPen(QPen(q.color.lighter(115), 1.6, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(-s * 0.8, s * 0.28), QPointF(s * 0.2, s * 0.28))
        elif kind in ("dust", "puff"):
            p.setPen(Qt.NoPen)
            p.setBrush(q.color)
            r = q.size * (0.6 + k)
            p.drawEllipse(QPointF(0, 0), r, r * 0.7)
        elif kind == "note":
            p.rotate(12 * math.sin(q.age * 6))
            p.scale(pop, pop)
            _outlined_text(p, q.text, q.size, q.color)
        elif kind == "emoji":
            p.rotate(q.rot)
            p.scale(pop, pop)
            if q.pm is not None:
                _draw_pm(p, q.pm, 40)
            else:
                p.setFont(_font(q.size, False, True))
                p.drawText(QRectF(-q.size, -q.size, q.size * 2, q.size * 2), Qt.AlignCenter, q.text)
        elif kind == "food":
            u = q.age / q.life
            s = 1.0 if u < 0.75 else max(0.2, 1 - (u - 0.75) * 3)
            p.setOpacity(1.0)
            p.rotate(-25 * math.sin(u * math.pi * 2))
            p.scale(s * pop, s * pop)
            if q.pm is not None:
                _draw_pm(p, q.pm, 40)
            else:
                p.setFont(_font(q.size, False, True))
                p.drawText(QRectF(-q.size, -q.size, q.size * 2, q.size * 2), Qt.AlignCenter, q.text)
        elif kind == "crumb":
            p.setPen(Qt.NoPen)
            p.setBrush(q.color)
            p.drawEllipse(QPointF(0, 0), q.size, q.size)
        elif kind == "steam":
            p.setPen(QPen(QColor(160, 170, 190, 160), 1.2))
            p.setBrush(QColor(255, 255, 255, 220))
            r = q.size * (0.6 + 0.8 * k)
            p.drawEllipse(QPointF(0, 0), r, r * 0.8)
        elif kind == "ring":
            r = 18 + 70 * (1 - (1 - k) ** 3)
            p.setOpacity(alpha * (1 - k))
            p.setPen(QPen(q.color, 2.4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(0, 0), r, r * 0.42)
            p.setPen(QPen(q.color.lighter(130), 1.2))
            p.drawEllipse(QPointF(0, 0), r * 0.78, r * 0.33)
            p.setPen(Qt.NoPen)
            p.setBrush(q.color)
            for i in range(6):
                a = q.age * 2.2 + i * math.pi / 3
                pt = QPointF(math.cos(a) * r, math.sin(a) * r * 0.42)
                p.drawPath(_star_path(3.2, 4, 0.35).translated(pt))
        elif kind == "drop":
            p.scale(pop, pop)
            p.setPen(QPen(QColor("#3A8FC7"), 1.2))
            p.setBrush(q.color)
            p.drawPath(_drop_path(q.size))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 220))
            p.drawEllipse(QPointF(-q.size * 0.25, q.size * 0.25), q.size * 0.18, q.size * 0.18)
        p.restore()

    def _paint_hud(self, p, hud, pos):
        """专注计时胶囊: 番茄 + mm:ss + 细进度条"""
        text = hud.get("text", "")
        frac = max(0.0, min(1.0, hud.get("frac", 0.0)))
        paused = hud.get("paused", False)
        f = _font(12, True)
        p.save()
        fm = QFontMetricsF(f)
        w = fm.horizontalAdvance(text) + 46
        h = 26.0
        r = QRectF(pos.x() - w / 2, pos.y() - h / 2, w, h)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(30, 45, 90, 38))
        p.drawRoundedRect(r.translated(0, 2.5), h / 2, h / 2)
        p.setBrush(QColor(255, 255, 255, 245))
        p.setPen(QPen(QColor(46, 63, 110, 30), 1))
        p.drawRoundedRect(r, h / 2, h / 2)
        bar = QRectF(r.left() + 12, r.bottom() - 5, r.width() - 24, 2.6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#EDF1F8"))
        p.drawRoundedRect(bar, 1.3, 1.3)
        g = QLinearGradient(bar.topLeft(), bar.topRight())
        g.setColorAt(0, QColor("#4FC7B5"))
        g.setColorAt(1, QColor("#B6A4F5"))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * frac, bar.height()), 1.3, 1.3)
        p.setFont(_font(13, False, True))
        p.setPen(QColor("#2E3F6E"))
        bob = 0 if paused else 1.2 * math.sin(self.clock * 4)
        p.drawText(QRectF(r.left() + 6, r.top() - 2 + bob, 24, h - 2), Qt.AlignCenter,
                   "\u23f8" if paused else "\U0001F345")
        p.setFont(f)
        p.setPen(QColor("#8A94AD") if paused else QColor("#2E3F6E"))
        p.drawText(QRectF(r.left() + 30, r.top() - 2, w - 36, h - 2), Qt.AlignVCenter | Qt.AlignLeft, text)
        p.restore()

    def _paint_badge(self, p, kind, pos):
        t = self.clock
        p.save()
        p.translate(pos.x(), pos.y() + 2.5 * math.sin(t * 3))
        r = 15
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawEllipse(QPointF(1.5, 2.5), r, r)
        p.setPen(QPen(INK, 2.2))
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(0, 0), r, r)
        pen = QPen(INK, 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        if kind == "search":
            a = 0.25 * math.sin(t * 4)
            p.rotate(math.degrees(a))
            p.drawEllipse(QPointF(-2, -2), 5.5, 5.5)
            p.drawLine(QPointF(2.2, 2.2), QPointF(7, 7))
        elif kind == "code":
            p.drawPolyline([QPointF(-4, -5), QPointF(-9, 0), QPointF(-4, 5)])
            p.drawPolyline([QPointF(4, -5), QPointF(9, 0), QPointF(4, 5)])
            p.drawLine(QPointF(1.8, -6), QPointF(-1.8, 6))
        elif kind == "cmd":
            p.drawPolyline([QPointF(-8, -4), QPointF(-3, 0), QPointF(-8, 4)])
            if int(t * 2.5) % 2 == 0:
                p.drawLine(QPointF(0, 5), QPointF(7, 5))
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(INK)
            for i in range(3):
                dy = -3 * max(0.0, math.sin(t * 6 - i * 0.8))
                p.drawEllipse(QPointF(-6 + i * 6, dy), 2.2, 2.2)
        p.restore()
