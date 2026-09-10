# advisoryTools

Tools from RJS Research that run inside Claude Code on your Mac. Everything runs
entirely on your machine — nothing you open, read or build is uploaded anywhere.

| Skill | What it does |
|---|---|
| **calPreview** | Turns your Mac calendar into a clean weekly view — pull, de-duplicate, render to a shareable HTML page |
| **deckRender** | Turns a markdown outline into an editable PowerPoint deck with native, clickable charts |

## Install

You need [Claude Code](https://claude.com/claude-code) installed first. Then, inside
Claude Code, two lines:

```
/plugin marketplace add RJS-Research/advisoryTools
/plugin install advisoryTools@rjsResearch
```

That is the whole install. No clone, no token, no script to run.

**Updating later:** `/plugin update advisoryTools`.

## Use them

Just ask. The matching skill loads itself — you never invoke one by name.

- *"Build my weekly calendar."* / *"What's my schedule this week?"* → **calPreview**
- *"Render the deck."* / *"Turn this outline into a pptx."* → **deckRender**

## calPreview

Two layouts: `week` is a fixed Sun–Sat calendar week, `rolling` is today plus the next
six days. Output saves to `~/Documents/calPreview/` and opens in your browser.

**Keeping a PDF:** open the HTML and press **⌘P → Save as PDF**. The page carries print
styling — landscape, colours preserved, the week on one sheet — so what prints matches
what you see. There is no separate export step.

### One-time Calendar permission

The first time you run it, macOS asks whether Claude Code may read your calendar.

1. Click **OK** on the prompt. If it offers a choice, pick **Full Access**.
2. **Then open a new Terminal window before trying again.** This step is easy to miss
   and is the single most common reason the first run fails.

calPreview only ever *reads* your calendar. macOS's other option is write-only, which
is not enough — if you land there, the tool will say so. To fix it: System Settings →
Privacy & Security → Calendars → switch Claude Code off and back on, choosing Full
Access, then open a new window.

**Configure:** edit `config.json` in the calPreview skill folder to list calendar-name
fragments that should be styled as personal rather than work.

## deckRender

Charts in the rendered deck are **real PowerPoint chart parts**, so a reader can click a
bar and see the number behind it. Most markdown-to-slides tools bake each slide to an
image, which means every figure has to be taken on trust.

Claude drafts the outline first and shows it to you. **The outline is the edit surface;
the deck is the artifact.** Edit the outline, then render.

### One extra package

deckRender needs a Python package that does not ship with macOS. Claude checks for it
before the first render and offers to install it:

```
python3 -m pip install --user python-pptx
```

### Making it yours

**The deck ships deliberately unbranded** — a neutral grey-and-blue placeholder, not
anyone's house style. Put your own brand in by editing `brand.json` in the deckRender
skill folder (palette, fonts, slide size), then regenerating the template:

```bash
python3 build-potx.py
```

Nothing is hardcoded in renderer code, so re-branding is a file swap. If you already
have a designer-made PowerPoint template, skip all of that and point the renderer at
your `.potx` directly with `--template` — it inherits the real slide master.

## Known limits

**calPreview** — multi-day timed events are clamped to their start day; the work/personal
split is by calendar name, not per event; single light theme.

**deckRender** — chart slides are verified structurally, by reading the file format, not
visually. Open the deck and look before it goes to a committee. The sample outline's
numbers are invented to exercise the chart paths and its title slide says so — never
leave fixture numbers in a real deck.

## If something goes wrong

Ask Claude to *"run the calPreview doctor"*. It probes each step — is the calendar
reachable, is access granted, does a real pull work — and writes a
`deliveryReport_<timestamp>.md`. Send that file back; it describes the setup pathway,
not your calendar contents, and it is the fastest way to get the next version right.

---
RJS Research LLC
