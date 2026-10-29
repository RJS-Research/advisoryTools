#!/usr/bin/env python3
"""Acceptance gate for the dedupe + render core (no calendar access needed).

Runs the deterministic pipeline against fixtures that encode the failure modes
found during development. Exits non-zero on any failure so it can gate a ship.

    python3 selfTest.py
"""
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import dedupe as D
import render as R

FAILS = []
HERE = Path(__file__).resolve().parent


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def ev(cal, title, s, e, allday=False):
    return {"calendar": cal, "title": title, "start": s, "end": e, "allDay": allday}


# ---- fixtures: synthetic week — doubled account + JOIN holds + all-day + overlap ----
# Invented names on purpose: this file ships to clients, so it must never carry
# real calendar contents.
RAW = [
    # duplicate-account rows (same event twice)
    ev("work@x.com", "Client Call: Northwind", "2026-07-13T11:00:00-04:00", "2026-07-13T12:00:00-04:00"),
    ev("work@x.com [dup]", "Client Call: Northwind", "2026-07-13T11:00:00-04:00", "2026-07-13T12:00:00-04:00"),
    # a call + its companion JOIN hold in the identical slot
    ev("work@x.com", "Discussion on Contoso", "2026-07-14T09:30:00-04:00", "2026-07-14T10:30:00-04:00"),
    ev("work@x.com", "▶ JOIN: Contoso — Zoom (moderator link)", "2026-07-14T09:30:00-04:00", "2026-07-14T10:30:00-04:00"),
    # an overlap on the same day (two real meetings that collide)
    ev("work@x.com", "Overlap A", "2026-07-14T09:45:00-04:00", "2026-07-14T10:45:00-04:00"),
    # an all-day event
    ev("Home", "Conference (all day)", "2026-07-15T00:00:00-04:00", "2026-07-16T00:00:00-04:00", allday=True),
    # a personal-calendar event + a late-night one (bounds must expand)
    ev("Home", "Volleyball", "2026-07-19T13:00:00-04:00", "2026-07-19T18:00:00-04:00"),
    ev("Home", "Late film", "2026-07-16T22:00:00-04:00", "2026-07-16T23:00:00-04:00"),
]


def check_eventkit_api():
    """Assert the EventKit selectors pull.js names actually exist.

    A misspelled ObjC selector is not an error in JXA — the property is just
    undefined, so `if (store.wrongName)` quietly takes the else branch. That is
    exactly how v0.2.0/0.2.1 shipped: pull.js probed for
    `requestFullAccessToEventsCompletion` (no "With"), always fell through to
    the deprecated pre-macOS-14 call, and every fresh Mac granted WRITE-ONLY
    access — status 4, zero events readable, tool dead on arrival. The
    dedupe/render gate passed the whole time, because it never touches EventKit.

    Needs no calendar permission: it only asks whether the methods resolve.
    """
    print("EventKit API surface (no permission needed):")
    if not shutil.which("osascript"):
        print("  SKIP  not a Mac (osascript absent)")
        return

    probe = ('ObjC.import("EventKit"); const s = $.EKEventStore.alloc.init; '
             'JSON.stringify({'
             'full: typeof s.requestFullAccessToEventsWithCompletion, '
             'legacy: typeof s.requestAccessToEntityTypeCompletion, '
             'statusFn: typeof $.EKEventStore.authorizationStatusForEntityType})')
    try:
        out = subprocess.run(["osascript", "-l", "JavaScript", "-e", probe],
                             capture_output=True, text=True, timeout=30)
    except Exception as exc:  # noqa: BLE001
        check("EventKit probe runs", False, repr(exc))
        return
    if out.returncode != 0:
        check("EventKit probe runs", False, out.stderr.strip()[:200])
        return

    import json
    try:
        api = json.loads(out.stdout)
    except Exception as exc:  # noqa: BLE001
        check("EventKit probe returns JSON", False, repr(exc))
        return

    check("full-access selector resolves (requestFullAccessToEventsWithCompletion)",
          api.get("full") == "function",
          "undefined — a typo here silently downgrades every install to write-only")
    check("status function resolves", api.get("statusFn") == "function")

    # and the source must actually call the name we just proved exists
    src = (HERE / "pull.js").read_text()
    check("pull.js calls the full-access selector by its real name",
          "requestFullAccessToEventsWithCompletion" in src)
    # must be the *request* guard, not merely the status-4 error message — the
    # first version of this check matched both and would have passed the bug
    check("pull.js re-asks on write-only (status 4), not just notDetermined",
          "status === 0 || status === 4" in src)


def main():
    check_eventkit_api()

    print("dedupe:")
    r = D.dedupe(RAW, personal_cals=["home"])
    ev_by_title = {e["title"]: e for e in r["events"]}

    check("exact dupes collapse", r["stats"]["raw"] == 8 and any(
        e["title"] == "Client Call: Northwind" for e in r["events"]))
    check("duplicate title appears once",
          sum(e["title"] == "Client Call: Northwind" for e in r["events"]) == 1)
    check("join hold merged, not standalone",
          r["stats"]["merged"] == 1
          and not any("JOIN" in e["title"] for e in r["events"])
          and ev_by_title["Discussion on Contoso"].get("links"))
    check("overlap survives as its own event", "Overlap A" in ev_by_title)
    check("personal classified", ev_by_title["Volleyball"]["kind"] == "personal")
    check("work classified", ev_by_title["Discussion on Contoso"]["kind"] == "work")

    print("render (week, ref inside the fixture week):")
    ref = date(2026, 7, 15)
    for view in ("week", "rolling"):
        try:
            html = R.render(r["events"], view, ref)
            ok = html.startswith("<!doctype html>") and "Weekly Calendar" in html
            check(f"{view}: renders", ok)
            check(f"{view}: all-day banded", "Conference (all day)" in html)
            check(f"{view}: late event present (bounds expand)",
                  "Late film" in html or view == "rolling")  # the late film (7/16) is in week view
        except Exception as exc:  # noqa: BLE001
            check(f"{view}: renders", False, repr(exc))

    print("render (empty week must not crash):")
    try:
        R.render([], "week", ref)
        check("empty week renders", True)
    except Exception as exc:  # noqa: BLE001
        check("empty week renders", False, repr(exc))

    print()
    if FAILS:
        print(f"GATE FAILED: {len(FAILS)} check(s) failed: {', '.join(FAILS)}")
        sys.exit(1)
    print("GATE PASSED")


if __name__ == "__main__":
    main()
