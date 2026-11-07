import sys, os, numpy as np
sys.path.insert(0, r"D:\States Project\social\instagram\carousel")
import make_carousel as mc
from PIL import Image, ImageDraw, ImageFilter
Image.MAX_IMAGE_PIXELS = None
WK = r"D:\States Project\social\tiktok\08_historical\_work" + "\\"
def state_mask(sm):
    a = np.asarray(sm).astype(int); R, G, B = a[..., 0], a[..., 1], a[..., 2]
    pink = (R - G > 40) & (R - B > 45)
    m = Image.fromarray((pink * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    m = m.point(lambda v: 255 if v > 0 else 0)
    h, w = a.shape[:2]
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if m.getpixel(seed) == 0: ImageDraw.floodfill(m, seed, 128)
    v = np.asarray(m)
    return v == 0
def state_detail(path, aspect):
    big = Image.open(path).convert("RGB"); W0, H0 = big.size
    sm = big.resize((900, int(900 * H0 / W0)), Image.BILINEAR); h, w = sm.size[1], sm.size[0]
    inside = state_mask(sm).astype(float)
    ink = (np.asarray(sm).astype(float).mean(2) < 120).astype(float)
    ww = int(w * 0.34); wh = int(ww / aspect)
    ii = np.pad(inside, ((1, 0), (1, 0))).cumsum(0).cumsum(1); ik = np.pad(ink, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    def S(I, x, y): return I[y + wh, x + ww] - I[y, x + ww] - I[y + wh, x] + I[y, x]
    ys, xs = np.nonzero(inside); cy, cx = ys.mean(), xs.mean()
    best = None; n = ww * wh
    for y in range(0, h - wh, 3):
        for x in range(0, w - ww, 3):
            fr = S(ii, x, y) / n
            if fr < 0.6: continue
            dn = S(ik, x, y) / n
            dist = np.hypot(x + ww / 2 - cx, y + wh / 2 - cy) / w
            sc = fr ** 8 * (dn + 0.02) * (1 - 0.6 * dist)
            if best is None or sc > best[0]: best = (sc, x, y, fr)
    if best is None:  # very small state: shrink window
        return None, inside.mean()
    _, x, y, fr = best; k = W0 / w
    return big.crop((int(x * k), int(y * k), int((x + ww) * k), int((y + wh) * k))), fr
if __name__ == "__main__":
    sts = sys.argv[1:] or sorted(mc.ALL48); tw, th = 480, 142
    rows = (len(sts) + 3) // 4
    sheet = Image.new("RGB", (tw * 4, (th + 20) * rows), (255, 255, 255)); d = ImageDraw.Draw(sheet)
    od = r"D:\States Project\social\instagram\carousel\upclose"; os.makedirs(od, exist_ok=True)
    log = []
    for i, st in enumerate(sts):
        c, fr = state_detail(mc.find(st, "vintage"), 980 / 290)
        x = (i % 4) * tw; y = (i // 4) * (th + 20)
        if c is not None:
            c.save(os.path.join(od, st + "_vintage_upclose.jpg"), quality=92)
            sheet.paste(mc.cover_crop(c, tw, th), (x, y + 20))
        d.text((x + 4, y + 3), "%s %.2f" % (st, fr), fill=(200, 0, 0)); log.append(st)
        open(WK + "upclose_log.txt", "w").write(" ".join(log))
    sheet.save(WK + "upclose_new.jpg", quality=85)
    open(WK + "upclose_log.txt", "a").write(" DONE")
