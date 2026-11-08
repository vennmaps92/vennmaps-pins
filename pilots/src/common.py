import subprocess, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
CREAM = (246, 240, 224)
INK = (58, 50, 38)
RED = (162, 59, 42)
BLUE = (31, 86, 140)
D = "/home/claude/pilots/"


def font(name, size):
    return ImageFont.truetype(D + {"R": "BOD_R.TTF", "B": "BOD_B.TTF", "I": "BOD_I.TTF", "BI": "BOD_BI.TTF"}[name], size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ramp(t, a, b):
    """0 before a, 1 after b, smooth in between."""
    if b <= a:
        return 1.0 if t >= a else 0.0
    return ease((t - a) / (b - a))


def text_center(img, y, txt, f, fill=INK, alpha=1.0, letter=0, shadow=False):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if letter:
        ws = [d.textlength(c, font=f) for c in txt]
        tw = sum(ws) + letter * (len(txt) - 1)
        x = (img.size[0] - tw) / 2
        for c, w in zip(txt, ws):
            d.text((x, y), c, font=f, fill=fill + (255,))
            x += w + letter
    else:
        tw = d.textlength(txt, font=f)
        if shadow:
            d.text(((img.size[0] - tw) / 2 + 2, y + 3), txt, font=f, fill=(0, 0, 0, 90))
        d.text(((img.size[0] - tw) / 2, y), txt, font=f, fill=fill + (255,))
    if alpha < 1:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer.putalpha(a)
    img.alpha_composite(layer)


def wrap(txt, f, maxw):
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    words, lines, cur = txt.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


class Writer:
    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                   "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                                   "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)

    def write(self, img):
        self.p.stdin.write(img.convert("RGB").tobytes())

    def close(self):
        self.p.stdin.close()
        assert self.p.wait() == 0


def mux(video, audio, out, audio_delay=0.0):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-filter_complex",
                    f"[1:a]adelay={int(audio_delay*1000)}|{int(audio_delay*1000)},apad[a]", "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)


def brand(img, alpha=1.0):
    text_center(img, 1800, "VennMaps", font("I", 40), INK, alpha)


def endcard(img, t, t0, product, line1, line2, line3):
    """Fade the product image + CTA in from t0."""
    a = ramp(t, t0, t0 + 0.5)
    if a <= 0:
        return
    veil = Image.new("RGBA", img.size, CREAM + (int(255 * a),))
    img.alpha_composite(veil)
    s = 0.94 + 0.06 * ease_out((t - t0) / 0.8)
    pw = int(920 * s)
    ph = int(product.size[1] * pw / product.size[0])
    p = product.resize((pw, ph), Image.LANCZOS).convert("RGBA")
    p.putalpha(int(255 * a))
    y = 300 + (1150 - ph) // 2
    img.alpha_composite(p, ((W - pw) // 2, y))
    text_center(img, 1500, line1, font("B", 64), INK, a)
    text_center(img, 1585, line2, font("B", 64), INK, a)
    text_center(img, 1690, line3, font("R", 40), RED, a)
