# -*- coding: utf-8 -*-
"""互动卡片菜单 / 薇斯纳的小屋 / 今日运势 / 猜拳 —— 全部自绘。panels 只调用 pet 的公开方法。"""
import math
import random
import time
from datetime import date

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtWidgets import QScrollArea, QWidget

import content as C
from ui_kit import (CARD, GOLD, GOLD_D, GOLD_L, INK, INK2, LAV, LINE, MINT, MINT_D, MINT_L, MUTED, ORANGE, PINK,
                    PINK_D, PINK_L, Bar, Button, CardWindow, CloseButton, IconTile, Label, Ring, Segmented,
                    Tabs, Toggle, alpha, draw_butterfly, draw_gem, ease_out_back, emoji_font, face_avatar, font,
                    food_pixmap, sparkle_path)

WEEK = "一二三四五六日"


def _dpr(w):
    try:
        return w.devicePixelRatioF() or 1.0
    except Exception:
        return 1.0


def place_near_pet(card: CardWindow, pet, body_w, body_h):
    """卡片放在桌宠旁边空间大的一侧; 返回主体左上角全局坐标"""
    r = pet.frameGeometry()
    scr = QGuiApplication.screenAt(r.center()) or QGuiApplication.primaryScreen()
    g = scr.availableGeometry()
    if r.center().x() > g.center().x():
        x = r.left() + pet.pad_x - body_w - 6
    else:
        x = r.right() - pet.pad_x + 6
    y = r.bottom() - body_h - 10
    return QPoint(int(x), int(y))


def paint_header_band(p: QPainter, rect: QRectF, radius, t=0.0):
    """面板顶部装饰带: 薄荷→薰衣草渐变 + 宝石/闪光/小蝴蝶"""
    p.save()
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.setClipPath(path)
    g = QLinearGradient(rect.topLeft(), rect.topRight())
    g.setColorAt(0, QColor("#D9F5EF"))
    g.setColorAt(0.55, QColor("#E9E6FB"))
    g.setColorAt(1, QColor("#FFE6EF"))
    p.fillRect(rect, g)
    # 底部白色弧
    wave = QPainterPath()
    wave.moveTo(rect.left(), rect.bottom())
    wave.lineTo(rect.left(), rect.bottom() - 14)
    wave.cubicTo(rect.left() + rect.width() * 0.3, rect.bottom() - 2, rect.left() + rect.width() * 0.65,
                 rect.bottom() - 26, rect.right(), rect.bottom() - 12)
    wave.lineTo(rect.right(), rect.bottom())
    wave.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(CARD)
    p.drawPath(wave)
    rnd = random.Random(7)
    for i in range(9):
        x = rect.left() + rnd.uniform(0.35, 0.98) * rect.width()
        y = rect.top() + rnd.uniform(0.12, 0.7) * rect.height()
        r = rnd.uniform(2.5, 5.5)
        tw = 0.55 + 0.45 * math.sin(t * 1.6 + i * 1.3)
        p.setBrush(QColor(255, 255, 255, int(200 * tw)))
        p.drawPath(sparkle_path(QPointF(x, y), r))
    draw_gem(p, QPointF(rect.right() - 58, rect.top() + 26), 6, MINT)
    draw_gem(p, QPointF(rect.right() - 92, rect.top() + 48), 4, LAV)
    p.setOpacity(0.85)
    draw_butterfly(p, QPointF(rect.right() - 126, rect.top() + 30 + 2 * math.sin(t * 2)), 9,
                   0.35 + 0.65 * abs(math.sin(t * 3.2)), (PINK, MINT))
    p.restore()


def paint_chip(p: QPainter, x, y, text, fg, bg, px=11, h=20):
    p.save()
    p.setFont(font(px, QFont.DemiBold))
    w = p.fontMetrics().horizontalAdvance(text) + 16
    r = QRectF(x, y, w, h)
    p.setPen(Qt.NoPen)
    p.setBrush(bg)
    p.drawRoundedRect(r, h / 2, h / 2)
    p.setPen(fg)
    p.drawText(r, Qt.AlignCenter, text)
    p.restore()
    return w


# =====================================================================
#   右键互动卡片
# =====================================================================
class ActionMenu(CardWindow):
    W = 316

    def __init__(self, pet):
        super().__init__(self.W, 430, popup=True, drag_h=0)
        self.pet = pet
        self.page = "main"
        self.radius = 22
        self._avatar = None
        self._t0 = time.monotonic()
        self.pages = {}
        self._build_main()
        self._build_food()
        self._build_focus()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_live)

    # ----- 构建 -----
    def _grid(self, parent, items, x0, y0, size=(66, 72), cols=4, gap=6):
        tiles = []
        for i, it in enumerate(items):
            emoji, label, fn = it[:3]
            sub = it[3] if len(it) > 3 else ""
            t = IconTile(emoji, label, parent, size=size, sub=sub)
            t.move(x0 + (i % cols) * (size[0] + gap), y0 + (i // cols) * (size[1] + gap))
            t.clicked.connect(fn)
            tiles.append(t)
        return tiles

    def _act(self, fn, close=True):
        def run():
            if close:
                self.hide()
            QTimer.singleShot(0, fn)
        return run

    def _build_main(self):
        pg = QWidget(self)
        pet = self.pet
        self.home_btn = IconTile("🏠", "", pg, size=(40, 40))
        self.home_btn.move(self.W - 54, 14)
        self.home_btn.clicked.connect(self._act(lambda: pet.open_home(0)))
        items = [
            ("🤚", "摸摸头", self._act(pet.pet)),
            ("🍰", "投喂", lambda: self.show_page("food")),
            ("🔮", "今日运势", self._act(pet.open_fortune)),
            ("✊", "猜拳", self._act(pet.open_rps)),
            ("🍅", "专注", lambda: self.show_page("focus")),
            ("👣", "过来~", self._act(pet.come_here)),
            ("🦋", "召唤蝴蝶", self._act(pet.summon_butterfly)),
            ("🧊", "达妮卡", self._act(pet.summon_danika)),
            ("🎉", "放彩带", self._act(lambda: (pet.note_interaction(), pet.celebrate()))),
        ]
        hub = getattr(pet, "_ix", None)                 # 互动扩展注册的菜单项(没装就没有)
        for emoji, label, fn in (hub.menu_items() if hub is not None and hasattr(hub, "menu_items") else []):
            items.append((emoji, label, self._act(fn)))
        self.main_tiles = self._grid(pg, items, 17, 76)
        rows = (len(items) + 3) // 4
        y = 76 + rows * 78 + 4
        self.status_y = y
        by = y + 38
        b1 = Button("小屋", pg, "soft", "🏠", h=30, px=12)
        b2 = Button("设置", pg, "soft", "⚙️", h=30, px=12)
        b3 = Button("隐藏", pg, "soft", "🙈", h=30, px=12)
        b4 = Button("退出", pg, "danger", "", h=30, px=12)
        xs = 17
        for b, w in ((b1, 74), (b2, 74), (b3, 74), (b4, 54)):
            b.setFixedWidth(w)
            b.move(xs, by)
            xs += w + 6
        b1.clicked.connect(self._act(lambda: pet.open_home(0)))
        b2.clicked.connect(self._act(lambda: pet.open_home(3)))
        b3.clicked.connect(self._act(pet.toggle_visible))
        b4.clicked.connect(self._act(pet.quit_requested.emit))
        pg.setGeometry(self.M, self.M, self.W, by + 44)
        self.pages["main"] = pg

    FOOD_TILE = (66, 86)
    FOOD_Y = 92
    FOOD_PER_PAGE = 8

    def _build_food(self):
        pg = QWidget(self)
        back = Button("返回", pg, "ghost", "‹", h=28, px=12)
        back.setFixedWidth(70)
        back.move(14, 16)
        back.clicked.connect(lambda: self.show_page("main"))
        self._food_hover = None
        self._food_tab = 0
        # 分页: 每地区一页, 一页最多 8 格(2 行), 多了自动拆成「名字 1/2」; 食物包的分页排在后面
        pages = []
        for name, regions in C.FOOD_REGIONS:
            foods = C.foods_in(regions)
            chunks = [foods[i:i + self.FOOD_PER_PAGE] for i in range(0, len(foods), self.FOOD_PER_PAGE)] or [[]]
            for j, ch in enumerate(chunks):
                pages.append((name if len(chunks) == 1 else f"{name} {j + 1}", ch))
        self.food_page_names = [nm for nm, _ in pages]
        self.food_seg = self.food_pager = None
        if len(pages) <= 3:                 # 原版: 分段选择器
            self.food_seg = Segmented([(i, nm) for i, nm in enumerate(self.food_page_names)], 0, pg, h=28, px=12)
            self.food_seg.move((self.W - self.food_seg.width()) // 2, 54)
            self.food_seg.changed.connect(self._set_food_tab)
        else:                               # 装了食物包、页数多: ‹ 页名 n/N › 翻页
            prev = Button("", pg, "soft", "‹", h=28, px=14)
            nxt = Button("", pg, "soft", "›", h=28, px=14)
            for b in (prev, nxt):
                b.setFixedWidth(40)
            prev.move(17, 54)
            nxt.move(self.W - 17 - 40, 54)
            prev.clicked.connect(lambda: self._set_food_tab((self._food_tab - 1) % len(self.food_page_names)))
            nxt.clicked.connect(lambda: self._set_food_tab((self._food_tab + 1) % len(self.food_page_names)))
            self.food_pager = Label("", pg, px=13, weight=QFont.DemiBold, align=Qt.AlignCenter, h=28)
            self.food_pager.setGeometry(60, 54, self.W - 120, 28)
        self.food_tabs = []         # [(容器, [(tile, food)])]
        tw, th = self.FOOD_TILE
        for _, foods in pages:
            box = QWidget(pg)
            box.setGeometry(0, self.FOOD_Y, self.W, 2 * (th + 6))
            items = []
            for f in foods:
                items.append((f["emoji"], f["short"], self._act(lambda k=f["key"]: self.pet.feed(k)), ""))
            tiles = self._grid(box, items, 17, 0, size=self.FOOD_TILE)
            for t, f in zip(tiles, foods):
                t.pixmap = food_pixmap(f["key"], 64)        # 有图标用图标, 缺图仍画 emoji
                t.on_hover = (lambda on, f=f: self._hover_food(f if on else None))
            self.food_tabs.append((box, list(zip(tiles, foods))))
        self.food_tiles = [t for _, tl in self.food_tabs for t, _ in tl]
        pg.setGeometry(self.M, self.M, self.W, self.FOOD_Y + 2 * (th + 6) + 68)
        self.pages["food"] = pg
        self._set_food_tab(0)

    def _set_food_tab(self, i):
        self._food_tab = int(i)
        if self.food_seg is not None and self.food_seg.value() != self._food_tab:
            self.food_seg.set_value(self._food_tab)
        if self.food_pager is not None:
            self.food_pager.set_text(f"{self.food_page_names[self._food_tab]}  ·  "
                                     f"{self._food_tab + 1}/{len(self.food_page_names)}")
        for k, (box, _) in enumerate(self.food_tabs):
            box.setVisible(k == self._food_tab)
        self._food_hover = None
        if self.isVisible():
            self.pet.sfx.play("tick")
        self.update()

    def _hover_food(self, f):
        self._food_hover = f
        self.update()

    def _refresh_food_tiles(self):
        st = self.pet.stats
        for _, tl in self.food_tabs:
            for t, f in tl:
                if st.food_known(f["key"]):
                    tname, badge, col = C.TIER_INFO[f["tier"]]
                    t.badge, t.sub, t.sub_color = badge, tname, QColor(col)
                else:
                    t.badge, t.sub, t.sub_color = "", f"{f['region']} · ?", None
                t.update()

    def _paint_food_footer(self, p: QPainter, ox, oy, bw):
        st = self.pet.stats
        y = oy + self.FOOD_Y + 2 * (self.FOOD_TILE[1] + 6) - 2
        r = QRectF(ox + 17, y, bw - 34, 62)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#F3F6FC"))
        p.drawRoundedRect(r, 12, 12)
        r1 = QRectF(r.left() + 10, r.top() + 4, r.width() - 20, 19)
        r2 = QRectF(r.left() + 10, r.top() + 23, r.width() - 20, 36)
        wrap = Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap
        f = self._food_hover
        if f is not None:
            known = st.food_known(f["key"])
            p.setFont(font(12, QFont.DemiBold))
            p.setPen(INK)
            p.drawText(r1, Qt.AlignVCenter | Qt.AlignLeft, f"{f['emoji']} {f['name']}")
            p.setFont(font(10))
            p.setPen(MUTED)
            extra = f"吃过 {st.food_count(f['key'])} 次" if known else f"饱腹 +{f['fill']}"
            p.drawText(r1, Qt.AlignVCenter | Qt.AlignRight, f"{f['region']} · {extra}")
            p.setFont(font(11))
            if known:
                tname, badge, col = C.TIER_INFO[f["tier"]]
                p.setPen(QColor(col))
                txt = f"{badge}{tname}:{f['desc']}"
            else:
                p.setPen(INK2)
                txt = "还没尝过……她会喜欢吗?"
            p.drawText(r2, wrap, txt)
            return
        n = len(C.FOODS)
        known = sum(1 for x in C.FOODS if st.food_known(x["key"]))
        favs = [x for x in C.FOODS if x["tier"] == "fav"]
        fk = [x for x in favs if st.food_known(x["key"])]
        p.setFont(font(12, QFont.DemiBold))
        p.setPen(INK)
        p.drawText(r1, Qt.AlignVCenter | Qt.AlignLeft, f"📖 美食图鉴 {known}/{n}")
        p.setFont(font(10))
        p.setPen(MUTED)
        p.drawText(r1, Qt.AlignVCenter | Qt.AlignRight, f"💗 最爱 {len(fk)}/{len(favs)}")
        p.setFont(font(11))
        p.setPen(INK2)
        if len(fk) == len(favs):
            txt = "最爱全被你找到啦:" + "、".join(x["short"] for x in fk) + "~"
        elif fk:
            txt = f"已发现最爱:{'、'.join(x['short'] for x in fk)}……还有别的哦"
        else:
            txt = "她有几样最喜欢的食物,猜猜看?(也有讨厌的…)"
        p.drawText(r2, wrap, txt)

    def _build_focus(self):
        pg = QWidget(self)
        back = Button("返回", pg, "ghost", "‹", h=28, px=12)
        back.setFixedWidth(70)
        back.move(14, 16)
        back.clicked.connect(lambda: self.show_page("main"))
        self.focus_btns = []
        for i, m in enumerate((15, 25, 45, 60)):
            b = Button(f"{m} 分钟", pg, "soft" if m != 25 else "primary", h=34, px=13)
            b.setFixedWidth(66)
            b.move(17 + i * 72, 92)
            b.clicked.connect(self._act(lambda m=m: self.pet.start_focus(m)))
            self.focus_btns.append(b)
        self.f_pause = Button("暂停", pg, "soft", "⏸️", h=34)
        self.f_pause.setFixedWidth(136)
        self.f_pause.move(17, 128)
        self.f_pause.clicked.connect(self._act(self.pet.toggle_pause_focus))
        self.f_stop = Button("结束", pg, "danger", "", h=34)
        self.f_stop.setFixedWidth(136)
        self.f_stop.move(163, 128)
        self.f_stop.clicked.connect(self._act(self.pet.stop_focus))
        more = Button("打开专注面板", pg, "ghost", "", h=30, px=12)
        more.setFixedWidth(282)
        more.move(17, 174)
        more.clicked.connect(self._act(lambda: self.pet.open_home(1)))
        pg.setGeometry(self.M, self.M, self.W, 214)
        self.pages["focus"] = pg

    # ----- 页面 -----
    def show_page(self, name):
        self.page = name
        for k, w in self.pages.items():
            w.setVisible(k == name)
        h = self.pages[name].height()
        self.resize(self.W + 2 * self.M, h + 2 * self.M)
        if name == "focus":
            run = self.pet.focus_end is not None
            for b in self.focus_btns:
                b.setVisible(not run)
            self.f_pause.setVisible(run)
            self.f_stop.setVisible(run)
            self.f_pause.setText("继续" if self.pet.focus_paused else "暂停")
            self.f_pause.icon = "▶️" if self.pet.focus_paused else "⏸️"
        if name == "food":
            self._food_hover = None
            self._refresh_food_tiles()
        self.pet.sfx.play("tick")
        self.update()

    def open_at(self, gpos: QPoint):
        self._avatar = None
        self.show_page("main")
        scr = QGuiApplication.screenAt(gpos) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        bw = self.W
        bh = self.pages["main"].height()
        x = gpos.x() + 8 if gpos.x() + bw + 20 < g.right() else gpos.x() - bw - 8
        y = gpos.y() - bh // 2
        self.popup_at(QPoint(x, y))
        self.timer.start(500)

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)

    def _refresh_live(self):
        self.update()

    # ----- 绘制 -----
    def paint_content(self, p: QPainter):
        b = self.body()
        pet = self.pet
        st = pet.stats
        ox, oy = b.left(), b.top()
        if self.page == "main":
            paint_header_band(p, QRectF(ox, oy, b.width(), 70), self.radius, time.monotonic() - self._t0)
            if self._avatar is None:
                self._avatar = face_avatar(pet.frames["happy"], 46, _dpr(self), **pet.AVATAR)
            p.drawPixmap(QPointF(ox + 14, oy + 13), self._avatar)
            lv, name, lo, hi = st.level()
            p.setPen(INK)
            p.setFont(font(16, QFont.Bold))
            p.drawText(QRectF(ox + 68, oy + 11, 80, 22), Qt.AlignLeft | Qt.AlignVCenter, "薇斯纳")
            paint_chip(p, ox + 128, oy + 13, f"Lv.{lv} {name}", MINT_D, QColor(255, 255, 255, 200))
            # 好感 + 饱腹 迷你条; 有插件状态条(如心情)时这一行往上挪, 下面再放一条
            ext = pet._ix.status_bars()[:1]
            by = 38 if ext else 40
            frac = 1.0 if hi is None else (st.affection - lo) / max(1, hi - lo)
            self._mini_bar(p, QRectF(ox + 68, oy + by, 104, 7), frac, (MINT, PINK), "💗")
            self._mini_bar(p, QRectF(ox + 192, oy + by, 58, 7), st.hunger / 100, (GOLD, ORANGE), "🍙")
            for e in ext:
                self._mini_bar(p, QRectF(ox + 68, oy + 53, 104, 7), e["frac"], tuple(QColor(c) for c in e["colors"]),
                               e["emoji"])
                p.setFont(font(10))
                p.setPen(INK2)
                p.drawText(QRectF(ox + 178, oy + 48, 80, 16), Qt.AlignVCenter | Qt.AlignLeft, e["text"])
            # 状态行
            y = oy + self.status_y
            r = QRectF(ox + 17, y, b.width() - 34, 28)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#F3F6FC"))
            p.drawRoundedRect(r, 14, 14)
            p.setFont(font(12, QFont.Normal))
            p.setPen(INK2)
            p.drawText(r.adjusted(12, 0, -12, 0), Qt.AlignVCenter | Qt.AlignLeft, self._status_text())
        elif self.page == "food":
            p.setPen(INK)
            p.setFont(font(15, QFont.Bold))
            p.drawText(QRectF(ox + 92, oy + 14, 140, 30), Qt.AlignLeft | Qt.AlignVCenter, "投喂薇斯纳")
            self._mini_bar(p, QRectF(ox + 206, oy + 26, 70, 7), st.hunger / 100, (GOLD, ORANGE), "🍙")
            self._paint_food_footer(p, ox, oy, b.width())
        elif self.page == "focus":
            p.setPen(INK)
            p.setFont(font(15, QFont.Bold))
            p.drawText(QRectF(ox + 92, oy + 14, 160, 30), Qt.AlignLeft | Qt.AlignVCenter, "专注陪伴")
            run = pet.focus_end is not None
            p.setFont(font(12))
            p.setPen(INK2)
            if run:
                rem, total = pet.focus_remaining(), pet.focus_total
                txt = f"{'已暂停' if pet.focus_paused else '专注中'} · 剩余 {rem // 60:02d}:{rem % 60:02d}"
                p.drawText(QRectF(ox + 17, oy + 54, 280, 22), Qt.AlignVCenter | Qt.AlignLeft, txt)
                bar = QRectF(ox + 17, oy + 80, b.width() - 34, 8)
                self._mini_bar(p, bar, 1 - rem / max(1, total), (MINT, LAV), "")
            else:
                p.drawText(QRectF(ox + 17, oy + 54, 280, 30), Qt.AlignVCenter | Qt.AlignLeft,
                           "选个时长,我安静地陪你~")

    def _mini_bar(self, p, r: QRectF, frac, colors, icon):
        frac = max(0.0, min(1.0, frac))
        x = r.left()
        if icon:
            p.setFont(emoji_font(11))
            p.setPen(INK)
            p.drawText(QRectF(x - 1, r.center().y() - 9, 16, 18), Qt.AlignCenter, icon)
            x += 17
        rr = QRectF(x, r.top(), r.right() - x, r.height())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 190) if self.page == "main" else QColor("#EDF1F8"))
        p.drawRoundedRect(rr, rr.height() / 2, rr.height() / 2)
        if frac > 0.01:
            g = QLinearGradient(rr.topLeft(), rr.topRight())
            g.setColorAt(0, colors[0])
            g.setColorAt(1, colors[1])
            p.setBrush(g)
            p.drawRoundedRect(QRectF(rr.left(), rr.top(), max(rr.height(), rr.width() * frac), rr.height()),
                              rr.height() / 2, rr.height() / 2)

    def _status_text(self):
        pet = self.pet
        parts = []
        if pet.focus_end is not None:
            rem = pet.focus_remaining()
            parts.append(f"🍅 {'暂停' if pet.focus_paused else '专注'} {rem // 60:02d}:{rem % 60:02d}")
        if pet.link is not None and pet.cfg["grok_link"]:
            try:
                parts.append(pet.link.status_text())
            except Exception:
                pass
        parts += pet._ix.status_lines()                  # 插件的状态(如: 正在等的小心愿)
        if not parts:
            if pet.stats.hunger < 30:
                parts.append("肚子有点饿了……")
            else:
                h = C.holiday_text()
                parts.append(h or random.Random(int(time.time() // 600)).choice(
                    ["今天也要开心哦~", "右键我可以做好多事~", "在头顶来回摸摸我试试?", "滚轮可以让我转圈圈!"]))
        return "  ·  ".join(parts)


# =====================================================================
#   薇斯纳的小屋
# =====================================================================
class _Row(QWidget):
    """设置行: 左侧 emoji+标题(+说明), 右侧控件"""

    def __init__(self, parent, emoji, title, desc, control, w=332, h=44):
        super().__init__(parent)
        self.emoji, self.title, self.desc = emoji, title, desc
        self.setFixedSize(w, h)
        control.setParent(self)
        if control.width() <= 0 or control.height() <= 0:
            sh = control.sizeHint()
            control.resize(max(control.minimumWidth(), sh.width()), max(control.minimumHeight() or 0, sh.height()))
        control.move(w - control.width() - 4, (h - control.height()) // 2)
        control.raise_()
        control.show()
        self.control = control

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(emoji_font(15))
        p.setPen(INK)
        p.drawText(QRectF(2, 0, 26, self.height()), Qt.AlignCenter, self.emoji)
        p.setFont(font(13, QFont.DemiBold))
        if self.desc:
            p.drawText(QRectF(34, 4, 200, 20), Qt.AlignVCenter | Qt.AlignLeft, self.title)
            p.setFont(font(11))
            p.setPen(MUTED)
            p.drawText(QRectF(34, 23, 230, 16), Qt.AlignVCenter | Qt.AlignLeft, self.desc)
        else:
            p.drawText(QRectF(34, 0, 200, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.title)
        p.setPen(QPen(LINE, 1))
        p.drawLine(QPointF(34, self.height() - 0.5), QPointF(self.width(), self.height() - 0.5))
        p.end()


class _Section(QWidget):
    def __init__(self, parent, text, w=332):
        super().__init__(parent)
        self.text = text
        self.setFixedSize(w, 30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        draw_gem(p, QPointF(7, 18), 4.5, MINT)
        p.setFont(font(12, QFont.Bold))
        p.setPen(MINT_D)
        p.drawText(QRectF(18, 8, 200, 20), Qt.AlignVCenter | Qt.AlignLeft, self.text)
        p.end()


class _Stat(QWidget):
    def __init__(self, parent, emoji, label, tint):
        super().__init__(parent)
        self.emoji, self.label, self.tint, self.value = emoji, label, tint, "0"
        self.setFixedSize(108, 64)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(Qt.NoPen)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, self.tint)
        g.setColorAt(1, QColor("#FFFFFF"))
        p.setBrush(g)
        p.drawRoundedRect(r, 14, 14)
        p.setFont(emoji_font(15))
        p.setPen(INK)
        p.drawText(QRectF(10, 8, 22, 22), Qt.AlignCenter, self.emoji)
        p.setFont(font(11))
        p.setPen(INK2)
        p.drawText(QRectF(34, 8, 72, 22), Qt.AlignVCenter | Qt.AlignLeft, self.label)
        p.setFont(font(19, QFont.Bold))
        p.setPen(INK)
        p.drawText(QRectF(12, 30, 92, 28), Qt.AlignVCenter | Qt.AlignLeft, self.value)
        p.end()


class _Codex(QWidget):
    """表情图鉴格子"""
    CW, CH, COLS = 56, 74, 6

    def __init__(self, parent, pet):
        super().__init__(parent)
        self.pet = pet
        self.hover = -1
        self.thumbs = {}
        self.setMouseTracking(True)
        rows = math.ceil(len(C.CODEX) / self.COLS)
        self.setFixedSize(self.CW * self.COLS, self.CH * rows)
        self.on_hover = None

    def _thumb(self, key, locked):
        ck = (key, locked)
        if ck in self.thumbs:
            return self.thumbs[ck]
        src = self.pet.frame_for_codex(key)
        dpr = _dpr(self)
        S = int(48 * dpr)
        pm = QPixmap(S, S)
        pm.fill(Qt.transparent)
        if src is not None and not src.isNull():
            sc = src.scaled(S, S, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p = QPainter(pm)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawPixmap((S - sc.width()) // 2, (S - sc.height()) // 2, sc)
            if locked:
                p.setCompositionMode(QPainter.CompositionMode_SourceIn)
                p.fillRect(pm.rect(), QColor("#CBD3E6"))
            p.end()
        pm.setDevicePixelRatio(dpr)
        self.thumbs[ck] = pm
        return pm

    def mouseMoveEvent(self, e):
        i = int(e.position().y() // self.CH) * self.COLS + int(e.position().x() // self.CW)
        i = i if 0 <= i < len(C.CODEX) else -1
        if i != self.hover:
            self.hover = i
            self.update()
            if self.on_hover:
                self.on_hover(i)

    def leaveEvent(self, e):
        self.hover = -1
        self.update()
        if self.on_hover:
            self.on_hover(-1)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        st = self.pet.stats
        for i, (key, name, hint) in enumerate(C.CODEX):
            x, y = (i % self.COLS) * self.CW, (i // self.COLS) * self.CH
            locked = not st.seen(key)
            box = QRectF(x + 3, y + 2, self.CW - 6, self.CW - 6)
            p.setPen(Qt.NoPen)
            hov = i == self.hover
            if locked:
                p.setBrush(QColor("#F1F4FA") if not hov else QColor("#E9EEF8"))
            else:
                g = QLinearGradient(box.topLeft(), box.bottomLeft())
                g.setColorAt(0, QColor("#F3FBF9") if not hov else MINT_L)
                g.setColorAt(1, QColor("#FFFFFF"))
                p.setBrush(g)
            p.drawRoundedRect(box, 12, 12)
            if hov:
                p.setPen(QPen(MINT, 1.4))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(box, 12, 12)
            pm = self._thumb(key, locked)
            p.drawPixmap(QPointF(box.center().x() - 24, box.center().y() - 24), pm)
            if locked:
                p.setPen(QColor("#A3AEC8"))
                p.setFont(font(16, QFont.Bold))
                p.drawText(box, Qt.AlignCenter, "?")
            p.setFont(font(10, QFont.DemiBold if not locked else QFont.Normal))
            p.setPen(INK2 if not locked else MUTED)
            p.drawText(QRectF(x, y + self.CW - 3, self.CW, 16), Qt.AlignHCenter | Qt.AlignTop,
                       name if not locked else "???")
        p.end()


class HomePanel(CardWindow):
    W, H = 380, 600
    TABS = ["状态", "专注", "图鉴", "设置"]

    def __init__(self, pet):
        super().__init__(self.W, self.H, topmost=pet.cfg["topmost"], drag_h=112)
        self.pet = pet
        self.radius = 24
        self._t0 = time.monotonic()
        self._avatar = None
        self.close_btn = CloseButton(self)
        self.close_btn.move(self.M + self.W - 40, self.M + 12)
        self.close_btn.clicked.connect(self.hide)
        self.tabs = Tabs(self.TABS, self)
        self.tabs.setGeometry(self.M + 18, self.M + 116, self.W - 36, 36)
        self.tabs.changed.connect(self._switch)
        self.pages = []
        area = QRect(self.M + 18, self.M + 162, self.W - 36, self.H - 162 - 14)
        self.area = area
        for build in (self._build_status, self._build_focus, self._build_codex, self._build_settings):
            pg = QWidget(self)
            pg.setGeometry(area)
            build(pg)
            pg.hide()
            self.pages.append(pg)
        self.pages[0].show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    # ----- 状态页 -----
    def _build_status(self, pg):
        w = self.area.width()
        self.aff_bar = Bar(pg, (MINT, PINK), 10)
        self.aff_bar.setGeometry(0, 26, w, 10)
        self.hun_bar = Bar(pg, (GOLD, ORANGE), 10)
        self.hun_bar.setGeometry(0, 74, w, 10)
        self.ext_bar = Bar(pg, (MINT, PINK), 10)        # 插件状态条(如心情), 有才显示
        self.ext_bar.setGeometry(0, 122, w, 10)
        self.ext_bar.hide()
        self._ext, self._ext_dy = None, 0
        self.fortune_btn = Button("抽一签", pg, "gold", "🔮", h=30, px=12)
        self.fortune_btn.setFixedWidth(96)
        self.fortune_btn.move(w - 96 - 14, 112 + 25)
        self.fortune_btn.clicked.connect(self.pet.open_fortune)
        specs = [("📅", "相伴天数", MINT_L), ("🤚", "摸头", PINK_L), ("🍰", "投喂", GOLD_L),
                 ("🦋", "蝴蝶", QColor("#EEEAFE")), ("🍅", "专注分钟", QColor("#FFEDE6")), ("✊", "猜拳胜场", QColor("#E6F3FE"))]
        self.stat_cards = []
        for i, (e, l, t) in enumerate(specs):
            c = _Stat(pg, e, l, t)
            c.move((i % 3) * (108 + 9), 212 + (i // 3) * 72)
            self.stat_cards.append(c)
        self.status_pg = pg
        pg.paintEvent = lambda ev, pg=pg: self._paint_status(pg)

    def _layout_status(self, dy):
        """有插件状态条时, 运势卡和统计格整体往下挪 dy"""
        w = self.area.width()
        self.fortune_btn.move(w - 96 - 14, 112 + 25 + dy)
        for i, c in enumerate(self.stat_cards):
            c.move((i % 3) * (108 + 9), 212 + dy + (i // 3) * 72)

    def _paint_status(self, pg):
        p = QPainter(pg)
        p.setRenderHint(QPainter.Antialiasing)
        st = self.pet.stats
        w = pg.width()
        lv, name, lo, hi = st.level()
        p.setFont(font(13, QFont.DemiBold))
        p.setPen(INK)
        p.drawText(QRectF(0, 0, 200, 22), Qt.AlignVCenter | Qt.AlignLeft, "💗 好感度")
        p.setFont(font(12))
        p.setPen(INK2)
        right = f"{int(st.affection)} / {hi}" if hi else f"{int(st.affection)} · 满级"
        p.drawText(QRectF(0, 0, w, 22), Qt.AlignVCenter | Qt.AlignRight, right)
        p.setFont(font(13, QFont.DemiBold))
        p.setPen(INK)
        p.drawText(QRectF(0, 48, 200, 22), Qt.AlignVCenter | Qt.AlignLeft, "🍙 饱腹度")
        p.setFont(font(12))
        p.setPen(INK2)
        hv = st.hunger
        mood = "饱饱的~" if hv > 80 else ("刚刚好" if hv > 45 else ("有点饿" if hv > 20 else "好饿……"))
        p.drawText(QRectF(0, 48, w, 22), Qt.AlignVCenter | Qt.AlignRight, f"{int(hv)}% · {mood}")
        dy = self._ext_dy
        if self._ext:                                     # 插件状态条(如心情), 和饱腹一样的样式
            e = self._ext
            p.setFont(font(13, QFont.DemiBold))
            p.setPen(INK)
            p.drawText(QRectF(0, 96, 200, 22), Qt.AlignVCenter | Qt.AlignLeft, f"{e['emoji']} {e['title']}")
            p.setFont(font(12))
            p.setPen(INK2)
            p.drawText(QRectF(0, 96, w, 22), Qt.AlignVCenter | Qt.AlignRight, e["text"])
        # 今日运势卡
        r = QRectF(0, 104 + dy, w, 92)
        p.setPen(Qt.NoPen)
        g = QLinearGradient(r.topLeft(), r.topRight())
        g.setColorAt(0, QColor("#FFF7E2"))
        g.setColorAt(1, QColor("#FFEFF4"))
        p.setBrush(g)
        p.drawRoundedRect(r, 16, 16)
        f = self.pet.today_fortune()
        if f:
            p.setFont(font(12))
            p.setPen(INK2)
            p.drawText(QRectF(16, 112 + dy, 200, 20), Qt.AlignVCenter | Qt.AlignLeft, "🔮 今日运势")
            p.setFont(font(26, QFont.Black))
            p.setPen(QColor(f["tier_color"]))
            p.drawText(QRectF(16, 132 + dy, 120, 38), Qt.AlignVCenter | Qt.AlignLeft, f["tier"])
            p.setFont(font(11))
            p.setPen(MINT_D)
            p.drawText(QRectF(16 + 92, 136 + dy, 180, 16), Qt.AlignVCenter | Qt.AlignLeft, "宜 " + " · ".join(f["good"]))
            p.setPen(PINK_D)
            p.drawText(QRectF(16 + 92, 154 + dy, 180, 16), Qt.AlignVCenter | Qt.AlignLeft, "忌 " + " · ".join(f["bad"]))
            p.setPen(INK2)
            p.drawText(QRectF(16, 172 + dy, w - 32, 18), Qt.AlignVCenter | Qt.AlignLeft,
                       f"幸运色 {f['lucky_color'][0]} · 幸运物 {f['lucky_item']}")
        else:
            p.setFont(font(14, QFont.Bold))
            p.setPen(INK)
            p.drawText(QRectF(16, 118 + dy, 220, 24), Qt.AlignVCenter | Qt.AlignLeft, "🔮 今天的运势还没抽~")
            p.setFont(font(12))
            p.setPen(INK2)
            p.drawText(QRectF(16, 146 + dy, 220, 40), Qt.AlignLeft | Qt.TextWordWrap, "让薇斯纳用蝴蝶法杖帮你占卜一下吧!")
        p.end()

    # ----- 专注页 -----
    def _build_focus(self, pg):
        w = self.area.width()
        self.ring = Ring(pg, 190)
        self.ring.move((w - 190) // 2, 4)
        self.seg = Segmented([(15, "15 分"), (25, "25 分"), (45, "45 分"), (60, "60 分")], 25, pg, h=30, px=12)
        self.seg.move((w - self.seg.width()) // 2, 206)
        self.seg.changed.connect(lambda v: self._refresh_focus())
        self.f_start = Button("开始专注", pg, "primary", "🍅", h=38, px=14)
        self.f_start.setFixedWidth(200)
        self.f_start.move((w - 200) // 2, 252)
        self.f_start.clicked.connect(lambda: self.pet.start_focus(self.seg.value()))
        self.f_pause = Button("暂停", pg, "soft", "⏸️", h=38, px=14)
        self.f_pause.setFixedWidth(150)
        self.f_pause.move(w // 2 - 156, 252)
        self.f_pause.clicked.connect(self.pet.toggle_pause_focus)
        self.f_stop = Button("结束", pg, "danger", "", h=38, px=14)
        self.f_stop.setFixedWidth(150)
        self.f_stop.move(w // 2 + 6, 252)
        self.f_stop.clicked.connect(self.pet.stop_focus)
        self.focus_info = Label("", pg, 12, INK2, align=Qt.AlignCenter, h=20)
        self.focus_info.setGeometry(0, 304, w, 20)
        tip = Label("专注期间她会安静陪着你,不主动搭话~", pg, 11, MUTED, align=Qt.AlignCenter, h=18)
        tip.setGeometry(0, 328, w, 18)

    def _refresh_focus(self):
        pet = self.pet
        run = pet.focus_end is not None
        self.f_start.setVisible(not run)
        self.seg.setEnabled(not run)
        self.f_pause.setVisible(run)
        self.f_stop.setVisible(run)
        if run:
            rem, total = pet.focus_remaining(), max(1, pet.focus_total)
            self.ring.frac = 1 - rem / total
            self.ring.big = f"{rem // 60:02d}:{rem % 60:02d}"
            self.ring.small = "已暂停" if pet.focus_paused else "专注中 · 我在陪你"
            self.ring.running = not pet.focus_paused
            self.f_pause.setText("继续" if pet.focus_paused else "暂停")
            self.f_pause.icon = "▶️" if pet.focus_paused else "⏸️"
            self.f_pause.update()
        else:
            m = self.seg.value()
            self.ring.frac = 0.0
            self.ring.big = f"{m:02d}:00"
            self.ring.small = "准备好了吗?"
            self.ring.running = False
        st = pet.stats
        self.focus_info.set_text(f"今天已专注 {st.d['daily'].get('focus_min', 0)} 分钟 · 累计完成 {st.d['focus_sessions']} 次")
        self.ring.update()

    # ----- 图鉴页 -----
    def _build_codex(self, pg):
        w = self.area.width()
        self.codex_bar = Bar(pg, (MINT, LAV), 8)
        self.codex_bar.setGeometry(0, 28, w, 8)
        self.codex = _Codex(pg, self.pet)
        self.codex.move((w - self.codex.width()) // 2, 48)
        self.codex_hint = Label("把鼠标放到格子上看解锁提示", pg, 12, INK2, align=Qt.AlignCenter, h=22)
        self.codex_hint.setGeometry(0, 48 + self.codex.height() + 6, w, 22)
        self.codex.on_hover = self._codex_hover
        self.codex_title = Label("", pg, 13, INK, QFont.DemiBold, h=22)
        self.codex_title.setGeometry(0, 0, w, 22)

    def _codex_hover(self, i):
        if i < 0:
            self.codex_hint.set_text("把鼠标放到格子上看解锁提示")
            return
        key, name, hint = C.CODEX[i]
        if self.pet.stats.seen(key):
            self.codex_hint.set_text(f"「{name}」已收集 ✓")
        else:
            self.codex_hint.set_text(f"提示:{hint}")

    def _refresh_codex(self):
        n = sum(1 for k, _, _ in C.CODEX if self.pet.stats.seen(k))
        self.codex_title.set_text(f"🖼️ 表情图鉴  {n} / {len(C.CODEX)}")
        self.codex_bar.set_value(n / len(C.CODEX))
        self.codex.thumbs.clear()
        self.codex.update()

    # ----- 设置页 -----
    def _build_settings(self, pg):
        pet = self.pet
        cfg = pet.cfg
        sa = QScrollArea(pg)
        sa.setGeometry(0, 0, pg.width(), pg.height())
        sa.setWidgetResizable(False)
        sa.setFrameShape(QScrollArea.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setStyleSheet("""
            QScrollArea{background:transparent;} QWidget#inner{background:transparent;}
            QScrollBar:vertical{background:transparent;width:8px;margin:4px 0 4px 0;}
            QScrollBar::handle:vertical{background:#D5DCEB;border-radius:4px;min-height:30px;}
            QScrollBar::handle:vertical:hover{background:#4FC7B5;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
            QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}
        """)
        sa.viewport().setAutoFillBackground(False)
        inner = QWidget()
        inner.setObjectName("inner")
        inner.setAttribute(Qt.WA_TranslucentBackground, True)
        RW = pg.width() - 14
        y = 0
        self.ctl = {}

        def section(t):
            nonlocal y
            s = _Section(inner, t, RW)
            s.move(0, y)
            y += 30

        def row(key, emoji, title, desc, control):
            nonlocal y
            r = _Row(inner, emoji, title, desc, control, RW)
            r.move(0, y)
            y += r.height()
            self.ctl[key] = control
            return control

        def toggle(key, emoji, title, desc, fn):
            t = Toggle(None, bool(cfg[key]))
            t.toggled.connect(fn)
            return row(key, emoji, title, desc, t)

        section("外观")
        sz = Segmented([("small", "小"), ("medium", "中"), ("large", "大")], cfg["size"], None, h=28)
        sz.changed.connect(pet.set_size)
        row("size", "📏", "大小", "", sz)
        toggle("topmost", "📌", "窗口置顶", "", pet.set_topmost)
        toggle("fx", "✨", "粒子特效", "爱心、星星、彩带等", pet.set_fx)
        section("互动")
        bub = Toggle(None, not cfg["mute"])
        bub.toggled.connect(lambda on: pet.set_mute(not on))
        row("bubble", "💬", "说话气泡", "关掉后只在你点她时说话", bub)
        toggle("sfx", "🔔", "音效", "点击、跳跃、吃东西的小声音", pet.set_sfx)
        toggle("walk", "👣", "自由散步", "闲着时会自己走来走去", pet.set_walk)
        toggle("butterfly", "🦋", "蝴蝶来访", "偶尔有小蝴蝶飞来,点它能抓住", pet.set_butterfly)
        toggle("peek", "🫣", "边缘探头", "拖到屏幕左/右/上边会探头", pet.set_peek)
        section("提醒")
        wt = Segmented([(0, "关"), (30, "30"), (45, "45"), (60, "60"), (90, "90")], cfg["water_min"], None, h=26, px=11)
        wt.changed.connect(pet.set_water)
        row("water_min", "💧", "喝水提醒", "间隔(分钟)", wt)
        sit = Segmented([(0, "关"), (60, "60"), (90, "90"), (120, "120")], cfg["sit_min"], None, h=26, px=11)
        sit.changed.connect(pet.set_sit)
        row("sit_min", "🧘", "久坐提醒", "间隔(分钟)", sit)
        toggle("chime", "🕐", "整点报时", "", pet.set_chime)
        section("联动")
        toggle("grok_link", "🤖", "联动 Grok App", "只读日志,不联网不读对话", pet.set_link)
        self.ctl_ext = []                    # 互动扩展注册的设置行(没装扩展就是空, 面板和原版一样)
        hub = getattr(pet, "_ix", None)
        ext = hub.settings_rows() if hub is not None and hasattr(hub, "settings_rows") else []
        if ext:
            section("扩展")
            for r in ext:
                ctl = r["control"]
                if ctl.width() <= 0 or ctl.height() <= 0:      # 防宽度 0 点不了
                    ctl.resize(ctl.sizeHint())
                rw = _Row(inner, str(r.get("emoji", "🧩")), str(r.get("title", "")), str(r.get("desc", "")), ctl, RW)
                rw.move(0, y)
                y += rw.height()
                self.ctl_ext.append(r)
        section("其他")
        def action_btn(text, icon, kind, slot):
            # Button 只设了 minimumWidth, 无父控件时 width 常为 0, 放进行后点中区域为空
            b = Button(text, inner, kind, icon, h=30, px=12)
            b.resize(b.sizeHint())
            b.clicked.connect(slot)
            return b
        row("force_sleep", "😴", "立刻睡着", "马上进入睡眠,方便试睡着时的互动",
            action_btn("睡着", "😴", "soft", pet.force_sleep))
        row("reset", "🧭", "找不到她了?", "把她放回主屏幕右下角",
            action_btn("回到桌面", "🏠", "soft", pet.reset_position))
        row("data", "🗂️", "数据文件夹", "配置、存档与日志",
            action_btn("打开", "📂", "soft", pet.open_data_dir))
        row("quit", "👋", "退出薇斯纳", "",
            action_btn("退出", "", "danger", pet.quit_requested.emit))
        y += 10
        inner.setFixedSize(RW, y)
        sa.setWidget(inner)

    def sync_settings(self):
        cfg = self.pet.cfg
        for key, ctl in self.ctl.items():
            if isinstance(ctl, Toggle):
                ctl.set_silent(bool(cfg[key]) if key != "bubble" else not cfg["mute"])
            elif isinstance(ctl, Segmented):
                ctl.set_value(cfg[key])
        for r in getattr(self, "ctl_ext", ()):
            f = r.get("sync")
            if f is not None:
                try:
                    f()
                except Exception:
                    pass

    # ----- 通用 -----
    def _switch(self, i):
        for k, pg in enumerate(self.pages):
            pg.setVisible(k == i)
        self._refresh()
        self.pet.sfx.play("tick")

    def _refresh(self):
        st = self.pet.stats
        lv, name, lo, hi = st.level()
        self.aff_bar.set_value(1.0 if hi is None else (st.affection - lo) / max(1, hi - lo))
        self.hun_bar.set_value(st.hunger / 100)
        bars = self.pet._ix.status_bars()[:1]           # 插件状态条(如心情); 这里只放得下一条
        self._ext = bars[0] if bars else None
        dy = 48 if self._ext else 0
        if dy != self._ext_dy:
            self._ext_dy = dy
            self._layout_status(dy)
        if self._ext:
            self.ext_bar.colors = tuple(QColor(c) for c in self._ext["colors"])
            self.ext_bar.set_value(self._ext["frac"])
        self.ext_bar.setVisible(self._ext is not None)
        vals = [st.d["days_met"], st.d["pets"], st.d["feeds"], st.d["butterflies"], st.d["focus_minutes"], st.d["rps_win"]]
        for c, v in zip(self.stat_cards, vals):
            c.value = str(v)
            c.update()
        self.fortune_btn.setVisible(self.pet.today_fortune() is None)
        self._refresh_focus()
        if self.tabs.idx == 2:
            self._refresh_codex()
        self.update()

    def open(self, tab=0):
        self._avatar = None
        self.sync_settings()
        self.tabs.set_index(tab, animate=False)
        if not self.isVisible():
            self.popup_at(place_near_pet(self, self.pet, self.W, self.H))
        else:
            self.raise_()
        self._refresh()
        self.timer.start(250)

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)

    def _tick(self):
        if self.tabs.idx == 1:
            self._refresh_focus()
        elif self.tabs.idx == 0 and int(time.monotonic() * 4) % 8 == 0:
            self._refresh()
        self.update(QRect(self.M, self.M, self.W, 112))

    def paint_content(self, p: QPainter):
        b = self.body()
        t = time.monotonic() - self._t0
        paint_header_band(p, QRectF(b.left(), b.top(), b.width(), 108), self.radius, t)
        pet = self.pet
        if self._avatar is None:
            self._avatar = face_avatar(pet.frames["happy"], 72, _dpr(self), **pet.AVATAR)
        p.drawPixmap(QPointF(b.left() + 20, b.top() + 18), self._avatar)
        st = pet.stats
        lv, name, lo, hi = st.level()
        p.setPen(INK)
        p.setFont(font(20, QFont.Bold))
        p.drawText(QRectF(b.left() + 104, b.top() + 20, 120, 30), Qt.AlignVCenter | Qt.AlignLeft, "薇斯纳")
        paint_chip(p, b.left() + 182, b.top() + 26, f"Lv.{lv} · {name}", MINT_D, QColor(255, 255, 255, 210), 11, 20)
        p.setFont(font(12))
        p.setPen(INK2)
        p.drawText(QRectF(b.left() + 104, b.top() + 54, 250, 20), Qt.AlignVCenter | Qt.AlignLeft,
                   f"冬契的蝴蝶小魔女 · 相伴第 {st.d['days_met']} 天")
        p.setFont(font(11))
        p.setPen(MUTED)
        mood = pet.mood_text()
        p.drawText(QRectF(b.left() + 104, b.top() + 74, 250, 18), Qt.AlignVCenter | Qt.AlignLeft, mood)


# =====================================================================
#   今日运势
# =====================================================================
class FortuneCard(CardWindow):
    W, H = 320, 456

    def __init__(self, pet):
        super().__init__(self.W, self.H, topmost=pet.cfg["topmost"], drag_h=60)
        self.pet = pet
        self.radius = 24
        self.data = None
        self.t0 = 0.0
        self._avatar = None
        self.close_btn = CloseButton(self)
        self.close_btn.move(self.M + self.W - 40, self.M + 12)
        self.close_btn.clicked.connect(self.hide)
        self.ok = Button("收下好运~", self, "pink", "💝", h=36, px=13)
        self.ok.setFixedWidth(150)
        self.ok.move(self.M + (self.W - 150) // 2, self.M + self.H - 52)
        self.ok.clicked.connect(self.hide)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def open(self, data, fresh):
        self.data = data
        self.fresh = fresh
        self.t0 = time.monotonic() - (0 if fresh else 5)
        self._avatar = None
        self.popup_at(place_near_pet(self, self.pet, self.W, self.H))
        self.timer.start(16)

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)

    def paint_bg(self, p):
        from ui_kit import draw_card
        draw_card(p, self.body(), self.radius, 18, QColor("#FFF6E8"), QColor(245, 196, 81, 90))

    def paint_content(self, p: QPainter):
        if not self.data:
            return
        d = self.data
        b = self.body()
        t = time.monotonic() - self.t0
        cx = b.center().x()
        # 标题
        p.setPen(GOLD_D)
        p.setFont(font(13, QFont.Bold))
        p.drawText(QRectF(b.left(), b.top() + 16, b.width(), 22), Qt.AlignCenter, "✦  今 日 运 势  ✦")
        dd = date.fromisoformat(d["date"])
        p.setFont(font(11))
        p.setPen(INK2)
        p.drawText(QRectF(b.left(), b.top() + 38, b.width(), 18), Qt.AlignCenter,
                   f"{dd.month}月{dd.day}日 · 星期{WEEK[dd.weekday()]}")
        # 魔法阵 + 签
        cy = b.top() + 140
        R = 68
        p.save()
        p.translate(cx, cy)
        p.rotate(t * 12)
        p.setPen(QPen(alpha(GOLD, 120), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), R + 16, R + 16)
        p.setPen(QPen(alpha(LAV, 110), 1.0, Qt.DashLine))
        p.drawEllipse(QPointF(0, 0), R + 9, R + 9)
        for i in range(8):
            a = i * math.pi / 4
            p.setPen(Qt.NoPen)
            p.setBrush(alpha(GOLD, 200))
            p.drawPath(sparkle_path(QPointF(math.cos(a) * (R + 16), math.sin(a) * (R + 16)), 4))
        p.restore()
        shuffle = t < 1.1
        if shuffle:
            tiers = [x[0] for x in C.TIERS]
            tier = tiers[int(t * 14) % len(tiers)]
            col = QColor(dict((x[0], x[2]) for x in C.TIERS)[tier])
            s = 0.92
        else:
            tier, col = d["tier"], QColor(d["tier_color"])
            s = 0.6 + 0.4 * ease_out_back(min(1.0, (t - 1.1) / 0.35))
        g = QRadialGradient(QPointF(cx - 18, cy - 22), R * 1.3)
        g.setColorAt(0, col.lighter(150))
        g.setColorAt(1, col)
        p.save()
        p.translate(cx, cy)
        p.scale(s, s)
        p.setPen(QPen(QColor("white"), 5))
        p.setBrush(g)
        p.drawEllipse(QPointF(0, 0), R, R)
        p.setPen(QPen(alpha(QColor("white"), 120), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), R - 9, R - 9)
        p.setFont(font(40 if len(tier) <= 2 else 34, QFont.Black))
        p.setPen(alpha(col.darker(160), 90))
        p.drawText(QRectF(-R, -R + 3, 2 * R, 2 * R), Qt.AlignCenter, tier)
        p.setPen(QColor("white"))
        p.drawText(QRectF(-R, -R, 2 * R, 2 * R), Qt.AlignCenter, tier)
        p.restore()
        if shuffle:
            return
        k = min(1.0, (t - 1.2) / 0.4)
        p.setOpacity(max(0.0, k))
        # 星级
        y = cy + R + 22
        for i in range(5):
            on = i < d["stars"]
            path = QPainterPath()
            for j in range(10):
                rr = 8 if j % 2 == 0 else 3.6
                a = -math.pi / 2 + j * math.pi / 5
                pt = QPointF(cx - 48 + i * 24 + math.cos(a) * rr, y + math.sin(a) * rr)
                path.moveTo(pt) if j == 0 else path.lineTo(pt)
            path.closeSubpath()
            p.setPen(QPen(GOLD_D if on else QColor("#D8DEEA"), 1))
            p.setBrush(GOLD if on else QColor("#EEF1F7"))
            p.drawPath(path)
        # 宜 / 忌
        y += 22
        colw = (b.width() - 40) / 2
        for ci, (lab, items, fg, bg) in enumerate((("宜", d["good"], MINT_D, MINT_L), ("忌", d["bad"], PINK_D, PINK_L))):
            x = b.left() + 16 + ci * (colw + 8)
            r = QRectF(x, y, colw, 70)
            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(r, 14, 14)
            p.setBrush(fg)
            p.drawEllipse(QRectF(x + 10, y + 10, 22, 22))
            p.setPen(QColor("white"))
            p.setFont(font(12, QFont.Bold))
            p.drawText(QRectF(x + 10, y + 10, 22, 22), Qt.AlignCenter, lab)
            p.setPen(INK)
            p.setFont(font(12, QFont.DemiBold))
            for j, it in enumerate(items):
                p.drawText(QRectF(x + 38, y + 8 + j * 26, colw - 42, 26), Qt.AlignVCenter | Qt.AlignLeft, it)
        # 幸运
        y += 82
        lc_name, lc_hex = d["lucky_color"]
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(lc_hex))
        p.drawEllipse(QRectF(b.left() + 20, y + 3, 14, 14))
        p.setPen(INK2)
        p.setFont(font(11))
        p.drawText(QRectF(b.left() + 40, y, 120, 20), Qt.AlignVCenter | Qt.AlignLeft, f"幸运色 {lc_name}")
        p.drawText(QRectF(b.left() + 130, y, 110, 20), Qt.AlignVCenter | Qt.AlignLeft, f"🍀 {d['lucky_item']}")
        p.drawText(QRectF(b.left() + 236, y, 70, 20), Qt.AlignVCenter | Qt.AlignLeft, f"🔢 {d['lucky_num']}")
        # 薇斯纳的话
        y += 28
        if self._avatar is None:
            self._avatar = face_avatar(self.pet.frames["happy"], 34, _dpr(self), **self.pet.AVATAR)
        p.drawPixmap(QPointF(b.left() + 16, y), self._avatar)
        r = QRectF(b.left() + 56, y - 2, b.width() - 72, 40)
        p.setPen(QPen(alpha(GOLD, 120), 1))
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawRoundedRect(r, 12, 12)
        p.setPen(INK)
        p.setFont(font(11))
        p.drawText(r.adjusted(10, 2, -8, -2), Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap, d["word"])
        p.setOpacity(1.0)


# =====================================================================
#   猜拳
# =====================================================================
class RpsCard(CardWindow):
    W, H = 320, 352
    HANDS = [("rock", "✊", "石头"), ("scissors", "✌️", "剪刀"), ("paper", "✋", "布")]
    BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

    def __init__(self, pet):
        super().__init__(self.W, self.H, topmost=pet.cfg["topmost"], drag_h=56)
        self.pet = pet
        self.radius = 24
        self.me = self.her = None
        self.score = [0, 0]
        self.result = ""
        self.rolling_until = 0.0
        self._avatar = None
        self.close_btn = CloseButton(self)
        self.close_btn.move(self.M + self.W - 40, self.M + 12)
        self.close_btn.clicked.connect(self.hide)
        self.btns = []
        for i, (k, e, n) in enumerate(self.HANDS):
            t = IconTile(e, n, self, size=(84, 84), tint=MINT_L)
            t.move(self.M + 20 + i * 96, self.M + self.H - 104)
            # clicked(bool) 会盖住默认参数; 忽略信号参数, 只传手势 key
            t.clicked.connect(lambda *_args, k=k: self.play(k))
            self.btns.append(t)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def open(self):
        self._avatar = None
        self.me = self.her = None
        self.result = "出拳吧!"
        self.popup_at(place_near_pet(self, self.pet, self.W, self.H))
        self.timer.start(16)

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)

    def play(self, k):
        if time.monotonic() < self.rolling_until:
            return
        self.me = k
        self.her = random.choice([h[0] for h in self.HANDS])
        self.rolling_until = time.monotonic() + 0.75
        self.result = "薇斯纳在想……"
        for b in self.btns:
            b.setEnabled(False)
        self.pet.sfx.play("tick")
        QTimer.singleShot(780, self._reveal)

    def _reveal(self):
        for b in self.btns:
            b.setEnabled(True)
        if self.me not in self.BEATS or self.her not in self.BEATS:
            self.result = "出拳失败,再点一次~"
            self.update()
            return
        if self.me == self.her:
            res = "draw"
            self.result = random.choice(["平局!再来一次~", "心有灵犀?平局!"])
        elif self.BEATS[self.me] == self.her:
            res = "win"
            self.score[0] += 1
            self.result = random.choice(["你赢啦……下次不会让你的!", "呜,输了……"])
        else:
            res = "lose"
            self.score[1] += 1
            self.result = random.choice(["我赢啦!嘿嘿~", "耶!薇斯纳胜利!"])
        self.pet.on_rps(res)
        self.update()

    def _tick(self):
        self.update()

    def paint_content(self, p: QPainter):
        b = self.body()
        p.setPen(INK)
        p.setFont(font(16, QFont.Bold))
        p.drawText(QRectF(b.left() + 20, b.top() + 14, 200, 28), Qt.AlignVCenter | Qt.AlignLeft, "✊ 和薇斯纳猜拳")
        p.setFont(font(12, QFont.DemiBold))
        p.setPen(INK2)
        p.drawText(QRectF(b.left() + 20, b.top() + 42, 200, 20), Qt.AlignVCenter | Qt.AlignLeft,
                   f"你 {self.score[0]}  :  {self.score[1]} 薇斯纳")
        cy = b.top() + 128
        now = time.monotonic()
        rolling = now < self.rolling_until
        emo = dict((h[0], h[1]) for h in self.HANDS)
        for side in (0, 1):
            cx = b.center().x() + (-74 if side == 0 else 74)
            r = 44
            g = QRadialGradient(QPointF(cx - 10, cy - 12), r * 1.4)
            g.setColorAt(0, QColor("#FFFFFF"))
            g.setColorAt(1, PINK_L if side == 0 else MINT_L)
            p.setPen(QPen(PINK if side == 0 else MINT, 2))
            p.setBrush(g)
            p.drawEllipse(QPointF(cx, cy), r, r)
            if side == 0:
                if rolling:
                    hand = self.HANDS[int(now * 12) % 3][1]
                    bounce = -6 * abs(math.sin(now * 14))
                else:
                    hand = emo[self.her] if self.her else "❔"
                    bounce = 0
            else:
                hand = emo[self.me] if self.me else "❔"
                bounce = -6 * abs(math.sin(now * 14)) if rolling else 0
            p.setFont(emoji_font(40))
            p.drawText(QRectF(cx - r, cy - r + bounce, 2 * r, 2 * r), Qt.AlignCenter, hand)
            p.setFont(font(11, QFont.DemiBold))
            p.setPen(INK2)
            p.drawText(QRectF(cx - 50, cy + r + 4, 100, 18), Qt.AlignCenter, "薇斯纳" if side == 0 else "你")
        if self._avatar is None:
            self._avatar = face_avatar(self.pet.frames["happy"], 26, _dpr(self), **self.pet.AVATAR)
        p.drawPixmap(QPointF(b.center().x() - 74 + 20, cy - 66), self._avatar)
        p.setFont(font(15, QFont.Black))
        p.setPen(alpha(INK, 140))
        p.drawText(QRectF(b.center().x() - 30, cy - 14, 60, 28), Qt.AlignCenter, "VS")
        p.setFont(font(13, QFont.DemiBold))
        p.setPen(INK)
        p.drawText(QRectF(b.left(), cy + 70, b.width(), 22), Qt.AlignCenter, self.result)
