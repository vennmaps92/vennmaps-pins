import sys, math, subprocess
from PIL import Image
from common import *

Image.MAX_IMAGE_PIXELS = None
P = Image.open(D + "CO_hydro_blue_relief.jpg").convert("RGB")
PW, PH = P.size
P_half = P.resize((PW // 2, PH // 2), Image.LANCZOS)

T_REVEAL, T_CTA, T_END = 7.35, 9.1, 12.0
WIN = (40, 470, 1000)  # x, y, side


def window(t):
    u = ease(min(t / (T_REVEAL - 0.15), 1.0))
    side = 900 * (4000 / 900) ** u
    cx = 3450 + (3700 - 3450) * u
    cy = 2750 + (2650 - 2750) * u
    box = (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
    src = P if side < 2200 else P_half
    k = 1 if src is P else 0.5
    return src.resize((WIN[2], WIN[2]), Image.BILINEAR, box=tuple(v * k for v in box), reducing_gap=2.0)


def full():
    w = 1040
    h = int(PH * w / PW)
    return P.resize((w, h), Image.LANCZOS)


FULL = full()


def frame(t):
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    r = ramp(t, T_REVEAL - 0.1, T_REVEAL + 0.35)
    if r < 1:
        win = window(min(t, T_REVEAL)).convert("RGBA")
        img.alpha_composite(win, (WIN[0], WIN[1]))
        d = ImageDraw.Draw(img)
        d.rectangle([WIN[0] - 2, WIN[1] - 2, WIN[0] + WIN[2] + 1, WIN[1] + WIN[2] + 1], outline=INK, width=3)
    if r > 0:
        f = FULL.convert("RGBA")
        f.putalpha(int(255 * r))
        layer = Image.new("RGBA", (W, H), CREAM + (int(255 * r),))
        img.alpha_composite(layer)
        y = 470 + (1000 - FULL.size[1]) // 2 - int(60 * ramp(t, T_CTA, T_CTA + 0.6))
        img.alpha_composite(f, (20, y))
    # header
    a1 = 1 - ramp(t, T_REVEAL - 0.1, T_REVEAL + 0.2)
    text_center(img, 170, "GUESS THE STATE", font("B", 92), INK, a1 * ramp(t, 0.0, 0.4), letter=4)
    text_center(img, 300, "from its rivers alone", font("I", 56), INK, a1 * ramp(t, 0.5, 0.9))
    a2 = ramp(t, T_REVEAL, T_REVEAL + 0.3)
    text_center(img, 200, "IT'S COLORADO!", font("B", 104), RED, a2, letter=3)
    # bottom
    text_center(img, 1560, "Comment your guess below", font("I", 60), INK, ramp(t, 2.6, 3.0) * (1 - ramp(t, 4.2, 4.4)))
    for i, n in enumerate(["3", "2", "1"]):
        t0 = 4.35 + i * 1.0
        if t0 <= t < t0 + 1.0:
            k = (t - t0) / 1.0
            s = int(230 - 50 * ease_out(k))
            text_center(img, 1500 + (230 - s) // 2, n, font("B", s), RED, 1 - ramp(k, 0.75, 1.0))
    # CTA
    a3 = ramp(t, T_CTA, T_CTA + 0.5)
    text_center(img, 1310, "Every river in Colorado", font("B", 66), INK, a3)
    text_center(img, 1400, "VennMaps on Etsy", font("B", 66), INK, a3)
    text_center(img, 1510, "12x18 & 24x36 · Free US shipping", font("R", 42), RED, a3)
    brand(img)
    return img


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for t in map(float, sys.argv[1:]):
            frame(t).convert("RGB").save(f"/tmp/guess_{t}.jpg", quality=88)
        sys.exit()
    w = Writer("guess_v.mp4")
    n = int(T_END * FPS)
    for i in range(n):
        w.write(frame(i / FPS))
    w.close()
    # audio: line1+2, 3 s gap, reveal line
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", D + "CO_guess_jessie.mp3", "-filter_complex",
                    "[0:a]atrim=0:4.35,asetpts=PTS-STARTPTS[a];[0:a]atrim=4.50,asetpts=PTS-STARTPTS,adelay=3080|3080[b];[a][b]concat=n=2:v=0:a=1[o]",
                    "-map", "[o]", "guess_a.wav"], check=True)
    mux("guess_v.mp4", "guess_a.wav", "CO_guess_the_state.mp4")
