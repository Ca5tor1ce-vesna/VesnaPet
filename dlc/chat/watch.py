# -*- coding: utf-8 -*-
"""最近 20 秒的互动 / 空闲动作 → 场景备忘。不改桌宠。
新版桌宠(live v2): 优先用事件推送(LiveSub), 快照轮询只拿当前状态和推送没覆盖的变化;
旧版桌宠(不认 subscribe): 完全退回快照 diff 推断。"""
import json
import time
from collections import deque
from datetime import datetime

from PySide6.QtCore import QMetaObject, QObject, QThread, QTimer, Qt, Signal, Slot

from live import LiveClient, LiveSub

WINDOW = 20.0          # 普通互动/台词保留多久
KEY_WINDOW = 20.0     # 喂食、整蛊、被丢等重要互动保留更久
MAX_LINES = 14
KEY_MARK = ("（互动）", "（整蛊）")


def _is_key(text):
    return any(m in text for m in KEY_MARK) or "劲儿" in text


STATE_LINE = {
    "idle": None,
    "happy": "自己开心了一下（空闲动作）",
    "wave": "挥了挥手（空闲动作）",
    "stretch": "伸了个懒腰（空闲动作）",
    "yawn": "打了个哈欠（空闲动作）",
    "cheer": "欢呼了一下（空闲动作）",
    "look": "往右边张望（空闲动作）",
    "look_left": "往左边张望（空闲动作）",
    "surprised": "被吓了一跳（互动）",
    "angry": "生气了（互动）",
    "content": "被摸头了，很舒服（互动）",
    "shy": "害羞了（互动）",
    "dizzy": "转晕了（互动）",
    "eat": "在吃东西",
    "love": "吃到最爱，超开心",
    "sleep": "睡着了",
    "focus": "认真起来了",
}


WAKE_LINE = {
    "pet": "被你摸头叫醒了，伸了个懒腰（互动）",
    "drag": "睡着时被你拎起来弄醒了，有点起床气（互动）",
    "spin": "睡着时被你转醒了，晕乎乎地生气（互动）",
    "click": "被你点醒了（互动）",
    "feed": "被你用吃的叫醒了（互动）",
    "butterfly": "被蝴蝶弄醒了",
    "back": "你回来了，她伸个懒腰醒过来迎接你",
    "reminder": "她自己醒过来提醒你",
}
IDLE_LINE = {
    "happy": "自己开心了一下（空闲动作）",
    "look": "左右张望了一下（空闲动作）",
    "stretch": "伸了个懒腰（空闲动作）",
    "hop": "原地蹦了一下（空闲动作）",
    "wave": "挥了挥手（空闲动作）",
    "walk": "她自己走起来了（空闲动作）",
    "sneak": "偷偷吃起了零食（空闲动作）",
}
MAKEUP_LINE = {
    "pet": "你摸头把她哄好了（互动）",
    "food": "你用好吃的把她哄好了（互动）",
    "click": "你轻轻点了几下，她消气了（互动）",
    "time": "她自己消气了",
}
BUTTERFLY_LINE = {
    "come": "一只小蝴蝶飞来了",
    "caught": "你抓到了蝴蝶，她很开心（互动）",
    "landed": "蝴蝶落在了她头上",
    "giveup": "她追蝴蝶没追上，有点失落",
}
MOOD_NAME = {"great": "超开心", "good": "不错", "ok": "平平", "low": "有点低落", "bad": "很糟"}
RPS_LINE = {
    "win": "你和她猜拳赢了，她不服气（互动）",
    "lose": "你和她猜拳输了，她得意洋洋（互动）",
    "draw": "你和她猜拳打平了（互动）",
}
REMINDER_LINE = {
    "water": "她提醒你喝水",
    "sit": "她提醒你起来活动活动",
    "hungry": "她说肚子饿了",
}


FOOD_FX_LINE = {
    "hyper": "她辣得满屋乱跑",
    "jitter": "她酸得浑身打哆嗦",
    "hop": "她在嘴里噼里啪啦地蹦个不停",
    "sneeze": "她冲得猛打喷嚏",
    "stink": "她被熏晕了，醒来很生气",
    "babble": "她吃了毒蘑菇，正在胡言乱语",
    "burp": "她喝完一直打嗝，很不好意思",
    "fly": "她吃完满屏幕乱飞停不下来",
    "shock": "她被电了一下，气炸了",
}


def event_line(ev):
    """把一条推送事件翻译成场景备忘行; 不需要记的返回 None。"""
    name = ev.get("ev")
    if name == "click":
        return "你点了她一下（互动）"
    if name == "double_click":
        return "你双击了她（互动）"
    if name == "pet":
        if ev.get("sleeping"):
            return "你摸了摸睡着的她的头（互动）"
        return "你摸头哄闹别扭的她（互动）" if ev.get("sulking") else "被你摸头了，很舒服（互动）"
    if name == "drag_start":
        return "你把睡着的她拎了起来（互动）" if ev.get("was_sleep") else "你抓住她拖来拖去（互动）"
    if name == "drag_end":
        if ev.get("thrown"):
            return None                     # 紧接着有 throw
        try:
            held = float(ev.get("held") or 0)
        except (TypeError, ValueError):
            held = 0.0
        return "你拖着她好久才放下，她挣扎了半天" if held >= 5 else "你把她放下了"
    if name == "throw":
        line = "你狠狠地把她丢了出去（互动）" if ev.get("hard") else "你把她丢了出去（互动）"
        try:
            lv = int(ev.get("level") or 1)
        except (TypeError, ValueError):
            lv = 1
        return line + (f"，一分钟内已经被丢第{lv}次了" if lv >= 2 and not ev.get("hard") else "")
    if name == "bonk":
        return "她撞到了屏幕边上，咚的一声"
    if name == "throw_land":
        return "她落地了，晕乎乎的还有点生气" if ev.get("wall") else "她落地了，有点生气"
    if name == "spin_start":
        return "你用滚轮转她转圈圈（互动）"
    if name == "spin_end":
        return "她停下来不转了"
    if name == "dizzy":
        return "她撞墙撞晕了" if ev.get("why") == "wall" else "她被转晕了（互动）"
    if name == "watered":
        if ev.get("forced"):
            return "你抓住她强行浇水，她气到极点（互动）"
        if ev.get("asleep"):
            return "她睡着时你给她浇了水，她被浇醒气坏了（互动）"
        return "你想给她浇水，被她躲开了（互动）" if ev.get("dodged") else None
    if name == "mood":
        return f"她的心情变成了「{MOOD_NAME.get(ev.get('band'), '')}」"
    if name == "approach":
        return "她饿了，自己走到你旁边要吃的（主动）" if ev.get("why") == "hungry" else "她自己走过来陪你（主动）"
    if name == "weak_hop":
        return "你双击她，可她饿得跳不动了（互动）"
    if name == "come_refused":
        return "你叫她过来，她不肯动（互动）"
    if name == "rage_poke":
        if ev.get("undo"):
            return "你快把她哄好了，又戳了她一下，前功尽弃（互动）"
        if ev.get("blew"):
            return "她超级生气时你一直戳，她跺脚朝你吹了一阵风（互动）"
        return "她正超级生气，你还去戳她（互动）" if ev.get("pokes") == 1 else None
    if name == "comforted":
        return "她生气时你摸了摸她的头，她别扭地消气了（互动）"
    if name == "carried":
        return "你轻轻抱着她走了一段，她不扑腾了，放下时还道了谢（互动）"
    if name == "pet_lean":
        return "你一直摸她的头，她靠过来蹭了蹭你的手（互动）"
    if name == "combed":
        if ev.get("sulk"):
            return "她闹别扭时你帮她把乱掉的头发梳顺了，她原谅你了（互动）"
        return "你帮她把乱掉的头发梳顺了（互动）" if ev.get("messy") else "你帮她梳了梳头（互动）"
    if name == "tucked":
        return "她睡着时你给她盖了小被子（互动）"
    if name == "woke_tucked":
        return "她醒来发现盖着你给的被子，向你道谢（互动）"
    if name == "waved_back":
        return "她冲你挥手，你也回应了她（互动）"
    if name == "goodnight":
        return "你跟她道了晚安，准备关掉桌宠（互动）"
    if name == "praised":
        n = ev.get("n") or 1
        return "你夸了她，她害羞了（互动）" if n == 1 else (f"你连着夸了她 {n} 句，她不好意思极了（互动）" if n >= 3 else None)
    if name == "companion_bonus":
        return "你陪了她很久，她别扭地说了句心里话（互动）"
    if name == "vomit":
        return "你把她转吐了，她饱食度掉了（互动）"
    if name == "feed":
        food = str(ev.get("name") or "东西")
        r = ev.get("reaction")
        if r == "refuse":
            return f"你喂了她{food}，她嫌弃地推开了（互动）"
        if r == "full":
            return f"你想喂她{food}，可她已经吃饱了（互动）"
        if r == "sulk_worse":
            return f"她正闹别扭，你还喂她不爱吃的{food}，她更生气了（互动）"
        if r == "fav":
            return f"你喂了她{food}，是她的最爱，超开心（互动）"
        if r == "like":
            return f"你喂了她{food}，她很喜欢（互动）"
        if r == "ok":
            return f"你喂了她{food}，她觉得还行（互动）"
        trait = ev.get("trait")
        if trait == "spicy":
            return f"你喂了她{food}，辣得她直冒汗（互动）"
        if trait == "dark" or r == "weird":
            return f"你喂了她{food}，她吃完头晕眼花，很嫌弃（互动）"
        return f"你喂了她{food}，她皱着脸勉强吃了，不太喜欢（互动）"
    if name == "sleep":
        return "睡着了"
    if name == "wake":
        return WAKE_LINE.get(ev.get("why"), "醒过来了")
    if name == "say":
        text = str(ev.get("text") or "").strip()
        if ev.get("src") == "dlc" or not text or text.startswith("📖"):
            return None                     # 自己刚回的话 / 图鉴提示不记
        return f"她说了「{text}」"
    if name == "idle_action":
        return IDLE_LINE.get(ev.get("act"))
    if name == "sneak_caught":
        return "你抓到她偷吃，她害羞地不承认（互动）"
    if name == "sulk":
        return "她闹别扭了（互动）"
    if name == "makeup":
        return MAKEUP_LINE.get(ev.get("how"), "她消气了")
    if name == "level_up":
        return f"你们的关系升到了「{ev.get('name') or ''}」"
    if name == "danika_visit":
        return "达妮卡来找她了（来访）"
    if name == "danika_end":
        return "达妮卡走了"
    if name == "butterfly":
        return BUTTERFLY_LINE.get(ev.get("stage"))
    if name == "rps":
        return RPS_LINE.get(ev.get("result"))
    if name == "fortune":
        return f"你们抽了今日运势，是「{ev.get('tier') or '?'}」（互动）" if ev.get("fresh") else None
    if name == "focus_start":
        return f"你开始专注 {ev.get('minutes') or '?'} 分钟，她安静陪着（互动）"
    if name == "focus_end":
        return "专注完成了，她在为你庆祝" if ev.get("done") else "你提前结束了专注"
    if name == "reminder":
        return REMINDER_LINE.get(ev.get("kind"))       # 整点报时不记
    if name == "user_away":
        return "你离开了电脑"
    if name == "user_back":
        try:
            mins = max(1, int(ev.get("away") or 0) // 60)
        except (TypeError, ValueError):
            mins = 1
        return f"你离开了 {mins} 分钟，回到了电脑前"
    if name == "wish":
        st = ev.get("stage")
        if st == "start":
            return f"她小声许了个心愿：「{ev.get('text') or ''}」"
        if st == "done":
            return "你满足了她的小心愿，她特别开心（互动）"
        return "她的小心愿没人理，过期了" if st == "miss" else None
    if name == "food_effect_start":
        how = FOOD_FX_LINE.get(ev.get("effect"), "她吃完不太对劲")
        return f"你喂了她{ev.get('name') or '奇怪的东西'}，{how}（整蛊）"
    if name == "food_effect_end":
        food = ev.get("name") or "那个东西"
        if ev.get("why") == "done":
            return f"{food}的劲儿过去了，她缓了过来，嘴上说要记小本本"
        return f"{food}的劲儿还没过就被打断了"
    return None                             # state 等: 已由上面的具体事件说明, 不重复


def _age_text(sec):
    if sec < 1.2:
        return "刚刚"
    return f"{int(round(sec))}秒前"


class _Poller(QObject):
    got = Signal(object)

    def __init__(self):
        super().__init__()
        self.client = None
        self.timer = None
        self._fail = 0

    @Slot()
    def start(self):
        self.client = LiveClient(timeout_ms=220)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(280)
        self._tick()

    @Slot()
    def stop(self):
        if self.timer:
            self.timer.stop()
        if self.client:
            self.client.close()
            self.client = None

    def _tick(self):
        if self.client is None:
            return
        data = self.client.get()
        if data is None or not data.get("ok"):
            self._fail += 1
            if self._fail >= 2:
                self.got.emit(None)
            if self.timer:
                self.timer.setInterval(900 if self._fail >= 2 else 280)
            return
        self._fail = 0
        if self.timer:
            self.timer.setInterval(280)
        self.got.emit(data)


class PetWatch(QObject):
    online_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.online = False
        self.last = None
        self.events = deque()
        self.pushed = False             # 订阅成功: diff 不再推断推送已覆盖的事件
        self.sub = LiveSub(self)
        self.sub.event.connect(self._on_event)
        self.sub.status.connect(self._on_sub)
        self.sub.start()
        self._thread = QThread(self)
        self._poller = _Poller()
        self._poller.moveToThread(self._thread)
        self._thread.started.connect(self._poller.start)
        self._poller.got.connect(self._on_snap)
        self._thread.start()

    def stop(self):
        self.sub.stop()
        if self._thread.isRunning():
            QMetaObject.invokeMethod(self._poller, "stop", Qt.BlockingQueuedConnection)
            self._thread.quit()
            self._thread.wait(800)

    def _note(self, text):
        if not text:
            return
        now = time.monotonic()
        if self.events and now - self.events[-1][0] < 0.35 and self.events[-1][1] == text:
            return
        self.events.append((now, text))
        self._prune(now)

    def _prune(self, now=None):
        now = now or time.monotonic()
        keep = deque()
        for t, text in self.events:
            age = now - t
            if age <= WINDOW or (age <= KEY_WINDOW and _is_key(text)):
                keep.append((t, text))
        # 太多时先丢掉普通的旧行, 重要互动尽量留着
        while len(keep) > MAX_LINES:
            for i, (t, text) in enumerate(keep):
                if not _is_key(text):
                    del keep[i]
                    break
            else:
                keep.popleft()
        self.events = keep

    def _on_sub(self, ok):
        self.pushed = bool(ok)

    def _on_event(self, ev):
        try:
            self._note(event_line(ev))
        except Exception:
            pass

    def can_say(self) -> bool:
        return self.online and self.sub.can_say()

    def say(self, text, expr=None, sec=4) -> bool:
        """让她在桌面上说一句; 不在线/旧版桌宠返回 False。失败(busy/rate)不回报。"""
        if not self.can_say():
            return False
        return self.sub.say(text, expr, sec)

    def _on_snap(self, snap):
        was = self.online
        if not snap:
            if was:
                self.online = False
                self.last = None
                self.online_changed.emit(False)
            return
        if not was:
            self.online = True
            self.online_changed.emit(True)
        prev, self.last = self.last, snap
        if prev is None:
            return
        self._diff(prev, snap)

    def _diff(self, a, b):
        pushed = self.pushed            # 有推送时, 下面带 (推送覆盖) 的推断跳过, 避免重复
        st_a, st_b = a.get("state"), b.get("state")
        if st_b and st_b != st_a and not pushed:           # (推送覆盖)
            line = STATE_LINE.get(st_b)
            if line:
                self._note(line)
            elif st_a == "sleep" and st_b != "sleep":
                self._note("醒过来了")

        bub_a = (a.get("bubble") or "").strip()
        bub_b = (b.get("bubble") or "").strip()
        if bub_b and bub_b != bub_a and not pushed:         # (推送覆盖)
            self._note(f"她说了「{bub_b}」")

        def rise(key, text):
            if (not a.get(key)) and b.get(key):
                self._note(text)

        def fall(key, text):
            if a.get(key) and not b.get(key):
                self._note(text)

        if not pushed:                                      # (推送覆盖)
            rise("dragging", "你抓住/拖着她（互动）")
            fall("dragging", "你松开了她")
            rise("spinning", "她被转了起来（互动）")
            fall("spinning", "她停下来不转了")
            rise("dizzy", "她处于眩晕")
            rise("sulking", "她闹别扭了（互动）")
            fall("sulking", "她消气了")
            rise("fling", "她被丢了出去（互动）")
            rise("walk", "她自己走起来了（空闲动作）")
        fall("walk", "她停下不走了")
        rise("focusing", "她在陪你专注")

        ea, eb = a.get("edge"), b.get("edge")
        if eb and eb != ea:
            self._note(f"她贴到屏幕{eb}边探头")
        if ea and not eb:
            self._note("她离开边缘回到桌面")

        try:
            ha, hb = float(a.get("hunger") or 0), float(b.get("hunger") or 0)
        except (TypeError, ValueError):
            ha = hb = 0.0
        fa, fb = int(a.get("feeds_window") or 0), int(b.get("feeds_window") or 0)
        if (fb > fa or hb >= ha + 6) and not pushed:      # (推送覆盖)
            self._note("你喂了她，她吃下去了（互动）")

        va, vb = bool(a.get("visible", True)), bool(b.get("visible", True))
        if va and not vb:
            self._note("她被藏起来了")
        if (not va) and vb:
            self._note("她又出现了")

    def state_json(self) -> str:
        """给模型的当前状态。没有桌宠则空串。界面不要用这个。"""
        s = self.last
        if not s:
            return ""
        hour = datetime.now().hour
        payload = {
            "state": s.get("state"),
            "hunger": s.get("hunger"),
            "affection": s.get("affection"),
            "level": s.get("level"),
            "mood": MOOD_NAME.get(s.get("mood_band"), ""),
            "grok": s.get("grok") or "",
            "focusing": bool(s.get("focusing")),
            "sleeping": bool(s.get("sleeping")),
            "dragging": bool(s.get("dragging")),
            "hour": hour,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def hidden_prompt(self) -> str:
        """给模型的隐藏场景。空字符串表示这一轮不加。界面不要用这个。"""
        now = time.monotonic()
        self._prune(now)
        parts = []
        st = self.state_json()
        if st:
            parts.append("【当前状态，用户看不见】只按这些字段反应，不要宣读。\n" + st)
        if self.events:
            lines = [f"- {_age_text(now - t)}：{text}" for t, text in self.events]
            parts.append(
                "【场景备忘，用户看不见】最近 20 秒内的互动或空闲动作（越靠下越新）。请自然接话，不要提起这份清单，不要逐条复述。\n"
                + "\n".join(lines)
            )
        return "\n\n".join(parts)
