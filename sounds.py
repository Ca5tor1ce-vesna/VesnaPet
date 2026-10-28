# -*- coding: utf-8 -*-
"""小音效: 纯 Python 合成 WAV(首次运行写到数据目录), QSoundEffect 播放; 缺 QtMultimedia 时静默。"""
import math
import random
import struct
import wave

from stats import data_dir

RATE = 22050


def _env(i, n, a=0.006, r=0.6):
    t = i / RATE
    dur = n / RATE
    atk = min(1.0, t / a)
    rel = max(0.0, 1.0 - max(0.0, t - dur * (1 - r)) / (dur * r))
    return atk * rel


def _tone(freqs, dur, vol=0.5, shape="sine", glide=None, vib=0.0):
    n = int(RATE * dur)
    out = []
    ph = [0.0] * len(freqs)
    for i in range(n):
        u = i / max(1, n - 1)
        s = 0.0
        for j, f in enumerate(freqs):
            ff = f if glide is None else f + (glide[j] - f) * u
            ff *= 1 + vib * math.sin(2 * math.pi * 7 * i / RATE)
            ph[j] += 2 * math.pi * ff / RATE
            if shape == "sine":
                s += math.sin(ph[j])
            elif shape == "tri":
                s += 2 / math.pi * math.asin(math.sin(ph[j]))
            else:
                s += math.sin(ph[j]) + 0.3 * math.sin(2 * ph[j])
        out.append(s / len(freqs) * vol * _env(i, n))
    return out


def _cat(*parts, gap=0.0):
    out = []
    for k, p in enumerate(parts):
        out += p
        if gap and k < len(parts) - 1:
            out += [0.0] * int(RATE * gap)
    return out


def _noise(dur, vol=0.3, lp=0.15):
    n = int(RATE * dur)
    out, y = [], 0.0
    rnd = random.Random(7)
    for i in range(n):
        y += lp * (rnd.uniform(-1, 1) - y)
        out.append(y * vol * 3 * _env(i, n, 0.003, 0.8))
    return out


def _bank():
    return {
        "pop": _tone([880], 0.08, 0.45, glide=[1320]),
        "boing": _tone([300], 0.28, 0.5, "tri", glide=[620], vib=0.04),
        "chime": _cat(_tone([1047, 1568], 0.16, 0.35), _tone([1319, 1976], 0.32, 0.35)),
        "sparkle": _cat(*[_tone([1800 + 300 * k], 0.06, 0.25) for k in range(4)]),
        "munch": _cat(_noise(0.06, 0.35), _noise(0.05, 0.3), _noise(0.07, 0.35), gap=0.05),
        "level": _cat(_tone([784], 0.12, 0.4), _tone([988], 0.12, 0.4), _tone([1175], 0.12, 0.4), _tone([1568, 1175], 0.4, 0.4)),
        "huh": _tone([520], 0.16, 0.4, "tri", glide=[760]),
        "hmph": _tone([420], 0.18, 0.4, "tri", glide=[260]),
        "tick": _tone([1400], 0.03, 0.25),
        "whoosh": _noise(0.22, 0.25, 0.05),
        "bonk": _cat(_tone([190], 0.10, 0.6, "tri", glide=[80]), _noise(0.06, 0.3, 0.3)),
    }


def _write(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))


class Sfx:
    VERSION = "3"

    def __init__(self, enabled=True, volume=0.35):
        self.enabled = enabled
        self.volume = volume
        self.effects = {}
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QSoundEffect
        except Exception:
            self.effects = None
            return
        try:
            d = data_dir() / "sfx"
            d.mkdir(parents=True, exist_ok=True)
            mark = d / f".v{self.VERSION}"
            bank = None
            for name in ("pop", "boing", "chime", "sparkle", "munch", "level", "huh", "hmph", "tick", "whoosh", "bonk"):
                p = d / f"{name}.wav"
                if not p.exists() or not mark.exists():
                    bank = bank or _bank()
                    _write(p, bank[name])
                e = QSoundEffect()
                e.setSource(QUrl.fromLocalFile(str(p)))
                e.setVolume(volume)
                self.effects[name] = e
            mark.write_text("ok")
        except Exception:
            self.effects = None

    def play(self, name):
        if not self.enabled or not self.effects:
            return
        e = self.effects.get(name)
        if e is not None:
            try:
                e.play()
            except Exception:
                pass
