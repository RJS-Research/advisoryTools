#!/usr/bin/env node
/*
 * Renderer B: PptxGenJS. Outline markdown to an editable .pptx with native charts.
 *
 *     node render-pptxgenjs.js sample-outline.md -o out/pptxgenjs.pptx
 *
 * This is the engine ICM's course-deck-production workspace uses, reached here
 * directly rather than through its html2pptx glue. That glue originates in
 * Anthropic's proprietary pptx skill, which the ICM repo vendors into an MIT
 * project; copying it into a client repo would carry that licence in with it.
 * Calling PptxGenJS (MIT) ourselves avoids the question entirely and costs about
 * forty lines.
 *
 * Reads the SAME outline via outline-parser.py, so a bake-off compares renderers
 * rather than two different readings of one file.
 */

const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const HERE = __dirname;
const brand = JSON.parse(fs.readFileSync(path.join(HERE, "brand.json"), "utf8"));

function parseArgs(argv) {
  const a = { outline: null, out: "out/pptxgenjs.pptx" };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "-o" || argv[i] === "--out") a.out = argv[++i];
    else if (!a.outline) a.outline = argv[i];
  }
  if (!a.outline) {
    console.error("usage: node render-pptxgenjs.js <outline.md> [-o out.pptx]");
    process.exit(2);
  }
  return a;
}

function parseOutline(file) {
  const out = execFileSync("python3", [path.join(HERE, "outline-parser.py"), file], {
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  return JSON.parse(out);
}

const CHART_TYPES = { bar: "bar", column: "bar", line: "line", pie: "pie" };

function main() {
  const args = parseArgs(process.argv);
  const deck = parseOutline(args.outline);
  const L = brand.layout;
  const F = brand.fonts;

  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: "RJS16x9", width: L.widthIn, height: L.heightIn });
  pptx.layout = "RJS16x9";

  const M = L.marginIn;
  const contentW = L.widthIn - 2 * M;

  // Title slide
  let s = pptx.addSlide();
  s.background = { color: brand.roles.background };
  s.addText(deck.title, {
    x: M, y: 2.4, w: contentW, h: 1.4,
    fontFace: F.heading.face, fontSize: F.heading.sizePt,
    bold: F.heading.bold, color: F.heading.color,
  });
  if (deck.subtitle) {
    s.addText(deck.subtitle, {
      x: M, y: 3.7, w: contentW, h: 0.8,
      fontFace: F.body.face, fontSize: F.body.sizePt, color: F.body.color,
    });
  }
  if (deck.footer) {
    s.addText(deck.footer, {
      x: M, y: L.heightIn - 0.9, w: contentW, h: 0.4,
      fontFace: F.footnote.face, fontSize: F.footnote.sizePt, color: F.footnote.color,
    });
  }

  for (const sl of deck.slides) {
    s = pptx.addSlide();
    s.background = { color: brand.roles.background };
    s.addText(sl.title, {
      x: M, y: L.titleTopIn, w: contentW, h: 0.9,
      fontFace: F.slideTitle.face, fontSize: F.slideTitle.sizePt,
      bold: F.slideTitle.bold, color: F.slideTitle.color,
    });

    const bullets = sl.blocks.filter((b) => b.kind === "bullet");
    const charts = sl.blocks.filter((b) => b.kind === "chart");
    const bodyW = charts.length ? contentW / 2 - 0.15 : contentW;
    const top = L.bodyTopIn;
    const bodyH = L.heightIn - top - 0.8;

    if (bullets.length) {
      s.addText(
        bullets.map((b) => ({ text: b.text, options: { bullet: true, breakLine: true } })),
        {
          x: M, y: top, w: bodyW, h: bodyH,
          fontFace: F.body.face, fontSize: F.body.sizePt, color: F.body.color,
          valign: "top", paraSpaceAfter: 10,
        }
      );
    }

    for (const c of charts) {
      const spec = c.spec;
      const type = CHART_TYPES[spec.type || "bar"];
      if (!type) throw new Error(`unsupported chart type ${spec.type}`);
      const data = spec.series.map((ser) => ({
        name: ser.name,
        labels: spec.categories,
        values: ser.values,
      }));
      s.addChart(type, data, {
        x: bullets.length ? M + bodyW + 0.3 : M,
        y: top,
        w: bullets.length ? contentW - bodyW - 0.3 : contentW,
        h: bodyH,
        chartColors: brand.chartSeriesOrder,
        showTitle: Boolean(spec.title),
        title: spec.title || "",
        titleFontFace: F.footnote.face,
        titleFontSize: F.footnote.sizePt,
        titleColor: F.footnote.color,
        showLegend: true,
        legendPos: "b",
        legendFontFace: F.footnote.face,
        legendFontSize: F.footnote.sizePt,
        catAxisLabelFontFace: F.footnote.face,
        catAxisLabelFontSize: F.footnote.sizePt,
        valAxisLabelFontFace: F.footnote.face,
        valAxisLabelFontSize: F.footnote.sizePt,
        lineDataSymbol: type === "line" ? "circle" : undefined,
        lineSize: type === "line" ? 2 : undefined,
      });
    }

    if (sl.notes) s.addNotes(sl.notes);
  }

  const out = path.resolve(args.out);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  return pptx.writeFile({ fileName: out }).then(() => {
    const nCharts = deck.slides.reduce(
      (n, sl) => n + sl.blocks.filter((b) => b.kind === "chart").length, 0);
    const nNotes = deck.slides.filter((sl) => sl.notes).length;
    console.log(`pptxgenjs    -> ${args.out}`);
    console.log(`  slides=${deck.slides.length + 1}  native charts=${nCharts}  slides with notes=${nNotes}`);
    console.log(`  size=${fs.statSync(out).size.toLocaleString()} bytes`);
  });
}

main().catch((e) => {
  console.error("FAILED:", e.message);
  process.exit(1);
});
