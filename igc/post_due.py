"""VennMaps automatic Instagram carousel (swipe) poster.

Runs from GitHub Actions every 15 minutes, next to ig/post_due.py (Reels).
Posts any carousel in igc/schedule.json whose time has come (up to 12 hours
late) and records it in igc/posted.json.

Images live on the `reels` branch at c/<file> (1080x1350 JPG).
Pause: create igc/PAUSE on main.
Dry run: creates the next carousel's containers and checks they process, no publish.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IG_USER = "17841414536676971"  # @vennmaps
API = "https://graph.facebook.com/v23.0/"
IMG_BASE = "https://raw.githubusercontent.com/vennmaps92/vennmaps-pins/reels/c/"
LATE_LIMIT_H = 12
MAX_PER_RUN = 1
MAX_TRIES = 3

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("IG_TOKEN", "").strip()
DRY = os.environ.get("DRY_RUN", "false").lower() == "true"


def call(method, path, **params):
    params["access_token"] = TOKEN
    q = urllib.parse.urlencode(params)
    url = API + path + ("?" + q if method == "GET" else "")
    req = urllib.request.Request(url, data=None if method == "GET" else q.encode(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {"error": {"message": f"HTTP {e.code}"}}


def load(name, default):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save(name, obj):
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def wait_ready(cid):
    for _ in range(40):  # up to ~10 minutes
        s = call("GET", cid, fields="status_code")
        code = s.get("status_code")
        if code == "FINISHED":
            return True, s
        if code in ("ERROR", "EXPIRED"):
            return False, s
        time.sleep(5)
    return False, {"error": {"message": "processing timed out"}}


def make_carousel(item):
    kids = []
    for img in item["images"]:
        c = call("POST", IG_USER + "/media", image_url=IMG_BASE + urllib.parse.quote(img),
                 is_carousel_item="true")
        if "id" not in c:
            return None, {"image": img, "resp": c}
        kids.append(c["id"])
    for k in kids:
        ok, s = wait_ready(k)
        if not ok:
            return None, s
    extra = {"location_id": item["location_id"]} if item.get("location_id") else {}
    c = call("POST", IG_USER + "/media", media_type="CAROUSEL", children=",".join(kids),
             caption=item["caption"], **extra)
    if "id" not in c:
        return None, c
    ok, s = wait_ready(c["id"])
    return (c["id"] if ok else None), s


def main():
    if not TOKEN:
        sys.exit("IG_TOKEN secret is missing")
    if os.path.exists(os.path.join(HERE, "PAUSE")):
        print("Paused (igc/PAUSE exists).")
        return
    me = call("GET", IG_USER, fields="username")
    if "error" in me:
        sys.exit("Token problem: " + me["error"].get("message", ""))

    schedule = load("schedule.json", [])
    posted = load("posted.json", {})
    now = datetime.datetime.now(datetime.timezone.utc)

    def when(i):
        return datetime.datetime.strptime(i["when_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)

    if DRY:
        nxt = [i for i in schedule if i["key"] not in posted and when(i) > now - datetime.timedelta(hours=LATE_LIMIT_H)]
        if not nxt:
            print("Nothing upcoming.")
            return
        cid, info = make_carousel(nxt[0])
        print(f"DRY RUN {nxt[0]['key']}: {'ready to publish' if cid else 'FAILED'} {json.dumps(info)[:300]}")
        if not cid:
            sys.exit(1)
        return

    due = [i for i in schedule
           if i["key"] not in posted or (posted[i["key"]].get("status") == "error"
                                         and posted[i["key"]].get("tries", 0) < MAX_TRIES)]
    due = [i for i in due if now - datetime.timedelta(hours=LATE_LIMIT_H) <= when(i) <= now]
    if not due:
        print(f"@{me.get('username', '?')} no carousel due at {now:%Y-%m-%d %H:%M} UTC")
        return

    failed = False
    for item in due[:MAX_PER_RUN]:
        rec = posted.get(item["key"], {})
        cid, info = make_carousel(item)
        res = call("POST", IG_USER + "/media_publish", creation_id=cid) if cid else info
        if cid and "id" in res:
            link = call("GET", res["id"], fields="permalink").get("permalink", "")
            posted[item["key"]] = {"status": "posted", "media_id": res["id"], "permalink": link,
                                   "posted_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            print(f"POSTED {item['key']} {link}")
        else:
            failed = True
            posted[item["key"]] = {"status": "error", "tries": rec.get("tries", 0) + 1,
                                   "last_error": json.dumps(res)[:400]}
            print(f"FAILED {item['key']}: {json.dumps(res)[:400]}")
        save("posted.json", posted)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
