# -*- coding: utf-8 -*-
"""互动扩展接口: 启动时 import <桌宠目录>/dlc/interactions/*.py, 每个模块提供 create(pet, log_fn) -> 插件对象
(返回 None = 不加载)。完整规范见 docs/接口规范.md。

目录不存在 / 没有插件 -> 所有钩子都是空操作, 原版行为不变。插件出错只记 error.log 并被停用
(menu_items / settings_rows 出错只跳过那一项)。插件可设 priority(默认 0), 大的先问; 同级按文件名顺序。
插件对象可选实现:
  on_event(name, data)          她身上发生的每个事件(和 live 管道推给 DLC 的同一套, 见文档); 只通知, 返回值不管
  busy() -> str | None          插件正在进行的活动名(如 "vomit"); 非空时并进 pet.activities(), 原版的自动行为会让路。
                                不要在 busy() 里调 pet.activities()(会递归)
  tune(name, value, ctx) -> v   本体在决策点问插件要不要调参数(main.TUNABLE 里的名字); 返回新值, None = 不改。
                                心情 / 好感要不要影响行为, 全靠这个; 多个插件按 priority 依次传下去
  on_pet() -> bool              摸头时先问插件; True = 插件接管(原版摸头效果不执行)
  on_click(double) -> bool      单击/双击时先问插件(double=True 是双击); True = 插件接管(原版的戳/跳不执行)
  on_spin_queasy(now) -> bool   转圈转到顶、即将生气时调用; 返回 True 表示插件接管(原版的生气逻辑不执行)
  step(t)                       每帧调用
  expr(key, state) -> str | None 每帧画立绘前问: 要不要换一张脸(main.FACES 里的名字, 如超级生气时换 "wet")。
                                key 是本体选好的图, state 是状态; None = 不换。多个插件按 priority 依次传下去。
                                只换图, 状态和逻辑不变; 那张图不存在就照常画
  paint(key, pm, t) -> (pm, dx) 画立绘前调用, 可替换图/加水平抖动
  on_say(text, src)             她冒台词气泡时通知
  on_mouse_press(event) -> bool 鼠标按下(任意键)先问插件; True = 插件吃掉这次按下
  on_wheel(event) -> bool        滚轮转圈前先问插件; True = 插件吃掉(不转、不攒晕度)
  on_context_menu(event) -> bool 右键菜单弹出前先问插件; True = 不弹
  status_text() -> str | None   插件想显示的一行状态(托盘提示、右键卡片的状态行), 如「小心愿: 想吃甜的」
  state_text() -> str | None    插件管的短暂状态正在进行时, 小屋头部那句话显示它(如「头发还在滴水,火气倒是很旺」);
                                只在那段时间返回, 平时返回 None(头部那句就照常按好感说)
  menu_items() -> [(emoji, label, fn)]  往右键菜单(和托盘「互动」子菜单)注册菜单项
  settings_rows() -> [dict]     往设置面板「扩展」区注册行: {key, emoji, title, desc, control(QWidget), sync(可选)}
"""
import importlib.util
import sys
from pathlib import Path


def pet_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class Hub:
    def __init__(self, log_fn=None):
        self.plugins = []
        self.log = log_fn

    def _err(self, where, e, plug):
        if self.log:
            try:
                self.log("interaction " + where, e)
            except Exception:
                pass
        if plug in self.plugins:
            self.plugins.remove(plug)

    def call(self, name, *a):
        # 插件可设 priority(默认 0), 大的先问; 同级按加载顺序
        for pl in sorted(self.plugins, key=lambda x: -getattr(x, "priority", 0)):
            f = getattr(pl, "on_" + name, None)
            if f is None:
                continue
            try:
                if f(*a):
                    return True
            except Exception as e:
                self._err(name, e, pl)
        return False

    def event(self, name, data):
        """把一个事件通知给所有插件(不短路); 每个插件拿到自己的一份 data"""
        for pl in list(self.plugins):
            f = getattr(pl, "on_event", None)
            if f is not None:
                try:
                    f(name, dict(data))
                except Exception as e:
                    self._err("event " + str(name), e, pl)

    def busy(self):
        """插件报上来的活动名列表; 都闲着就是空列表"""
        out = []
        for pl in list(self.plugins):
            f = getattr(pl, "busy", None)
            if f is not None:
                try:
                    b = f()
                    if b:
                        out.append(str(b))
                except Exception as e:
                    self._err("busy", e, pl)
        return out

    def tune(self, name, value, ctx):
        """决策点: 依次问插件(priority 大的先), 每个插件拿到上一个改过的值; 返回最终值(本体再校验)"""
        for pl in sorted(self.plugins, key=lambda x: -getattr(x, "priority", 0)):
            f = getattr(pl, "tune", None)
            if f is None:
                continue
            try:
                v = f(name, value, dict(ctx))
                if v is not None:
                    value = v
            except Exception as e:
                self._err("tune " + str(name), e, pl)
        return value

    def expr(self, key, state):
        """每帧问插件换不换脸: priority 大的先, 每个拿到上一个换过的; 返回最终的(本体再校验有没有这张图)"""
        for pl in sorted(self.plugins, key=lambda x: -getattr(x, "priority", 0)):
            f = getattr(pl, "expr", None)
            if f is None:
                continue
            try:
                k = f(key, state)
                if k:
                    key = str(k)
            except Exception as e:
                self._err("expr", e, pl)
        return key

    def state_texts(self):
        """插件管的短暂状态的一句话(超级生气、转吐……); 都没有就是空列表"""
        out = []
        for pl in list(self.plugins):
            f = getattr(pl, "state_text", None)
            if f is not None:
                try:
                    txt = f()
                    if txt:
                        out.append(str(txt))
                except Exception as e:
                    self._err("state_text", e, pl)
        return out

    def status_lines(self):
        """插件的状态行; 都没有就是空列表"""
        out = []
        for pl in list(self.plugins):
            f = getattr(pl, "status_text", None)
            if f is not None:
                try:
                    txt = f()
                    if txt:
                        out.append(str(txt))
                except Exception as e:
                    self._err("status_text", e, pl)
        return out

    def step(self, t):
        for pl in list(self.plugins):
            f = getattr(pl, "step", None)
            if f is not None:
                try:
                    f(t)
                except Exception as e:
                    self._err("step", e, pl)

    def menu_items(self):
        """收集插件注册的菜单项 [(emoji, label, fn)]; 出错的插件只跳过它的项。"""
        items = []
        for pl in list(self.plugins):
            f = getattr(pl, "menu_items", None)
            if f is None:
                continue
            try:
                for it in (f() or []):
                    if isinstance(it, (tuple, list)) and len(it) >= 3 and callable(it[2]):
                        items.append((str(it[0]), str(it[1]), it[2]))
            except Exception as e:
                if self.log:
                    try:
                        self.log("interaction menu_items", e)
                    except Exception:
                        pass
        return items

    def settings_rows(self):
        """收集插件注册的设置行; 出错的插件只跳过它的行(记日志), 不停用插件。"""
        rows = []
        for pl in list(self.plugins):
            f = getattr(pl, "settings_rows", None)
            if f is None:
                continue
            try:
                for r in (f() or []):
                    if isinstance(r, dict) and r.get("control") is not None:
                        rows.append(r)
            except Exception as e:
                if self.log:
                    try:
                        self.log("interaction settings_rows", e)
                    except Exception:
                        pass
        return rows

    def paint(self, key, pm, t):
        dx = 0.0
        for pl in list(self.plugins):
            f = getattr(pl, "paint", None)
            if f is not None:
                try:
                    r = f(key, pm, t)
                    if r:
                        pm, d = r
                        dx += float(d or 0.0)
                except Exception as e:
                    self._err("paint", e, pl)
        return pm, dx


def load(pet, log_fn=None) -> Hub:
    hub = Hub(log_fn)
    d = pet_dir() / "dlc" / "interactions"
    if not d.is_dir():
        return hub
    for f in sorted(d.glob("*.py")):
        if f.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location("vesna_ix_" + f.stem, str(f))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            plug = mod.create(pet, log_fn)
            if plug is not None:
                hub.plugins.append(plug)
        except Exception as e:
            if log_fn:
                try:
                    log_fn("interaction load " + f.name, e)
                except Exception:
                    pass
    return hub
