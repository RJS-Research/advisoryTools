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

If `pip` itself is missing or the install is refused, say so plainly and stop. Do not
fall back to the JavaScript renderer to route around it -- that one needs `npm install`
and cannot use a `.potx` template, so it is a different tool, not a substitute. Once
`import pptx` succeeds, this never needs checking again on that machine.

## Run it

```bash
cd scripts
python3 render-python-pptx.py outline.md -o out/deck.pptx
python3 render-python-pptx.py outline.md -o out/deck.pptx --template brand.potx
node render-pptxgenjs.js outline.md -o out/deck.pptx     # needs: npm install
python3 compare.py                                        # render both, gate the result
```

Prints a line like `slides=5  native charts=2  slides with notes=4`. Read it back to
the user -- a chart count of 0 when the outline has chart blocks means a malformed
JSON spec, not an empty deck.

**Which renderer.** Reach for `render-python-pptx.py`. It is the default, it is pure
Python, and it is the only one that can open a real `.potx` and inherit its slide
master. `render-pptxgenjs.js` cannot import a template -- its API only offers
`defineSlideMaster()`, which means re-coding the master in JavaScript by hand. Keep
the JS one for the case where python-pptx's staleness bites.

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

```bash
python3 build-potx.py            # regenerate brand.potx from brand.json
```

The template supplies four things the blank layout still shows: the theme colour
scheme (so anything a human adds later picks brand colours out of PowerPoint's own
picker), the theme font scheme, master decoration, and the 16:9 slide size. It does
**not** supply placeholder geometry -- the renderer places every shape explicitly.

**To carry your own brand:** edit `brand.json`, re-run `build-potx.py`, then render
with `--template brand.potx`. To use a designer-made template instead, point
`--template` straight at their `.potx` and skip `build-potx.py` entirely.

## Your job as the assistant

1. Draft the outline in the dialect above, one slide per argument, each carrying its
   own exhibit. Do not render before the user has read the outline -- the outline is
   the edit surface and the deck is the artifact.
2. Run the renderer. Report the printed counts.
3. If a chart matters to the argument, say so and confirm it rendered as a chart part
   rather than silently dropping.

## Gate before shipping changes

```bash
cd scripts && npm install                            # one time -- compare.py needs both renderers
cd scripts && python3 compare.py                     # must exit 0
cd scripts && python3 compare.py --negative-control   # proves the gate can fail
```

`compare.py` asserts both decks carry the same content, that charts are native chart
parts rather than pictures, and that body text is real text in the slide XML.

**It renders with both engines, so it needs the JS one installed.** Without
`npm install` it dies on a `node` subprocess -- that is a missing optional dependency,
not a broken deck. The Python renderer alone needs nothing but `python-pptx`, and you
can verify it on its own by rendering `sample-outline.md` and reading the printed
counts.

## Known limits

- The chart slides have never been visually inspected on this toolchain -- they are
  verified structurally, by reading the OOXML. Open the deck and look before it goes
  to a client.
- `python-pptx` has had no upstream release since 2024-08-07. It works; it is not
  actively maintained. That is the standing argument for keeping the JS renderer.
- `sample-outline.md` numbers are invented to exercise the chart paths. They are not
  researched and its title slide says so. Never leave fixture numbers in a real deck.
