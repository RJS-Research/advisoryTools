# advisoryTools

Tools from RJS Research that run inside Claude Code on your Mac. Everything runs
entirely on your machine — nothing you open, read or build is uploaded anywhere.

| Skill | What it does |
|---|---|
| **calPreview** | Turns your Mac calendar into a clean weekly view — pull, de-duplicate, render to a shareable HTML page |
| **deckRender** | Turns a markdown outline into an editable PowerPoint deck with native, clickable charts |

## Install

You need [Claude Code](https://claude.com/claude-code) installed first. Add the
marketplace once, then install whichever tools you want — they are independent, and
installing one does not bring the other along:

```
/plugin marketplace add RJS-Research/advisoryTools
/plugin install deck-render@rjsResearch
/plugin install cal-preview@rjsResearch
```

That is the whole install. No clone, no token, no script to run.

In the Claude Code **desktop app**, `/plugin` opens the Plugins pane without reading the
rest of the line — use the **+ Add** button there, or run the commands from a terminal
(`claude`), where they take their arguments.

**Updating later:** `/plugin update deck-render` (or `cal-preview`).

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

**If that fails with `error: externally-managed-environment`,** your `python3` is
Homebrew's, which refuses to install packages into itself. Retrying will not help.
Three ways out, simplest first:

```bash
/usr/bin/python3 -m pip install --user python-pptx        # Apple's python3, unrestricted
python3 -m venv ~/.deckRender && ~/.deckRender/bin/pip install python-pptx
python3 -m pip install --user --break-system-packages python-pptx
```

With either of the first two you must then render with *that* interpreter
(`/usr/bin/python3 …` or `~/.deckRender/bin/python …`), not a bare `python3` — tell
Claude which one you used. The third is simplest, at the cost of a Homebrew warning
the next time it upgrades python. The renderer prints these options itself if it is
ever run without the package.

### Making it yours

**The deck ships deliberately unbranded** — a neutral grey-and-blue placeholder, not
anyone's house style. Two files carry the brand: `brand.json` (palette, fonts, slide
size) and `brand.potx` (the slide master built from it). Nothing is hardcoded in
renderer code, so re-branding is a file swap, never a code edit.

⛔ **Do not edit them where they ship.** They live in Claude Code's versioned plugin
cache, and the next `/plugin update deck-render` installs into a new version folder and
prunes the old one — taking your palette with it. Copy them somewhere you own first:

```bash
SCRIPTS="$(ls -d ~/.claude/plugins/cache/*/deck-render/*/skills/deckRender/scripts | tail -1)"

mkdir -p ~/Documents/deckRender
cp "$SCRIPTS/brand.json" ~/Documents/deckRender/brand.json     # then edit this copy
python3 "$SCRIPTS/build-potx.py" --brand ~/Documents/deckRender/brand.json \
                                 -o     ~/Documents/deckRender/brand.potx
```

Then each render names both — `--template` for the slide master, `--brand` for the
colours the renderer draws with. Both are needed; `--template` alone leaves every shape
in the neutral palette. Tell Claude where the two files live and it will pass them.

If you already have a designer-made PowerPoint template, skip `build-potx.py` and point
`--template` straight at your `.potx` — it inherits the real slide master.

The plugin carries its own README with the full branding walk-through, the outline
dialect and a troubleshooting table. It is installed alongside the skill, and is in the
repo at `plugins/deckRender/README.md`.

## Known limits

**calPreview** — multi-day timed events are clamped to their start day; the work/personal
split is by calendar name, not per event; single light theme.

**deckRender** — chart slides are verified structurally, by reading the file format, not
visually. Open the deck and look before it goes to a committee. The sample outline's
numbers are invented to exercise the chart paths and its title slide says so — never
leave fixture numbers in a real deck.

## If something goes wrong

**calPreview.** Ask Claude to *"run the calPreview doctor"*. It probes each step — is
the calendar reachable, is access granted, does a real pull work — and writes a
`deliveryReport_<timestamp>.md`. Send that file back; it describes the setup pathway,
not your calendar contents, and it is the fastest way to get the next version right.
The doctor is calPreview's own; it cannot diagnose deckRender.

**deckRender.** Ask Claude, and say which of these you are seeing.

| What you see | What it means |
|---|---|
| `No module named 'pptx'` | The extra package above is not installed for the `python3` in use. |
| `error: externally-managed-environment` | Homebrew python. See the three options above. |
| `native charts=0` with chart blocks in the outline | A malformed JSON chart spec, not an empty deck. |
| Your brand reverted to grey and blue | A `/plugin update` replaced the cache copy. Keep `brand.json` and `brand.potx` in a folder you own, as above. |
| `not a template, no template content type` | The file given to `--template` is not a real `.potx`. |
| Charts render but look wrong | Possible by design: the check reads the file format, not the picture. Describe what you see. |

---
RJS Research LLC
