# -*- coding: utf-8 -*-
"""小蝴蝶来访: 绕着薇斯纳飞, 偶尔停在头冠上; 鼠标点中算"抓到", 冲太快它会躲。"""
import math
import sys
from pathlib import Path
import random
import time

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QTransform, QImage, QPixmap
from PySide6.QtWidgets import QWidget

from ui_kit import LAV, MINT, PINK, SKY, GOLD, draw_butterfly

PALETTES = [(PINK, MINT), (MINT, SKY), (LAV, PINK), (GOLD, PINK), (SKY, LAV)]


class Butterfly(QWidget):
    caught = Signal()
    landed = Signal()
    dodged = Signal()
    gone = Signal()
    SIZE = 64

    def __init__(self, host, log_fn=None):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        super().__init__(None, flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._log = log_fn
        self._chase_land = False      # 被追到后更愿意落在头上, 且停得更久
        self.sit_for = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.host = host
        self.mode = "off"
        self.pos_f = QPointF()
        self.vel = QPointF()
        self.phase = 0.0
        self.t_mode = 0.0
        self.t_total = 0.0
        self.wander_end = 0.0
        self.dodges = 0
        self.colors = PALETTES[0]
        self.wing = 15.0
        self._seed = random.random() * 100
        self._last = time.monotonic()
        self._cursor_prev = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    # ----- 控制 -----
    def active(self):
        return self.mode != "off"

    def start(self):
        if self.active():
            return
        hp = self.host.head_point()
        scr = QGuiApplication.screenAt(hp.toPoint()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        side = random.choice(("left", "right", "top"))
        if side == "left":
            self.pos_f = QPointF(g.left() - 30, g.top() + random.uniform(0.15, 0.6) * g.height())
        elif side == "right":
            self.pos_f = QPointF(g.right() + 30, g.top() + random.uniform(0.15, 0.6) * g.height())
        else:
            self.pos_f = QPointF(g.left() + random.uniform(0.2, 0.8) * g.width(), g.top() - 30)
        self.vel = QPointF()
        self.colors = random.choice(PALETTES)
        self.wing = random.uniform(13, 16)
        self.mode = "enter"
        self.t_mode = 0.0
        self.t_total = 0.0
        self.dodges = 0
        self._chase_land = False
        self.wander_end = random.uniform(22, 38)
        self._last = time.monotonic()
        self._place()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(self.host.cfg["topmost"]))
        self.show()
        self.timer.start(16)

    def land_now(self, chased=True):
        """薇斯纳追到它了: 马上飞去头冠上落下。"""
        if self.mode in ("enter", "wander") and not self.host.edge:
            self._chase_land = bool(chased)
            self.mode = "land"
            self.t_mode = 0.0
            return True
        return False

    def leave(self):
        if self.mode in ("off", "leave"):
            return
        self.mode = "leave"
        self.t_mode = 0.0

    def stop(self):
        self.mode = "off"
        self.timer.stop()
        self.hide()

    # ----- 运动 -----
    def _landing_point(self):
        h = self.host
        if h.edge:
            return h.head_point()
        return QPointF(h.x() + h.width() / 2 + h.char_w * 0.12, h.y() + h.pad_top() + h.char_h * 0.06)

    def _offscreen_target(self):
        scr = QGuiApplication.screenAt(self.pos_f.toPoint()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        c = g.center()
        dx = -1 if self.pos_f.x() < c.x() else 1
        return QPointF(g.left() - 120 if dx < 0 else g.right() + 120, self.pos_f.y() - 200)

    def _tick(self):
        try:
            now = time.monotonic()
            dt = max(0.0, min(0.05, now - self._last))
            self._last = now
            self._step(dt)
        except Exception as e:
            try:
                if self._log:
                    self._log("butterfly_tick", e)
            except Exception:
                pass
            self.stop()
            self.gone.emit()

    def _step(self, dt):
        if not self.host.isVisible() and self.mode not in ("leave", "off"):
            self.leave()
        self.t_mode += dt
        self.t_total += dt
        s = self._seed + self.t_total
        flying = True
        if self.mode in ("enter", "wander"):
            hp = self.host.head_point()
            r = 110 + 40 * math.sin(s * 0.7)
            ang = s * 0.9 + 1.7 * math.sin(s * 0.33)
            target = QPointF(hp.x() + math.cos(ang) * r, hp.y() - 40 + math.sin(ang * 1.3) * r * 0.55)
            speed = 210 if self.mode == "enter" else 120
            if self.mode == "enter" and (self.pos_f - hp).manhattanLength() < 260:
                self.mode = "wander"
                self.t_mode = 0.0
            if self.mode == "wander":
                if self.t_mode > self.wander_end:
                    self.leave()
                elif self.t_mode > 6 and random.random() < dt * 0.06 and not self.host.edge:
                    self.mode = "land"
                    self.t_mode = 0.0
        elif self.mode == "land":
            target = self._landing_point()
            speed = 90
            d = target - self.pos_f
            if math.hypot(d.x(), d.y()) < 5:
                self.mode = "sit"
                self.t_mode = 0.0
                self.sit_for = random.uniform(8.0, 12.0) if self._chase_land else random.uniform(4.5, 8.0)
                self.landed.emit()
        elif self.mode == "sit":
            flying = False
            self.pos_f = self._landing_point()
            self.vel = QPointF()
            target = self.pos_f
            speed = 0
            if self.t_mode > self.sit_for or self.host._dragging or self.host.fling:
                self._chase_land = False
                self.mode = "wander"
                self.t_mode = 0.0
                self.wander_end = random.uniform(8, 16)
                self.vel = QPointF(random.uniform(-80, 80), -140)
        else:  # leave
            target = self._offscreen_target()
            speed = 240
        if self.mode != "sit":
            d = target - self.pos_f
            dist = math.hypot(d.x(), d.y())
            desired = QPointF(d.x() / dist * speed, d.y() / dist * speed) if dist > 1 else QPointF()
            k = min(1.0, dt * 2.6)
            self.vel = self.vel + (desired - self.vel) * k
            # 扑翅的上下起伏
            flutter = QPointF(18 * math.sin(s * 5.1), 34 * math.sin(s * 7.3))
            self.pos_f = self.pos_f + (self.vel + flutter) * dt
            self._dodge(dt)
            if self.mode == "leave":
                scr_ok = any(sc.geometry().adjusted(-60, -60, 60, 60).contains(self.pos_f.toPoint())
                             for sc in QGuiApplication.screens())
                if not scr_ok or self.t_mode > 8:
                    self.stop()
                    self.gone.emit()
                    return
        self.phase += dt * (17.0 if flying else 4.0)
        self._place()
        self.update()

    def _dodge(self, dt):
        cur = QCursor.pos()
        cp = QPointF(cur)
        d = cp - self.pos_f
        dist = math.hypot(d.x(), d.y())
        if self._cursor_prev is not None and dt > 0 and self.dodges < 2:
            pd = self._cursor_prev - self.pos_f
            approach = (math.hypot(pd.x(), pd.y()) - dist) / dt
            if dist < 70 and approach > 900:
                away = QPointF(-d.x() / max(1, dist), -d.y() / max(1, dist))
                self.vel = away * 520
                self.dodges += 1
                if self.mode == "sit":
                    self.mode = "wander"
                    self.t_mode = 0.0
                self.dodged.emit()
        self._cursor_prev = cp

    def _place(self):
        self.move(int(self.pos_f.x() - self.SIZE / 2), int(self.pos_f.y() - self.SIZE / 2))

    # ----- 交互 / 绘制 -----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.mode not in ("off", "leave"):
            self.stop()
            self.caught.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        c = QPointF(self.SIZE / 2, self.SIZE / 2)
        flap = 0.22 + 0.78 * abs(math.sin(self.phase))
        if self.mode == "sit":
            flap = 0.55 + 0.45 * abs(math.sin(self.phase))
        tilt = max(-25.0, min(25.0, self.vel.x() * 0.08))
        # 点击判定区: 极淡的圆, 让透明窗口能收到鼠标
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 2))
        p.drawEllipse(c, self.SIZE / 2 - 4, self.SIZE / 2 - 4)
        p.translate(c)
        p.rotate(tilt)
        p.translate(-c)
        draw_butterfly(p, c, self.wing, flap, self.colors)
        p.end()


class DanikaVisit(QWidget):
    """达妮卡来访: 从侧边滑入, 与薇斯纳短对话后离开。点击可提前告辞。

    依赖由 main 注入(Bubble / ASSET_DIR / log_error), 禁止 `import main`
    —— 进程以 `python main.py` 启动时模块名是 __main__, `import main` 会再执行一遍。
    """
    skipped = Signal()
    finished = Signal()
    FIG_SCALE = 1.12          # 可见身高相对薇斯纳可见身高
    ENTER_SEC = 1.15
    LEAVE_SEC = 1.05
    LINE_SEC = 3.6

    def __init__(self, host, bubble_cls=None, asset_dir=None, log_fn=None):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        super().__init__(None, flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setCursor(Qt.PointingHandCursor)
        self.host = host
        self._bubble_cls = bubble_cls
        self._asset_dir = Path(asset_dir) if asset_dir else (Path(__file__).resolve().parent / "assets")
        self._log = log_fn
        self.mode = "off"          # off / enter / talk / leave
        self.pose = "idle"         # idle / talk / sigh
        self.side = "right"
        self.t_mode = 0.0
        self.opacity = 0.0
        self._script = []
        self._line_i = -1
        self._line_t = 0.0
        self._spoken = []          # [(who, line), ...] for tests
        self._target = QPointF()
        self._start = QPointF()
        self._pos = QPointF()
        self._pix = {}             # cropped pose pixmaps (shared bbox)
        self._crop_w = 1
        self._crop_h = 1
        self._w = 120
        self._h = 120
        self._last = time.monotonic()
        self.bubble = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._closing_line = False
        self._load_pix()

    # ----- 素材 -----
    def _log_error(self, where, e=None):
        try:
            if self._log:
                self._log(where, e)
                return
        except Exception:
            pass
        # fallback: append to APPDATA / ~/.config VesnaPet/error.log
        try:
            import os, traceback
            if sys.platform.startswith("win"):
                root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            else:
                root = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
            p = Path(root) / "VesnaPet" / "error.log"
            p.parent.mkdir(parents=True, exist_ok=True)
            msg = where if e is None else f"{where}: {e}\n{traceback.format_exc()}"
            with open(p, "a", encoding="utf-8") as f:
                f.write(msg.rstrip() + "\n")
        except Exception:
            pass

    def _load_pix(self):
        """加载三张图, 用共享 alpha bbox 裁切, 避免动作切换跳动。"""
        self._pix = {}
        imgs = {}
        for name in ("idle", "talk", "sigh"):
            p = self._asset_dir / f"danika_{name}.png"
            if not p.exists():
                continue
            img = QImage(str(p))
            if img.isNull():
                continue
            imgs[name] = img.convertToFormat(QImage.Format_ARGB32)
        if not imgs:
            return
        # shared bbox
        box = None
        for img in imgs.values():
            r = self._alpha_bbox(img)
            box = r if box is None else box.united(r)
        if box is None or box.width() < 2 or box.height() < 2:
            return
        self._crop_w, self._crop_h = box.width(), box.height()
        for name, img in imgs.items():
            self._pix[name] = QPixmap.fromImage(img.copy(box))
        if "sigh" not in self._pix and "idle" in self._pix:
            self._pix["sigh"] = self._pix["idle"]
        if "talk" not in self._pix and "idle" in self._pix:
            self._pix["talk"] = self._pix["idle"]

    @staticmethod
    def _alpha_bbox(img: QImage, thr=8) -> QRect:
        img = img.convertToFormat(QImage.Format_ARGB32)
        w, h, bpl = img.width(), img.height(), img.bytesPerLine()
        data = bytes(img.constBits())
        x0, y0, x1, y1 = w, h, -1, -1
        for y in range(h):
            row = data[y * bpl + 3: y * bpl + 4 * w: 4]
            if not row or max(row) <= thr:
                continue
            xs = [i for i, a in enumerate(row) if a > thr]
            x0, x1 = min(x0, xs[0]), max(x1, xs[-1])
            y0 = min(y0, y)
            y1 = y
        if x1 < 0:
            return QRect(0, 0, w, h)
        return QRect(x0, y0, x1 - x0 + 1, y1 - y0 + 1)

    def active(self):
        return self.mode != "off"

    # ----- 尺寸 / 站位: 按「可见身高」对齐薇斯纳 -----
    def _vesna_fig_h(self):
        """薇斯纳当前绘制尺寸下的可见身高(像素)。frames 已是 alpha-crop 后的图。"""
        h = self.host
        return max(40, int(getattr(h, "char_h", 160)))

    def _char_size(self):
        """达妮卡窗口尺寸 = 裁切后 pixmap 按可见身高缩放到 ≈0.95×薇斯纳。"""
        fig_h = max(1, self._crop_h)
        fig_w = max(1, self._crop_w)
        target_h = max(48, int(self._vesna_fig_h() * self.FIG_SCALE))
        scale = target_h / fig_h
        cw = max(40, int(fig_w * scale))
        ch = max(40, int(fig_h * scale))
        return cw, ch

    def _stand_side(self):
        h = self.host
        scr = QGuiApplication.screenAt(h.frameGeometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        cx = h.x() + h.width() / 2
        return "right" if cx < g.center().x() else "left"

    def _anchor_for_side(self, side):
        """贴在薇斯纳身体旁, 脚底与薇斯纳同一基线, 小间距不重叠。"""
        h = self.host
        cw, ch = self._char_size()
        gap = max(4, int(h.char_w * 0.04))
        # 薇斯纳角色区: pad_x .. pad_x+char_w, 垂直 pad_top .. pad_top+char_h
        base_y = h.y() + h.pad_top() + h.char_h - ch
        if side == "right":
            x = h.x() + h.pad_x + h.char_w + gap
        else:
            x = h.x() + h.pad_x - gap - cw
        return QPointF(x, base_y)

    def _offscreen_for_side(self, side):
        scr = QGuiApplication.screenAt(self.host.frameGeometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        cw, _ = self._char_size()
        tgt = self._anchor_for_side(side)
        if side == "right":
            return QPointF(g.right() + 40, tgt.y())
        return QPointF(g.left() - cw - 40, tgt.y())

    # ----- 控制 -----
    def start(self, script=None):
        self._load_pix()
        if self.active() or "idle" not in self._pix:
            return False
        h = self.host
        if h.edge or h._dragging or h.fling or h.walk:
            return False
        if h.state == "sleep" or (hasattr(h, "sulking") and h.sulking()):
            return False
        if h.link_busy:
            return False
        for p in getattr(h, "_panels", {}).values():
            if p is not None and p.isVisible():
                return False
        import content as C
        self._script = list(script or random.choice(C.DANIKA_VISITS))
        if not self._script:
            return False
        self.side = self._stand_side()
        self._target = self._anchor_for_side(self.side)
        self._start = self._offscreen_for_side(self.side)
        self._pos = QPointF(self._start)
        self.mode = "enter"
        self.pose = "idle"
        self.t_mode = 0.0
        self.opacity = 0.0
        self._line_i = -1
        self._line_t = 0.0
        self._spoken = []
        self._closing_line = False
        cw, ch = self._char_size()
        self._w, self._h = cw, ch
        self.setFixedSize(cw, ch)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(h.cfg["topmost"]))
        self._place()
        self.show()
        self.raise_()
        self._last = time.monotonic()
        self.timer.start(16)
        try:
            h.sfx.play("whoosh")
        except Exception:
            pass
        try:
            h.sfx.play("chime")
        except Exception:
            pass
        return True

    def skip(self):
        if not self.active() or self.mode == "leave":
            return
        self._closing_line = True
        self.pose = "idle"
        try:
            self._say_danika("……告辞。", duration=1.6)
        except Exception as e:
            self._log_error("danika skip say", e)
        self.mode = "leave"
        self.t_mode = 0.0
        self._start = QPointF(self._pos)
        self._target = self._offscreen_for_side(self.side)
        self.skipped.emit()

    def stop(self):
        self.mode = "off"
        self.timer.stop()
        self.hide()
        if self.bubble is not None:
            try:
                self.bubble.hide()
            except Exception:
                pass

    def _place(self):
        self.move(int(self._pos.x()), int(self._pos.y()))

    def _anchor_bubble(self):
        # 气泡锚在达妮卡头顶中央; 略偏外侧避免和薇斯纳气泡叠在一起
        cx = self._pos.x() + self._w / 2
        if self.side == "right":
            cx += self._w * 0.12
        else:
            cx -= self._w * 0.12
        return QPoint(int(cx), int(self._pos.y() + 6))

    def _ensure_bubble(self):
        if self.bubble is None:
            cls = self._bubble_cls
            if cls is None:
                raise RuntimeError("DanikaVisit: Bubble class not injected (pass bubble_cls= from main)")
            self.bubble = cls()
        return self.bubble

    def _say_danika(self, text, duration=None):
        b = self._ensure_bubble()
        b.popup(text, self._anchor_bubble(), duration or self.LINE_SEC,
                topmost=bool(self.host.cfg["topmost"]), side="top", tone="cool")
        self._spoken.append(("danika", text))

    def _tick(self):
        try:
            now = time.monotonic()
            dt = max(0.0, min(0.05, now - self._last))
            self._last = now
            self._step(dt)
        except Exception as e:
            self._log_error("danika_tick", e)
            self.stop()
            self.finished.emit()

    def _step(self, dt):
        h = self.host
        if not h.isVisible() or h._dragging or h.fling or h.edge:
            if self.mode not in ("leave", "off"):
                self.skip()
        self.t_mode += dt
        if self.mode == "enter":
            t = min(1.0, self.t_mode / self.ENTER_SEC)
            e = 1 - (1 - t) ** 3
            self._pos = self._start + (self._target - self._start) * e
            self.opacity = e
            self._place()
            self.update()
            if t >= 1.0:
                self.mode = "talk"
                self.t_mode = 0.0
                self._line_i = -1
                self._advance_line()
        elif self.mode == "talk":
            self._target = self._anchor_for_side(self.side)
            self._pos = self._pos + (self._target - self._pos) * min(1.0, dt * 8)
            self.opacity = 1.0
            self._place()
            if self.bubble and self.bubble.isVisible():
                self.bubble.follow(self._anchor_bubble(), "top")
            self._line_t += dt
            if self._line_t >= self.LINE_SEC * 0.95:
                self._advance_line()
            self.update()
        elif self.mode == "leave":
            t = min(1.0, self.t_mode / self.LEAVE_SEC)
            e = t * t
            self._pos = self._start + (self._target - self._start) * e
            self.opacity = 1.0 - e
            self._place()
            self.update()
            if t >= 1.0:
                self.stop()
                try:
                    if h.state not in ("sleep",) and not (hasattr(h, "sulking") and h.sulking()):
                        h.set_state("idle")
                except Exception as e:
                    self._log_error("danika leave idle", e)
                self.finished.emit()

    def _advance_line(self):
        self._line_i += 1
        if self._line_i >= len(self._script):
            self.pose = "idle"
            self.mode = "leave"
            self.t_mode = 0.0
            self._start = QPointF(self._pos)
            self._target = self._offscreen_for_side(self.side)
            if not self._closing_line:
                try:
                    self.host.sfx.play("whoosh")
                except Exception:
                    pass
            return
        who, line = self._script[self._line_i]
        self._line_t = 0.0
        h = self.host
        if who == "danika":
            if "告辞" in line:
                self.pose = "idle"
            elif any(k in line for k in ("拿你", "彼此", "……")):
                self.pose = "sigh" if "拿你" in line or "彼此" in line else "talk"
            else:
                self.pose = "talk"
            self._say_danika(line)
            try:
                # 薇斯纳看向达妮卡; 气泡侧略偏, 避免和达妮卡气泡正对叠
                h.set_state("look" if self.side == "right" else "look_left", self.LINE_SEC)
            except Exception as e:
                self._log_error("danika set_state look", e)
        else:
            self.pose = "idle"
            face = "happy"
            if any(k in line for k in ("达妮卡!", "别乱说", "叛徒", "哼")):
                face = "shy" if ("别乱说" in line or "达妮卡!" in line) else "angry"
            elif any(k in line for k in ("……", "再坐", "可以装")):
                face = "content" if "再坐" in line else "surprised"
            elif "小气" in line or "漂亮" in line:
                face = "shy"
            try:
                h.set_state(face, self.LINE_SEC)
            except Exception as e:
                self._log_error("danika set_state face", e)
            try:
                h.say(line, force=True, duration=self.LINE_SEC)
                self._spoken.append(("vesna", line))
            except Exception as e:
                self._log_error("danika host.say", e)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.active():
            self.skip()

    def paintEvent(self, _):
        pm = self._pix.get(self.pose) or self._pix.get("idle")
        if pm is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setOpacity(max(0.0, min(1.0, self.opacity)))
        scaled = pm.scaled(self._w, self._h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        if self.side == "right":
            scaled = scaled.transformed(QTransform().scale(-1, 1))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 2))
        p.drawRect(self.rect())
        p.drawPixmap(0, 0, scaled)
        p.end()
