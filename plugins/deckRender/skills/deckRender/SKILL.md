---
name: deckRender
description: Turn a markdown outline into an editable PowerPoint deck with native, clickable charts -- not pictures of charts. Optionally inherits a .potx template's slide master so the deck carries your brand. Triggers: "render the deck", "build the slides", "make a pptx", "turn this outline into a deck", "editable chart deck".
---

# deckRender -- outline to editable deck

Writes a `.pptx` from a small markdown dialect. Two renderers are kept side by side;
both read the same outline through `outline-parser.py`, so they differ as renderers
and never as two readings of one file.

**The point is editability.** Charts are real PowerPoint chart parts, so a reader can
click a bar and see the number behind it. Most markdown-to-slides tools bake each
slide to a background image, which means a committee has to take every figure on
trust. If your deck's argument turns on a number, that difference is the whole game.

## Preflight -- do this before the first render, every new machine

The renderer needs one package that does not ship with macOS. **Check it before you
render, not after**, so the user sees an install prompt rather than a traceback:

```bash
python3 -c "import pptx" 2>/dev/null && echo "ready" || echo "MISSING python-pptx"
```

If it prints `MISSING python-pptx`, tell the user what is missing and why, then offer
to install it:

```bash
python3 -m pip install --user python-pptx
```

**If that install fails with `error: externally-managed-environment`,** the user's
`python3` is Homebrew's, which refuses to install into itself. Do not retry the same
command. Offer, in this order:

```bash
/usr/bin/python3 -m pip install --user python-pptx   # Apple's python3, no restriction
                                                     # -- then render with /usr/bin/python3
python3 -m venv ~/.deckRender && ~/.deckRender/bin/pip install python-pptx
                                                     # -- then render with ~/.deckRender/bin/python
python3 -m pip install --user --break-system-packages python-pptx
                                                     # simplest; Homebrew may warn later
```

The renderer prints this same list itself if it is ever reached without the package,
so a user who runs it by hand is not left with a bare traceback.

If `pip` itself is missing or the install is refused, say so plainly and stop. Do not
fall back to the JavaScript renderer to route around it -- that one needs `npm install`
and cannot use a `.potx` template, so it is a different tool, not a substitute. Once
`import pptx` succeeds, this never needs checking again on that machine.

## Run it

The scripts live in this skill's own `scripts/` folder. When the skill is installed as
a plugin, that folder sits inside Claude Code's plugin cache, so resolve it once rather
than guessing at a path:

```bash
SCRIPTS="$(ls -d ~/.claude/plugins/cache/*/deck-render/*/skills/deckRender/scripts | tail -1)"
```

```bash
python3 "$SCRIPTS/render-python-pptx.py" outline.md -o deck.pptx
python3 "$SCRIPTS/render-python-pptx.py" outline.md -o deck.pptx --template ~/Documents/deckRender/brand.potx
node "$SCRIPTS/render-pptxgenjs.js" outline.md -o deck.pptx    # needs: npm install, run in $SCRIPTS
```

Write the deck somewhere the user owns, never into `$SCRIPTS` -- see **Branding** for
why that folder is not a place to keep anything.

Prints a line like `slides=5  native charts=2  slides with notes=4`. Read it back to
the user -- a chart count of 0 when the outline has chart blocks means a malformed
JSON spec, not an empty deck.

**Which renderer.** Reach for `render-python-pptx.py`. It is the default, it is pure
Python, and it is the only one that can open a real `.potx` and inherit its slide
master. `render-pptxgenjs.js` cannot import a template -- its API only offers
`defineSlideMaster()`, which means re-coding the master in JavaScript by hand. Keep
the JS one for the case where python-pptx's staleness bites. Its `node_modules` also
lives in `$SCRIPTS`, so `plugin update` removes it and `npm install` has to be re-run
-- one more reason the Python renderer is the default.

## The outline dialect

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

`<!-- comments -->` are ignored. `sample-outline.md` exercises every path and is the
reference for the dialect -- read it before writing your first outline.

## Branding

`brand.json` holds the palette, fonts and slide size. Nothing is hardcoded in renderer
code, so re-branding is a file swap, never a code edit.

⛔ **Never edit `brand.json` or `brand.potx` inside `$SCRIPTS`, and never tell the user
to.** That folder is a versioned plugin cache: the next `claude plugin update
deck-render` installs into a new version directory and prunes the old one, taking the
user's palette, their `brand.potx` and any `node_modules` with it. The copies that ship
there are a neutral starting point to be *copied out*, not a config file to edit.

**Set a brand up in a folder the user owns**, once:

```bash
mkdir -p ~/Documents/deckRender
cp "$SCRIPTS/brand.json" ~/Documents/deckRender/brand.json     # then edit this copy
python3 "$SCRIPTS/build-potx.py" --brand ~/Documents/deckRender/brand.json \
                                 -o     ~/Documents/deckRender/brand.potx
```

Then every render names both files, and an update cannot touch either:

```bash
python3 "$SCRIPTS/render-python-pptx.py" outline.md -o deck.pptx \
        --template ~/Documents/deckRender/brand.potx \
        --brand    ~/Documents/deckRender/brand.json
```

Both are needed and they do different jobs: `--template` supplies the slide master,
`--brand` supplies the colours and fonts the renderer draws with. Passing only
`--template` leaves every shape in the shipped neutral palette.

The template supplies four things the blank layout still shows: the theme colour
scheme (so anything a human adds later picks brand colours out of PowerPoint's own
picker), the theme font scheme, master decoration, and the 16:9 slide size. It does
**not** supply placeholder geometry -- the renderer places every shape explicitly.

If the user already has a designer-made `.potx`, skip `build-potx.py`: point
`--template` straight at their file. Pair it with a `--brand` copy whose colours match,
or the shapes and the master will disagree.

## Your job as the assistant

1. Draft the outline in the dialect above, one slide per argument, each carrying its
   own exhibit. Do not render before the user has read the outline -- the outline is
   the edit surface and the deck is the artifact.
2. Run the renderer. Report the printed counts.
3. If a chart matters to the argument, say so and confirm it rendered as a chart part
   rather than silently dropping.

## Checking a render

Render `sample-outline.md` and read the printed counts back. It exercises every path in
the dialect, so if its chart count is 2 the chart path works on this machine. That
needs nothing but `python-pptx`.

*Maintainer gate, not part of using the skill:* `compare.py` renders with **both**
engines and asserts they agree, that charts are native chart parts rather than
pictures, and that body text is real text in the slide XML. It therefore needs the JS
renderer installed (`npm install` in `$SCRIPTS`), and `--negative-control` proves it
can fail. A user who only wants a deck never needs to run it.

## Known limits

- The chart slides have never been visually inspected on this toolchain -- they are
  verified structurally, by reading the OOXML. Open the deck and look before it goes
  to a client.
- `python-pptx` has had no upstream release since 2024-08-07. It works; it is not
  actively maintained. That is the standing argument for keeping the JS renderer.
- `sample-outline.md` numbers are invented to exercise the chart paths. They are not
  researched and its title slide says so. Never leave fixture numbers in a real deck.
- `npm install`, for the JS renderer only, reports two high-severity advisories against
  `image-size` (transitive through `pptxgenjs`). They are denial-of-service bugs in
  image parsers this skill never calls, and the only offered fix is a breaking
  downgrade. Say so if a user asks; do not run `npm audit fix --force`.
