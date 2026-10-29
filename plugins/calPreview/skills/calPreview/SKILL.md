---
name: calPreview
description: Build a clean, brand-styled weekly calendar from the user's local Mac calendar — pulls this week's (or the next 7 days') events, removes duplicates, and renders a shareable HTML view. Triggers: "cal preview", "weekly calendar", "my schedule this week", "next 7 days", "build my calendar".
---

# calPreview — weekly calendar

Turns the local macOS calendar into a clean weekly view: pull → de-duplicate →
render to HTML. Two layouts:

- **`week`** — a fixed **Sun–Sat** calendar week.
- **`rolling`** — the **current date through the next 6 days** (7 columns), with
  weekend columns highlighted.

Everything runs locally; calendar data never leaves the machine.

## Run it

```bash
cd scripts
python3 build.py --view week --open        # this Sun–Sat week
python3 build.py --view rolling --open      # today + next 6 days
python3 build.py --view week --ref 2026-07-20   # a specific week (any date in it)
```

`build.py` does the whole pipeline and saves
`~/Documents/calPreview/calPreview_<view>_<date>.html` (the folder is created on
first run; `--out <path>` overrides). `--open` opens it in the browser.

**Keeping a PDF:** open the HTML and press **⌘P → Save as PDF**. The page carries
print styling — landscape, colours preserved, the week kept on one sheet — so what
prints matches what you see. There is no separate export step.

**Your job as the assistant:**
1. Read the user's phrasing to pick `--view` and `--ref` ("this week" → `week`,
   today's date; "next seven days" → `rolling`; "week of the 20th" → `week --ref`).
2. Run `build.py`. It prints a line like `pulled 40 raw -> 21 unique (2 join-holds merged)`.
3. Sanity-check that line with the user: if `raw` and `unique` are far apart, say
   how many duplicates collapsed and why (usually an account listed twice). If the
   merge count looks wrong, the user can inspect `scripts/dedupe.py` rules.
4. Open/point them to the HTML. Note it may contain personal events — it is a
   personal view, not a client-facing document, unless the user says otherwise.

## First-run setup (one time)

The pull uses macOS EventKit, which needs **Calendar access** for the app running
this skill (Claude, Terminal, etc.):

- On first run macOS shows a **"… wants to access your Calendar"** prompt → click **OK**.
- If it was dismissed or no prompt appears, the pull exits with a message and you
  enable it manually: **System Settings → Privacy & Security → Calendars →** turn on
  the app. Then re-run.
- **macOS 14+ distinguishes Full Access from write-only.** calPreview *reads*
  events, so write-only is not enough — the pull stops with `status=4` and says
  so. Fix: System Settings → Privacy & Security → Calendars → switch the app
  **off and back on**, choosing **Full Access**. Re-running also re-asks.
- No install, no compilation, no admin rights — `osascript` ships with macOS.

## Configure (optional)

`config.json` (beside this file):

```json
{ "personalCalendars": ["Home", "Family", "you@gmail.com"] }
```

Any calendar whose name contains one of these substrings is styled as **personal**
(warm/olive); everything else is **work** (green). Default: all events are work.

## What the pipeline handles

| Step | File | Handles |
|---|---|---|
| Pull | `scripts/pull.js` | EventKit via JXA (~1s); permission preflight; local-time ISO output |
| Dedupe | `scripts/dedupe.py` | exact duplicates (doubled accounts); folding "▶ JOIN /moderator-link" holds into their call; work/personal classification |
| Render | `scripts/render.py` | both views; dynamic time bounds; all-day band; side-by-side lanes for overlapping events; empty weeks |

## Gate before shipping changes

```bash
cd scripts && python3 selfTest.py     # must print GATE PASSED
```

`selfTest.py` runs the dedupe+render core against fixtures encoding every known
failure mode (duplicate accounts, JOIN holds, overlaps, all-day, late-night bounds,
empty week). It needs no calendar access, so it runs anywhere.

## When setup misbehaves (help improve the tool)

This is a first-version delivery. **Whenever the first run hiccups — no Calendar
prompt, a pull error, anything confusing — capture it rather than working around it,
so the author can improve the *setup pathway*:**

```bash
cd scripts && python3 doctor.py --note "what happened, in your words"
```

`doctor.py` probes the runtime steps (osascript reachable, EventKit auth, a real
pull, the dedupe/render gate), records any failures, and writes
`deliveryReport_<timestamp>.md` at the skill root. `build.py` also writes one
automatically if a pull fails.

**Your job as the assistant:** when you hit friction, open the latest
`deliveryReport_*.md` and fill the *Observations & improvements* section — one
entry per issue, each tagged by **layer**:
- `code` — deterministic script behaviour (hardest to break; codify last)
- `llm-advised` — a script you drove/interpreted (harden toward pure code next)
- `llm` — pure model judgement (least stable; first candidate to codify)

Then tell the user: *"Send `deliveryReport_<ts>.md` back to improve calPreview."*
The report is about the setup pathway, **not** the calendar features.

## Known MVP limits (harden on feedback)

- Multi-day timed events are clamped to their start day.
- Work/personal split is calendar-name based, not per-event.
- Single light theme.
