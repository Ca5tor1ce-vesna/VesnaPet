# -*- coding: utf-8 -*-
"""好感度 / 饱腹 / 统计 / 图鉴进度, 存 %APPDATA%\\VesnaPet\\stats.json"""
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

from content import level_info

DAILY_CAPS = {"feed": 6, "rps": 10, "pet": 15, "jump": 5, "butterfly": 8}
HUNGER_PER_HOUR = 9.0           # 运行时每小时掉多少饱腹
OFFLINE_FLOOR = 35.0            # 关掉期间最多饿到这里(她会自己找吃的~)


def data_dir() -> Path:
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        root = str(Path.home() / "Library" / "Application Support")
    else:
        root = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(root) / "VesnaPet"


def _same_kind(default, v):
    if default is None:
        return True
    if isinstance(default, (int, float)) and not isinstance(default, bool):
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, type(default))


class Stats:
    DEFAULTS = {
        "affection": 0.0, "hunger": 70.0, "first_day": None, "days_met": 0, "last_day": None, "last_seen": None,
        "pets": 0, "feeds": 0, "butterflies": 0, "danika_visits": 0, "focus_minutes": 0, "focus_sessions": 0,
        "rps_win": 0, "rps_lose": 0, "rps_draw": 0, "jumps": 0, "uptime_sec": 0.0,
        "throws": 0, "wall_bonks": 0, "sulks": 0, "dizzies": 0,
        "seen": [], "fav_found": False, "fortune_day": None,
        "foods": {}, "food_known": [], "food_refused": 0, "food_sulks": 0,
        "daily": {"day": None, "counts": {}, "focus_min": 0},
    }

    def __init__(self, path: Path = None):
        self.path = path or (data_dir() / "stats.json")
        self.d = json.loads(json.dumps(self.DEFAULTS))
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    if k in self.DEFAULTS and _same_kind(self.DEFAULTS[k], v):
                        self.d[k] = v
                    elif k not in self.DEFAULTS and isinstance(v, int) and not isinstance(v, bool):
                        self.d[k] = v          # 插件用 inc() 记的计数(如 vomits): 原样保留, 不然重启就清零
        except Exception:
            pass
        if not isinstance(self.d.get("seen"), list):
            self.d["seen"] = []
        if not isinstance(self.d.get("food_known"), list):
            self.d["food_known"] = []
        if not isinstance(self.d.get("foods"), dict):
            self.d["foods"] = {}
        if self.d.get("fav_found") and "tofu" not in self.d["food_known"]:   # 旧版只有杏仁豆腐一个最爱
            self.d["food_known"].append("tofu")
        self._dirty = False
        self._last_save = 0.0
        self.away_hours = 0.0
        self.new_day = False
        self._open()

    # ----- 生命周期 -----
    def _open(self):
        today = date.today().isoformat()
        now = time.time()
        if not self.d["first_day"]:
            self.d["first_day"] = today
        last = self.d.get("last_seen")
        if isinstance(last, (int, float)) and now > last:
            hrs = (now - last) / 3600.0
            self.away_hours = hrs
            h = float(self.d["hunger"])
            if h > OFFLINE_FLOOR:
                self.d["hunger"] = max(OFFLINE_FLOOR, h - hrs * HUNGER_PER_HOUR * 0.5)
        if self.d.get("last_day") != today:
            self.d["last_day"] = today
            self.d["days_met"] = int(self.d.get("days_met", 0)) + 1
            self.new_day = True
        self._roll_daily()
        self.d["last_seen"] = now
        self.save(force=True)

    def _roll_daily(self):
        today = date.today().isoformat()
        dl = self.d.get("daily")
        if not isinstance(dl, dict) or dl.get("day") != today:
            self.d["daily"] = {"day": today, "counts": {}, "focus_min": 0}

    def save(self, force=False):
        now = time.monotonic()
        if not force and (not self._dirty or now - self._last_save < 5):
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.d["last_seen"] = time.time()
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
            self._dirty = False
            self._last_save = now
        except Exception as e:
            print("save stats failed:", e, file=sys.stderr)

    def touch(self):
        self._dirty = True

    # ----- 好感 -----
    @property
    def affection(self):
        return float(self.d["affection"])

    def level(self):
        return level_info(self.affection)

    def daily_ok(self, kind):
        """当日该类加好感次数是否未满"""
        self._roll_daily()
        cap = DAILY_CAPS.get(kind)
        if cap is None:
            return True
        return self.d["daily"]["counts"].get(kind, 0) < cap

    def gain(self, n, kind=None):
        """加好感; 返回 (加了多少, 是否升级, 新等级名)"""
        self._roll_daily()
        if kind and not self.daily_ok(kind):
            return 0, False, None
        before = self.level()[0]
        self.d["affection"] = max(0.0, self.affection + n)
        if kind:
            c = self.d["daily"]["counts"]
            c[kind] = c.get(kind, 0) + 1
        self.touch()
        lv = self.level()
        return n, lv[0] > before, lv[1]

    # ----- 饱腹 -----
    @property
    def hunger(self):
        return float(self.d["hunger"])

    def feed(self, amount):
        self.d["hunger"] = min(100.0, self.hunger + amount)
        self.d["feeds"] = int(self.d["feeds"]) + 1
        self.touch()

    def add_hunger(self, delta):
        """饱腹 +delta(可为负), 夹在 0-100, 返回新值; 不算一次投喂"""
        self.d["hunger"] = max(0.0, min(100.0, self.hunger + delta))
        self.touch()
        return self.hunger

    def tick(self, dt):
        self.d["hunger"] = max(0.0, self.hunger - HUNGER_PER_HOUR * dt / 3600.0)
        self.d["uptime_sec"] = float(self.d["uptime_sec"]) + dt
        self.touch()

    # ----- 美食图鉴 -----
    def taste(self, key, eaten=True):
        """记录喂过的食物; 第一次尝到/见到(推开也算认识了)返回 True"""
        foods = self.d["foods"]
        known = self.d["food_known"]
        first = key not in known
        if first:
            known.append(key)
        if eaten:
            foods[key] = int(foods.get(key, 0)) + 1
        else:
            self.d["food_refused"] = int(self.d.get("food_refused", 0)) + 1
        self.touch()
        return first

    def food_known(self, key):
        return key in self.d["food_known"]

    def food_count(self, key):
        try:
            return int(self.d["foods"].get(key, 0))
        except Exception:
            return 0

    # ----- 计数 / 图鉴 -----
    def inc(self, key, n=1):
        self.d[key] = int(self.d.get(key, 0)) + n
        self.touch()

    def add_focus(self, minutes):
        self._roll_daily()
        self.d["focus_minutes"] = int(self.d["focus_minutes"]) + int(minutes)
        self.d["focus_sessions"] = int(self.d["focus_sessions"]) + 1
        self.d["daily"]["focus_min"] = int(self.d["daily"].get("focus_min", 0)) + int(minutes)
        self.touch()

    def see(self, key):
        """记录看到过的表情; 新解锁返回 True"""
        if key not in self.d["seen"]:
            self.d["seen"].append(key)
            self.touch()
            return True
        return False

    def seen(self, key):
        return key in self.d["seen"]
