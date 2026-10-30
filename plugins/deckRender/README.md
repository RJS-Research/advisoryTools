# deck-render

Turn a markdown outline into an editable PowerPoint deck whose charts are **real
PowerPoint chart parts** — a reader can click a bar and see the number behind it.

Most markdown-to-slides tools bake each slide to a background image. The deck looks
fine and nothing in it can be edited or interrogated, so every figure has to be taken
on trust. If your deck's argument turns on a number, that difference is the whole game.

Everything runs on your machine. Nothing you outline, render or open is uploaded
anywhere.

```
claude plugin marketplace add RJS-Research/advisoryTools
claude plugin install deck-render@rjsResearch
```

In the Claude Code **desktop app**, `/plugin` opens the Plugins pane without reading the
rest of the line — use **+ Add** there, or run the commands above from a terminal
(`claude`), where they take their arguments.

Then just ask: *"turn this outline into a deck"*, *"render the slides"*. The skill loads
itself; you never invoke it by name. Claude drafts the outline, shows it to you, and
renders only once you have read it — **the outline is the edit surface, the deck is the
artifact.**

## One prerequisite

The default renderer needs one Python package that does not ship with macOS:

```bash
python3 -m pip install --user python-pptx
```

Claude checks for this before the first render and offers to install it, so you may
never type it yourself.

**If that fails with `error: externally-managed-environment`,** your `python3` is
Homebrew's, which refuses to install packages into itself. Retrying will not help.
Three ways out, simplest first:

```bash
# 1. Use the python3 Apple ships, which has no such restriction, and render with it.
/usr/bin/python3 -m pip install --user python-pptx

# 2. Make a virtual environment, and render with ITS python.
python3 -m venv ~/.deckRender
~/.deckRender/bin/pip install python-pptx

# 3. Install into your user site anyway. Simplest, but Homebrew may warn about the
#    unmanaged package when it next upgrades python.
python3 -m pip install --user --break-system-packages python-pptx
```

With option 1 or 2 you must run the renderer with *that* interpreter — `/usr/bin/python3
…` or `~/.deckRender/bin/python …` — not with a bare `python3`. Tell Claude which one you
installed into and it will use it. The renderer prints this same list if it is ever run
without the package, so you will not meet a bare traceback.

## The outline dialect

Deliberately small. Six constructs, and `sample-outline.md` in the skill's `scripts/`
folder exercises every one of them.

```markdown
# Deck title
subtitle: one line under the title
footer: appears on every slide

## A content slide
- a bullet
- another bullet

```chart {"type": "bar", "categories": ["A","B"], "series": [{"name":"X","values":[1,2]}]}```

> A speaker note. Multiple lines join into one paragraph.
```

Chart types are `bar`, `column`, `line`, `pie`. `<!-- comments -->` are ignored.

Every number in `sample-outline.md` is invented, to exercise the chart paths — its own
title slide says so. Never leave fixture numbers in a real deck.

## Making it yours

The deck ships deliberately unbranded: a neutral grey-and-blue placeholder, not anyone's
house style. Two files carry the brand — `brand.json` (palette, fonts, slide size) and
`brand.potx` (the PowerPoint slide master built from it). Nothing is hardcoded in
renderer code, so re-branding is a file swap and never a code edit.

⛔ **Do not edit those files where they ship.** They live in Claude Code's versioned
plugin cache (`~/.claude/plugins/cache/…/deck-render/<version>/…`). The next
`claude plugin update deck-render` installs into a new version folder and prunes the old
one, which would silently take your palette, your `.potx` and any `node_modules` with
it. Treat the shipped copies as a starting point to copy out.

Set your brand up once, in a folder you own:

```bash
SCRIPTS="$(ls -d ~/.claude/plugins/cache/*/deck-render/*/skills/deckRender/scripts | tail -1)"

mkdir -p ~/Documents/deckRender
cp "$SCRIPTS/brand.json" ~/Documents/deckRender/brand.json     # then edit this copy
python3 "$SCRIPTS/build-potx.py" --brand ~/Documents/deckRender/brand.json \
                                 -o     ~/Documents/deckRender/brand.potx
```

Then every render names both files, and no update can touch either:

```bash
python3 "$SCRIPTS/render-python-pptx.py" outline.md -o deck.pptx \
        --template ~/Documents/deckRender/brand.potx \
        --brand    ~/Documents/deckRender/brand.json
```

Both flags are needed and they do different jobs. `--template` supplies the slide
master: the theme colour scheme (so anything you add later picks your colours out of
PowerPoint's own picker), the theme fonts, master decoration and the 16:9 slide size.
`--brand` supplies the colours and fonts the renderer draws each shape with. Pass only
`--template` and every shape stays in the shipped neutral palette.

**Already have a designer-made template?** Skip `build-potx.py` and point `--template`
straight at their `.potx`. Pair it with a `--brand` copy whose colours match it, or the
shapes and the master will disagree.

Tell Claude where your two files live and it will pass them for you.

## Known limits

- Chart slides are verified **structurally**, by reading the PowerPoint file format, not
  visually. Open the deck and look at it before it goes to a committee.
- Multi-level bullets, images, tables and slide transitions are not in the dialect. One
  bullet level, charts, and speaker notes.
- `python-pptx` has had no upstream release since 2024-08-07. It works; it is not
  actively maintained.
- A second renderer (`render-pptxgenjs.js`, Node) ships alongside for the case where
  that staleness bites. It cannot inherit a `.potx` slide master, so it is a fallback
  rather than a substitute. Using it means `npm install` in the scripts folder — which
  `plugin update` also prunes.
- That `npm install` reports two high-severity advisories against `image-size`, pulled
  in transitively by `pptxgenjs`: denial of service in its JXL, HEIF and ICNS parsers
  (GHSA-5p2g-fcmc-qvqq, GHSA-w3rx-r6r6-pgpr). Nothing here parses an image — a deck is
  built from an outline and drawn as shapes — so the vulnerable code is never reached.
  `npm audit fix --force` offers only a breaking `pptxgenjs` downgrade, so the
  advisories are left standing rather than papered over. The Python renderer, the
  default, has no Node dependencies at all.

## If something goes wrong

Ask Claude, and say which of these you are seeing.

| What you see | What it means |
|---|---|
| `No module named 'pptx'` | The prerequisite above is not installed for the python3 being used. |
| `error: externally-managed-environment` | Homebrew python. See the three options above. |
| `native charts=0` but your outline has chart blocks | A malformed JSON chart spec, not an empty deck. Claude can read the spec back and fix it. |
| Your brand reverted to grey and blue | A `plugin update` replaced the cache copy. Set the brand up in a folder you own, as above. |
| `not a template, no template content type` | The file passed to `--template` is not a real `.potx`. |
| Charts look wrong, or labels are unreadable | Expected to be possible: the gate reads the file format, not the picture. Say what you see and Claude can adjust the outline or the brand. |

## Licence

MIT. See `LICENSE` beside this file.

---
RJS Research LLC
