"""Post the next Reel in queue/ to Instagram. Runs once a day on GitHub Actions.

Queue layout (folders are posted in name order):
    queue/001-gradient-descent/video.mp4
    queue/001-gradient-descent/caption.txt

The video must be reachable at a public URL, because Instagram downloads it
itself. GitHub Pages serves this repo at PUBLIC_BASE_URL.

Environment:
    IG_ACCESS_TOKEN   Meta access token (GitHub secret)
    IG_USER_ID        Instagram account ID (from Meta Business settings)
    PUBLIC_BASE_URL   e.g. https://yourname.github.io/insta-queue
    IG_API_BASE       default https://graph.facebook.com/v23.0
    DRY_RUN=1         show what would be posted, call nothing
    FORCE=1           post now, ignoring schedule.json (the manual Run button)

The posting time in schedule.json is Tashkent time.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
LOG = ROOT / "posted.json"
API = os.environ.get("IG_API_BASE", "https://graph.facebook.com/v23.0").rstrip("/")


def log(msg: str) -> None:
    print(msg, flush=True)


def call(method: str, path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    url = f"{API}/{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"Instagram API error on {method} {path}: HTTP {e.code}\n{body}")


def url_is_live(url: str) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def next_item(posted: set[str]) -> Path | None:
    for folder in sorted(p for p in QUEUE.iterdir() if p.is_dir()) if QUEUE.exists() else []:
        if folder.name in posted:
            continue
        if (folder / "video.mp4").exists() and (folder / "caption.txt").exists():
            return folder
        log(f"Skipping {folder.name}: needs video.mp4 and caption.txt")
    return None


def main() -> None:
    history = json.loads(LOG.read_text()) if LOG.exists() else []
    now = datetime.now(plan.TASHKENT)
    if os.environ.get("NOW"):  # for testing, e.g. NOW=2026-11-21T20:07:00+05:00
        now = datetime.fromisoformat(os.environ["NOW"])

    if plan.paused() and not os.environ.get("FORCE"):
        log("Paused in schedule.json: posts are scheduled in Meta Business Suite. Nothing to do.")
        return
    if not os.environ.get("FORCE"):
        today = now.astimezone(plan.TASHKENT).date()  # days follow the Tashkent calendar
        slot = plan.slot_on(today)
        if now < slot:
            log(f"Not time yet: today's post is due at {slot:%H:%M} Tashkent.")
            return
        if plan.posted_on(today, history):
            log("Already posted today (Tashkent date).")
            return
        if now - slot > plan.WINDOW:
            log(f"Today's posting window ({slot:%H:%M} Tashkent + 3 h) has passed; next post is tomorrow.")
            return
        first_run_after_slot = now - slot < timedelta(minutes=30)
    else:
        first_run_after_slot = True

    item = next_item({h["folder"] for h in history})
    if item is None:
        log("Queue is empty. Nothing to post today.")
        if first_run_after_slot and os.environ.get("IG_USER_ID") and os.environ.get("IG_ACCESS_TOKEN"):
            # Check the token once a day, so a broken one fails the run (GitHub emails you).
            me = call("GET", os.environ["IG_USER_ID"], fields="username")
            log(f"Token check OK: connected to @{me.get('username')}")
        return

    caption = (item / "caption.txt").read_text(encoding="utf-8").strip()
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    video_url = f"{base}/queue/{urllib.parse.quote(item.name)}/video.mp4"
    cover = item / "cover.jpg"
    extra = {"cover_url": f"{base}/queue/{urllib.parse.quote(item.name)}/cover.jpg"} if cover.exists() else {}
    log(f"Next up: {item.name}\nVideo URL: {video_url}\nCover: {extra.get('cover_url', 'none')}\nCaption:\n{caption}\n")

    if os.environ.get("DRY_RUN"):
        log("DRY_RUN set: stopping before any upload.")
        return

    # GitHub Pages may still be deploying a video that was just pushed.
    for attempt in range(10):
        if url_is_live(video_url):
            break
        log(f"Video not reachable yet, waiting 30s ({attempt + 1}/10)...")
        time.sleep(30)
    else:
        sys.exit(f"Video URL never became reachable: {video_url}. Is GitHub Pages turned on?")

    user_id = os.environ["IG_USER_ID"]
    me = call("GET", user_id, fields="username")
    log(f"Posting as @{me.get('username')}")

    container = call(
        "POST", f"{user_id}/media",
        media_type="REELS", video_url=video_url, caption=caption, share_to_feed="true", **extra,
    )["id"]

    # Instagram downloads and processes the video before it can be published.
    for _ in range(60):
        status = call("GET", container, fields="status_code,status")
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram could not process the video: {status}")
        log(f"Processing on Instagram's side: {code}")
        time.sleep(10)
    else:
        sys.exit("Instagram took over 10 minutes to process the video; giving up for today.")

    media_id = call("POST", f"{user_id}/media_publish", creation_id=container)["id"]
    permalink = call("GET", media_id, fields="permalink").get("permalink", "")
    log(f"Published: {permalink}")

    history.append({
        "folder": item.name,
        "media_id": media_id,
        "permalink": permalink,
        "posted_at": datetime.now(plan.TASHKENT).isoformat(timespec="seconds"),
    })
    LOG.write_text(json.dumps(history, indent=2) + "\n")
    # The video is on Instagram now; drop it so the repo and website stay small.
    (item / "video.mp4").unlink()
    cover.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
    plan.write()
