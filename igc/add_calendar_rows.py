"""Add the Rock Layers + Face-off carousel rows to the VennMaps master calendar (run on Alan's PC).

    python add_calendar_rows.py ["D:\\States Project\\social\\posting_schedule\\VennMaps_master_calendar.xlsx"]

Reads igc/schedule.json from GitHub (main), finds carousel posts whose series is "Rock Layers" or "Face-off",
and adds one row per post to the Calendar tab, styled like the existing green "Instagram carousel" rows and
sorted into date/time order. Rows already present (same date + time + platform + state) are skipped, so it is
safe to run again. A backup copy of the workbook is saved first. Close Excel before running.
"""
import copy, datetime as dt, json, os, re, shutil, sys, urllib.request

XLSX = sys.argv[1] if len(sys.argv) > 1 else r"D:\States Project\social\posting_schedule\VennMaps_master_calendar.xlsx"
URL = "https://raw.githubusercontent.com/vennmaps92/vennmaps-pins/main/igc/schedule.json"
SERIES = tuple(os.environ.get("SERIES", "Rock Layers|Face-off").split("|"))
NAMES = dict(AL="Alabama", AZ="Arizona", AR="Arkansas", CA="California", CO="Colorado", CT="Connecticut", DE="Delaware",
             FL="Florida", GA="Georgia", ID="Idaho", IL="Illinois", IN="Indiana", IA="Iowa", KS="Kansas", KY="Kentucky",
             LA="Louisiana", ME="Maine", MD="Maryland", MA="Massachusetts", MI="Michigan", MN="Minnesota", MS="Mississippi",
             MO="Missouri", MT="Montana", NE="Nebraska", NV="Nevada", NH="New Hampshire", NJ="New Jersey", NM="New Mexico",
             NY="New York", NC="North Carolina", ND="North Dakota", OH="Ohio", OK="Oklahoma", OR="Oregon", PA="Pennsylvania",
             RI="Rhode Island", SC="South Carolina", SD="South Dakota", TN="Tennessee", TX="Texas", UT="Utah", VT="Vermont",
             VA="Virginia", WA="Washington", WV="West Virginia", WI="Wisconsin", WY="Wyoming")
TIME_FMTS = ["%I:%M %p", "%#I:%M %p", "%-I:%M %p", "%H:%M", "%I %p", "%#I %p", "%-I %p", "%I:%M%p", "%#I:%M%p", "%-I:%M%p"]
DATE_FMTS = ["%Y-%m-%d", "%m/%d/%Y", "%#m/%#d/%Y", "%-m/%-d/%Y", "%b %d", "%b %#d", "%b %-d", "%d %b %Y", "%a %b %d", "%B %d, %Y"]

def fmt(d, f):
    try: return d.strftime(f)
    except ValueError: return None

def main():
    import openpyxl
    if os.path.exists(os.path.join(os.path.dirname(XLSX), "~$" + os.path.basename(XLSX))):
        sys.exit("Excel has the calendar open. Close it and run again.")
    src = os.environ.get("SCHEDULE_FILE")
    data = json.load(open(src, encoding="utf-8")) if src else json.load(urllib.request.urlopen(URL, timeout=60))
    items = [i for i in data if (i.get("series") or "3 ways") in SERIES]
    print(f"{len(items)} {SERIES} posts in the schedule")
    bak = XLSX.replace(".xlsx", f"_bak_{dt.datetime.now():%Y%m%d_%H%M}_newcarousels.xlsx")
    shutil.copy2(XLSX, bak); print("Backup:", bak)

    wb = openpyxl.load_workbook(XLSX); ws = wb["Calendar"]
    hdr = {str(c.value).strip(): c.column for c in ws[1] if c.value}
    def col(name):
        for k, v in hdr.items():
            if k.lower().startswith(name.lower()): return v
        return None
    cW, cD, cDay, cT, cP, cWhat, cS, cSer = (col("Week"), col("Date"), col("Day"), col("Time"), col("Platform"),
                                            col("What to do"), col("State"), col("Series"))
    cVid, cOpen, cCap = col("Video file"), col("On-screen opener"), col("Caption")
    cTT, cIG = col("TikTok hashtags"), col("Instagram hashtags")
    cTTd, cIGd, cYTd, cNotes = col("TikTok done"), col("Instagram done"), col("YouTube done"), col("Notes")
    cTags, cLoc = col("Instagram tags"), col("Instagram location")
    ncol = ws.max_column

    rows = []
    for r in range(2, ws.max_row + 1):
        cells = [ws.cell(r, c) for c in range(1, ncol + 1)]
        if all(c.value in (None, "") for c in cells): continue
        rows.append([(c.value, copy.copy(c._style), c.hyperlink.target if c.hyperlink else None, c.number_format) for c in cells])
    def v(row, c): return row[c - 1][0] if c else None

    tmpl = next((row for row in rows if str(v(row, cP) or "").lower().startswith("instagram carousel")), None)
    if not tmpl: sys.exit("No existing 'Instagram carousel' row to copy the style from.")
    tdate, ttime, tday, tstate = v(tmpl, cD), v(tmpl, cT), v(tmpl, cDay), str(v(tmpl, cS) or "")

    def parse_date(x):
        if isinstance(x, dt.datetime): return x.date()
        if isinstance(x, dt.date): return x
        s = str(x or "").strip()
        for f in DATE_FMTS:
            try: return dt.datetime.strptime(s, f.replace("#", "").replace("-", "") if "%#" in f or "%-" in f else f).date()
            except ValueError: pass
        return None
    def parse_time(x):
        if isinstance(x, dt.time): return x
        if isinstance(x, dt.datetime): return x.time()
        s = str(x or "").strip().upper().replace(".", "")
        for f in ("%I:%M %p", "%H:%M", "%I %p", "%I:%M%p", "%H:%M:%S"):
            try: return dt.datetime.strptime(s, f).time()
            except ValueError: pass
        return None

    # how the template writes dates / times / days / states
    t_d = parse_date(tdate); t_t = parse_time(ttime)
    date_f = next((f for f in DATE_FMTS if isinstance(tdate, str) and t_d and fmt(t_d, f) == tdate), None)
    time_f = next((f for f in TIME_FMTS if isinstance(ttime, str) and t_t and fmt(dt.datetime.combine(dt.date.today(), t_t), f) == ttime), None)
    day_f = "%A" if tday and len(str(tday)) > 3 else "%a"
    full_names = tstate in NAMES.values()

    def week_value(d):
        for row in rows:
            rd = parse_date(v(row, cD))
            if rd and rd - dt.timedelta(days=rd.weekday()) == d - dt.timedelta(days=d.weekday()):
                return v(row, cW)
        return None

    def state_text(s):
        if "-" in s:
            a, b = s.split("-"); return f"{NAMES[a]} vs {NAMES[b]}" if full_names else s
        return NAMES[s] if full_names else s

    existing = {(parse_date(v(r, cD)), parse_time(v(r, cT)), str(v(r, cP) or "").lower(), str(v(r, cS) or "")) for r in rows}
    added = 0
    for it in items:
        when = dt.datetime.strptime(it["when_local"], "%Y-%m-%d %H:%M")
        key = (when.date(), when.time(), "instagram carousel", state_text(it["state"]))
        if key in existing: continue
        new = [list(c) for c in tmpl]
        for c in range(ncol): new[c][0] = None; new[c][2] = None
        def put(c, val):
            if c: new[c - 1][0] = val
        put(cW, week_value(when.date()))
        put(cD, fmt(when.date(), date_f) if date_f else (dt.datetime.combine(when.date(), dt.time()) if isinstance(tdate, dt.datetime) else when.date()))
        put(cDay, when.strftime(day_f))
        put(cT, fmt(when, time_f) if time_f else when.time())
        put(cP, v(tmpl, cP))
        n = len(it["images"])
        if it.get("series") == "Rock Layers":
            what = f"Auto-posts (Blotato): Rock Layers carousel, {n} slides"
            opener = f"{NAMES[it['state']]}: dig down through the rock layers"
        elif not it.get("series"):
            what = f"Auto-posts (Blotato): 3 ways carousel, {n} slides"
            opener = f"{NAMES[it['state']]}, mapped 3 ways"
        elif it["series"] != "Face-off":
            what = f"Auto-posts (Blotato): {it['series']} carousel, {n} slides"
            opener = it["caption"].split("\n")[0][:90]
        else:
            a, b = it["state"].split("-")
            what = f"Auto-posts (Blotato): Face-off carousel, {n} slides"
            opener = f"{NAMES[a]} vs {NAMES[b]}"
        put(cWhat, what); put(cS, state_text(it["state"])); put(cSer, it.get("series") or "3 ways")
        put(cVid, ", ".join(it["images"][:1]) + f" (+{n - 1} more, reels branch c/)")
        put(cOpen, opener); put(cCap, it["caption"])
        put(cTT, "n/a"); put(cIG, " ".join(re.findall(r"#\w+", it["caption"])))
        put(cTTd, "n/a"); put(cYTd, "n/a")
        put(cNotes, "Holiday Etsy slide" if it.get("holiday") else None)
        m = re.search(r"Map data: ([^\n]+)", it["caption"]); put(cTags, "Map data: " + m.group(1) if m else None)
        put(cLoc, "\u2014")
        rows.append([tuple(x) for x in new]); existing.add(key); added += 1

    def sort_key(row, last=[(dt.date.min, dt.time.min)]):
        d, t = parse_date(v(row, cD)), parse_time(v(row, cT))
        if d is None: return last[0]
        last[0] = (d, t or dt.time.min); return last[0]
    keyed = [(sort_key(r), i, r) for i, r in enumerate(rows)]
    keyed.sort(key=lambda x: (x[0], x[1]))

    for r in range(2, ws.max_row + 1):
        for c in range(1, ncol + 1):
            cell = ws.cell(r, c); cell.value = None; cell.hyperlink = None
    for i, (_, _, row) in enumerate(keyed, start=2):
        for c, (val, style, link, nf) in enumerate(row, start=1):
            cell = ws.cell(i, c); cell.value = val; cell._style = copy.copy(style); cell.number_format = nf
            if link: cell.hyperlink = link
    tmp = XLSX + ".tmp.xlsx"; wb.save(tmp); os.replace(tmp, XLSX)
    print(f"Added {added} rows ({len(keyed)} rows in Calendar). Saved {XLSX}")

if __name__ == "__main__":
    main()
