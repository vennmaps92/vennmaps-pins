"""VennMaps automatic Instagram poster.

Runs from GitHub Actions every 15 minutes. Posts any Reel in ig/schedule.json
whose time has come (up to 12 hours late) and records it in ig/posted.json.

Pause everything: create a file named ig/PAUSE on the main branch.
Dry run (Actions > Run workflow > dry_run=true): uploads the next due-or-upcoming
video to Instagram and checks it processes, but does not publish.
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
VIDEO_BASE = "https://raw.githubusercontent.com/vennmaps92/vennmaps-pins/reels/v/"
LATE_LIMIT_H = 12      # don't post anything more than this late
MAX_PER_RUN = 2        # catch up gently if runs were missed
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


def make_container(item):
    url = VIDEO_BASE + urllib.parse.quote(item["video"])
    extra = {"location_id": item["location_id"]} if item.get("location_id") else {}
    c = call("POST", IG_USER + "/media", media_type="REELS", video_url=url,
             caption=item["caption"], share_to_feed="true", **extra)
    if "id" not in c:
        return None, c
    for _ in range(40):  # up to ~10 minutes
        s = call("GET", c["id"], fields="status_code,status")
        code = s.get("status_code")
        if code == "FINISHED":
            return c["id"], s
        if code in ("ERROR", "EXPIRED"):
            return None, s
        time.sleep(15)
    return None, {"error": {"message": "processing timed out"}}


def main():
    if not TOKEN:
        sys.exit("IG_TOKEN secret is missing")
    if os.path.exists(os.path.join(HERE, "PAUSE")):
        print("Paused (ig/PAUSE exists).")
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
        item = nxt[0]
        cid, info = make_container(item)
        print(f"DRY RUN {item['key']}: {'ready to publish' if cid else 'FAILED'} {json.dumps(info)[:300]}")
        if not cid:
            sys.exit(1)
        return

    due = [i for i in schedule
           if i["key"] not in posted or (posted[i["key"]].get("status") == "error"
                                         and posted[i["key"]].get("tries", 0) < MAX_TRIES)]
    due = [i for i in due if now - datetime.timedelta(hours=LATE_LIMIT_H) <= when(i) <= now]
    if not due:
        print(f"{_ok(me)} nothing due at {now:%Y-%m-%d %H:%M} UTC")
        return

    failed = False
    for item in due[:MAX_PER_RUN]:
        rec = posted.get(item["key"], {})
        cid, info = make_container(item)
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
        sys.exit(1)  # makes the run red so GitHub emails you


def _ok(me):
    return "@" + me.get("username", "?")


if __name__ == "__main__":
    main()
