"""VennMaps automatic TikTok poster (via Blotato's audited TikTok app).

Runs from GitHub Actions. Hands each video to Blotato up to 18 hours ahead with its
exact time (Blotato publishes on the minute), or posts right away if already due
(up to 12 hours late). Posts any video in tt/schedule.json
whose time has come (up to 12 hours late) and records it in tt/posted.json.

Pause TikTok only: create a file named tt/PAUSE on the main branch.
Dry run: checks the API key and that @vennmaps is connected; posts nothing.
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
ACCOUNT_ID = "67693"  # TikTok @vennmaps in Blotato
VIDEO_BASE = "https://raw.githubusercontent.com/vennmaps92/vennmaps-pins/reels/v/"
LATE_LIMIT_H = 12
MAX_PER_RUN = 6
AHEAD_H = 18        # hand posts to Blotato up to 18 hours early; it publishes on the minute
LABEL = "TikTok"
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
        "content": {"text": item["caption"], "platform": "tiktok",
                    "mediaUrls": [VIDEO_BASE + urllib.parse.quote(item["video"])]},
        "target": {"targetType": "tiktok", "privacyLevel": "PUBLIC_TO_EVERYONE",
                   "disabledComments": False, "disabledDuet": False, "disabledStitch": False,
                   "isBrandedContent": False, "isYourBrand": True,
                   "isAiGenerated": bool(item.get("ai_voice"))}}}


def check_status(sub_id):
    """One status check: returns ("posted"|"error"|"pending", info)."""
    code, info = call("GET", "posts/" + sub_id)
    if not isinstance(info, dict):
        return "pending", {}
    inner = info.get("post") if isinstance(info.get("post"), dict) else {}
    st = str(info.get("status") or inner.get("status") or "").lower()
    if "fail" in st or "error" in st:
        return "error", info
    if "publish" in st or info.get("publicUrl"):
        return "posted", info
    return "pending", info


def main():
    if not KEY:
        sys.exit("BLOTATO_API_KEY secret is missing")
    if os.path.exists(os.path.join(HERE, "PAUSE")):
        print("TikTok paused (tt/PAUSE exists).")
        return

    code, accts = call("GET", "users/me/accounts")
    if code >= 400:
        sys.exit(f"Blotato key problem: HTTP {code} {json.dumps(accts)[:300]}")
    if ACCOUNT_ID not in json.dumps(accts):
        sys.exit("TikTok account 67693 is not connected in Blotato")
    if DRY:
        print("DRY RUN: Blotato key OK, TikTok @vennmaps connected. Nothing posted.")
        return

    schedule = load("schedule.json", [])
    posted = load("posted.json", {})
    now = datetime.datetime.now(datetime.timezone.utc)

    def when(i):
        return datetime.datetime.strptime(i["when_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)

    by_key = {i["key"]: i for i in schedule}
    failed = False

    # 1) Follow up on posts Blotato is holding or still processing.
    for k, rec in list(posted.items()):
        if rec.get("status") not in ("scheduled", "submitted") or not rec.get("submission_id") or k not in by_key:
            continue
        if now < when(by_key[k]) + datetime.timedelta(minutes=10):
            continue
        state, info = check_status(rec["submission_id"])
        if state == "posted":
            rec.update(status="posted", url=info.get("publicUrl") or info.get("url") or rec.get("url", ""))
            print(f"CONFIRMED {k} {rec.get('url', '')}")
        elif state == "error":
            rec.update(status="error", tries=rec.get("tries", 0) + 1, last_error=json.dumps(info)[:400])
            failed = True
            print(f"FAILED {k}: {json.dumps(info)[:300]}")
        posted[k] = rec
    save("posted.json", posted)

    # 2) Hand upcoming posts to Blotato with their exact time (or post now if already due).
    todo = [i for i in schedule
            if i["key"] not in posted or (posted[i["key"]].get("status") == "error"
                                          and posted[i["key"]].get("tries", 0) < MAX_TRIES)]
    todo = [i for i in todo if now - datetime.timedelta(hours=LATE_LIMIT_H) <= when(i) <= now + datetime.timedelta(hours=AHEAD_H)]
    if not todo:
        print(f"{LABEL}: nothing to queue at {now:%Y-%m-%d %H:%M} UTC")
    for item in todo[:MAX_PER_RUN]:
        rec = posted.get(item["key"], {})
        body = body_for(item)
        future = when(item) > now + datetime.timedelta(minutes=3)
        if future:
            body["scheduledTime"] = item["when_utc"]
        code, res = call("POST", "posts", body)
        sub = res.get("postSubmissionId") if isinstance(res, dict) else None
        if code < 300 and sub:
            if future and not res.get("scheduledTime"):
                posted[item["key"]] = {"status": "submitted", "submission_id": sub, "tries": rec.get("tries", 0),
                                       "note": "Blotato did not confirm the schedule time; it may have posted early"}
                save("posted.json", posted)
                sys.exit(f"{LABEL}: Blotato did not confirm scheduledTime for {item['key']}; stopping to avoid early posts")
            posted[item["key"]] = {"status": "scheduled" if future else "submitted", "submission_id": sub,
                                   "for_local": item["when_local"], "tries": rec.get("tries", 0)}
            print(f"{'SCHEDULED' if future else 'SUBMITTED'} {item['key']} for {item['when_local']}")
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
