#!/usr/bin/env python3
"""Normalize + dedupe pulled calendar events.

Reads a JSON array of raw events (from pull.js) on stdin and writes a JSON
object {events, stats} on stdout. Also importable: dedupe(raw, personal_cals).

Three collapses, in order:
  1. Exact duplicates — the same (title, start, end, allDay) coming from more
     than one calendar (an account listed twice yields every event twice).
     Sources are unioned into `calendars`.
  2. Companion "JOIN"/moderator-link holds — a join-link event sitting in the
     identical slot as a real call is the same meeting; it is folded into that
     call as a `links` sub-line rather than shown as a second block. A JOIN with
     no same-slot sibling is kept (it is the only record of that meeting).
  3. Classification — `kind` = personal when any source calendar name matches a
     configured personal substring, else work. Default: everything is work.
"""
import argparse
import json
import re
import sys

JOIN_RE = re.compile(r"\bJOIN\b|moderator link", re.I)


def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def _link_label(title: str) -> str:
    """Short muted sub-line for a folded join hold."""
    low = title.lower()
    if "zoom" in low:
        return "Zoom — join link"
    if "teams" in low:
        return "Teams — join link"
    if "meet" in low:
        return "Google Meet — join link"
    return "Join link"


def dedupe(raw: list, personal_cals=()) -> dict:
    personal = [p.lower() for p in personal_cals if p.strip()]

    # 1. exact dedupe, unioning source calendars
    seen = {}
    for e in raw:
        title = _norm_title(e.get("title"))
        key = (title, e["start"], e["end"], bool(e.get("allDay")))
        if key not in seen:
            seen[key] = {
                "title": title,
                "start": e["start"],
                "end": e["end"],
                "allDay": bool(e.get("allDay")),
                "calendars": {e.get("calendar", "")},
            }
        else:
            seen[key]["calendars"].add(e.get("calendar", ""))
    events = list(seen.values())

    # 2. fold companion JOIN holds into a same-slot sibling
    joins = [e for e in events if JOIN_RE.search(e["title"])]
    hosts = [e for e in events if not JOIN_RE.search(e["title"])]
    merged = 0
    for j in joins:
        sib = next((h for h in hosts
                    if h["start"] == j["start"] and h["end"] == j["end"]), None)
        if sib is not None:
            sib.setdefault("links", []).append(_link_label(j["title"]))
            merged += 1
        else:
            hosts.append(j)  # no sibling — keep as its own block
    events = hosts

    # 3. classify + finalize
    for e in events:
        cals = " ".join(e["calendars"]).lower()
        e["kind"] = "personal" if any(p in cals for p in personal) else "work"
        e["calendars"] = sorted(c for c in e["calendars"] if c)
    events.sort(key=lambda e: (e["allDay"] is False, e["start"], e["end"]))

    return {
        "events": events,
        "stats": {"raw": len(raw), "unique": len(events), "merged": merged},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="dedupe pulled calendar events")
    ap.add_argument("--personal-cal", action="append", default=[],
                    metavar="SUBSTR",
                    help="calendar-name substring to style as personal "
                         "(repeatable); default: all events are work")
    a = ap.parse_args()
    raw = json.load(sys.stdin)
    if not isinstance(raw, list):
        sys.exit("ERROR: expected a JSON array of events on stdin")
    json.dump(dedupe(raw, a.personal_cal), sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
