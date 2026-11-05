# make_holiday_pins.py - holiday sale pins (Nov 20 - Dec 13 2026, 20% off, order by Dec 10)
#   image pins: pins\<ST>_<series>_holiday.jpg  (existing flat full-map pin with holiday top/bottom bands; no model scenes)
#   video pins: videos\<ST>_<series>_holiday.mp4 (720x1280 copies of the TikTok holiday videos, 12:00 posts)
#   CSV with FIXED publish dates: new_pins\holiday_pins.csv  (plan_weekly keeps these dates and gives them priority)
import os, json, csv, datetime as dt, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
P = r"D:\States Project\social\pinterest"; T = r"D:\States Project\social\tiktok"
sys.path.insert(0, os.path.join(T, "_scripts")); import viral_common as VC
FF = VC.FF; RAW = "https://raw.githubusercontent.com/vennmaps92/vennmaps-pins/main/"
LINK = json.load(open(os.path.join(P, "_check", "listing_links.json")))
PAPER = (246, 240, 224); INK = (40, 34, 28); RED = (166, 30, 36); GREEN = (30, 92, 56); GOLD = (196, 160, 70); CREAM = (255, 248, 236)
def f(sz, b=True): return ImageFont.truetype(VC.FB if b else VC.FR, sz)
SER = {"vintage": ("Vintage State Map", "Vintage State Maps", "vintage map"), "hydro": ("Watershed & River Map", "Watershed & River Maps", "river map"),
       "legend": ("Geology Map with Legend", "Geology Maps of US States", "geology map"), "full": ("Geology Map & Rock Column", "Geology Maps of US States", "geology map")}
SHOP = "TX CA FL NY PA OH IL GA NC MI NJ VA WA AZ TN MA IN MO MD WI CO MN SC AL KY OR UT NV NM MT WY".split()
rows = []
d0 = dt.datetime(2026, 11, 20)
for i, st in enumerate(SHOP):
    s = ["vintage", "hydro", "legend", "full"][i % 4]; n = VC.NAMES[st]
    im = Image.open(os.path.join(P, "pins", "%s_%s_C_full.jpg" % (st, s))).convert("RGB"); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1000, 270), fill=PAPER)
    d.rectangle((0, 0, 1000, 18), fill=RED); d.rectangle((0, 18, 1000, 34), fill=GREEN)
    d.text((500, 62), "THE PERFECT GIFT", font=f(40), fill=RED, anchor="mt")
    d.text((500, 112), n.upper(), font=f(92 if len(n) < 12 else 70), fill=INK, anchor="mt")
    d.text((500, 222), SER[s][0], font=f(40, False), fill=(85, 78, 70), anchor="mt")
    d.rectangle((0, 1270, 1000, 1500), fill=RED); d.rectangle((0, 1270, 1000, 1282), fill=GOLD)
    d.text((500, 1310), "HOLIDAY SALE  ·  20% OFF", font=f(58), fill=CREAM, anchor="mt")
    d.text((500, 1392), "Order by Dec 10 for Christmas  ·  Sale ends Dec 13", font=f(34, False), fill=CREAM, anchor="mt")
    d.text((500, 1446), "VENNMAPS on Etsy", font=f(30), fill=(250, 220, 150), anchor="mt")
    fn = "%s_%s_holiday.jpg" % (st, s); im.save(os.path.join(P, "pins", fn), quality=90)
    day = d0 + dt.timedelta(days=i % 24); t = day.replace(hour=21) if i < 24 else day.replace(hour=18, minute=30)
    rows.append({"Title": "%s %s | Christmas Gift Idea, 20%% Off" % (n, SER[s][0]), "Media URL": RAW + "pins/" + fn, "Pinterest board": SER[s][1], "Thumbnail": "",
                 "Description": "Holiday gift idea for anyone who loves %s: a %s print from VennMaps, made by a Denver geoscientist. 20%% off in our holiday sale through Dec 13; order by Dec 10 for Christmas. 12x18 and 24x36 archival prints." % (n, SER[s][2]),
                 "Link": LINK["%s|%s" % (st, s)], "Publish date": t.strftime("%Y-%m-%dT%H:%M:%S"),
                 "Keywords": "%s gift, christmas gift idea, %s, gift for map lovers, holiday sale" % (n, SER[s][2])})
plan = json.load(open(os.path.join(T, "07_holiday", "holiday_plan.json")))
VS = {"dig": ("Geology Video: Dig a Hole", "Geology Maps of US States", "full"), "river": ("Every River Video", "Watershed & River Maps", "hydro"),
      "tvn": ("Then vs Now Video", "Vintage State Maps", "vintage"), "load": ("Map Reveal Video", "Geology Maps of US States", "full"),
      "close": ("Ancient Sea Floor Video", "Geology Maps of US States", "legend")}
for p in [p for p in plan if p["time"].startswith("12")]:
    st, s = p["state"], p["series"]; n = VC.NAMES[st]; fn = "%s_%s_holiday.mp4" % (st, s)
    src = os.path.join(T, "07_holiday", p["file"]); out = os.path.join(P, "videos", fn)
    if not os.path.exists(out):
        subprocess.run([FF, "-y", "-v", "error", "-i", src, "-vf", "scale=720:1280", "-c:v", "libx264", "-preset", "slow", "-crf", "26",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k", out], check=True)
    t = dt.datetime.fromisoformat(p["date"]).replace(hour=17, minute=30)
    rows.append({"Title": "%s %s | Christmas Gift Idea" % (n, VS[s][0]), "Media URL": RAW + "videos/" + fn, "Pinterest board": VS[s][1], "Thumbnail": "3",
                 "Description": "%s %s Holiday sale: 20%% off every map through Dec 13; order by Dec 10 for Christmas. VennMaps state map prints, made by a Denver geoscientist." % (p["opener"] + ("." if not p["opener"].endswith(("?", "!", ".")) else ""), p["caption"].split("🎁 ")[1].split(" 20%")[0]),
                 "Link": LINK["%s|%s" % (st, VS[s][2])], "Publish date": t.strftime("%Y-%m-%dT%H:%M:%S"),
                 "Keywords": "%s gift, christmas gift idea, map video, holiday sale" % n})
assert len({r["Title"] for r in rows}) == len(rows), "duplicate titles"
os.makedirs(os.path.join(P, "new_pins"), exist_ok=True)
with open(os.path.join(P, "new_pins", "holiday_pins.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("holiday pins", len(rows))
