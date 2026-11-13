"""Append the 4 new carousel series (What's under your city? / State extremes / Drive through time / Where the rain goes)
to igc/schedule.json: one post a day at 5:00 PM Denver from Nov 16 2026, rotating series, 192 posts.
Slide lists and facts come from the PC's new_series/_meta/*.json (copied to igc/series/data/ns_meta/)."""
import json, os, re, sys, datetime as dt
from zoneinfo import ZoneInfo
D = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(D))
sys.path.insert(0, D)
import gen
den = ZoneInfo("America/Denver")
META = f"{D}/data/ns_meta"
IMGDIR = sys.argv[1] if len(sys.argv) > 1 else f"{D}/out/ns"     # local copy of the slides, for the existence check

sched = json.load(open(f"{REPO}/igc/schedule.json"))
old = [i for i in sched if i.get("series") not in ("Under your city", "State extremes", "Drive through time", "Where the rain goes")]
base = [i for i in old if not i.get("series")]
order = [i["state"] for i in base]
credit = {i["state"]: re.search(r"Map data: ([^\n]+)", i["caption"]).group(1) for i in base}
tag = {i["state"]: re.search(r"\n#(\w+) ", i["caption"]).group(1) for i in base}
HOLI = "\U0001F381 Holiday sale: 20% off every map through Dec 13. Order by Dec 10 for Christmas."
ETSY = "Prints in 12x18 and 24x36 on Etsy: VennMaps (link in bio)."
SER = [("under_city", "uc", "Under your city"), ("extremes", "ex", "State extremes"),
       ("drive_time", "dt", "Drive through time"), ("rain", "rg", "Where the rain goes")]

def holiday(d): return dt.date(2026, 11, 20) <= d <= dt.date(2026, 12, 10)

def listing(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]

def hook(code, st, m):
    nm = gen.NAMES[st]
    if code == "uc":
        c = [x["name"] for x in m["cities"]]
        return (f"What's under your city? Swipe to see the rock beneath {listing(c)}: what it is, how old it is "
                f"and how it got there. Don't see your town? Comment it below \U0001F447"), "#maps"
    if code == "ex":
        h, l = m["data"]["high"], m["data"]["low"]
        lowp = (f"the low point at sea level on the {l['sub'].replace('Atlantic Ocean and Gulf of Mexico', 'Atlantic and the Gulf')}"
                if l["value"] == "Sea level" else f"the low point ({l['sub']}) at {l['value'].lower()}")
        rocks = "the oldest and youngest rock" if m["data"].get("youngest") else "the oldest rock"
        return (f"{nm} at the extremes: {h['sub']} at {h['value']}, {lowp}, plus {rocks} in the state. "
                f"Which one have you stood on? \U0001F447"), "#maps"
    if code == "dt":
        n = len([f for f in m["files"] if "_holiday" not in f]) - 2
        if n == 1:
            return (f"Drive {m['route']} across {nm}: {m['miles']} miles, and almost all of it on one chapter of Earth history. "
                    f"Swipe to see which. Have you driven it? \U0001F447"), "#roadtrip"
        return (f"Drive {m['route']} across {nm} and you roll through {n} chapters of Earth history in "
                f"{m['miles']} miles. Swipe for the stops. Have you driven it? \U0001F447"), "#roadtrip"
    if code == "rg":
        s = m["slides"]
        DESTS = {"Atlantic Ocean", "Gulf of Mexico", "Gulf of California", "Pacific Ocean", "Hudson Bay", "Both coasts"}
        if all(x["title"] in DESTS or x["title"].startswith("Nowhere") for x in s):
            def nm_(t):
                if t.startswith("Nowhere"): return "nowhere (it never reaches the sea)"
                return "both coasts" if t == "Both coasts" else t if t == "Hudson Bay" else "the " + t
            parts = listing(f"{round(x['pct'])}% to {nm_(x['title'])}" for x in s)
            txt = f"Where does the rain that falls on {nm} end up? {parts}. Swipe to follow it. Did you guess right? \U0001F447"
        else:
            v = s[0]["via"]
            end = ("the Gulf of California" if "Gulf of California" in v else "the Gulf of Mexico" if "Gulf" in v else
                   "Hudson Bay" if "Hudson Bay" in v else "the Atlantic Ocean" if "Atlantic" in v else
                   "the Pacific Ocean" if "Pacific" in v else None)
            assert end, (st, v)
            txt = (f"Almost all the rain that falls on {nm} heads for {end}, but it takes different rivers to get there. "
                   f"Swipe to see which basin your town drains to. Did you know? \U0001F447")
        return txt, "#rivers"

def stamp(d):
    loc = dt.datetime(d.year, d.month, d.day, 17, 0, tzinfo=den)
    return loc.strftime("%Y-%m-%d %H:%M"), loc.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

new = []; day = dt.date(2026, 11, 16)
for i in range(4 * len(order)):
    ser, code, label = SER[i % 4]; st = order[(i // 4 + 12 * (i % 4)) % len(order)]
    m = json.load(open(f"{META}/{ser}_{st}.json"))
    shop = st not in gen.NONSHOP; hol = shop and holiday(day)
    files = [f for f in m["files"] if "_holiday" not in f]
    if hol: files[-1] = files[-1].replace(".jpg", "_holiday.jpg")
    txt, t2 = hook(code, st, m)
    cap = txt + "\n\n"
    if hol: cap += HOLI + "\n\n"
    cap += ETSY if shop else f"Want {gen.NAMES[st]} in the shop? Comment below. 31 other states are already on Etsy: VennMaps (link in bio)."
    cap += f"\n\nMap data: {credit[st]}\n\n#{tag[st]} #geology {t2} #wallart #vennmaps"
    lw, lu = stamp(day)
    new.append(dict(key=f"{day}_1700_{st}_{code}", state=st, series=label, shop=shop, when_local=lw, when_utc=lu,
                    holiday=hol, images=files, caption=cap))
    day += dt.timedelta(days=1)

for it in new:
    assert 2 <= len(it["images"]) <= 10, it["key"]
    for im in it["images"]: assert os.path.exists(os.path.join(IMGDIR, im)), im
    assert len(it["caption"]) <= 2200 and it["caption"].count("#") <= 5, it["key"]
allk = [i["key"] for i in old + new]; assert len(allk) == len(set(allk))
out = sorted(old + new, key=lambda i: i["when_utc"])
json.dump(out, open(f"{REPO}/igc/schedule.json", "w"), indent=1, ensure_ascii=False)
json.dump(new, open(f"{D}/ns_new_items.json", "w"), indent=1, ensure_ascii=False)
print(len(old), "existing +", len(new), "new =", len(out), "| last", new[-1]["when_local"])
for it in new[:5]: print(it["when_local"], it["key"], len(it["images"]), it["holiday"]); print(it["caption"]); print()
