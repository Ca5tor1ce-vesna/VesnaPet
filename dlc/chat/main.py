# -*- coding: utf-8 -*-
"""薇斯纳对话 DLC。独立窗口；桌宠不在也能开。"""
import re
import sys

from PySide6.QtCore import QEvent, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget)

import config as cfg
from llm import ChatJob
import memory as mem
from watch import PetWatch

INK = QColor("#2E3F6E")
INK2 = QColor("#5B6A92")
MUTED = QColor("#9AA5C0")
MINT = QColor("#4FC7B5")
MINT_D = QColor("#2C9F8F")
MINT_L = QColor("#E3F7F3")
PINK = QColor("#FF8FB1")
GOLD = QColor("#F5C451")
CARD = QColor("#FFFFFF")
LINE = QColor(46, 63, 110, 32)
FAMILIES = ["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "sans-serif"]


def font(px=13, bold=False):
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPixelSize(int(px))
    f.setBold(bold)
    return f


# 回复完让她在桌面上说出来: 取第一句(或前 60 字), 按简单关键词挑表情
SAY_MAX = 60
_SENT_END = re.compile(r"^(.+?[。！？!?…~～]+)")
SAY_EXPR_RULES = (          # (表情, 关键词) 从上往下, 先命中先用
    ("shy", ("害羞", "脸红", "才不是", "才没有", "讨厌啦", "不好意思", "人家")),
    ("angry", ("哼", "生气", "气死", "笨蛋", "不理你", "讨厌", "别戳")),
    ("surprised", ("诶", "欸", "咦", "哇", "真的吗", "什么?", "什么？", "吓")),
    ("happy", ("嘿嘿", "哈哈", "开心", "喜欢", "太好了", "好耶", "耶", "最棒", "~", "～")),
)


def pet_line(text):
    """回复里取要在桌面上说的一句: 第一句太短就带上第二句; 最多 60 字。"""
    t = " ".join((text or "").split())
    if not t:
        return ""
    m = _SENT_END.match(t)
    line = m.group(1) if m else t
    if len(line) < 4 and m:
        m2 = _SENT_END.match(t[len(line):].lstrip())
        if m2:
            line = line + m2.group(1)
    return line[:SAY_MAX]


def pet_expr(line):
    for expr, keys in SAY_EXPR_RULES:
        if any(k in line for k in keys):
            return expr
    return None


def apply_btn(btn, fill, fg=None):
    fg = fg or "white"
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFont(font(12, True))
    btn.setStyleSheet(
        f"QPushButton{{background:{fill};color:{fg};border:none;border-radius:10px;padding:6px 12px;}}"
        f"QPushButton:hover{{opacity:0.9;}}"
        f"QPushButton:disabled{{background:#D5DCE8;color:#9AA5C0;}}"
    )


class Bubble(QFrame):
    def __init__(self, role, text, parent=None):
        super().__init__(parent)
        self.role = role
        self.lab = QLabel(text, self)
        self.lab.setWordWrap(True)
        self.lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lab.setFont(font(13))
        if role == "user":
            self.lab.setStyleSheet("color:#FFFFFF;background:transparent;")
            bg = MINT_D.name()
        elif role == "err":
            self.lab.setStyleSheet("color:#8A3A4A;background:transparent;")
            bg = "#FDE8EE"
        else:
            self.lab.setStyleSheet("color:#2E3F6E;background:transparent;")
            bg = "#F3F6FC"
        self.setStyleSheet(f"QFrame{{background:{bg};border-radius:14px;}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.addWidget(self.lab)
        self.setMaximumWidth(300)

    def set_text(self, text):
        self.lab.setText(text)


class SettingsDlg(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("对话设置")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.key = QLineEdit(data.get("api_key", ""))
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("sk-...")
        self.base = QLineEdit(data.get("base_url", ""))
        self.base.setPlaceholderText("https://api.xiaomimimo.com/v1  或其它 OpenAI 兼容地址")
        self.model = QLineEdit(data.get("model", ""))
        self.model.setPlaceholderText("mimo-v2.6-flash")
        self.pet_say = QCheckBox("让她在桌面上说出来")
        self.pet_say.setChecked(bool(data.get("pet_say", True)))
        self.pet_say.setToolTip("回复完后, 桌宠头顶冒出回复的第一句(需要新版桌宠; 她在忙或睡着时会跳过)")
        show = QPushButton("显示")
        show.setCheckable(True)
        show.toggled.connect(lambda on: self.key.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        row = QHBoxLayout()
        row.addWidget(self.key)
        row.addWidget(show)
        form = QFormLayout()
        form.addRow("API Key", row)
        form.addRow("接口地址", self.base)
        form.addRow("模型名", self.model)
        form.addRow("", self.pet_say)
        hint = QLabel("默认 MiMo v2.6 Flash。官方地址 https://api.xiaomimimo.com/v1 ；中转站改地址即可。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9AA5C0;")
        ok = QPushButton("保存")
        apply_btn(ok, MINT_D.name())
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        apply_btn(cancel, "#E8EEF6", INK.name())
        cancel.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        box = QVBoxLayout(self)
        box.addLayout(form)
        box.addWidget(hint)
        box.addLayout(btns)

    def values(self):
        return {
            "api_key": self.key.text().strip(),
            "base_url": self.base.text().strip(),
            "model": self.model.text().strip(),
            "pet_say": self.pet_say.isChecked(),
        }


class ChatWin(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("薇斯纳 · 对话")
        self.cfg = cfg.load()
        self.watch = PetWatch(self)
        self.mem = mem.load()
        self.history = list(self.mem.get("recent") or [])
        self.job = None
        self.compress = None
        self._stream = None
        self._stream_text = ""
        self._drag = None
        self.resize(400, 560)
        self._build()
        self.watch.online_changed.connect(self._on_online)
        QTimer.singleShot(400, lambda: self._on_online(self.watch.online))
        QTimer.singleShot(0, self._restore_recent)
        self._place()

    def _build(self):
        self.title = QLabel("和薇斯纳说话")
        self.title.setFont(font(16, True))
        self.title.setStyleSheet("color:#2E3F6E;background:transparent;")
        self.dot = QLabel("桌宠未开启")
        self.dot.setFont(font(11))
        self.dot.setStyleSheet("color:#9AA5C0;background:transparent;")
        gear = QPushButton("设置")
        apply_btn(gear, "#E8EEF6", INK.name())
        gear.clicked.connect(self._settings)
        close = QPushButton("×")
        close.setFixedSize(28, 28)
        apply_btn(close, "#FFE9F0", "#E2557F")
        close.clicked.connect(self.close)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(self.title)
        col.addWidget(self.dot)
        head.addLayout(col, 1)
        head.addWidget(gear, 0, Qt.AlignTop)
        head.addWidget(close, 0, Qt.AlignTop)

        self.stream_host = QWidget()
        self.stream_lay = QVBoxLayout(self.stream_host)
        self.stream_lay.setContentsMargins(8, 8, 8, 8)
        self.stream_lay.setSpacing(8)
        self.stream_lay.addStretch(1)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        sc.setWidget(self.stream_host)
        sc.setStyleSheet("QScrollArea{background:transparent;border:none;} QWidget{background:transparent;}")
        self.scroll = sc

        self.input = QTextEdit()
        self.input.setFixedHeight(72)
        self.input.setPlaceholderText("跟她说点什么… Enter 发送，Shift+Enter 换行")
        self.input.setFont(font(13))
        self.input.setStyleSheet(
            "QTextEdit{background:#F7FBFF;border:1px solid #DCE3F1;border-radius:12px;padding:8px;color:#2E3F6E;}"
        )
        self.input.installEventFilter(self)
        self.send_btn = QPushButton("发送")
        apply_btn(self.send_btn, MINT_D.name())
        self.send_btn.clicked.connect(self._send)
        bottom = QHBoxLayout()
        bottom.addWidget(self.input, 1)
        bottom.addWidget(self.send_btn, 0, Qt.AlignBottom)

        self.card = QWidget(self)
        inner = QVBoxLayout(self.card)
        inner.setContentsMargins(16, 14, 16, 14)
        inner.setSpacing(10)
        inner.addLayout(head)
        inner.addWidget(sc, 1)
        inner.addLayout(bottom)
        self.card.setStyleSheet("QWidget{background:transparent;}")

        hint = QLabel("她不在也可以聊。填好 Key 就能说话。")
        hint.setFont(font(11))
        hint.setStyleSheet("color:#9AA5C0;background:transparent;")
        inner.addWidget(hint)

    def _place(self):
        scr = QGuiApplication.primaryScreen()
        g = scr.availableGeometry() if scr else QRect(0, 0, 1280, 720)
        self.move(g.right() - self.width() - 24, g.bottom() - self.height() - 24)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(12, 12, self.width() - 24, self.height() - 24)
        sh = QColor(30, 45, 90, 40)
        p.setPen(Qt.NoPen)
        p.setBrush(sh)
        p.drawRoundedRect(r.adjusted(2, 5, 2, 5), 20, 20)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor("#F7FBFF"))
        g.setColorAt(1, CARD)
        p.setPen(QPen(LINE, 1))
        p.setBrush(g)
        p.drawRoundedRect(r, 20, 20)
        band = QPainterPath()
        band.addRoundedRect(QRectF(r.left(), r.top(), r.width(), 58), 20, 20)
        p.setClipPath(band)
        bg = QLinearGradient(r.topLeft(), r.topRight())
        bg.setColorAt(0, QColor("#D9F5EF"))
        bg.setColorAt(1, QColor("#FFE6EF"))
        p.fillRect(QRectF(r.left(), r.top(), r.width(), 58), bg)
        p.setClipping(False)
        self.card.setGeometry(int(r.x()), int(r.y()), int(r.width()), int(r.height()))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 70:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()
        else:
            self._drag = None

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def eventFilter(self, obj, e):
        if obj is self.input and e.type() == QEvent.Type.KeyPress:
            if e.key() in (Qt.Key_Return, Qt.Key_Enter) and not (e.modifiers() & Qt.ShiftModifier):
                self._send()
                return True
        return super().eventFilter(obj, e)

    def _on_online(self, on):
        if on:
            self.dot.setText("薇斯纳在桌面上")
            self.dot.setStyleSheet("color:#2C9F8F;background:transparent;")
        else:
            self.dot.setText("桌宠未开启 · 仍可对话")
            self.dot.setStyleSheet("color:#9AA5C0;background:transparent;")

    def _settings(self):
        dlg = SettingsDlg(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            vals = dlg.values()
            self.cfg.update(vals)
            cfg.save(self.cfg)

    def _add(self, role, text) -> Bubble:
        b = Bubble(role, text, self.stream_host)
        stretch = self.stream_lay.takeAt(self.stream_lay.count() - 1)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row.addStretch(1)
            row.addWidget(b, 0, Qt.AlignRight)
        else:
            row.addWidget(b, 0, Qt.AlignLeft)
            row.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(row)
        self.stream_lay.addWidget(wrap)
        self.stream_lay.addItem(stretch)
        QTimer.singleShot(30, self._scroll_end)
        return b

    def _scroll_end(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _send(self):
        if self.job is not None:
            return
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self._add("user", text)
        hidden = self.watch.hidden_prompt()
        self._stream_text = ""
        self._stream = self._add("assistant", "……")
        self.send_btn.setEnabled(False)
        self.job = ChatJob(self.cfg, self.history, text, hidden, mem.memory_block(self.mem), self)
        self.job.delta.connect(self._on_delta)
        self.job.done.connect(self._on_done)
        self.job.fail.connect(self._on_fail)
        self._pending_user = text
        self.job.start()

    def _on_delta(self, piece):
        self._stream_text += piece
        if self._stream:
            self._stream.set_text(self._stream_text)
        self._scroll_end()

    def _on_done(self):
        text = self._stream_text.strip()
        if text:
            self.history.append(("user", self._pending_user))
            self.history.append(("assistant", text))
            self.mem["recent"] = list(self.history)
            mem.save(self.mem)
            self._maybe_compress()
            self._say_on_pet(text)
        elif self._stream:
            self._stream.set_text("（没有回上话）")
        self._finish_job()

    def _say_on_pet(self, text):
        """桌宠在线且支持 say 时, 让她把回复第一句说出来; 失败(busy/rate/离线)静默忽略。"""
        if not self.cfg.get("pet_say", True):
            return
        try:
            line = pet_line(text)
            if line and self.watch.can_say():
                self.watch.say(line, pet_expr(line), 4)
        except Exception:
            pass

    def _on_fail(self, err):
        if self._stream:
            self._stream.set_text("")
            self._stream.hide()
        self._add("err", err)
        self._finish_job()

    def _finish_job(self):
        self.job = None
        self._stream = None
        self.send_btn.setEnabled(True)
        self.input.setFocus()

    def _restore_recent(self):
        for role, text in self.history[-6:]:
            self._add(role, text)

    def _maybe_compress(self):
        if self.compress is not None:
            return
        if len(self.history) < mem.COMPRESS_AT:
            return
        old = self.history[:-mem.KEEP_RECENT]
        if not old:
            return
        self.compress = mem.CompressJob(self.cfg, old, self.mem, self)
        self.compress.finished_ok.connect(self._on_compressed)
        self.compress.finished_fail.connect(self._on_compress_fail)
        self.compress.start()

    def _on_compressed(self, payload):
        self.history = self.history[-mem.KEEP_RECENT:]
        self.mem["facts"] = payload.get("facts") or self.mem.get("facts") or []
        self.mem["summary"] = payload.get("summary") or self.mem.get("summary") or ""
        self.mem["recent"] = list(self.history)
        mem.save(self.mem)
        self.compress = None

    def _on_compress_fail(self):
        self.compress = None

    def closeEvent(self, e):
        if self.job:
            self.job.requestInterruption()
            self.job.wait(400)
        if self.compress:
            try:
                self.compress.finished_ok.disconnect()
                self.compress.finished_fail.disconnect()
            except Exception:
                pass
            self.compress.wait(400)
        self.mem["recent"] = list(self.history)
        try:
            mem.save(self.mem)
        except Exception:
            pass
        self.watch.stop()
        super().closeEvent(e)


def _single_key():
    import os
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return f"VesnaDLC-{user}-single"


def _already_running(key) -> bool:
    """已有窗口就叫它到前面, 返回 True。"""
    from PySide6.QtNetwork import QLocalSocket
    s = QLocalSocket()
    s.connectToServer(key)
    if s.waitForConnected(300):
        s.write(b"show\n")
        s.waitForBytesWritten(300)
        s.disconnectFromServer()
        return True
    return False


def _listen_single(key, win):
    from PySide6.QtNetwork import QLocalServer
    QLocalServer.removeServer(key)
    srv = QLocalServer(win)
    if not srv.listen(key):
        return None

    def on_conn():
        c = srv.nextPendingConnection()
        if c is None:
            return
        c.disconnected.connect(c.deleteLater)
        win.showNormal()
        win.raise_()
        win.activateWindow()

    srv.newConnection.connect(on_conn)
    return srv


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VesnaDLC")
    app.setQuitOnLastWindowClosed(True)
    key = _single_key()
    if _already_running(key):
        return 0
    w = ChatWin()
    w._single_srv = _listen_single(key, w)
    w.show()
    w.raise_()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
