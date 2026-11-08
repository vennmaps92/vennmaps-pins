"""Find the state geology map inside each <ST>_ig_3_full.jpg; writes data/maps.json {ST: [x0,y0,x1,y1]}."""
import json, os, math, sys
sys.argv = sys.argv[:1]
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

D = os.path.dirname(os.path.abspath(__file__))

def runs(mask1d, minlen):
    out = []; start = None
    for i, v in enumerate(list(mask1d) + [False]):
        if v and start is None: start = i
        if not v and start is not None:
            if i - start >= minlen: out.append((start, i))
            start = None
    return out

def poster_rect(a):
    """Largest frame rectangle drawn with the dark frame colour."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dark = (abs(r - 95) < 30) & (abs(g - 88) < 30) & (abs(b - 76) < 30)
    H, W = dark.shape
    hl = []
    for y in range(H):
        for s, e in runs(dark[y], 250): hl.append((y, s, e))
    vl = []
    for x in range(W):
        for s, e in runs(dark[:, x], 250): vl.append((x, s, e))
    best = None
    for (y, s, e) in hl:
        for (y2, s2, e2) in hl:
            if y2 - y < 200 or abs(s - s2) > 8 or abs(e - e2) > 8: continue
            # no other line with the same extent between them (consecutive frames)
            if any(y + 6 < y3 < y2 - 6 and abs(s3 - s) < 8 and abs(e3 - e) < 8 for (y3, s3, e3) in hl): continue
            area = (e - s) * (y2 - y)
            if best is None or area > best[0]: best = (area, s, y, e, y2)
    if best is None:
        return (0, 200, W, 1190)
    _, x0, y0, x1, y1 = best
    return (x0 + 4, y0 + 4, x1 - 4, y1 - 4)

def detect(path, use_warm=True):
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    x0, y0, x1, y1 = poster_rect(a)
    sub = a[y0:y1, x0:x1] / 255
    mx, mn = sub.max(2), sub.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    warm = (sub[..., 0] - sub[..., 2]) / np.maximum(sub[..., 0], 1e-6)
    m = ((sat > 0.15) | (warm < 0.05)) if use_warm else (sat > 0.15)
    m = ndi.binary_opening(m, iterations=1)
    m = ndi.binary_closing(m, iterations=3)
    m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1)); objs = ndi.find_objects(lab)
    order = list(np.argsort(sizes)[::-1])
    def shape_ok(k):
        sl = objs[k]; h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        return max(h, w) / max(1, min(h, w)) < 4.0
    main = next(k for k in order if shape_ok(k))
    sl = objs[main]
    by0, by1, bx0, bx1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    for k in order:
        if k == main or sizes[k] < 0.03 * sizes[main] or not shape_ok(k): continue
        s2 = objs[k]
        a0, a1, b0, b1 = s2[0].start, s2[0].stop, s2[1].start, s2[1].stop
        pad = 0.15 * max(by1 - by0, bx1 - bx0)
        if b0 < bx1 + pad and b1 > bx0 - pad and a0 < by1 + pad and a1 > by0 - pad:
            by0, by1, bx0, bx1 = min(by0, a0), max(by1, a1), min(bx0, b0), max(bx1, b1)
    return [int(x0 + bx0), int(y0 + by0), int(x0 + bx1), int(y0 + by1)], [int(x0), int(y0), int(x1), int(y1)]

def expected_aspect(st):
    import importlib.util
    src = open(os.path.join(D, "gen.py")).read()
    start = src.index("BBOX = dict("); end = src.index("MAPS = json")
    ns = {}; exec(src[start:src.index("WARN = []")], ns)
    w, e, s, n = ns["BBOX"][st]
    lon0 = math.radians((w + e) / 2); p1 = math.radians(s + (n - s) / 6); p2 = math.radians(n - (n - s) / 6)
    nn = (math.sin(p1) + math.sin(p2)) / 2; C = math.cos(p1) ** 2 + 2 * nn * math.sin(p1)
    def P(lon, lat):
        rho = math.sqrt(C - 2 * nn * math.sin(math.radians(lat))) / nn; th = nn * (math.radians(lon) - lon0)
        return rho * math.sin(th), -rho * math.cos(th)
    pts = [P(w + (e - w) * t / 40, s) for t in range(41)] + [P(w + (e - w) * t / 40, n) for t in range(41)] + \
          [P(w, s + (n - s) * t / 40) for t in range(41)] + [P(e, s + (n - s) * t / 40) for t in range(41)]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (max(xs) - min(xs)) / (max(ys) - min(ys))

if __name__ == "__main__":
    out = {}
    states = sorted(f.split("_")[0] for f in os.listdir(f"{D}/all") if f.endswith("_ig_3_full.jpg"))
    tiles = []
    for st in states:
        p = f"{D}/all/{st}_ig_3_full.jpg"
        exp = expected_aspect(st)
        best = None
        for uw in (True, False):
            b, pr = detect(p, uw); asp = (b[2] - b[0]) / max(1, b[3] - b[1])
            err = abs(math.log(asp / exp))
            if best is None or err < best[0]: best = (err, b, pr)
        err, b, pr = best; out[st] = b
        if err > 0.05: print("CHECK", st, round(math.exp(err), 3))
        im = Image.open(p).convert("RGB"); d = ImageDraw.Draw(im)
        d.rectangle(pr, outline=(0, 0, 255), width=3)
        d.rectangle(b, outline=(255, 0, 0), width=5); d.text((20, 20), st, fill=(255, 0, 0))
        tiles.append(im.resize((216, 270)))
    json.dump(out, open(f"{D}/data/maps.json", "w"), indent=0)
    s = Image.new("RGB", (216 * 12, 270 * 4))
    for i, t in enumerate(tiles): s.paste(t, ((i % 12) * 216, (i // 12) * 270))
    s.save(f"{D}/detect_sheet.jpg")
