# WWMath Time Machine

A [vis-timeline](https://github.com/visjs/vis-timeline) view of the as-of tree: every
item is a leaf of the archive, and the red **as-of line** is random access to history.
Drag it, click the timeline, or type a year (negative for BC). The page then shows the
record as it stood on that date: which works existed, how many formulas they
contribute, and which of those formulas are checked against the source. It also shows
notes wherever the archive records something in a form published later (for example,
Bates 1996 formulas written in the 2007 little-trap form).

```bash
python timeline/build.py                 # regenerate data.js from the as-of tree
python3 -m http.server -d timeline 8000  # then open http://localhost:8000
(cd timeline/test && npm install && node browser.mjs)   # headless check
```

- **Data.** `data.js` is generated; nothing about a work is typed into the page.
  Lanes come from each leaf's `[timeline] lane`.
- **Dates.** BC dates use ISO 8601 expanded years, which JavaScript parses
  (1 BC is year 0).
- **Libraries.** vis-timeline 8.5.4 and MathJax 3.2.2 are vendored in `vendor/`
  with their licences, so the page works offline and from any static host.
- **Deep links.** `#heston1993` opens with that work selected.
