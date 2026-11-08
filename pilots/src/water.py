import sys, json, math
import numpy as np
from PIL import Image, ImageDraw
from common import *

Image.MAX_IMAGE_PIXELS = None
PIX = json.load(open(D + "pix.json"))


def recolor(path):
    a = np.array(Image.open(path).convert("RGB"))
    m = (a[:, :, 0] == 243) & (a[:, :, 1] == 236) & (a[:, :, 2] == 221)
    a[m] = CREAM
    return Image.fromarray(a)


BASE = recolor(D + "base_rivers.png")  # 2000 x 1603
K = 1040 / BASE.size[0]
MX, MY = 20, 500
MH = int(BASE.size[1] * K)
POSTER = Image.open(D + "CO_hydro_blue_relief.jpg").convert("RGB").resize((1800, 1200), Image.LANCZOS)

E = PIX["routes"]["Cache la Poudre River"]
Wr = PIX["routes"]["Colorado River"]
NAVY = (20, 70, 140)
ORNG = (196, 84, 36)


def cum(pts):
    c = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        c.append(c[-1] + math.hypot(x1 - x0, y1 - y0))
    return c


EC, WC = cum(E["px"]), cum(Wr["px"])


def partial(pts, c, f):
    L = c[-1] * f
    out = [pts[0]]
    for i in range(1, len(pts)):
        if c[i] <= L:
            out.append(pts[i])
        else:
            k = (L - c[i - 1]) / max(c[i] - c[i - 1], 1e-9)
            out.append([pts[i - 1][0] + k * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + k * (pts[i][1] - pts[i - 1][1])])
            break
    return out


T = dict(east0=6.2, east1=12.5, west0=14.5, west1=19.5, divide=19.83, end=21.9, total=25.0)


def drop(d, x, y, r, col):
    d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    d.polygon([(x - r * 0.93, y - r * 0.35), (x + r * 0.93, y - r * 0.35), (x, y - r * 2.3)], fill=col)


RM = PIX["towns"]["RMNP"]


def view(t):
    z = 3.0 + (1.0 - 3.0) * ease((t - 4.9) / 1.4)
    u = ease((t - 4.9) / 1.4)
    cx = RM[0] + (1000 - RM[0]) * u
    cy = RM[1] + 60 + (801.5 - RM[1] - 60) * u
    bw, bh = 2000 / z, 1603 / z
    x0 = min(max(cx - bw / 2, 0), 2000 - bw)
    y0 = min(max(cy - bh / 2, 0), 1603 - bh)
    return x0, y0, bw, bh


VIEW = (0, 0, 2000, 1603)


def tomap(p):
    x0, y0, bw, bh = VIEW
    return (MX + (p[0] - x0) * 1040 / bw, MY + (p[1] - y0) * MH / bh)


def frame(t):
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    # map with routes drawn at 2x
    m = BASE.copy()
    d = ImageDraw.Draw(m)
    fe = ease((t - T["east0"]) / (T["east1"] - T["east0"])) if t > T["east0"] else 0
    fw = ease((t - T["west0"]) / (T["west1"] - T["west0"])) if t > T["west0"] else 0
    for pts, c, f, col in ((E["px"], EC, fe, NAVY), (Wr["px"], WC, fw, ORNG)):
        if f > 0:
            pp = [tuple(p) for p in partial(pts, c, f)]
            d.line(pp, fill=(255, 255, 255), width=22, joint="curve")
            d.line(pp, fill=col, width=12, joint="curve")
    global VIEW
    VIEW = view(t)
    x0, y0, bw, bh = VIEW
    m = m.resize((1040, MH), Image.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh), reducing_gap=2.0).convert("RGBA")
    img.alpha_composite(m, (MX, MY))
    dd = ImageDraw.Draw(img)
    # raindrops: fall then travel with the route head
    for pts, c, f, col, t0 in ((E["px"], EC, fe, NAVY, 1.0), (Wr["px"], WC, fw, ORNG, 1.5)):
        sx, sy = tomap(pts[0])
        if t < t0:
            continue
        k = ease_out((t - t0) / 1.0)
        if f > 0:
            hx, hy = tomap(partial(pts, c, f)[-1])
        else:
            hx, hy = sx, sy - (1 - k) * 420
        r = 11
        dd.ellipse([hx - r - 5, hy - r - 5, hx + r + 5, hy + r + 5], fill=(255, 255, 255))
        drop(dd, hx, hy, r, col)
    # header
    a_div = ramp(t, T["divide"], T["divide"] + 0.3)
    text_center(img, 150, "WHERE DOES", font("B", 90), INK, (1 - a_div) * ramp(t, 0, 0.4), letter=3)
    text_center(img, 260, "THE RAIN GO?", font("B", 90), INK, (1 - a_div) * ramp(t, 0.2, 0.6), letter=3)
    text_center(img, 180, "THE CONTINENTAL", font("B", 90), RED, a_div, letter=3)
    text_center(img, 290, "DIVIDE", font("B", 90), RED, a_div, letter=3)
    text_center(img, 390, "Two raindrops · Rocky Mountain National Park", font("I", 40), INK,
                ramp(t, 1.8, 2.3) * (1 - a_div))
    # map labels at the state line
    ex, ey = tomap(E["px"][-1])
    wx, wy = tomap(Wr["px"][-1])
    lab = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lab)
    f_l = font("BI", 34)
    ae, aw = ramp(t, T["east1"] - 0.3, T["east1"] + 0.2), ramp(t, T["west1"] - 0.3, T["west1"] + 0.2)
    if ae:
        ld.text((ex - 200, ey - 66), "to Nebraska", font=f_l, fill=NAVY + (int(255 * ae),), stroke_width=4, stroke_fill=(255, 255, 255, int(255 * ae)))
    if aw:
        ld.text((wx + 14, wy + 22), "to Utah", font=f_l, fill=ORNG + (int(255 * aw),), stroke_width=4, stroke_fill=(255, 255, 255, int(255 * aw)))
    img.alpha_composite(lab)
    # counters
    y0 = MY + MH + 60
    if t > T["east0"] - 0.6:
        a = ramp(t, T["east0"] - 0.6, T["east0"])
        mi = round(E["miles"] * fe)
        text_center(img, y0, f"EAST · {mi} miles", font("B", 62), NAVY, a)
        text_center(img, y0 + 80, "on to the Gulf of Mexico", font("I", 50), NAVY, ae)
    if t > T["west0"] - 0.6:
        a = ramp(t, T["west0"] - 0.6, T["west0"])
        mi = round(Wr["miles"] * fw)
        text_center(img, y0 + 190, f"WEST · {mi} miles", font("B", 62), ORNG, a)
        text_center(img, y0 + 270, "on to the Gulf of California", font("I", 50), ORNG, aw)
    brand(img)
    endcard(img, t, T["end"], POSTER, "Every river in Colorado", "VennMaps on Etsy", "12x18 & 24x36 · Free US shipping")
    return img


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for t in map(float, sys.argv[1:]):
            frame(t).convert("RGB").save(f"/tmp/water_{t}.jpg", quality=88)
        sys.exit()
    w = Writer("water_v.mp4")
    for i in range(int(T["total"] * FPS)):
        w.write(frame(i / FPS))
    w.close()
    mux("water_v.mp4", D + "water_tight.wav", "CO_where_the_water_goes.mp4", 0.0)
