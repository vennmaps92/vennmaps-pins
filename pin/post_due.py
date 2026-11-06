"""VennMaps automatic Pinterest poster (via Blotato).

Runs from GitHub Actions every 15 minutes. Posts any pin in pin/schedule.json
whose time has come (up to 12 hours late) and records it in pin/posted.json.
Replaces the weekly Pinterest bulk-upload CSVs.

Pause Pinterest only: create a file named pin/PAUSE on the main branch.
Dry run: checks the key, finds the Pinterest account and the boards; posts nothing.
Test one pin now: set env PIN_KEY to a schedule key (ignores its time).
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://backend.blotato.com/v2/"
LATE_LIMIT_H = 12
MAX_PER_RUN = 3
MAX_TRIES = 3

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("BLOTATO_API_KEY", "").strip()
DRY = os.environ.get("DRY_RUN", "false").lower() == "true"
ONLY = os.environ.get("PIN_KEY", "").strip()


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


def items(obj):
    """Return the list inside a Blotato list response."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("items", "accounts", "boards", "data", "results"):
            if isinstance(obj.get(k), list):
                return obj[k]
    return []


def norm(s):
    return "".join(ch for ch in str(s).lower().replace("&", "and") if ch.isalnum())


def find_account():
    code, accts = call("GET", "users/me/accounts")
    if code >= 400:
        sys.exit(f"Blotato key problem: HTTP {code} {json.dumps(accts)[:300]}")
    pins = [a for a in items(accts) if "pinterest" in str(a.get("platform", "")).lower()]
    if not pins:
        sys.exit("No Pinterest account connected in Blotato")
    a = pins[0]
    return str(a.get("id") or a.get("accountId")), a


def find_boards(account_id):
    code, res = call("GET", "social/pinterest/boards?accountId=" + account_id)
    if code >= 400:
        sys.exit(f"Board lookup failed: HTTP {code} {json.dumps(res)[:300]}")
    return {norm(b.get("name")): str(b.get("id") or b.get("boardId")) for b in items(res)}, res


def body_for(item, account_id, board_id):
    return {"post": {
        "accountId": account_id,
        "content": {"text": item["description"], "platform": "pinterest", "mediaUrls": [item["media"]]},
        "target": {"targetType": "pinterest", "boardId": board_id, "title": item["title"][:100],
                   "altText": item["title"][:500], "link": item["link"]}}}


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
        print("Pinterest paused (pin/PAUSE exists).")
        return

    account_id, acct = find_account()
    boards, raw = find_boards(account_id)
    schedule = load("schedule.json", [])
    missing = sorted({i["board"] for i in schedule} - {b for b in {i["board"] for i in schedule} if norm(b) in boards})
    if DRY:
        print(f"DRY RUN: Pinterest account {account_id} ({acct.get('username') or acct.get('name') or ''})")
        print("Boards:", json.dumps(raw)[:1500])
        print("Missing boards:", missing or "none")
        return
    if missing:
        sys.exit(f"Boards not found on Pinterest: {missing}")

    posted = load("posted.json", {})
    now = datetime.datetime.now(datetime.timezone.utc)

    def when(i):
        return datetime.datetime.strptime(i["when_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)

    if ONLY:
        due = [i for i in schedule if i["key"] == ONLY and i["key"] not in posted]
    else:
        due = [i for i in schedule
               if i["key"] not in posted or (posted[i["key"]].get("status") == "error"
                                             and posted[i["key"]].get("tries", 0) < MAX_TRIES)]
        due = [i for i in due if now - datetime.timedelta(hours=LATE_LIMIT_H) <= when(i) <= now]
    if not due:
        print(f"Pinterest: nothing due at {now:%Y-%m-%d %H:%M} UTC")
        return

    failed = False
    for item in due[:MAX_PER_RUN]:
        rec = posted.get(item["key"], {})
        code, res = call("POST", "posts", body_for(item, account_id, boards[norm(item["board"])]))
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
