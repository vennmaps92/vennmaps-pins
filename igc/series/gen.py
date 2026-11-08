"""VennMaps carousel generator: "Rock Layers" (per state) and "Face-off" (state pairs).

python3 gen.py layers CO [UT ...]      -> out/c/CO_rl_1.jpg .. CO_rl_N.jpg (+ CO_rl_N_holiday.jpg for shop states)
python3 gen.py faceoff CO-UT [...]     -> out/c/CO-UT_fo_1.jpg .. _8.jpg (+ _8_holiday.jpg if both shop)
python3 gen.py all
Inputs: data/layers/<ST>.json, data/faceoff/<A>-<B>.json, data/maps.json (state map boxes in
all/<ST>_ig_3_full.jpg), all/<ST>_ig_5_etsy[_holiday].jpg.
"""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

D = os.path.dirname(os.path.abspath(__file__))
ALL = f"{D}/all"; OUT = f"{D}/out/c"; os.makedirs(OUT, exist_ok=True)
LM = "/usr/share/texmf/fonts/opentype/public/lm/"
_fc = {}
def F(kind, size):
    k = (kind, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(LM + {"b": "lmroman10-bold.otf", "i": "lmroman10-italic.otf", "r": "lmroman10-regular.otf",
                                          "bi": "lmroman10-bolditalic.otf", "c": "lmromancaps10-regular.otf"}[kind], size)
    return _fc[k]
W, H = 1080, 1350
BG = (246, 240, 224); INK = (34, 31, 27); RED = (138, 64, 51); GREY = (107, 99, 88); FRAME = (95, 88, 76)
LOSE = (180, 170, 152); HOLI = (166, 32, 32); GREEN = (30, 90, 50)

NAMES = dict(AL="Alabama", AZ="Arizona", AR="Arkansas", CA="California", CO="Colorado", CT="Connecticut", DE="Delaware",
             FL="Florida", GA="Georgia", ID="Idaho", IL="Illinois", IN="Indiana", IA="Iowa", KS="Kansas", KY="Kentucky",
             LA="Louisiana", ME="Maine", MD="Maryland", MA="Massachusetts", MI="Michigan", MN="Minnesota", MS="Mississippi",
             MO="Missouri", MT="Montana", NE="Nebraska", NV="Nevada", NH="New Hampshire", NJ="New Jersey", NM="New Mexico",
             NY="New York", NC="North Carolina", ND="North Dakota", OH="Ohio", OK="Oklahoma", OR="Oregon", PA="Pennsylvania",
             RI="Rhode Island", SC="South Carolina", SD="South Dakota", TN="Tennessee", TX="Texas", UT="Utah", VT="Vermont",
             VA="Virginia", WA="Washington", WV="West Virginia", WI="Wisconsin", WY="Wyoming")
NONSHOP = set("ID LA OK KS AR IA CT MS NE WV NH ME RI DE SD ND VT".split())

# lon/lat extent of each state's mapped land (W, E, S, N)
BBOX = dict(
 AL=(-88.47, -84.89, 30.22, 35.01), AZ=(-114.82, -109.04, 31.33, 37.00), AR=(-94.62, -89.64, 33.00, 36.50),
 CA=(-124.41, -114.13, 32.53, 42.01), CO=(-109.06, -102.04, 36.99, 41.00), CT=(-73.73, -71.79, 40.98, 42.05),
 DE=(-75.79, -75.05, 38.45, 39.84), FL=(-87.63, -80.03, 24.52, 31.00), GA=(-85.61, -80.84, 30.36, 35.00),
 ID=(-117.24, -111.04, 41.99, 49.00), IL=(-91.51, -87.50, 36.97, 42.51), IN=(-88.10, -84.78, 37.77, 41.76),
 IA=(-96.64, -90.14, 40.38, 43.50), KS=(-102.05, -94.59, 36.99, 40.00), KY=(-89.57, -81.96, 36.50, 39.15),
 LA=(-94.04, -88.82, 28.93, 33.02), ME=(-71.08, -66.95, 43.06, 47.46), MD=(-79.49, -75.05, 37.91, 39.72),
 MA=(-73.51, -69.93, 41.24, 42.89), MI=(-90.42, -82.41, 41.70, 47.47), MN=(-97.24, -89.49, 43.50, 49.38),
 MS=(-91.66, -88.10, 30.17, 35.00), MO=(-95.77, -89.10, 35.99, 40.61), MT=(-116.05, -104.04, 44.36, 49.00),
 NE=(-104.05, -95.31, 40.00, 43.00), NV=(-120.01, -114.04, 35.00, 42.00), NH=(-72.56, -70.61, 42.70, 45.31),
 NJ=(-75.56, -73.89, 38.93, 41.36), NM=(-109.05, -103.00, 31.33, 37.00), NY=(-79.76, -71.86, 40.50, 45.02),
 NC=(-84.32, -75.46, 33.84, 36.59), ND=(-104.05, -96.55, 45.94, 49.00), OH=(-84.82, -80.52, 38.40, 41.98),
 OK=(-103.00, -94.43, 33.62, 37.00), OR=(-124.57, -116.46, 41.99, 46.29), PA=(-80.52, -74.69, 39.72, 42.27),
 RI=(-71.86, -71.12, 41.15, 42.02), SC=(-83.35, -78.54, 32.03, 35.22), SD=(-104.06, -96.44, 42.48, 45.95),
 TN=(-90.31, -81.65, 34.98, 36.68), TX=(-106.65, -93.51, 25.84, 36.50), UT=(-114.05, -109.04, 37.00, 42.00),
 VT=(-73.44, -71.46, 42.73, 45.02), VA=(-83.68, -75.24, 36.54, 39.47), WA=(-124.73, -116.92, 45.54, 49.00),
 WV=(-82.64, -77.72, 37.20, 40.64), WI=(-92.89, -86.80, 42.49, 47.08), WY=(-111.06, -104.05, 40.99, 45.01))

WARN = []
MAPS = json.load(open(f"{D}/data/maps.json"))

# ---------------- helpers ----------------
def canvas(): return Image.new("RGB", (W, H), BG)

def ctext(d, y, s, font, fill=INK, x=W // 2, spacing=0):
    if spacing:
        ws = [d.textlength(ch, font=font) for ch in s]; tot = sum(ws) + spacing * (len(s) - 1); cx = x - tot / 2
        for ch, w in zip(s, ws): d.text((cx, y), ch, font=font, fill=fill); cx += w + spacing
        return
    d.text((x, y), s, font=font, fill=fill, anchor="ma")

def fitfont(d, s, kind, size, maxw, spacing=0):
    f = F(kind, size)
    while d.textlength(s, font=f) + spacing * len(s) > maxw and f.size > 14: f = F(kind, f.size - 2)
    return f

def wrap(d, s, font, maxw):
    out, line = [], ""
    for w in s.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: line = t
        else: out.append(line); line = w
    out.append(line); return out

def para(d, x, y, s, font, maxw, fill=INK, lh=1.32, draw=True):
    for ln in wrap(d, s, font, maxw):
        if draw: d.text((x, y), ln, font=font, fill=fill)
        y += int(font.size * lh)
    return y

def rule(d, y, w=140): d.line((W // 2 - w // 2, y, W // 2 + w // 2, y), fill=RED, width=3)

def title_block(d, y, title, sub, tsize=86, subsize=42):
    f = fitfont(d, title, "b", tsize, W - 100)
    ctext(d, y, title, f)
    bot = d.textbbox((W // 2, y), title, font=f, anchor="ma")[3]
    rule(d, bot + 34)
    if sub:
        sf = fitfont(d, sub, "i", subsize, W - 100)
        ctext(d, bot + 54, sub, sf, GREY); return bot + 54 + sf.size + 10
    return bot + 50

def footer(d, n, N):
    ctext(d, 1232, "VENNMAPS", F("b", 34), RED, spacing=1)
    ctext(d, 1278, ("Swipe for more   ·   " if n < N else "") + f"{n} / {N}", F("i", 30), GREY)

def framed(img, box, im):
    x0, y0, x1, y1 = [int(v) for v in box]
    sh = Image.new("RGBA", (x1 - x0, y1 - y0), (120, 110, 95, 90)); img.paste(sh, (x0 + 9, y0 + 9), sh)
    img.paste(im.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
    ImageDraw.Draw(img).rectangle((x0, y0, x1, y1), outline=FRAME, width=2)

def fit(im, maxw, maxh):
    r = min(maxw / im.width, maxh / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)

PAD = 8
TITLED = {"NH"}
TITLE_RECT = {"KY": (55, 238, 385, 326), "MS": (55, 238, 352, 312), "NY": (30, 238, 372, 322),
              "VA": (55, 238, 330, 318), "TX": (55, 238, 260, 318)}
def cover_title(full, rect):
    """Cover the poster title/scale bar with a feathered patch of the surrounding background tone."""
    from PIL import ImageFilter
    x0, y0, x1, y1 = rect
    ring = [full.getpixel((x, y)) for x in range(x0, x1, 6) for y in (y0 - 4, y1 + 4)]
    ring.sort(key=sum); col = ring[len(ring) * 2 // 3]
    mask = Image.new("L", full.size, 0); ImageDraw.Draw(mask).rectangle(rect, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(6))
    patch = Image.new("RGB", full.size, col)
    tex = full.filter(ImageFilter.GaussianBlur(14))
    patch = Image.blend(patch, tex, 0.0)
    return Image.composite(patch, full, mask)
def erase_title(full):
    """Paint out the poster title + scale bar (dark, unsaturated pixels top-left) with nearby background."""
    import numpy as np
    from scipy import ndimage as ndi
    a = np.asarray(full).astype(float) / 255
    y0, y1, x0, x1 = 235, 330, 30, 760
    sub = a[y0:y1, x0:x1]
    lum = sub.mean(2); sat = (sub.max(2) - sub.min(2)) / np.maximum(sub.max(2), 1e-6)
    warm = (sub[..., 0] - sub[..., 2]) / np.maximum(sub[..., 0], 1e-6)
    m = (lum < 0.62) & (sat < 0.15) & (warm >= 0.05)
    lab, n = ndi.label(ndi.binary_dilation(m, iterations=2))
    # keep only blobs that are mostly text/scale-bar (small), not big dark map areas
    sizes = ndi.sum(np.ones_like(lum), lab, range(1, n + 1))
    m = np.isin(lab, [i + 1 for i, z in enumerate(sizes) if z < 6000])
    # white boxes of the scale bar
    bar = (lum > 0.93) & (sat < 0.06)
    m = m | (ndi.binary_dilation(m, iterations=6) & bar)
    m = ndi.binary_dilation(m, iterations=2)
    keep = (~m).astype(float)
    num = np.stack([ndi.gaussian_filter(sub[..., c] * keep, 8) for c in range(3)], 2)
    den = ndi.gaussian_filter(keep, 8)[..., None]
    fill = num / np.maximum(den, 1e-3)
    sub = np.where(m[..., None], fill, sub)
    a = a.copy(); a[y0:y1, x0:x1] = sub
    return Image.fromarray((a * 255).clip(0, 255).astype("uint8"))

def state_map(st):
    x0, y0, x1, y1 = MAPS[st]
    full = Image.open(f"{ALL}/{st}_ig_3_full.jpg").convert("RGB")
    if st in TITLE_RECT: full = cover_title(full, TITLE_RECT[st])
    elif st in TITLED: full = erase_title(full)
    return full.crop((x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD))

# ---- projection: Albers centred on the state, fitted to the detected map box ----
def albers(st):
    w, e, s, n = BBOX[st]
    lon0 = math.radians((w + e) / 2); p1 = math.radians(s + (n - s) / 6); p2 = math.radians(n - (n - s) / 6)
    nn = (math.sin(p1) + math.sin(p2)) / 2; C = math.cos(p1) ** 2 + 2 * nn * math.sin(p1)
    rho0 = math.sqrt(C - 2 * nn * math.sin(math.radians((s + n) / 2))) / nn
    def P(lon, lat):
        rho = math.sqrt(C - 2 * nn * math.sin(math.radians(lat))) / nn; th = nn * (math.radians(lon) - lon0)
        return rho * math.sin(th), rho0 - rho * math.cos(th)
    pts = [P(w + (e - w) * t / 40, s) for t in range(41)] + [P(w + (e - w) * t / 40, n) for t in range(41)] + \
          [P(w, s + (n - s) * t / 40) for t in range(41)] + [P(e, s + (n - s) * t / 40) for t in range(41)]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    bx0, by0, bx1, by1 = MAPS[st]
    sx = (bx1 - bx0) / (max(xs) - min(xs)); sy = (by1 - by0) / (max(ys) - min(ys))
    def to_crop(lon, lat):  # pixel in the state_map() crop
        x, y = P(lon, lat)
        return (x - min(xs)) * sx + PAD, (max(ys) - y) * sy + PAD
    return to_crop, sx / sy

def pin(d, x, y, label, font, side="r"):
    r = 13
    d.ellipse((x - r, y - r, x + r, y + r), fill=RED, outline=(255, 250, 240), width=4)
    tw = d.textlength(label, font=font)
    lx = x + r + 10 if side == "r" else x - r - 10 - tw; pad = 7
    d.rounded_rectangle((lx - pad, y - font.size * 0.62 - pad, lx + tw + pad, y + font.size * 0.5 + pad),
                        radius=5, fill=(250, 246, 236), outline=FRAME, width=1)
    d.text((lx, y), label, font=font, fill=INK, anchor="lm")

# ---------------- lithology ----------------
PERIOD = {"quaternary": (232, 220, 168), "neogene": (222, 196, 120), "tertiary": (218, 186, 112), "paleogene": (212, 170, 100),
          "cretaceous": (194, 192, 141), "jurassic": (179, 195, 189), "triassic": (200, 160, 168), "permian": (203, 166, 152),
          "pennsylvanian": (197, 164, 123), "carboniferous": (180, 170, 140), "mississippian": (160, 178, 160),
          "devonian": (205, 178, 132), "silurian": (176, 200, 186), "ordovician": (150, 182, 168), "cambrian": (172, 186, 140),
          "precambrian": (160, 137, 131), "proterozoic": (160, 137, 131), "archean": (150, 120, 128)}
KIND_SHIFT = {"sand": 0.94, "gravel": 0.95, "shale": 1.0, "mud": 1.02, "lime": 1.05, "granite": 1.0, "volcanic": 0.88,
              "meta": 0.93, "coal": 0.85, "salt": 1.08, "glacial": 1.04}
def layer_color(L):
    p = L.get("period", "").lower()
    keys = sorted(PERIOD, key=lambda k: -len(k))   # 'precambrian' before 'cambrian'
    base = next((PERIOD[k] for k in keys if k in p), (190, 180, 150))
    f = KIND_SHIFT.get(L.get("kind"), 1.0)
    return tuple(max(0, min(255, int(c * f))) for c in base)

def pattern(d, box, kind, col):
    x0, y0, x1, y1 = [int(v) for v in box]; dark = tuple(int(c * 0.62) for c in col)
    if kind in ("sand",):
        for yy in range(y0 + 6, y1 - 2, 11):
            off = 0 if (yy // 11) % 2 else 6
            for xx in range(x0 + 4 + off, x1 - 2, 12): d.ellipse((xx - 1.6, yy - 1.6, xx + 1.6, yy + 1.6), fill=dark)
    elif kind == "shale":
        for yy in range(y0 + 8, y1 - 2, 12):
            off = 0 if (yy // 12) % 2 else 10
            for xx in range(x0 + 4 + off, x1 - 12, 22): d.line((xx, yy, xx + 11, yy), fill=dark, width=2)
    elif kind == "mud":
        for yy in range(y0 + 8, y1 - 2, 14):
            d.line((x0 + 4, yy, x1 - 4, yy), fill=dark, width=1)
            off = 0 if (yy // 14) % 2 else 9
            for xx in range(x0 + 6 + off, x1 - 6, 18): d.ellipse((xx - 1.5, yy + 5, xx + 1.5, yy + 8), fill=dark)
    elif kind == "gravel":
        for yy in range(y0 + 8, y1 - 4, 15):
            off = 0 if (yy // 15) % 2 else 9
            for xx in range(x0 + 8 + off, x1 - 8, 18): d.ellipse((xx - 4, yy - 3, xx + 4, yy + 3), outline=dark, width=2)
    elif kind == "glacial":
        for q, yy in enumerate(range(y0 + 8, y1 - 4, 13)):
            for xx in range(x0 + 6 + (q * 7) % 15, x1 - 6, 16):
                r = 2 + (xx * 7 + yy * 3) % 4; d.ellipse((xx - r, yy - r * 0.7, xx + r, yy + r * 0.7), outline=dark, width=1)
    elif kind == "granite":
        for yy in range(y0 + 10, y1 - 4, 18):
            off = 0 if (yy // 18) % 2 else 11
            for xx in range(x0 + 10 + off, x1 - 8, 22):
                d.line((xx - 5, yy, xx + 5, yy), fill=dark, width=2); d.line((xx, yy - 5, xx, yy + 5), fill=dark, width=2)
    elif kind == "lime":
        for i, yy in enumerate(range(y0, y1, 14)):
            d.line((x0, yy, x1, yy), fill=dark, width=1)
            off = 0 if i % 2 else 14
            for xx in range(x0 + off, x1, 28): d.line((xx, yy, xx, min(y1, yy + 14)), fill=dark, width=1)
    elif kind == "volcanic":
        for yy in range(y0 + 8, y1 - 6, 16):
            off = 0 if (yy // 16) % 2 else 10
            for xx in range(x0 + 8 + off, x1 - 8, 20): d.line((xx - 5, yy - 4, xx, yy + 4, xx + 5, yy - 4), fill=dark, width=2)
    elif kind == "meta":
        for yy in range(y0 + 8, y1 - 4, 12):
            pts = [(xx, yy + 3 * math.sin(xx / 6.0)) for xx in range(x0 + 3, x1 - 2, 3)]
            d.line(pts, fill=dark, width=2)
    elif kind == "coal":
        for yy in range(y0 + 10, y1 - 4, 20): d.rectangle((x0 + 2, yy, x1 - 2, yy + 5), fill=(50, 45, 40))
    elif kind == "salt":
        for yy in range(y0 + 10, y1 - 6, 18):
            for xx in range(x0 + 10, x1 - 8, 20):
                d.line((xx - 5, yy - 5, xx + 5, yy + 5), fill=dark, width=1); d.line((xx - 5, yy + 5, xx + 5, yy - 5), fill=dark, width=1)

def core(img, layers, x, y, w, h, cur=None):
    d = ImageDraw.Draw(img)
    hs = [1.6 if i == 0 else (1.4 if i == len(layers) - 1 else 1.0) for i in range(len(layers))]
    tot = sum(hs); yy = y; boxes = []; prev = None
    for i, L in enumerate(layers):
        hh = h * hs[i] / tot; col = layer_color(L)
        if prev is not None and sum(abs(a - b) for a, b in zip(col, prev)) < 30:
            col = tuple(int(c * 0.88) for c in col)
        prev = col
        L["_col"] = col
        if cur is not None and i != cur: col = tuple(int(c * 0.35 + b * 0.65) for c, b in zip(col, BG))
        d.rectangle((x, yy, x + w, yy + hh), fill=col); pattern(d, (x, yy, x + w, yy + hh), L.get("kind"), col)
        boxes.append((yy, yy + hh)); yy += hh
    for (a, b) in boxes[1:]: d.line((x, a, x + w, a), fill=FRAME, width=1)
    d.rectangle((x, y, x + w, y + h), outline=FRAME, width=3)
    d.line((x - 30, y - 2, x + w + 30, y - 2), fill=INK, width=4)
    return boxes

def etsy_slide(st, n, N, holiday):
    p = f"{ALL}/{st}_ig_5_etsy{'_holiday' if holiday else ''}.jpg"
    im = Image.open(p).convert("RGB"); d = ImageDraw.Draw(im)
    bg = im.getpixel((60, 1300))
    d.rectangle((300, 1266, 780, 1322), fill=bg)
    ctext(d, 1278, f"{n} / {N}", F("i", 30), GREY)
    return im

# ---------------- Rock Layers ----------------
def layers_carousel(st):
    data = json.load(open(f"{D}/data/layers/{st}.json"))
    Ls = data["layers"]; nL = len(Ls); N = nL + 2
    smap = state_map(st); to_crop, ratio = albers(st)
    slides = []
    # cover
    img = canvas(); d = ImageDraw.Draw(img)
    title_block(d, 60, NAMES[st].upper(), data["cover_sub"], tsize=118, subsize=40)
    cx, cy, cw, ch = 140, 380, 150, 720
    ctext(d, cy - 50, "SURFACE", F("c", 26), GREY, x=cx + cw // 2, spacing=2)
    boxes = core(img, Ls, cx, cy, cw, ch)
    m = fit(smap, 400, 470)
    mx0 = W - 60 - m.width
    for L, (a, b) in zip(Ls, boxes):
        nm = L["name"].title().replace("'S", "'s")
        f = fitfont(d, nm, "b", 30, mx0 - (cx + cw + 24) - 20)
        d.text((cx + cw + 24, (a + b) / 2), nm, font=f, fill=INK, anchor="lm")
        d.text((cx - 16, (a + b) / 2), L["short"], font=F("i", 24), fill=GREY, anchor="rm")
    ctext(d, cy + ch + 20, "Not to scale", F("i", 22), GREY, x=cx + cw // 2)
    framed(img, (mx0, 380, mx0 + m.width, 380 + m.height), m)
    ctext(d, 380 + m.height + 26, "The map shows the top layer.", F("i", 27), GREY, x=mx0 + m.width // 2)
    ctext(d, 380 + m.height + 62, "Swipe to drill down.", F("bi", 30), INK, x=mx0 + m.width // 2)
    footer(d, 1, N); slides.append(img)
    # layer slides
    for i, L in enumerate(Ls):
        img = canvas(); d = ImageDraw.Draw(img)
        top = f"LAYER {i + 1} OF {nL}   ·   {L['age'].upper()}"
        ctext(d, 52, top, fitfont(d, top, "c", 28, W - 80, spacing=2), RED, spacing=2)
        f = fitfont(d, L["name"], "b", 86, W - 100); ctext(d, 100, L["name"], f)
        bot = d.textbbox((W // 2, 100), L["name"], font=f, anchor="ma")[3]
        rule(d, bot + 34); hf = fitfont(d, L["hook"], "i", 44, W - 100); ctext(d, bot + 54, L["hook"], hf, GREY)
        cx, cy, cw, ch = 70, 340, 120, 800
        ctext(d, cy - 42, "SURFACE", F("c", 22), GREY, x=cx + cw // 2, spacing=2)
        boxes = core(img, Ls, cx, cy, cw, ch, cur=i)
        a, b = boxes[i]; mid = (a + b) / 2
        d.rectangle((cx - 4, a - 2, cx + cw + 4, b + 2), outline=RED, width=5)
        d.polygon([(cx + cw + 14, mid), (cx + cw + 34, mid - 14), (cx + cw + 34, mid + 14)], fill=RED)
        rx = 250; rw = W - rx - 50
        # text sizing first, so the map gets the rest of the room
        for fs in (31, 29, 27, 25):
            tf, bf = F("r", fs), F("i", fs)
            th = para(d, 0, 0, L["what"], tf, rw, draw=False) + 14 + para(d, 0, 0, L["bonus"], bf, rw, draw=False)
            maxh = 1200 - 340 - 34 - th
            if maxh >= 330: break
        m = fit(smap, rw, min(maxh, 560))
        my = 345; mx = rx + (rw - m.width) // 2
        framed(img, (mx, my, mx + m.width, my + m.height), m)
        sc = m.width / smap.width
        pf = F("b", 25)
        for p in L["pins"]:
            lab, lon, lat = p[0], p[1], p[2]
            px, py = to_crop(lon, lat); X = mx + px * sc; Y = my + py * sc
            if not (0 <= px < smap.width and 0 <= py < smap.height):
                WARN.append(f"{st} L{i+1} pin {lab} OUTSIDE map ({px:.0f},{py:.0f})")
            else:
                c = smap.getpixel((int(px), int(py))); mx_, mn_ = max(c), min(c)
                if (mx_ - mn_) / max(mx_, 1) < 0.15 and (c[0] - c[2]) / max(c[0], 1) >= 0.05:
                    WARN.append(f"{st} L{i+1} pin {lab} maybe off-state")
            tw = d.textlength(lab, font=pf)
            side = "r" if X + 30 + tw < mx + m.width + 40 else "l"
            pin(d, X, Y, lab, pf, side=side)
        d.text((mx, my - 30), "WHERE TO SEE IT", font=F("c", 22), fill=GREY)
        ty = my + m.height + 34
        ty = para(d, rx, ty, L["what"], tf, rw) + 14
        endy = para(d, rx, ty, L["bonus"], bf, rw, fill=RED)
        if endy > 1210: WARN.append(f"{st} L{i+1} text overflow {endy}")
        footer(d, i + 2, N); slides.append(img)
    names = []
    for k, s in enumerate(slides, 1):
        fn = f"{st}_rl_{k}.jpg"; s.save(f"{OUT}/{fn}", quality=90); names.append(fn)
    last = f"{st}_rl_{N}.jpg"; etsy_slide(st, N, N, False).save(f"{OUT}/{last}", quality=90); names.append(last)
    if st not in NONSHOP:
        etsy_slide(st, N, N, True).save(f"{OUT}/{st}_rl_{N}_holiday.jpg", quality=90)
    return names, ratio

# ---------------- Face-off ----------------
def faceoff_carousel(pair):
    R = json.load(open(f"{D}/data/faceoff/{pair}.json"))
    A, B = R["a"], R["b"]; an, bn = NAMES[A], NAMES[B]
    ma, mb = state_map(A), state_map(B); N = 8
    slides = []
    img = canvas(); d = ImageDraw.Draw(img)
    fa = fitfont(d, an.upper(), "b", 104, W - 100); fb = fitfont(d, bn.upper(), "b", 104, W - 100)
    fs = min(fa.size, fb.size)
    ctext(d, 60, an.upper(), F("b", fs)); ctext(d, 60 + fs + 16, "vs", F("i", 60), RED); ctext(d, 60 + fs + 96, bn.upper(), F("b", fs))
    ry = d.textbbox((W // 2, 60 + fs + 96), bn.upper(), font=F("b", fs), anchor="ma")[3] + 30; rule(d, ry)
    ctext(d, ry + 20, R["tagline"], fitfont(d, R["tagline"], "i", 38, W - 100), GREY)
    top = ry + 100; bottom = 1100
    a = fit(ma, 450, bottom - top - 60); b = fit(mb, 450, bottom - top - 60)
    ay = top + (bottom - top - 60 - a.height) // 2; by = top + (bottom - top - 60 - b.height) // 2
    ax = 60 + (450 - a.width) // 2; bx = W - 60 - 450 + (450 - b.width) // 2
    framed(img, (ax, ay, ax + a.width, ay + a.height), a); framed(img, (bx, by, bx + b.width, by + b.height), b)
    ctext(d, ay + a.height + 20, an, F("i", 32), GREY, x=ax + a.width // 2)
    ctext(d, by + b.height + 20, bn, F("i", 32), GREY, x=bx + b.width // 2)
    ctext(d, 1140, "5 rounds. Keep score. Vote at the end.", F("b", 36))
    footer(d, 1, N); slides.append(img)
    sa = sb = 0
    colx = [W // 4 + 10, 3 * W // 4 - 10]
    for k, r in enumerate(R["rounds"], 1):
        if r["win"] == "a": sa += 1
        else: sb += 1
        img = canvas(); d = ImageDraw.Draw(img)
        ctext(d, 52, f"ROUND {k}", F("c", 30), RED, spacing=3)
        title_block(d, 96, r["t"], None, tsize=84)
        thumbs = [fit(ma, 300, 210), fit(mb, 300, 210)]
        for j, (side, name, th) in enumerate(zip("ab", [an.upper(), bn.upper()], thumbs)):
            x = colx[j]; win = r["win"] == side; lbl, val, txt = r[side]
            th2 = th if win else ImageEnhance.Color(th).enhance(0.25)
            ty = 250 + (210 - th.height) // 2
            framed(img, (x - th.width // 2, ty, x - th.width // 2 + th.width, ty + th.height), th2)
            ctext(d, 492, name, fitfont(d, name, "b", 40, 470, spacing=2), INK if win else GREY, x=x, spacing=2)
            f = fitfont(d, txt, "b", 96 if len(txt) < 6 else 70, 470)
            ctext(d, 560, txt, f, RED if win else GREY, x=x)
            ctext(d, 680, lbl, fitfont(d, lbl, "i", 32, 470), GREY, x=x)
            if win:
                d.rounded_rectangle((x - 70, 735, x + 70, 785), radius=25, fill=RED)
                ctext(d, 742, "POINT", F("b", 30), (250, 244, 232), x=x, spacing=2)
        d.line((W // 2, 260, W // 2, 790), fill=(205, 196, 178), width=2)
        va, vb = float(r["a"][1]), float(r["b"][1]); vy0, vy1 = 830, 1090
        cols = [RED if r["win"] == "a" else LOSE, RED if r["win"] == "b" else LOSE]
        if r["kind"] == "peak":
            mxv = max(va, vb, 1)
            for j, v in enumerate([va, vb]):
                x = colx[j]; hgt = max(6, (vy1 - vy0) * v / mxv)
                d.polygon([(x - 190, vy1), (x, vy1 - hgt), (x + 190, vy1)], fill=cols[j])
                if hgt > 60:
                    d.polygon([(x - 40, vy1 - hgt * 0.79), (x, vy1 - hgt), (x + 40, vy1 - hgt * 0.79), (x + 12, vy1 - hgt * 0.75),
                               (x - 8, vy1 - hgt * 0.8)], fill=(250, 246, 236))
            d.line((60, vy1, W - 60, vy1), fill=FRAME, width=3)
            ctext(d, vy1 + 10, "drawn to the same scale", F("i", 24), GREY)
        elif r["kind"] == "dots" and max(va, vb) <= 8:
            for j, v in enumerate([va, vb]):
                x = colx[j]; n = int(v); sp = min(78, 420 / max(n, 1))
                if n == 0: ctext(d, 960, "none", F("i", 36), GREY, x=x)
                for q in range(n):
                    cx = x - (n - 1) * sp / 2 + q * sp
                    d.polygon([(cx - 28, 1010), (cx, 950), (cx + 28, 1010)], fill=cols[j]); d.rectangle((cx - 5, 1010, cx + 5, 1030), fill=FRAME)
        else:
            mxv = max(va, vb, 1e-9)
            for j, v in enumerate([va, vb]):
                y = vy0 + 40 + j * 110; ww = (W - 300) * v / mxv
                d.text((80, y + 30), [A, B][j], font=F("b", 40), fill=INK, anchor="lm")
                if ww > 0: d.rectangle((170, y, 170 + ww, y + 60), fill=cols[j])
                else: d.text((180, y + 30), "zero", font=F("i", 32), fill=GREY, anchor="lm")
        ctext(d, 1150, f"{an.upper()}  {sa}   –   {sb}  {bn.upper()}", fitfont(d, f"{an.upper()}  {sa}   –   {sb}  {bn.upper()}", "b", 38, W - 80), INK)
        footer(d, k + 1, N); slides.append(img)
    # bonus vote
    bo = R["bonus"]; img = canvas(); d = ImageDraw.Draw(img)
    ctext(d, 52, "BONUS ROUND", F("c", 30), RED, spacing=3)
    title_block(d, 96, bo["title"], bo.get("sub", ""), tsize=84)
    for j, (name, side) in enumerate([(an.upper(), bo["a"]), (bn.upper(), bo["b"])]):
        x = colx[j]
        ctext(d, 340, name, fitfont(d, name, "b", 40, 470, spacing=2), INK, x=x, spacing=2)
        ctext(d, 405, side[0], fitfont(d, side[0], "b", 64, 480), RED, x=x)
        for q, ln in enumerate(side[1:3]): ctext(d, 500 + q * 44, ln, fitfont(d, ln, "i", 34, 480), GREY, x=x)
    d.line((W // 2, 330, W // 2, 600), fill=(205, 196, 178), width=2)
    for q, ln in enumerate(bo.get("mid", [])[:3]):
        if ln: ctext(d, 680 + q * 50, ln, fitfont(d, ln, "r", 40, W - 120))
    ctext(d, 880, bo["q"], fitfont(d, bo["q"], "b", 56, W - 100))
    ctext(d, 960, bo["cta"], fitfont(d, bo["cta"], "i", 44, W - 100), RED)
    ctext(d, 1150, f"{an.upper()}  {sa}   –   {sb}  {bn.upper()}", fitfont(d, f"{an.upper()}  {sa}   –   {sb}  {bn.upper()}", "b", 38, W - 80), INK)
    footer(d, 7, N); slides.append(img)
    # final
    def final(holiday):
        img = canvas(); d = ImageDraw.Draw(img)
        ctext(d, 52, "FINAL SCORE", F("c", 30), RED, spacing=3)
        t = f"{an.upper()} {sa} – {sb} {bn.upper()}"
        f = fitfont(d, t, "b", 74, W - 80); ctext(d, 100, t, f)
        bot = d.textbbox((W // 2, 100), t, font=f, anchor="ma")[3]; rule(d, bot + 30)
        ctext(d, bot + 50, "Do you agree? Settle it in the comments:", F("i", 38), GREY)
        ctext(d, bot + 106, f"“{A}” or “{B}”", F("b", 48), RED)
        top = bot + 190
        pics = []
        for st, mp in ((A, ma), (B, mb)):
            if st in NONSHOP: pics.append(fit(mp, 470, 330))
            else: pics.append(fit(Image.open(f"{ALL}/{st}_ig_5_etsy.jpg").convert("RGB").crop((50, 60, 1030, 700)), 470, 330))
        hmax = max(p.height for p in pics)
        for j, p in enumerate(pics):
            x = 55 + (470 - p.width) // 2 if j == 0 else W - 55 - 470 + (470 - p.width) // 2
            y = top + (hmax - p.height) // 2
            framed(img, (x, y, x + p.width, y + p.height), p)
            ctext(d, top + hmax + 16, [an, bn][j], F("i", 30), GREY, x=x + p.width // 2)
        y = top + hmax + 90
        shop = [s for s in (A, B) if s not in NONSHOP]; non = [s for s in (A, B) if s in NONSHOP]
        if len(shop) == 2:
            ctext(d, y, "CAN'T PICK? HANG BOTH.", F("b", 58)); y += 80
            ctext(d, y, "VennMaps on Etsy", F("i", 48), RED); y += 66
            if holiday:
                ctext(d, y, "Holiday sale: 20% off  ·  Order by Dec 10 for Christmas", fitfont(d, "x" * 52, "b", 32, W - 100), GREEN); y += 50
            ctext(d, y, "12x18 & 24x36 prints  ·  Free US shipping", F("r", 34)); y += 52
            ctext(d, y, "Link in bio  ·  or search “VennMaps” on Etsy", F("i", 32), GREY)
        elif len(shop) == 1:
            s_, n_ = NAMES[shop[0]], NAMES[non[0]]
            ctext(d, y, f"{s_.upper()} IS ON ETSY", fitfont(d, f"{s_.upper()} IS ON ETSY", "b", 58, W - 100)); y += 80
            ctext(d, y, "VennMaps on Etsy  ·  link in bio", F("i", 44), RED); y += 66
            if holiday:
                ctext(d, y, "Holiday sale: 20% off  ·  Order by Dec 10 for Christmas", fitfont(d, "x" * 52, "b", 32, W - 100), GREEN); y += 50
            ctext(d, y, f"Want {n_} too? Comment “{n_}” below", fitfont(d, f"Want {n_} too? Comment “{n_}” below", "r", 36, W - 100)); y += 52
            ctext(d, y, "and we'll add it to the shop", F("i", 32), GREY)
        else:
            ctext(d, y, "WANT ONE ON YOUR WALL?", F("b", 58)); y += 80
            ctext(d, y, f"Comment “{an}” or “{bn}”", fitfont(d, f"Comment “{an}” or “{bn}”", "i", 44, W - 100), RED); y += 66
            ctext(d, y, "and we'll add it to the shop", F("r", 34)); y += 52
            ctext(d, y, "31 states already in print: VennMaps on Etsy", F("i", 32), GREY)
        footer(d, N, N); return img
    slides.append(final(False))
    names = []
    for k, s in enumerate(slides, 1):
        fn = f"{pair}_fo_{k}.jpg"; s.save(f"{OUT}/{fn}", quality=90); names.append(fn)
    if A not in NONSHOP or B not in NONSHOP:
        final(True).save(f"{OUT}/{pair}_fo_{N}_holiday.jpg", quality=90)
    return names, (sa, sb)

if __name__ == "__main__":
    what = sys.argv[1]; args = sys.argv[2:]
    if what == "layers":
        for st in args or sorted(f[:-5] for f in os.listdir(f"{D}/data/layers")):
            names, ratio = layers_carousel(st); print(st, len(names), "slides", f"proj ratio {ratio:.2f}")
        print("\n".join(WARN))
    elif what == "faceoff":
        for p in args or sorted(f[:-5] for f in os.listdir(f"{D}/data/faceoff")):
            names, sc = faceoff_carousel(p); print(p, sc)
