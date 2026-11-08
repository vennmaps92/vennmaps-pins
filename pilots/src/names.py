import sys, json, math
import numpy as np
from PIL import Image, ImageDraw
from common import *
from water import recolor

PIX = json.load(open(D + "pix.json"))
BASE = recolor(D + "base_counties.png")
BW, BH = BASE.size
MX, MY = 20, 500
MH = int(BH * 1040 / BW)
PRODUCT = Image.open(D + "CO_end_vintage.jpg").convert("RGB")

TOWNS = [  # name, speech start, fact start, fact
    ("Dinosaur", 3.6, 4.5, "Its streets include Brontosaurus Boulevard"),
    ("No Name", 7.38, 8.25, "The I-70 exit sign really says No Name"),
    ("Hygiene", 12.31, 13.01, "Named for an 1880s tuberculosis sanitarium"),
    ("Paradox", 15.61, 16.57, "The river cuts across the valley, not down it"),
    ("Last Chance", 19.3, 21.07, "The last stop before the empty plains"),
]
T_FAV, T_END, T_TOTAL = 23.4, 25.0, 28.0


def active(t):
    cur = None
    for i, tw in enumerate(TOWNS):
        if t >= tw[1] - 0.15:
            cur = i
    return cur


def target(i):
    if i is None:
        return 1.0, (BW / 2, BH / 2)
    return 1.2, tuple(PIX["towns"][TOWNS[i][0]])


def view(t):
    # blend from previous target to current target over 0.7 s after each switch
    i = active(t)
    if t >= T_FAV:
        zp, cp = target(len(TOWNS) - 1)
        u = ease((t - T_FAV) / 0.8)
        zc, cc = 1.0, (BW / 2, BH / 2)
    elif i is None:
        zp, cp = zc, cc = 1.0, (BW / 2, BH / 2)
        u = 1
    else:
        zp, cp = target(i - 1) if i > 0 else (1.0, (BW / 2, BH / 2))
        zc, cc = target(i)
        u = ease((t - (TOWNS[i][1] - 0.15)) / 0.7)
    z = zp + (zc - zp) * u
    cx = cp[0] + (cc[0] - cp[0]) * u
    cy = cp[1] + (cc[1] - cp[1]) * u
    bw, bh = BW / z, BH / z
    x0 = min(max(cx - bw / 2, 0), BW - bw)
    y0 = min(max(cy - bh / 2, 0), BH - bh)
    return x0, y0, bw, bh


def pin(d, x, y, s, col):
    r = 13 * s
    d.ellipse([x - r - 4, y - 2.6 * r - r - 4, x + r + 4, y - 2.6 * r + r + 4], fill=(255, 255, 255))
    d.polygon([(x - r * 0.8, y - 2.4 * r), (x + r * 0.8, y - 2.4 * r), (x, y)], fill=col)
    d.ellipse([x - r, y - 2.6 * r - r, x + r, y - 2.6 * r + r], fill=col)
    d.ellipse([x - r * 0.38, y - 2.6 * r - r * 0.38, x + r * 0.38, y - 2.6 * r + r * 0.38], fill=(255, 255, 255))


def frame(t):
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    x0, y0, bw, bh = view(t)
    m = BASE.resize((1040, MH), Image.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh), reducing_gap=2.0).convert("RGBA")
    img.alpha_composite(m, (MX, MY))
    lab = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lab)
    cur = active(t)
    f_lab = font("B", 42)
    for i, (nm, ts, tf, fact) in enumerate(TOWNS):
        if t < ts - 0.15:
            continue
        p = PIX["towns"][nm]
        x = MX + (p[0] - x0) * 1040 / bw
        y = MY + (p[1] - y0) * MH / bh
        k = (t - (ts - 0.15)) / 0.45
        drop = (1 - ease_out(min(k, 1))) * 160
        bounce = math.sin(min(k, 1) * math.pi) * 0  # keep it clean
        on = (i == cur) or t >= T_FAV
        col = RED if on else (150, 120, 100)
        pin(d, x, y - drop, 1.4 if on else 1.0, col)
        a = int(255 * min(1, max(0, k)))
        d.text((x + 24, y - 52), nm, font=f_lab, fill=(INK if on else (120, 105, 85)) + (a,), stroke_width=4,
               stroke_fill=(255, 255, 255, a))
    clip = Image.new("L", (W, H), 0)
    ImageDraw.Draw(clip).rectangle([MX, MY, MX + 1040, MY + MH], fill=255)
    lab.putalpha(Image.fromarray(np.minimum(np.array(lab.getchannel("A")), np.array(clip))))
    img.alpha_composite(lab)
    # header
    text_center(img, 150, "COLORADO'S WEIRDEST", font("B", 78), INK, ramp(t, 0, 0.4), letter=2)
    text_center(img, 250, "TOWN NAMES", font("B", 96), RED, ramp(t, 0.3, 0.7), letter=4)
    # caption card
    y = MY + MH + 50
    if cur is not None and t < T_FAV:
        nm, ts, tf, fact = TOWNS[cur]
        a = ramp(t, ts - 0.15, ts + 0.2)
        text_center(img, y, nm.upper(), font("B", 100), RED, a, letter=4)
        fa = ramp(t, tf - 0.2, tf + 0.2)
        for j, line in enumerate(wrap(fact, font("I", 56), 960)):
            text_center(img, y + 135 + j * 70, line, font("I", 56), INK, fa)
    elif cur is None:
        text_center(img, y + 40, "5 real places, 1 state", font("I", 58), INK, ramp(t, 0.8, 1.2))
    else:
        a = ramp(t, T_FAV, T_FAV + 0.3)
        text_center(img, y + 30, "Which one's", font("B", 84), INK, a)
        text_center(img, y + 130, "your favorite?", font("B", 84), INK, a)
    brand(img)
    endcard(img, t, T_END, PRODUCT, "Every county & town", "VennMaps on Etsy", "12x18 & 24x36 · Free US shipping")
    return img


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for t in map(float, sys.argv[1:]):
            frame(t).convert("RGB").save(f"/tmp/names_{t}.jpg", quality=88)
        sys.exit()
    w = Writer("names_v.mp4")
    for i in range(int(T_TOTAL * FPS)):
        w.write(frame(i / FPS))
    w.close()
    mux("names_v.mp4", D + "names_tight.wav", "CO_weird_town_names.mp4", 0.0)
