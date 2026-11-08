"""Append Rock Layers (Tue/Thu) + Face-off (Sat) carousels, 9:00 AM Denver, to igc/schedule.json."""
import json, os, re, sys, datetime as dt
from zoneinfo import ZoneInfo
D = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/claude/vennmaps-pins"
sys.path.insert(0, D)
import gen
den = ZoneInfo("America/Denver")

sched = json.load(open(f"{REPO}/igc/schedule.json"))
base = [i for i in sched if i.get("series") not in ("Rock Layers", "Face-off")]
order = [i["state"] for i in base]                       # existing carousel order (shop first, then alternating)
credit = {i["state"]: re.search(r"Map data: ([^\n]+)", i["caption"]).group(1) for i in base}
tag = {i["state"]: re.search(r"\n#(\w+) ", i["caption"]).group(1) for i in base}
HOLI = "\U0001F381 Holiday sale: 20% off every map through Dec 13. Order by Dec 10 for Christmas."
ETSY = "Prints in 12x18 and 24x36 on Etsy: VennMaps (link in bio)."

def holiday(d): return dt.date(2026, 11, 20) <= d <= dt.date(2026, 12, 10)

def slots(start, weekdays, n):
    d = start; out = []
    while len(out) < n:
        if d.weekday() in weekdays: out.append(d)
        d += dt.timedelta(days=1)
    return out

def stamp(d):
    loc = dt.datetime(d.year, d.month, d.day, 9, 0, tzinfo=den)
    return loc.strftime("%Y-%m-%d %H:%M"), loc.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

new = []
# Rock Layers: Tue + Thu
for d, st in zip(slots(dt.date(2026, 11, 10), {1, 3}, 48), order):
    L = json.load(open(f"{D}/data/layers/{st}.json")); N = len(L["layers"]) + 2
    shop = st not in gen.NONSHOP; hol = shop and holiday(d)
    imgs = [f"{st}_rl_{k}.jpg" for k in range(1, N)] + [f"{st}_rl_{N}{'_holiday' if hol else ''}.jpg"]
    span = L["cover_sub"].replace("Dig down through ", "")
    cap = (f"{L['caption_hook']} Swipe to dig down through {gen.NAMES[st]}, layer by layer, through {span} of rock. "
           f"Which layer have you stood on? \U0001F447\n\n")
    if hol: cap += HOLI + "\n\n"
    cap += ETSY if shop else f"Want {gen.NAMES[st]} in the shop? Comment below. 31 other states are already on Etsy: VennMaps (link in bio)."
    cap += f"\n\nMap data: {credit[st]}\n\n#{tag[st]} #geology #rocks #wallart #vennmaps"
    lw, lu = stamp(d)
    new.append(dict(key=f"{d}_0900_{st}_layers", state=st, series="Rock Layers", shop=shop, when_local=lw, when_utc=lu,
                    holiday=hol, images=imgs, caption=cap))

# Face-offs: Saturdays; CO-UT first, then pairs with two shop states, ordered by their earliest state in `order`
pairs = sorted(f[:-5] for f in os.listdir(f"{D}/data/faceoff"))
def prio(p):
    a, b = p.split("-"); nshop = (a not in gen.NONSHOP) + (b not in gen.NONSHOP)
    return (p != "CO-UT", -nshop if nshop == 2 else 0, min(order.index(a), order.index(b)))
pairs.sort(key=prio)
for d, p in zip(slots(dt.date(2026, 11, 14), {5}, 24), pairs):
    R = json.load(open(f"{D}/data/faceoff/{p}.json")); a, b = R["a"], R["b"]
    sa = sum(r["win"] == "a" for r in R["rounds"]); sb = 5 - sa
    an, bn = gen.NAMES[a], gen.NAMES[b]
    shops = [s for s in (a, b) if s not in gen.NONSHOP]; nons = [s for s in (a, b) if s in gen.NONSHOP]
    hol = bool(shops) and holiday(d)
    imgs = [f"{p}_fo_{k}.jpg" for k in range(1, 8)] + [f"{p}_fo_8{'_holiday' if hol else ''}.jpg"]
    cap = (f"{R['caption_hook']} Final score: {an} {sa}, {bn} {sb}. Do you agree? Comment {a} or {b} \U0001F447\n\n")
    if hol: cap += HOLI + "\n\n"
    if len(shops) == 2: cap += "Both are on Etsy as 12x18 and 24x36 prints: VennMaps (link in bio)."
    elif len(shops) == 1: cap += (f"{gen.NAMES[shops[0]]} is on Etsy as a 12x18 or 24x36 print: VennMaps (link in bio). "
                                  f"Want {gen.NAMES[nons[0]]} in the shop? Comment below.")
    else: cap += f"Want {an} or {bn} in the shop? Comment below. 31 other states are already on Etsy: VennMaps (link in bio)."
    cr = " · ".join(dict.fromkeys([x.strip() for x in (credit[a] + " · " + credit[b]).split("·")]))
    cap += f"\n\nMap data: {cr}\n\n#{tag[a]} #{tag[b]} #geology #maps #vennmaps"
    lw, lu = stamp(d)
    new.append(dict(key=f"{d}_0900_{p}_faceoff", state=p, series="Face-off", shop=bool(shops), when_local=lw, when_utc=lu,
                    holiday=hol, images=imgs, caption=cap))

# sanity: every image exists, <= 10 per post, caption <= 2200
for it in new:
    assert 2 <= len(it["images"]) <= 10, it["key"]
    for im in it["images"]: assert os.path.exists(f"{D}/out/c/{im}"), im
    assert len(it["caption"]) <= 2200 and it["caption"].count("#") <= 5, it["key"]
allk = [i["key"] for i in base + new]; assert len(allk) == len(set(allk))
out = sorted(base + new, key=lambda i: i["when_utc"])
json.dump(out, open(f"{REPO}/igc/schedule.json", "w"), indent=1, ensure_ascii=False)
json.dump(new, open(f"{D}/new_items.json", "w"), indent=1, ensure_ascii=False)
print(len(base), "existing +", len(new), "new =", len(out))
for it in new[:4] + new[48:50]: print(it["when_local"], it["key"], len(it["images"]), it["holiday"])
print(new[-1]["when_local"], new[47]["when_local"])
print(new[48]["caption"])
