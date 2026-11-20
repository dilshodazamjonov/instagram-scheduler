"""Write PLAN.md: what has been posted, and when each queued video will go out.

Run any time:  python3 scripts/plan.py
The daily job and add_to_queue.sh also run it, so PLAN.md stays current.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASHKENT = timezone(timedelta(hours=5))
WINDOW = timedelta(hours=3)  # a day's post can go out up to this long after the slot


def post_time() -> tuple[int, int]:
    """Daily posting time in Tashkent time, from schedule.json."""
    cfg = json.loads((ROOT / "schedule.json").read_text())
    hh, mm = map(int, cfg.get("post_time_tashkent", "19:30").split(":"))
    return hh, mm


def slot_on(day) -> datetime:
    """The posting moment on a Tashkent calendar day."""
    hh, mm = post_time()
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=TASHKENT)


def local_day(iso: str):
    return datetime.fromisoformat(iso).astimezone(TASHKENT).date()


def posted_on(day, history: list[dict]) -> bool:
    return any(h.get("posted_at") and local_day(h["posted_at"]) == day for h in history)


def first_free_day(now: datetime, history: list[dict]):
    """The first Tashkent day whose slot can still be used."""
    day = now.astimezone(TASHKENT).date()
    if posted_on(day, history) or now > slot_on(day) + WINDOW:
        day += timedelta(days=1)
    return day


def queued(history: list[dict]) -> list[Path]:
    done = {h["folder"] for h in history}
    folders = sorted(p for p in (ROOT / "queue").iterdir() if p.is_dir()) if (ROOT / "queue").exists() else []
    return [f for f in folders if f.name not in done and (f / "video.mp4").exists() and (f / "caption.txt").exists()]


def build(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    history = json.loads((ROOT / "posted.json").read_text()) if (ROOT / "posted.json").exists() else []
    hh, mm = post_time()
    utc = slot_on(now.astimezone(TASHKENT).date()).astimezone(timezone.utc)
    rows = []
    for h in history:
        when = datetime.fromisoformat(h["posted_at"]).astimezone(TASHKENT)
        link = f"[open]({h['permalink']})" if h.get("permalink") else ""
        rows.append(f"| {h['folder']} | posted | {when:%a %d %b %Y, %H:%M} | {link} |")
    day = first_free_day(now, history)
    for folder in queued(history):
        when = slot_on(day)
        cover = "with cover" if (folder / "cover.jpg").exists() else ""
        rows.append(f"| {folder.name} | queued | {when:%a %d %b %Y, %H:%M} | {cover} |")
        day += timedelta(days=1)
    return "\n".join([
        "# Posting plan",
        "",
        f"One Reel a day at **{hh:02d}:{mm:02d} Tashkent** ({utc:%H:%M} UTC). GitHub usually starts the job",
        "within about 35 minutes of that time. Times below are Tashkent time.",
        "This file is updated automatically.",
        "",
        "| Video | Status | Date (Tashkent) | |",
        "|---|---|---|---|",
        *rows,
        "",
    ])


def write(now: datetime | None = None) -> None:
    (ROOT / "PLAN.md").write_text(build(now), encoding="utf-8")


if __name__ == "__main__":
    write()
    print((ROOT / "PLAN.md").read_text())
