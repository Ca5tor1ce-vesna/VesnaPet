# -*- coding: utf-8 -*-
"""语音 DLC: 她冒台词气泡时(main.say -> on_say), 按 dlc/voice/voice_map.json 查原文播放 <id>.ogg。
- 查表: 原文精确 -> 去首尾空格; 查不到跳过。同一时间一句, 新的打断旧的。
- 跟随设置: 勿扰(mute) 或 关闭音效(sfx) 时不播。src="dlc"(聊天 DLC 的 say 命令)不播。
- 达妮卡的台词走她自己的气泡, 不经过 say, 不会播。
- 配置 dlc/voice/voice_config.json: {"enabled": true, "volume": 0.8}; 设置面板「扩展」区有开关和音量条, 即时生效。
- 每次查表前看 voice_map.json 的修改时间, 变了就重新加载(补录不用重启)。
- 缺 QtMultimedia / 播放出错: error.log 记一次, 然后停用, 不影响桌宠。
音频目录不存在 -> 插件不加载。
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOICE_DIR = HERE.parent / "voice"


MAP = VOICE_DIR / "voice_map.json"
SKIP_SRC = {"dlc", "water"}        # 不配音的来源: 聊天 DLC 的 say 命令 / 浇水插件
CONF = VOICE_DIR / "voice_config.json"


def _read_map():
    table = json.loads(MAP.read_text(encoding="utf-8-sig"))
    if not isinstance(table, dict):
        raise ValueError("voice_map.json 不是对象")
    return {str(k): str(v) for k, v in table.items()
            if isinstance(v, str) and v.endswith(".ogg") and "/" not in v and "\\" not in v}


class Voice:
    def __init__(self, pet, log_fn, table, volume, enabled=True):
        self.pet, self.log = pet, log_fn
        self.table = table
        self.volume = volume
        self.enabled = enabled
        try:
            self._mtime = MAP.stat().st_mtime_ns
        except OSError:
            self._mtime = None
        self.dead = False
        self.player = None
        self.out = None
        self.last = None          # 最近一次播放的文件(测试/调试用)

    def _fail(self, where, e=None):
        if self.dead:
            return
        self.dead = True
        if self.log:
            try:
                self.log("voice " + where + " (语音已停用)", e if e is not None else RuntimeError(where))
            except Exception:
                pass
        try:
            if self.player is not None:
                self.player.stop()
        except Exception:
            pass

    def _maybe_reload(self):
        try:
            mt = MAP.stat().st_mtime_ns
        except OSError:
            return
        if mt == self._mtime:
            return
        self._mtime = mt
        try:
            self.table = _read_map()
        except Exception as e:                 # 补录写到一半: 保留旧表, 下次 mtime 变了再试
            if self.log:
                self.log("voice reload map", e)

    def lookup(self, text):
        self._maybe_reload()
        f = self.table.get(text)
        if f is None:
            f = self.table.get(text.strip())
        return f

    def _ensure(self):
        if self.player is not None:
            return True
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except Exception as e:
            self._fail("import QtMultimedia", e)
            return False
        self.out = QAudioOutput()
        self.out.setVolume(self.volume)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.out)
        self.player.errorOccurred.connect(self._on_error)
        return True

    def _on_error(self, err, msg=""):
        try:
            from PySide6.QtMultimedia import QMediaPlayer
            if err == QMediaPlayer.Error.NoError:
                return
        except Exception:
            pass
        self._fail("play error: %s %s (%s)" % (err, msg, self.last))

    def on_say(self, text, src="pet"):
        if self.dead or not self.enabled or src in SKIP_SRC:
            return False
        cfg = self.pet.cfg
        if cfg["mute"] or not cfg["sfx"]:
            return False
        name = self.lookup(text)
        if not name:
            return False
        path = VOICE_DIR / name
        if not path.is_file():
            return False
        try:
            if not self._ensure():
                return False
            from PySide6.QtCore import QUrl
            self.last = name
            self.player.stop()                        # 新台词打断旧的
            self.player.setSource(QUrl.fromLocalFile(str(path)))
            self.player.play()
        except Exception as e:
            self._fail("play", e)
        return False                                  # 只是旁听, 不接管


    # ----- 设置面板 -----
    def _save_conf(self):
        try:
            c = {}
            if CONF.is_file():
                try:
                    c = json.loads(CONF.read_text(encoding="utf-8-sig"))
                    c = c if isinstance(c, dict) else {}
                except Exception:
                    c = {}
            c["enabled"] = bool(self.enabled)
            c["volume"] = round(float(self.volume), 2)
            tmp = CONF.with_suffix(".tmp")
            tmp.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, CONF)
        except Exception as e:
            if self.log:
                self.log("voice save config", e)

    def set_enabled(self, on):
        self.enabled = bool(on)
        if not self.enabled and self.player is not None:
            try:
                self.player.stop()                    # 关掉: 正在播的立即停
            except Exception:
                pass
        self._save_conf()

    def set_volume(self, v100):
        self.volume = max(0.0, min(1.0, int(v100) / 100.0))
        if self.out is not None:
            try:
                self.out.setVolume(self.volume)
            except Exception:
                pass
        self._save_conf()

    def settings_rows(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QSlider
        from ui_kit import Toggle
        tg = Toggle(None, self.enabled)
        tg.toggled.connect(self.set_enabled)
        sl = QSlider(Qt.Horizontal)
        sl.setRange(0, 100)
        sl.setValue(int(round(self.volume * 100)))
        sl.setFixedSize(140, 24)
        sl.setCursor(Qt.PointingHandCursor)
        sl.setToolTip("语音音量")
        sl.setStyleSheet("""
            QSlider::groove:horizontal{height:6px;background:#DCE2EE;border-radius:3px;}
            QSlider::sub-page:horizontal{background:#4FC7B5;border-radius:3px;}
            QSlider::handle:horizontal{background:white;border:2px solid #4FC7B5;width:12px;margin:-5px 0;border-radius:8px;}
        """)
        sl.valueChanged.connect(lambda v: (self.out is not None and self.out.setVolume(v / 100.0)))
        sl.sliderReleased.connect(lambda: self.set_volume(sl.value()))
        sl.valueChanged.connect(lambda v: (not sl.isSliderDown()) and self.set_volume(v))   # 键盘/点击轨道
        self._tg, self._sl = tg, sl

        def sync():
            tg.set_silent(self.enabled)
            sl.blockSignals(True)
            sl.setValue(int(round(self.volume * 100)))
            sl.blockSignals(False)
        return [dict(key="voice_enabled", emoji="🗣️", title="语音", desc="薇斯纳说话时配音", control=tg, sync=sync),
                dict(key="voice_volume", emoji="🎚️", title="语音音量", desc="0–100", control=sl, sync=sync)]


def create(pet, log_fn=None):
    if not MAP.is_file():
        return None
    table = _read_map()
    vol, on = 0.8, True
    if CONF.is_file():
        try:
            c = json.loads(CONF.read_text(encoding="utf-8-sig"))
            on = bool(c.get("enabled", True))
            vol = max(0.0, min(1.0, float(c.get("volume", 0.8))))
        except Exception as e:
            if log_fn:
                log_fn("voice config", e)
    return Voice(pet, log_fn, table, vol, on)     # 关着也加载, 好让设置里能再打开
