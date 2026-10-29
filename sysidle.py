# -*- coding: utf-8 -*-
"""整台电脑多久没碰键盘鼠标(Windows GetLastInputInfo)。
用来分清「你离开了电脑」和「你在忙, 只是没理她」。不是 Windows 或读取失败返回 None, 调用方按读不到处理。
只读一个系统计时, 不挂键盘鼠标钩子, 不知道你按了什么。"""
import ctypes
import sys

_ok = False
if sys.platform.startswith("win"):
    try:
        from ctypes import wintypes

        class _LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        _u32 = ctypes.WinDLL("user32")
        _k32 = ctypes.WinDLL("kernel32")
        _u32.GetLastInputInfo.argtypes = [ctypes.POINTER(_LASTINPUTINFO)]
        _u32.GetLastInputInfo.restype = wintypes.BOOL
        _k32.GetTickCount.argtypes = []
        _k32.GetTickCount.restype = wintypes.DWORD
        _ok = True
    except Exception:
        _ok = False


def idle_seconds():
    """距上一次键盘/鼠标输入多少秒; 读不到返回 None"""
    if not _ok:
        return None
    try:
        info = _LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
        if not _u32.GetLastInputInfo(ctypes.byref(info)):
            return None
        # 两个都是开机后的毫秒数(32 位, 约 49.7 天回绕一次), 取差再按 32 位回绕
        return ((_k32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:
        return None
