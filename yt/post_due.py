"""VennMaps automatic YouTube Shorts poster (via Blotato).

Runs from GitHub Actions every 15 minutes. Posts any video in yt/schedule.json
whose time has come (up to 12 hours late) and records it in yt/posted.json.

Pause YouTube only: create a file named yt/PAUSE on the main branch.
Dry run: checks the API key and that the YouTube channel is connected; posts nothing.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://backend.blotato.com/v2/"
ACCOUNT_ID = "56547"  # YouTube "Alan (VennMaps)" in Blotato
VIDEO_BASE = "https://raw.githubusercontent.com/vennmaps92/vennmaps-pins/reels/v/"
LATE_LIMIT_H = 12
MAX_PER_RUN = 2
MAX_TRIES = 3

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("BLOTATO_API_KEY", "").strip()
DRY = os.environ.get("DRY_RUN", "false").lower() == "true"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"blotato-api-key": KEY, "Content-Type": "application/json",
                                          "User-Agent": "vennmaps-poster"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {"error": f"HTTP {e.code}"}


def load(name, default):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save(name, obj):
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def body_for(item):
    return {"post": {
        "accountId": ACCOUNT_ID,
        "content": {"text": item["description"], "platform": "youtube",
                    "mediaUrls": [VIDEO_BASE + urllib.parse.quote(item["video"])]},
        "target": {"targetType": "youtube", "title": item["title"], "privacyStatus": "public",
                   "shouldNotifySubscribers": True, "isMadeForKids": False,
                   "containsSyntheticMedia": bool(item.get("ai_voice"))}}}


def wait_status(sub_id):
    """Poll the submission for up to ~6 minutes; return (state, info)."""
    info = {}
    for _ in range(24):
        time.sleep(15)
        code, info = call("GET", "posts/" + sub_id)
        if not isinstance(info, dict):
            continue
        inner = info.get("post") if isinstance(info.get("post"), dict) else {}
        st = str(info.get("status") or inner.get("status") or "").lower()
        if "fail" in st or "error" in st:
            return "error", info
        if "publish" in st or info.get("publicUrl"):
            return "posted", info
    return "submitted", info  # still processing; Blotato finishes it


def main():
    if not KEY:
        sys.exit("BLOTATO_API_KEY secret is missing")
    if os.path.exists(os.path.join(HERE, "PAUSE")):
        print("YouTube paused (yt/PAUSE exists).")
        return

    code, accts = call("GET", "users/me/accounts")
    if code >= 400:
        sys.exit(f"Blotato key problem: HTTP {code} {json.dumps(accts)[:300]}")
    if ACCOUNT_ID not in json.dumps(accts):
        sys.exit("YouTube account 56547 is not connected in Blotato")
    if DRY:
        print("DRY RUN: Blotato key OK, YouTube channel connected. Nothing posted.")
        return

    schedule = load("schedule.json", [])
    posted = load("posted.json", {})
    now = datetime.datetime.now(datetime.timezone.utc)

    def when(i):
        return datetime.datetime.strptime(i["when_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)

    due = [i for i in schedule
           if i["key"] not in posted or (posted[i["key"]].get("status") == "error"
                                         and posted[i["key"]].get("tries", 0) < MAX_TRIES)]
    due = [i for i in due if now - datetime.timedelta(hours=LATE_LIMIT_H) <= when(i) <= now]
    if not due:
        print(f"YouTube: nothing due at {now:%Y-%m-%d %H:%M} UTC")
        return

    failed = False
    for item in due[:MAX_PER_RUN]:
        rec = posted.get(item["key"], {})
        code, res = call("POST", "posts", body_for(item))
        sub = res.get("postSubmissionId") if isinstance(res, dict) else None
        if code < 300 and sub:
            # Record the submission right away so a crash can't cause a double post.
            posted[item["key"]] = {"status": "submitted", "submission_id": sub}
            save("posted.json", posted)
            state, info = wait_status(sub)
            entry = {"status": state, "submission_id": sub, "tries": rec.get("tries", 0) + (state == "error"),
                     "time_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            if state == "error":
                entry["last_error"] = json.dumps(info)[:400]
                failed = True
            else:
                url = (info.get("publicUrl") or info.get("url")) if isinstance(info, dict) else None
                if url:
                    entry["url"] = url
            posted[item["key"]] = entry
            print(f"{state.upper()} {item['key']}")
        else:
            failed = True
            posted[item["key"]] = {"status": "error", "tries": rec.get("tries", 0) + 1,
                                   "last_error": f"HTTP {code} " + json.dumps(res)[:400]}
            print(f"FAILED {item['key']}: HTTP {code} {json.dumps(res)[:400]}")
        save("posted.json", posted)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
