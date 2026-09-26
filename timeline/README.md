# WWMath Time Machine

A [vis-timeline](https://github.com/visjs/vis-timeline) view of the as-of tree: every
item is a leaf of the archive, and the red **as-of line** is random access to history.
Drag it, click the timeline, or type a year (negative for BC). The page then shows the
record as it stood on that date: which works existed, how many formulas they
contribute, and which of those formulas are checked against the source. It also shows
notes wherever the archive records something in a form published later (for example,
Bates 1996 formulas written in the 2007 little-trap form).

**To view it, open `timeline/wwmath-time-machine.html`.** It is one self-contained file
(data, app, vis-timeline and MathJax inlined, about 2.7 MB), so double-clicking it in a
clone works with no web server, offline included. Only the Google Fonts are fetched,
and the page falls back to system fonts without them. GitHub's file view shows HTML
as source, so to open it from GitHub itself use Pages or download the raw file.

```bash
python timeline/build.py                 # regenerate data.js and wwmath-time-machine.html
python3 -m http.server -d timeline 8000  # the multi-file index.html, for editing app.js
(cd timeline/test && npm install && node browser.mjs)   # headless check
```

- **Single file.** `wwmath-time-machine.html` is generated from `index.html` by inlining
  its four scripts; edit `index.html`/`app.js`, then rebuild.
- **Data.** `data.js` is generated; nothing about a work is typed into the page.
  Lanes come from each leaf's `[timeline] lane`.
- **Dates.** BC dates use ISO 8601 expanded years, which JavaScript parses
  (1 BC is year 0).
- **Libraries.** vis-timeline 8.5.4 and MathJax 3.2.2 are vendored in `vendor/`
  with their licences, so the page works offline and from any static host.
- **Deep links.** `#heston1993` opens with that work selected.
