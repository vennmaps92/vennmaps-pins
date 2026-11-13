"""Re-plan every not-yet-queued Instagram carousel (Nov 12 2026, Alan approved):
  * 1 carousel a day (Instagram = 1 carousel + 2 reels; the 3 PM reels are TikTok/YouTube only)
  * time by the state's region: Eastern/Central states 9 AM Denver (10 AM on Sundays, a reel holds 9 AM),
    Mountain/Pacific states 6 PM Denver
  * Nov 20 - Dec 25: shop states only (holiday Etsy slide + sale line through Dec 10); non-shop after Christmas
  * the same state never twice within 3 days on Instagram carousels, and not on a day it already has a reel
  * every series keeps moving: the series furthest behind its share goes next
Items already handed to Blotato (in igc/posted.json) or dated before START are left exactly as they are.
Usage: python3 replan.py <c_files.txt> <ig_schedule.json>"""
import json, os, sys, datetime as dt
from zoneinfo import ZoneInfo
D = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(D))
sys.path.insert(0, D)
import gen
den = ZoneInfo("America/Denver")
START = dt.date(2026, 11, 14)
HOL0, HOL1, SHOPONLY_END = dt.date(2026, 11, 20), dt.date(2026, 12, 10), dt.date(2026, 12, 25)
HOLI = "\U0001F381 Holiday sale: 20% off every map through Dec 13. Order by Dec 10 for Christmas."
WEST = set("WA OR CA NV ID MT WY UT CO AZ NM".split())
CFILES = set(open(sys.argv[1]).read().split())
reels = json.load(open(sys.argv[2]))
reel_states = {}
for r in reels: reel_states.setdefault(r["when_local"][:10], set()).add(r["state"])

sched = json.load(open(f"{REPO}/igc/schedule.json")); posted = json.load(open(f"{REPO}/igc/posted.json"))
fixed = [i for i in sched if i["key"] in posted or i["when_local"][:10] < str(START)]
todo = [i for i in sched if i not in fixed]
print(len(fixed), "fixed,", len(todo), "to re-plan")

def states(i): return i["state"].split("-")
def shop(i): return any(s not in gen.NONSHOP for s in states(i))
def series(i): return i.get("series") or "3 ways"

order = {}                                   # keep each series' current order
for i in sorted(todo, key=lambda i: i["when_utc"]): order.setdefault(series(i), []).append(i)
total = {s: len(v) for s, v in order.items()}; done = {s: 0 for s in order}
last_seen = {}
for i in fixed:
    for s in states(i): last_seen[s] = max(last_seen.get(s, dt.date(2000, 1, 1)), dt.date.fromisoformat(i["when_local"][:10]))

def set_holiday(i, hol):
    imgs = i["images"][:]; last = imgs[-1].replace("_holiday.jpg", ".jpg")
    if hol:
        h = last.replace(".jpg", "_holiday.jpg")
        assert h in CFILES, h
        last = h
    imgs[-1] = last; assert last in CFILES, last
    blocks = [b for b in i["caption"].split("\n\n") if b != HOLI]
    if hol: blocks.insert(1, HOLI)
    i["images"], i["caption"], i["holiday"] = imgs, "\n\n".join(blocks), hol

out = []; day = START; prev_series = None
while any(order.values()):
    best = None
    for relax in (0, 1, 2):
        for s, lst in sorted(order.items(), key=lambda kv: done[kv[0]] / total[kv[0]]):
            if not lst or (relax < 2 and s == prev_series and len([x for x in order.values() if x]) > 1): continue
            for i in lst[:12]:
                if HOL0 <= day <= SHOPONLY_END and not shop(i) and any(shop(x) for v in order.values() for x in v): continue
                gap = 3 if relax == 0 else 1 if relax == 1 else 0
                if any((day - last_seen.get(st, dt.date(2000, 1, 1))).days <= gap for st in states(i)): continue
                if relax == 0 and any(st in reel_states.get(str(day), ()) for st in states(i)): continue
                best = (s, i); break
            if best: break
        if best: break
    if not best: day += dt.timedelta(days=1); continue
    s, i = best; order[s].remove(i); done[s] += 1; prev_series = s
    west = states(i)[0] in WEST
    hh = 18 if west else (10 if day.weekday() == 6 else 9)
    loc = dt.datetime(day.year, day.month, day.day, hh, 0, tzinfo=den)
    suffix = i["key"].split("_", 2)[2]
    i["key"] = f"{day}_{hh:02d}00_{suffix}"
    i["when_local"] = loc.strftime("%Y-%m-%d %H:%M"); i["when_utc"] = loc.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    set_holiday(i, shop(i) and HOL0 <= day <= HOL1)
    for st in states(i): last_seen[st] = day
    out.append(i); day += dt.timedelta(days=1)

allk = [i["key"] for i in fixed + out]; assert len(allk) == len(set(allk))
rt = {r["when_local"] for r in reels}; assert not any(i["when_local"] in rt for i in out)
for i in out: assert len(i["caption"]) <= 2200 and i["caption"].count("#") <= 5
json.dump(sorted(fixed + out, key=lambda i: i["when_utc"]), open(f"{REPO}/igc/schedule.json", "w"), indent=1, ensure_ascii=False)
print(len(out), "re-planned:", out[0]["when_local"], "->", out[-1]["when_local"])
