# -*- coding: utf-8 -*-
"""从现有 7 张贴纸派生新表情: 同一角色、同一画布、同一脚底基线。
手法: SIFT 相似变换对齐 -> 局部换眼/换嘴 -> 程序化贴纸风小符号(白描边)。"""
import math
import sys

import cv2
import numpy as np

SRC = sys.argv[1] if len(sys.argv) > 1 else 'F:/codel/VesnaPet_unz/VesnaPet/assets/'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'F:/codel/work/out/'
BOX = (14, 130, 498, 498)          # 现有站立图 alpha 并集, 新图不越界(否则整套缩小)

sift = cv2.SIFT_create(6000)
bf = cv2.BFMatcher()
HEAD = (130, 140, 420, 400)
EYES_IDLE = [(181, 316), (269, 317)]
MOUTH_IDLE = (224, 351)
LASH = np.array([46, 34, 52], np.float32) / 255.0      # BGR 线稿深色
NAVY = np.array([110, 63, 43], np.float32) / 255.0     # BGR #2B3F6E 贴纸符号蓝


def load(n):
    im = cv2.imread(SRC + n + '.png', cv2.IMREAD_UNCHANGED)
    return im.astype(np.float32) / 255.0


def to8(im):
    return np.clip(im * 255 + 0.5, 0, 255).astype(np.uint8)


def feats(im, roi=None):
    g = cv2.cvtColor(to8(im[:, :, :3]), cv2.COLOR_BGR2GRAY)
    m = (im[:, :, 3] > 0.8).astype(np.uint8) * 255
    if roi is not None:
        x0, y0, x1, y1 = roi
        r = np.zeros_like(m); r[y0:y1, x0:x1] = 255
        m = cv2.bitwise_and(m, r)
    return sift.detectAndCompute(g, m)


def estimate(src, dst, roi_s=None, roi_d=None):
    k1, d1 = feats(src, roi_s); k2, d2 = feats(dst, roi_d)
    ms = bf.knnMatch(d1, d2, k=2)
    good = [a for a, b in ms if a.distance < 0.75 * b.distance]
    s = np.float32([k1[m.queryIdx].pt for m in good]); d = np.float32([k2[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(s, d, method=cv2.RANSAC, ransacReprojThreshold=2)
    keep = inl.ravel() == 1
    M, _ = cv2.estimateAffinePartial2D(s[keep], d[keep], method=cv2.LMEDS)
    return M


def warp(im, M, size=(512, 512)):
    return cv2.warpAffine(im, M, size, flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def inv(M):
    return cv2.invertAffineTransform(M)


def compose(A, B):
    """A∘B (先 B 后 A)"""
    A3 = np.vstack([A, [0, 0, 1]]); B3 = np.vstack([B, [0, 0, 1]])
    return (A3 @ B3)[:2].astype(np.float32)


def tpt(M, p):
    return (M[0, 0] * p[0] + M[0, 1] * p[1] + M[0, 2], M[1, 0] * p[0] + M[1, 1] * p[1] + M[1, 2])


def mscale(M):
    return float(np.hypot(M[0, 0], M[1, 0]))


def feather(mask, r):
    if r <= 0:
        return mask.astype(np.float32)
    k = int(r) * 2 + 1
    return cv2.GaussianBlur(mask.astype(np.float32), (k, k), r / 2.0)


def dilate(mask, r):
    if r <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(mask.astype(np.uint8), k)


def blend(dst, src, m):
    m = m[..., None]
    return dst * (1 - m) + src * m


def over(dst, src):
    sa = src[..., 3:4]; da = dst[..., 3:4]
    oa = sa + da * (1 - sa)
    rgb = (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
    return np.concatenate([rgb, oa], 2)


def hsv8(im):
    return cv2.cvtColor(to8(im[:, :, :3]), cv2.COLOR_BGR2HSV).astype(int)


# ---------------- 对齐 ----------------
IM = {n: load(n) for n in ('idle', 'happy', 'angry', 'sleep', 'surprised', 'peek_awake', 'peek_sleep')}
T = {'idle': np.float32([[1, 0, 0], [0, 1, 0]])}          # name -> (name 坐标 -> idle 坐标)
for n in ('happy', 'angry', 'sleep', 'surprised'):
    T[n] = estimate(IM[n], IM['idle'], HEAD, HEAD)
T['peek_awake'] = estimate(IM['peek_awake'], IM['idle'], None, HEAD)
T['peek_sleep'] = estimate(IM['peek_sleep'], IM['sleep'], None, HEAD)
T['peek_sleep'] = compose(T['sleep'], T['peek_sleep'])


def xf(src, dst):
    """src 坐标 -> dst 坐标"""
    return compose(inv(T[dst]), T[src])


EYE_OVERRIDE = {'sleep': [(184.5, 325.0), (265.5, 337.0)]}
_EYES = {}


def eyes_rough(name):
    M = inv(T[name])
    return [tpt(M, e) for e in EYES_IDLE]


def eyes_in(name):
    """眼睛中心: 睁眼图用分割出的眼眶质心; 睡脸手工标定"""
    if name in EYE_OVERRIDE:
        return EYE_OVERRIDE[name]
    if name not in _EYES:
        out = []
        k = k_of(name)
        for i, c in enumerate(eyes_rough(name)):
            h = eye_hull(IM[name], c, k, i)
            ys, xs = np.nonzero(h)
            out.append((float(xs.mean()), float(ys.mean())) if len(xs) > 50 else c)
        _EYES[name] = out
    return _EYES[name]


def mouth_in(name):
    return tpt(inv(T[name]), MOUTH_IDLE)


def k_of(name):
    """该图相对 idle 的线性尺度"""
    return 1.0 / mscale(T[name])


# ---------------- 眼睛分割 ----------------
def eye_hull(im, c, k, side):
    hsv = hsv8(im)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    iris = (H >= 35) & (H <= 105) & (S > 40)
    dark = V < 120
    m = ((iris | dark) & (im[..., 3] > 0.8)).astype(np.uint8)
    win = np.zeros_like(m)
    rx, ry = 30 * k, 24 * k
    cx = c[0] + (3 * k if side == 0 else -3 * k)          # 向脸内侧偏, 避开脸颊轮廓线
    cv2.ellipse(win, (int(cx), int(c[1])), (int(rx), int(ry)), 0, 0, 360, 1, -1)
    m &= win
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] >= 25 * k * k:
            keep[lab == i] = 1
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    cnts, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = np.zeros_like(keep)
    if cnts:
        cv2.fillConvexPoly(hull, cv2.convexHull(np.vstack(cnts)), 1)
    return hull


def eye_masks(name, im=None):
    im = IM[name] if im is None else im
    k = k_of(name)
    return [eye_hull(im, c, k, i) for i, c in enumerate(eyes_rough(name))]


# ---------------- 干净的睡脸底(无睫毛/鼻泡/zzz) ----------------
def _skin_fill(im, holes, ring_src):
    """holes 区域用周围皮肤中位色填, 羽化接缝"""
    px = im[(ring_src > 0)]
    px = px[(px[:, 2] - px[:, 0] > 0.04) & (px[:, 2] > 0.9)]          # R>B 且够亮 = 皮肤
    col = np.median(px[:, :3], 0) if len(px) > 20 else np.array([0.902, 0.933, 0.996])
    fill = im.copy(); fill[..., :3] = col
    m = feather(dilate(holes, 1), 2.4)
    return blend(im, fill, m * (im[..., 3] > 0.9))


def make_sleep_clean():
    im = IM['sleep'].copy()
    a = im[..., 3]
    yy, xx = np.mgrid[0:512, 0:512]
    a[(xx < 117) & (yy < 302)] = 0
    im[..., 3] = a
    hsv = hsv8(im)
    k = k_of('sleep')
    holes = np.zeros((512, 512), np.uint8)
    ring = np.zeros((512, 512), np.uint8)
    lash_only = np.zeros((512, 512), np.float32)
    for i, c in enumerate(eyes_in('sleep')):
        win = np.zeros((512, 512), np.uint8)
        cx = c[0]
        rx = 25
        cv2.ellipse(win, (int(cx), int(c[1])), (int(rx * k), int(11 * k)), 0, 0, 360, 1, -1)
        hairish = (hsv[..., 0] >= 12) & (hsv[..., 0] <= 32) & (hsv[..., 1] > 70) & (hsv[..., 2] > 180)
        lash = ((hsv[..., 2] < 205) & ~hairish & (win > 0)).astype(np.uint8)
        lash = dilate(lash, 2) & win
        holes |= lash
        big = np.zeros((512, 512), np.uint8)
        cv2.ellipse(big, (int(cx), int(c[1])), (int((rx + 5) * k), int(16 * k)), 0, 0, 360, 1, -1)
        ring |= big & (1 - win)
        lash_only = np.maximum(lash_only, np.clip((200 - hsv[..., 2]) / 120.0, 0, 1) * (win > 0))
    out = _skin_fill(im, holes, ring)
    # 鼻泡: 手工圆(脸颊), 周围皮肤色填
    bub = np.zeros((512, 512), np.uint8)
    cv2.circle(bub, (205, 342), 14, 1, -1)
    bring = np.zeros((512, 512), np.uint8)
    cv2.circle(bring, (205, 342), 19, 1, -1); bring &= (1 - bub)
    nobub = _skin_fill(im, bub, bring)
    out = _skin_fill(out, bub, bring)
    return out, nobub, lash_only


SLEEP_CLEAN, SLEEP_NOBUB, SLEEP_LASH = make_sleep_clean()
T['sleep_clean'] = T['sleep']


def cover_eyes(name, base=None, grow=4):
    """用对齐后的干净睡脸皮肤盖掉睁开的眼睛"""
    base = IM[name].copy() if base is None else base.copy()
    skin = warp(SLEEP_CLEAN, xf('sleep', name))
    k = k_of(name)
    m = np.zeros((512, 512), np.uint8)
    for e in eye_masks(name):
        m |= e
    m = dilate(m, int(grow * k))
    mf = feather(m, 3 * k) * (skin[..., 3] > 0.9)
    return blend(base, skin, mf)


def transplant(src_im, src_name, dst, dst_name, mask_src, fr=3):
    """把 src 中 mask_src 区域按头部对齐贴到 dst"""
    M = xf(src_name, dst_name)
    w = warp(src_im, M)
    m = warp(mask_src.astype(np.float32), M)
    m = feather((m > 0.5).astype(np.float32), fr * k_of(dst_name)) * (w[..., 3] > 0.9)
    return blend(dst, w, m)


def mouth_mask(name, rx, ry, dx=0, dy=0):
    k = k_of(name)
    mx, my = mouth_in(name)
    m = np.zeros((512, 512), np.uint8)
    cv2.ellipse(m, (int(mx + dx * k), int(my + dy * k)), (int(rx * k), int(ry * k)), 0, 0, 360, 1, -1)
    return m


# ---------------- 矢量绘制(4x 超采样) ----------------
SS = 4


class Layer:
    def __init__(self):
        self.a = np.zeros((512 * SS, 512 * SS), np.uint8)
        self.c = np.zeros((512 * SS, 512 * SS, 3), np.uint8)

    def poly(self, pts, color, closed=True, width=0):
        P = np.int32(np.round(np.array(pts) * SS))
        col = tuple(int(v * 255) for v in color)
        if width <= 0:
            cv2.fillPoly(self.c, [P], col, cv2.LINE_AA); cv2.fillPoly(self.a, [P], 255, cv2.LINE_AA)
        else:
            w = max(1, int(width * SS))
            cv2.polylines(self.c, [P], closed, col, w, cv2.LINE_AA); cv2.polylines(self.a, [P], closed, 255, w, cv2.LINE_AA)

    def circle(self, c, r, color, width=0):
        col = tuple(int(v * 255) for v in color)
        C = (int(c[0] * SS), int(c[1] * SS)); R = max(1, int(r * SS))
        th = -1 if width <= 0 else max(1, int(width * SS))
        cv2.circle(self.c, C, R, col, th, cv2.LINE_AA); cv2.circle(self.a, C, R, 255, th, cv2.LINE_AA)

    def get(self):
        a = cv2.resize(self.a, (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        c = cv2.resize(self.c, (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        # 预乘近似: 颜色按 alpha 混过的边缘会发暗, 用 alpha 归一
        ca = cv2.resize((self.c.astype(np.float32) * (self.a[..., None] / 255.0)), (512, 512), interpolation=cv2.INTER_AREA)
        c = ca / np.maximum(a[..., None] * 255.0, 1e-6)
        return np.concatenate([np.clip(c, 0, 1), a[..., None]], 2)


def bezier(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)


def tapered(pts, wmax, wmin=0.6, power=0.7):
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    d = np.gradient(pts, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    t = np.linspace(0, 1, n)
    w = wmin + (wmax - wmin) * np.sin(np.pi * t) ** power
    left = pts + nrm * (w[:, None] / 2); right = pts - nrm * (w[:, None] / 2)
    return np.vstack([left, right[::-1]])


def star_pts(c, r, n=5, inner=0.45, rot=-90):
    out = []
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * inner
        a = math.radians(rot) + i * math.pi / n
        out.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    return out


def sparkle_pts(c, r, rot=0):
    pts = []
    for i in range(8):
        rr = r if i % 2 == 0 else r * 0.22
        a = math.radians(rot) + i * math.pi / 4 - math.pi / 2
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    return pts


def heart_pts(c, s, rot=0):
    t = np.linspace(0, 2 * np.pi, 80)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    pts = np.stack([x, y], 1) * (s / 16.0)
    r = math.radians(rot)
    R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    return pts @ R.T + np.array(c)


def drop_pts(c, s, rot=0):
    t = np.linspace(0, 2 * np.pi, 80)
    x = np.sin(t) * (1 - np.cos(t)) * 0.55
    y = -np.cos(t)
    pts = np.stack([x, y], 1) * s
    r = math.radians(rot)
    R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    return pts @ R.T + np.array(c)


def note_pts(c, s):
    """八分音符: 符头 + 符干 + 符尾"""
    x, y = c
    head = [(x + math.cos(a) * s * 0.55 - math.sin(a) * 0, y + math.sin(a) * s * 0.4) for a in np.linspace(0, 2 * np.pi, 30)]
    return head


def sticker_band(alpha, r=7):
    """贴纸白边(超采样膨胀, 边缘利落) + 1px 极淡灰外缘"""
    up = cv2.resize(alpha.astype(np.float32), (512 * SS, 512 * SS), interpolation=cv2.INTER_LINEAR)
    up = (up > 0.5).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r * SS + 1, 2 * r * SS + 1))
    band = cv2.resize(cv2.dilate(up, k), (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * (r + 1) * SS + 1, 2 * (r + 1) * SS + 1))
    edge = cv2.resize(cv2.dilate(up, k2), (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    out = np.zeros((512, 512, 4), np.float32)
    out[..., :3] = 0.78; out[..., 3] = edge * 0.45
    white = np.zeros((512, 512, 4), np.float32); white[..., :3] = 1.0; white[..., 3] = band
    return over(out, white)


def radial_dashes(L, alpha, center, angles, length=16, clear=11, color=None, w=3.4):
    """从 center 往外的短线(用力/伸展); 自动推到角色轮廓外"""
    color = NAVY if color is None else color
    occ = dilate((alpha > 0.1).astype(np.uint8), clear)
    for ang in angles:
        a = math.radians(ang)
        d = np.array([math.cos(a), math.sin(a)])
        for r in range(60, 330, 2):
            p0 = np.array(center) + d * r; p1 = p0 + d * length
            pts = [p0 + (p1 - p0) * t for t in np.linspace(0, 1, 8)]
            x0, y0, x1, y1 = BOX[0] + 9, BOX[1] + 9, BOX[2] - 9, BOX[3] - 9
            if all(x0 <= p[0] < x1 and y0 <= p[1] < y1 and not occ[int(p[1]), int(p[0])] for p in pts):
                L.poly(tapered(np.array(pts), w, 1.0, 0.6), color)
                break


def clip_box(im):
    x0, y0, x1, y1 = BOX
    m = np.zeros((512, 512), np.float32); m[y0:y1 + 1, x0:x1 + 1] = 1
    im = im.copy(); im[..., 3] *= m
    return im


def add_deco(base, deco, band=True, r=7):
    """deco 在最上; 白边垫在角色下面(不盖住角色本身)"""
    out = base
    if band:
        out = over(sticker_band(deco[..., 3], r), out)
    out = over(out, deco)
    return clip_box(out)


def outlined(layer_fn, fill, edge, ew=1.6):
    """先画描边(稍粗)再画填充 -> 符号自带深色细边"""
    L = Layer()
    layer_fn(L, edge, ew)
    layer_fn(L, fill, 0)
    return L


# ---------------- 程序化眼睛 ----------------
def eye_geom(name, i):
    k = k_of(name)
    c = eyes_in(name)[i]
    rot = -math.degrees(math.atan2(T[name][1, 0], T[name][0, 0]))
    return c, k, rot


def rot_pts(pts, c, deg):
    r = math.radians(deg)
    R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    return (np.asarray(pts) - c) @ R.T + c


def happy_closed_eyes(name, L=None, lift=0.0):
    """^ ^ 眯眼笑: 粗弧 + 外眼角两根小睫毛"""
    L = L or Layer()
    for i in range(2):
        c, k, rot = eye_geom(name, i)
        c = (c[0], c[1] + (2 - lift) * k)
        w, h = 19 * k, 9 * k
        p0, p1, p2 = (c[0] - w, c[1] + h * 0.55), (c[0], c[1] - h * 1.45), (c[0] + w, c[1] + h * 0.55)
        arc = rot_pts(bezier(p0, p1, p2, 60), np.array(c), rot)
        L.poly(tapered(arc, 4.6 * k, 1.0 * k, 0.6), LASH)
        outer = 1 if i == 1 else -1          # 外眼角方向
        e = arc[-1] if outer > 0 else arc[0]
        for j, (ang, ln) in enumerate(((-35, 6.5), (-5, 5.5))):
            a = math.radians(ang)
            d = np.array([math.cos(a) * outer, math.sin(a)]) * ln * k
            seg = bezier(e, e + d * 0.6 + np.array([0, -1.5 * k]), e + d, 12)
            L.poly(tapered(seg, 2.4 * k, 0.4 * k, 0.5), LASH)
    return L


def xx_eyes(name, L=None):
    """> < 用力眯眼"""
    L = L or Layer()
    for i in range(2):
        c, k, rot = eye_geom(name, i)
        c = np.array((c[0], c[1] + 1 * k))
        s = 1 if i == 0 else -1               # 左眼 >, 右眼 <
        w, h = 13 * k, 10 * k
        pts = [(c[0] - s * w, c[1] - h), (c[0] + s * w * 0.9, c[1]), (c[0] - s * w, c[1] + h)]
        p = rot_pts(np.array(pts), c, rot)
        a = bezier(p[0], (p[0] + p[1]) / 2 + np.array([0, 0.8 * k]), p[1], 24)
        b = bezier(p[1], (p[1] + p[2]) / 2 + np.array([0, -0.8 * k]), p[2], 24)
        L.poly(tapered(a, 4.4 * k, 1.2 * k, 0.5), LASH)
        L.poly(tapered(b, 4.4 * k, 1.2 * k, 0.5), LASH)
        L.circle(p[1], 2.1 * k, LASH)
    return L


def spiral_eyes(name, L=None):
    L = L or Layer()
    for i in range(2):
        c, k, rot = eye_geom(name, i)
        c = (c[0] + (1 if i == 0 else -1) * k, c[1] + 1 * k)
        t = np.linspace(0, 2.6 * 2 * np.pi, 160)
        r = (1.8 + 14.0 * t / t[-1]) * k
        sgn = 1 if i == 0 else -1
        pts = np.stack([c[0] + r * np.cos(sgn * t), c[1] + r * np.sin(sgn * t) * 0.92], 1)
        L.poly(tapered(pts, 3.0 * k, 1.4 * k, 0.3), NAVY)
    return L


# ---------------- 虹膜平移(看向一侧) ----------------
def glance(name, base, dx_px, dy_px=0.0):
    """虹膜在眼眶内平移; 眼眶 = 凸包内 非睫毛 且 非皮肤 的像素"""
    out = base.copy()
    src = IM[name]
    hsv = hsv8(src)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    k = k_of(name)
    for hull in eye_masks(name):
        hb = hull > 0
        lash = (V < 125) & ~((H >= 70) & (H <= 105) & (S > 70))
        skin = (((H <= 25) | (H >= 160)) & (S < 75) & (V > 200))
        whiteish = (V > 225) & (S < 22) & ~skin
        opening = (hb & ~lash & ~skin).astype(np.uint8)
        opening = cv2.morphologyEx(opening, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(opening)
        if n <= 1:
            continue
        big = 1 + int(np.argmax(st[1:, 4]))
        opening = (lab == big).astype(np.uint8)
        opening = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        iris = (opening > 0) & ~whiteish
        iris = cv2.morphologyEx(iris.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        cnts, _ = cv2.findContours(iris, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        irisf = np.zeros_like(iris)
        cv2.drawContours(irisf, [max(cnts, key=cv2.contourArea)], -1, 1, -1)
        ys, xs = np.nonzero(opening)
        y0, y1 = ys.min(), ys.max()
        t = np.clip((np.arange(512) - y0) / max(1.0, (y1 - y0) * 0.55), 0, 1)[:, None, None]
        top = np.array([0.80, 0.74, 0.76], np.float32)          # 上眼睑投影(偏紫灰)
        bot = np.array([0.985, 0.975, 0.97], np.float32)
        sclera = np.ones((512, 512, 4), np.float32)
        sclera[..., :3] = top * (1 - t) + bot * t
        M = np.float32([[1, 0, dx_px * k], [0, 1, dy_px * k]])
        moved = warp(src, M)
        mi = warp(irisf.astype(np.float32), M)
        layer = blend(sclera, moved, feather(mi > 0.5, 1.0))
        om = feather(dilate(opening, 1), 1.0) * hb
        out = blend(out, layer, om)
        lm = feather((lash & hb).astype(np.uint8), 0.7)
        out = blend(out, src, np.clip(lm * 1.1, 0, 1))
    return out


# ---------------- 符号 ----------------
GOLD = np.array([77, 210, 255], np.float32) / 255.0          # BGR
GOLD_E = np.array([20, 140, 210], np.float32) / 255.0
PINK = np.array([150, 120, 255], np.float32) / 255.0
PINK_E = np.array([105, 70, 220], np.float32) / 255.0
MINT = np.array([200, 225, 120], np.float32) / 255.0
MINT_E = np.array([150, 170, 40], np.float32) / 255.0
SKY = np.array([245, 210, 140], np.float32) / 255.0
SKY_E = np.array([200, 140, 60], np.float32) / 255.0
BLUSH = np.array([150, 140, 245], np.float32) / 255.0


def deco_star(L, c, r, rot=-90, fill=GOLD, edge=GOLD_E):
    pts = star_pts(c, r, rot=rot)
    L.poly(pts, edge, True, 2.0); L.poly(pts, fill)


def deco_sparkle(L, c, r, fill=GOLD, edge=GOLD_E, rot=0):
    pts = sparkle_pts(c, r, rot)
    L.poly(pts, edge, True, 1.6); L.poly(pts, fill)


def deco_heart(L, c, s, rot=0, fill=PINK, edge=PINK_E):
    pts = heart_pts(c, s, rot)
    L.poly(pts, edge, True, 1.8); L.poly(pts, fill)
    hl = heart_pts((c[0] - s * 0.35, c[1] - s * 0.25), s * 0.22, rot)
    L.poly(hl, np.array([1, 1, 1.0]))


def deco_drop(L, c, s, rot=0):
    pts = drop_pts(c, s, rot)
    L.poly(pts, SKY_E, True, 1.6); L.poly(pts, SKY)
    L.circle((c[0] - s * 0.18, c[1] + s * 0.25), s * 0.16, np.array([1, 1, 1.0]))


def deco_arcs(L, c, r, a0, a1, n=3, gap=7, color=NAVY, w=3.0):
    """动作弧线(挥手/伸展)"""
    for i in range(n):
        rr = r + i * gap
        t = np.radians(np.linspace(a0, a1, 30))
        pts = np.stack([c[0] + rr * np.cos(t), c[1] + rr * np.sin(t)], 1)
        L.poly(tapered(pts, w, 0.8, 0.6), color)


def deco_note(L, c, s, color=NAVY):
    x, y = c
    L.poly([(x + s * 0.30, y - s * 1.15), (x + s * 0.30 + s * 0.16, y - s * 1.15), (x + s * 0.30 + s * 0.16, y), (x + s * 0.30, y)], color)
    head = [(x + math.cos(a) * s * 0.42 * math.cos(-0.45) - math.sin(a) * s * 0.30 * math.sin(-0.45),
             y + math.cos(a) * s * 0.42 * math.sin(-0.45) + math.sin(a) * s * 0.30 * math.cos(-0.45)) for a in np.linspace(0, 2 * np.pi, 30)]
    L.poly(head, color)
    flag = bezier((x + s * 0.40, y - s * 1.15), (x + s * 0.95, y - s * 0.85), (x + s * 0.80, y - s * 0.35), 20)
    L.poly(tapered(flag, s * 0.22, s * 0.08, 0.6), color)


def deco_squiggle(L, c, w, h, color=NAVY, lw=2.6):
    t = np.linspace(0, 1, 50)
    pts = np.stack([c[0] - w / 2 + w * t, c[1] + h * np.sin(t * 2 * np.pi * 1.5)], 1)
    L.poly(tapered(pts, lw, 0.9, 0.5), color)


def deco_hatch(L, c, k, n=3, color=BLUSH):
    for j in range(n):
        x = c[0] - 6 * k + j * 6 * k
        L.poly(tapered([(x + 2.5 * k, c[1] - 3 * k), (x - 1.5 * k, c[1] + 3 * k)], 2.2 * k, 0.8 * k, 0.6), color * 0.85)


def deco_blush(base, name, strength=0.55):
    k = k_of(name)
    out = base.copy()
    for i, (cx, cy) in enumerate(eyes_in(name)):
        m = np.zeros((512, 512), np.float32)
        cv2.ellipse(m, (int(cx + (-2 if i == 0 else 2) * k), int(cy + 26 * k)), (int(15 * k), int(7 * k)), 0, 0, 360, 1, -1)
        m = cv2.GaussianBlur(m, (0, 0), 4 * k) * strength
        col = np.zeros_like(out); col[..., :3] = BLUSH; col[..., 3] = 1
        out = blend(out, col, m * (out[..., 3] > 0.9))
    return out


# ---------------- 生成 ----------------
def strip_component(im, x0, y0, x1, y1):
    """把指定矩形里的独立符号(比如 '!')连同白边一起抹掉"""
    out = im.copy()
    a = (out[..., 3] > 0.02).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(a)
    yy, xx = np.mgrid[0:512, 0:512]
    box = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
    out[..., 3] = np.where(box, 0, out[..., 3])
    return out


def make_all():
    res = {}
    E = lambda n: eyes_in(n)
    # ---- look: 往右看 / look_left 往左看(idle 虹膜平移) ----
    res['look'] = glance('idle', IM['idle'], 5.5, 0.5)
    res['look_left'] = glance('idle', IM['idle'], -5.5, 0.5)

    # ---- cheer: happy + ^^ 眼 + 星星彩纸 ----
    b = cover_eyes('happy')
    L = happy_closed_eyes('happy')
    b = over(b, L.get())
    b = deco_blush(b, 'happy', 0.35)
    D = Layer()
    deco_star(D, (60, 190), 17, -80)
    deco_star(D, (452, 205), 13, -100)
    deco_sparkle(D, (100, 152), 10)
    deco_sparkle(D, (420, 160), 9, MINT, MINT_E)
    deco_sparkle(D, (478, 262), 7, PINK, PINK_E)
    deco_heart(D, (34, 255), 9, -18)
    res['cheer'] = add_deco(b, D.get())

    # ---- wave: happy + 挥动弧线 + 闪光 ----
    b = IM['happy'].copy()
    D = Layer()
    deco_arcs(D, (95, 300), 52, 195, 250, 3, 8, NAVY, 3.2)
    deco_sparkle(D, (60, 185), 12)
    deco_sparkle(D, (128, 160), 7, MINT, MINT_E)
    deco_note(D, (440, 215), 22)
    res['wave'] = add_deco(b, D.get())

    # ---- stretch: happy + >< 眼 + 用力线 ----
    b = cover_eyes('happy')
    b = over(b, xx_eyes('happy').get())
    b = deco_blush(b, 'happy', 0.3)
    D = Layer()
    radial_dashes(D, b[..., 3], (250, 300), (200, 218, 236), 15)
    radial_dashes(D, b[..., 3], (250, 300), (306, 322, 340), 15)
    deco_sparkle(D, (466, 262), 9)
    deco_sparkle(D, (40, 270), 7, MINT, MINT_E)
    res['stretch'] = add_deco(b, D.get())

    # ---- yawn: 睡姿(去 zzz/鼻泡) + 惊讶的圆嘴 + 泪花 ----
    b = SLEEP_NOBUB.copy()
    a = b[..., 3]; yy, xx = np.mgrid[0:512, 0:512]; a[(xx < 117) & (yy < 302)] = 0; b[..., 3] = a
    # 先抹掉原来的小嘴, 再贴圆嘴
    skin = SLEEP_CLEAN
    mm = mouth_mask('sleep', 10, 6)
    b = blend(b, skin, feather(mm, 2))
    src_m = mouth_mask('surprised', 13, 15, 0, 3)
    b = transplant(IM['surprised'], 'surprised', b, 'sleep', src_m, 2.5)
    D = Layer()
    c, k, _ = eye_geom('sleep', 1)
    deco_drop(D, (c[0] + 21 * k, c[1] - 2 * k), 5.5 * k, -35)
    tear = D.get()
    b = over(b, tear)
    D2 = Layer()
    deco_squiggle(D2, (78, 230), 34, 4.5)
    deco_squiggle(D2, (70, 258), 22, 3.5)
    res['yawn'] = add_deco(b, D2.get())

    # ---- dizzy: surprised 去掉 '!' + 蚊香眼 ----
    b = strip_component(IM['surprised'], 0, 150, 140, 262)
    bb = cover_eyes('surprised', b)
    bb = over(bb, spiral_eyes('surprised').get())
    D = Layer()
    deco_star(D, (70, 200), 12, -70)
    deco_star(D, (448, 190), 10, -110)
    deco_sparkle(D, (105, 165), 8)
    deco_squiggle(D, (440, 240), 26, 4)
    res['dizzy'] = add_deco(bb, D.get())

    # ---- eat: idle + ^^ 眼 + 生气图的鼓腮嘴(咀嚼) + 爱心 ----
    b = cover_eyes('idle')
    b = over(b, happy_closed_eyes('idle').get())
    mm = mouth_mask('idle', 10, 6)
    b = blend(b, warp(SLEEP_CLEAN, xf('sleep', 'idle')), feather(mm, 2))
    src_m = mouth_mask('angry', 17, 11, 0, 1)
    b = transplant(IM['angry'], 'angry', b, 'idle', src_m, 2.5)
    b = deco_blush(b, 'idle', 0.4)
    D = Layer()
    deco_heart(D, (448, 200), 12, 15)
    deco_sparkle(D, (60, 190), 9)
    deco_note(D, (420, 160), 15)
    res['eat'] = add_deco(b, D.get())

    # ---- content: 抱法杖睡姿 + ^^ 眼(被摸头) ----
    b = SLEEP_CLEAN.copy()
    a = b[..., 3]; a[(xx < 117) & (yy < 302)] = 0; b[..., 3] = a
    b = over(b, happy_closed_eyes('sleep').get())
    b = deco_blush(b, 'sleep', 0.45)
    D = Layer()
    deco_heart(D, (70, 210), 13, -15)
    deco_heart(D, (448, 205), 9, 18)
    deco_sparkle(D, (100, 160), 8, PINK, PINK_E)
    res['content'] = add_deco(b, D.get())

    # ---- shy: idle 往旁边看 + 重腮红 + 斜线 + 汗滴 ----
    b = glance('idle', IM['idle'], -5.0, 1.5)
    b = deco_blush(b, 'idle', 0.75)
    L = Layer()
    k = k_of('idle')
    for i, (cx, cy) in enumerate(eyes_in('idle')):
        deco_hatch(L, (cx + (-2 if i == 0 else 2) * k, cy + 26 * k), k)
    deco_drop(L, (322, 272), 8, 25)
    b = over(b, L.get())
    D = Layer()
    deco_heart(D, (448, 210), 10, 15)
    res['shy'] = add_deco(b, D.get())

    # ---- focus: idle + 生气图的半眯认真眼 ----
    b = cover_eyes('idle')
    em = np.zeros((512, 512), np.uint8)
    for e in eye_masks('angry'):
        em |= e
    b = transplant(IM['angry'], 'angry', b, 'idle', dilate(em, 3), 2)
    D = Layer()
    deco_sparkle(D, (452, 200), 11, MINT, MINT_E)
    deco_sparkle(D, (62, 196), 8)
    res['focus'] = add_deco(b, D.get())

    # ---- love: happy + 眼中爱心高光 ----
    b = IM['happy'].copy()
    L = Layer()
    for i, (cx, cy) in enumerate(eyes_in('happy')):
        kk = k_of('happy')
        deco_heart(L, (cx + (2 if i == 0 else -1) * kk, cy + 2 * kk), 9.5 * kk, 0)
    b = over(b, L.get())
    D = Layer()
    deco_heart(D, (62, 196), 15, -15)
    deco_heart(D, (450, 196), 11, 18)
    deco_heart(D, (100, 152), 7, -5)
    res['love'] = add_deco(b, D.get())

    # ---- 探头: 把 happy / surprised 的脸换进 peek_awake ----
    pk = IM['peek_awake']
    for nm, src in (('peek_happy', 'happy'), ('peek_surprised', 'surprised')):
        b = pk.copy()
        # 先用 peek 自己的脸 -> 盖眼(用睡脸皮肤)
        sk = warp(SLEEP_CLEAN, xf('sleep', 'peek_awake'))
        em = np.zeros((512, 512), np.uint8)
        for e in eye_masks('peek_awake'):
            em |= e
        kk = k_of('peek_awake')
        b = blend(b, sk, feather(dilate(em, int(4 * kk)), 3 * kk) * (sk[..., 3] > 0.9))
        mm = mouth_mask('peek_awake', 10, 6)
        b = blend(b, sk, feather(mm, 2) * (sk[..., 3] > 0.9))
        se = np.zeros((512, 512), np.uint8)
        for e in eye_masks(src):
            se |= e
        se = dilate(se, 3)
        smm = mouth_mask(src, 14, 14, 0, 2) if src == 'surprised' else mouth_mask(src, 16, 13, 0, 2)
        b = transplant(IM[src], src, b, 'peek_awake', se | smm, 2.5)
        b[..., 3] = np.minimum(b[..., 3], pk[..., 3])
        res[nm] = b
    return res


if __name__ == '__main__':
    import os
    os.makedirs(OUT, exist_ok=True)
    res = make_all()
    for k, v in res.items():
        cv2.imwrite(OUT + k + '.png', to8(v))
    print('ok', sorted(res))
