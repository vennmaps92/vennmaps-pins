# plan_weekly.py - rebuild the Sunday Pinterest upload files (D:\States Project\pintrest).
#
# Pinterest's bulk uploader only keeps ~100 pins scheduled at once and only ~30 days ahead, so pins go up in
# weekly batches. This script keeps that plan:
#   * weekly_YYYY-MM-DD_upload.csv  - the files still to upload, one per Sunday (rebuilt every run)
#   * new_pins\*.csv                - NEW pins to add (no publish date needed); dated and folded into the plan,
#                                       RATE per day in their own time slots, starting the day after the next upload Sunday
#   * _already_uploaded\uploaded_dates.json - publish dates of every pin already on Pinterest (the 100-pin cap)
#
#   python plan_weekly.py                    re-plan from the next Sunday
#   python plan_weekly.py --uploaded FILE    record FILE as uploaded (moves it to _already_uploaded), then re-plan
#
# Rules: <= 96 pins scheduled at any time, nothing more than 29 days ahead, no two pins in one file share a title,
# every pin dated after its upload Sunday. Pins that cannot fit before their date are moved to the end of the plan.
import os, sys, csv, json, glob, shutil, datetime as dt

P = r"D:\States Project\pintrest"
UP = os.path.join(P, "_already_uploaded"); NEW = os.path.join(P, "new_pins")
DATES = os.path.join(UP, "uploaded_dates.json")
CAP, WINDOW, RATE = 96, 29, 3
SLOTS = [(16, 0), (23, 0), (2, 0)]   # UTC = 9:00, 16:00, 19:00 Denver (MST); free of the image-pin slots; (2,0) rolls to next UTC day
COLS = ["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"]
os.makedirs(UP, exist_ok=True); os.makedirs(NEW, exist_ok=True)
P_ = lambda r: dt.datetime.fromisoformat(r["Publish date"])

def read(f): return list(csv.DictReader(open(f, encoding="utf-8")))
def write(f, rows):
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows([{k: r.get(k, "") for k in COLS} for r in rows])

uploaded = json.load(open(DATES)) if os.path.exists(DATES) else []
if "--uploaded" in sys.argv:
    f = sys.argv[sys.argv.index("--uploaded") + 1]; f = f if os.path.isabs(f) else os.path.join(P, f)
    uploaded += [r["Publish date"] for r in read(f)]
    json.dump(uploaded, open(DATES, "w"), indent=0); shutil.move(f, os.path.join(UP, os.path.basename(f)))
    print("recorded", os.path.basename(f), "as uploaded")

# everything not yet uploaded: the current weekly files + any new pins
plan = [r for f in sorted(glob.glob(os.path.join(P, "weekly_*_upload.csv"))) for r in read(f)]
new = [r for f in sorted(glob.glob(os.path.join(NEW, "*.csv"))) for r in read(f)]
now = dt.datetime.now()                               # PC clock (Denver)
today = now.date(); sun = today + dt.timedelta(days=(6 - today.weekday()) % 7)
if sun == today and now.hour >= 12: sun += dt.timedelta(days=7)   # Sunday afternoon: plan from next Sunday
day = sun + dt.timedelta(days=1); k = 0
for r in new:                                         # date the new pins, RATE per day, from the day after the next upload
    h, m = SLOTS[k]; t = dt.datetime(day.year, day.month, day.day, h, m) + (dt.timedelta(days=1) if h < 12 else dt.timedelta())
    r["Publish date"] = t.strftime("%Y-%m-%dT%H:%M:%S"); k += 1
    if k == RATE: k = 0; day += dt.timedelta(days=1)
rest = sorted(plan + new, key=P_)

# rebuild the Sunday files
for f in glob.glob(os.path.join(P, "weekly_*_upload.csv")): os.remove(f)
S = dt.datetime(sun.year, sun.month, sun.day, 16, 0)  # 9 am Denver
sched = [dt.datetime.fromisoformat(d) for d in uploaded]; out = []
while rest:
    free = CAP - len([d for d in sched if d > S]); lim = S + dt.timedelta(days=WINDOW)
    take, titles, keep = [], set(), []
    for r in rest:
        if len(take) < free and S < P_(r) <= lim and r["Title"] not in titles: take.append(r); titles.add(r["Title"])
        else: keep.append(r)
    rest = [r for r in keep if P_(r) > S] + [r for r in keep if P_(r) <= S]
    late = [r for r in rest if P_(r) <= S]               # pins whose date passed before they fit: push to the end
    if late:
        rest = [r for r in rest if P_(r) > S]; d0 = max(P_(r) for r in rest) if rest else S
        for i, r in enumerate(late): r["Publish date"] = (d0 + dt.timedelta(hours=6 * (i + 1))).strftime("%Y-%m-%dT%H:%M:%S")
        rest = sorted(rest + late, key=P_)
    if take:
        name = "weekly_%s_upload.csv" % S.strftime("%Y-%m-%d"); write(os.path.join(P, name), take)
        out.append((name, len(take))); sched += [P_(r) for r in take]
    S += dt.timedelta(days=7)
for f in glob.glob(os.path.join(NEW, "*.csv")): shutil.move(f, os.path.join(UP, "added_" + os.path.basename(f)))
for n, c in out: print(n, c)
print("total", sum(c for _, c in out))
