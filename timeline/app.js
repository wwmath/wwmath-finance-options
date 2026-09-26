// WWMath Time Machine: page logic. Data comes from data.js (timeline/build.py), which is
// generated from the as-of tree, so every item here is a leaf of the archive.
(function () {
  "use strict";
  const DATA = window.WWMATH;
  const $ = (id) => document.getElementById(id);
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const works = DATA.works.map((w) => ({ ...w, when: new Date(w.start) }));
  const byId = Object.fromEntries(works.map((w) => [w.id, w]));
  const lanes = Object.fromEntries(DATA.lanes.map((l) => [l.id, l]));

  // Astronomical year (1 BC = 0) -> label. JavaScript Dates use astronomical years.
  const yearLabel = (y) => (y <= 0 ? `${1 - y} BC` : `${y}`);
  const dateLabel = (d) => `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${yearLabel(d.getUTCFullYear())}`;
  const fromYear = (y) => { const d = new Date(Date.UTC(2000, 0, 1)); d.setUTCFullYear(y); return d; };
  const today = () => { const n = new Date(); return new Date(Date.UTC(n.getFullYear(), n.getMonth(), n.getDate())); };

  // ---------------------------------------------------------------- timeline
  const items = new vis.DataSet();
  for (const w of works) {
    items.add({ id: w.id, group: w.lane, start: w.when, type: "box", className: `lane-${w.lane}`,
                content: `${esc(w.name)}<small>${esc(w.label)}</small>`,
                title: `${esc(w.title)} (${esc(w.label)})` });
    w.later.forEach((e, i) => items.add({
      id: `${w.id}~${i}`, group: w.lane, start: new Date(e.start), type: "point", className: "later",
      content: `${esc(w.name)}: ${esc(e.label)}`, title: esc(e.event), work: w.id }));
  }
  const groups = new vis.DataSet(DATA.lanes.map((l, i) => ({
    id: l.id, order: i, content: `${esc(l.label)}<small>${esc(l.note)}</small>` })));

  const axisLabel = (date, scale) => {
    const y = date.year();
    if (scale === "year" || scale === "decade" || scale === "century") return yearLabel(y);
    if (scale === "month") return `${MONTHS[date.month()]} ${yearLabel(y)}`;
    return `${date.date()} ${MONTHS[date.month()]}`;
  };
  const YEAR = 365.25 * 24 * 3600 * 1000;
  const timeline = new vis.Timeline($("timeline"), items, groups, {
    stack: true, orientation: { axis: "top" }, margin: { item: { horizontal: 6, vertical: 6 } },
    min: fromYear(-600), max: fromYear(2040), zoomMin: 0.25 * YEAR, zoomMax: 2700 * YEAR,
    start: fromYear(1890), end: fromYear(2031), showCurrentTime: true, groupOrder: "order",
    format: { minorLabels: axisLabel, majorLabels: (d, s) => (s === "year" || s === "decade" || s === "century" ? "" : yearLabel(d.year())) },
    tooltip: { followMouse: true }, selectable: true,
  });

  // ---------------------------------------------------------------- as-of cursor
  let asOf = today();
  timeline.addCustomTime(asOf, "asof");
  const setAsOf = (d, { move = true } = {}) => {
    asOf = d;
    if (move) timeline.setCustomTime(d, "asof");
    timeline.setCustomTimeMarker(yearLabel(d.getUTCFullYear()), "asof", false);
    $("asof-date").textContent = dateLabel(d);
    $("asof-year").value = d.getUTCFullYear() <= 0 ? d.getUTCFullYear() - 1 : d.getUTCFullYear();
    const upd = [];
    for (const w of works) {
      upd.push({ id: w.id, className: `lane-${w.lane}${w.when > d ? " future" : ""}` });
      w.later.forEach((e, i) => upd.push({ id: `${w.id}~${i}`, className: `later${new Date(e.start) > d ? " future" : ""}` }));
    }
    items.update(upd);
    renderRecord();
    if (selected) renderDetail(selected);
  };
  timeline.on("timechange", (p) => p.id === "asof" && setAsOf(p.time, { move: false }));
  timeline.on("click", (p) => {
    if (p.what === "background" || p.what === "axis") setAsOf(p.time);
  });
  timeline.on("select", (p) => {
    const id = p.items[0];
    if (!id) return;
    select(items.get(id).work || id, false);
  });

  // ---------------------------------------------------------------- the record as of the date
  function renderRecord() {
    const known = works.filter((w) => w.when <= asOf);
    const future = works.filter((w) => w.when > asOf);
    const formulas = known.reduce((n, w) => n + w.formulas.length, 0);
    const verified = known.reduce((n, w) => n + w.formulas.filter((f) => f.verified).length, 0);
    const notes = [];
    for (const w of known) {
      const later = new Set(w.formulas.flatMap((f) => f.uses_later_work).filter((x) => byId[x] && byId[x].when > asOf));
      for (const x of later) {
        const n = w.formulas.filter((f) => f.uses_later_work.includes(x)).length;
        notes.push(`<b>${esc(w.name)}</b>: ${n} formula${n > 1 ? "s are" : " is"} recorded in a form first published by ${esc(byId[x].name)} (${esc(byId[x].label)}), after this date. They will be restated from the original once its text is transcribed.`);
      }
      for (const e of w.later) if (new Date(e.start) > asOf && /surviv|revision|version of record/i.test(e.event))
        notes.push(`<b>${esc(w.name)}</b>: ${esc(e.event)} (${esc(e.label)}), after this date.`);
    }
    const next = future[0];
    $("record").innerHTML = `
      <div class="kicker">The record as of</div>
      <h2>${esc(dateLabel(asOf))}</h2>
      <div class="stats">
        <div class="stat"><b>${known.length}<small style="font-size:14px;color:var(--faint)">/${works.length}</small></b><span>works published</span></div>
        <div class="stat"><b>${formulas}</b><span>formulas in the archive</span></div>
        <div class="stat"><b>${verified}</b><span>checked against the source</span></div>
      </div>
      ${known.length ? `<ol class="known">${known.slice().reverse().map((w) => `
        <li class="lane-${w.lane}" data-id="${w.id}" tabindex="0">
          <span class="d">${esc(w.label)}</span>
          <span class="n">${esc(w.name)} <small>${esc(w.title)}</small></span></li>`).join("")}</ol>`
        : `<p class="empty">Nothing in the archive yet: the earliest work is ${esc(works[0].name)}, ${esc(works[0].label)}.</p>`}
      ${next ? `<p class="next">Next: <a href="#${next.id}" data-id="${next.id}">${esc(next.name)}</a>, ${esc(next.label)}.</p>` : `<p class="next">Every work in the archive is published by this date.</p>`}
      ${notes.map((n) => `<div class="note">${n}</div>`).join("")}`;
    for (const el of $("record").querySelectorAll("[data-id]")) {
      el.addEventListener("click", (ev) => { ev.preventDefault(); select(el.dataset.id, true); });
      el.addEventListener("keydown", (ev) => { if (ev.key === "Enter") select(el.dataset.id, true); });
    }
  }

  // ---------------------------------------------------------------- selected work
  let selected = null;
  function select(id, focus) {
    if (!byId[id]) return;
    selected = id;
    timeline.setSelection([id]);
    if (focus) timeline.focus(id, { animation: { duration: 400 } });
    try { history.replaceState(null, "", `#${id}`); } catch (e) { /* sandboxed frames */ }
    renderDetail(id);
  }

  function chipsFor(f) {
    const c = [];
    if (f.equation) c.push(`<span class="chip">eq. ${esc(f.equation)}</span>`);
    if (f.page) c.push(`<span class="chip">p. ${esc(f.page)}</span>`);
    if (f.fidelity) c.push(`<span class="chip">${esc(f.fidelity)}</span>`);
    c.push(f.verified ? `<span class="chip ok">checked against source</span>` : `<span class="chip">not yet checked against source</span>`);
    for (const x of f.uses_later_work) c.push(`<span class="chip warn">uses ${esc(byId[x] ? byId[x].name + " " + byId[x].label : x)}</span>`);
    return c.join("");
  }

  const link = (id) => `<a href="#${id}" data-id="${id}">${esc(byId[id].name)} (${esc(byId[id].label)})</a>`;

  function renderDetail(id) {
    const w = byId[id];
    const lane = lanes[w.lane];
    const rows = [
      ["As of", `${esc(w.label)}: ${esc(w.event)}`],
      w.venue && ["Published", esc(w.venue) + (w.pages ? `, pp. ${esc(w.pages)}` : "")],
      w.doi && ["DOI", `<a href="https://doi.org/${esc(w.doi)}" target="_blank" rel="noopener">${esc(w.doi)}</a>`],
      w.landing && ["Source", `<a href="${esc(w.landing)}" target="_blank" rel="noopener">${esc(w.landing)}</a>`],
      w.access && ["Access", esc(w.access)],
      ["Archive", `<a href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.path)}</a>` +
                  (w.pdf ? ` · <a href="${esc(w.pdf)}" target="_blank" rel="noopener">PDF</a>` : "")],
      ["Transcription", `${esc(w.status)}${w.checks ? ` · ${w.checks} executable checks` : ""}`],
      w.imports.length && ["Builds on", w.imports.map(link).join(", ")],
      w.imported_by.length && ["Built on by", w.imported_by.map(link).join(", ")],
    ].filter(Boolean);
    const later = w.later.map((e) => `<li>${esc(e.label)}: ${esc(e.event)}</li>`).join("");
    $("detail").innerHTML = `
      <div class="kicker">${esc(lane.label)} · ${esc(w.label)}${w.when > asOf ? " · not yet published at the as-of date" : ""}</div>
      <h2>${esc(w.title)}</h2>
      <div>${esc(w.authors.join(", "))}</div>
      <dl class="meta">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
      ${w.role ? `<p class="fn">${esc(w.role)}</p>` : ""}
      ${later ? `<div class="kicker" style="margin-top:12px">Later events</div><ul class="fn">${later}</ul>` : ""}
      ${w.findings.map((f) => `<div class="note"><b>Finding</b>: ${esc(f)}</div>`).join("")}
      <div class="formulas">${w.formulas.length ? w.formulas.map((f) => `
        <div class="formula">
          <div class="fh"><b>${esc(f.name)}</b><span class="fid">${esc(f.id)}</span></div>
          <div class="tex">\\(\\displaystyle ${esc(f.latex)}\\)</div>
          <div class="chips">${chipsFor(f)}</div>
          ${f.notes ? `<div class="fn">${esc(f.notes)}</div>` : ""}
        </div>`).join("") : `<p class="empty">A dated record only: no formulas are transcribed for this work yet.</p>`}</div>`;
    for (const el of $("detail").querySelectorAll("a[data-id]"))
      el.addEventListener("click", (ev) => { ev.preventDefault(); select(el.dataset.id, true); });
    if (window.MathJax && MathJax.typesetPromise)
      MathJax.startup.promise.then(() => MathJax.typesetPromise([$("detail")])).catch(() => {});
  }

  // ---------------------------------------------------------------- controls
  for (const b of document.querySelectorAll("[data-year]")) {
    b.addEventListener("click", () => {
      const v = b.dataset.year;
      const d = v === "today" ? today() : fromYear(Number(v) < 0 ? Number(v) + 1 : Number(v));
      if (v !== "today") d.setUTCMonth(11, 31);
      setAsOf(d);
      timeline.moveTo(d, { animation: { duration: 400 } });
    });
  }
  $("asof-year").addEventListener("change", (ev) => {
    const y = Math.trunc(Number(ev.target.value));
    if (!Number.isFinite(y) || y === 0) return;
    const d = fromYear(y < 0 ? y + 1 : y);
    d.setUTCMonth(11, 31);
    setAsOf(d);
    timeline.moveTo(d, { animation: { duration: 400 } });
  });
  $("zoom-all").addEventListener("click", () => timeline.setWindow(fromYear(-420), fromYear(2060), { animation: { duration: 500 } }));
  $("zoom-modern").addEventListener("click", () => timeline.setWindow(fromYear(1890), fromYear(2031), { animation: { duration: 500 } }));

  // ---------------------------------------------------------------- page text
  $("repo").innerHTML = `<a href="${esc(DATA.repository)}/tree/${esc(DATA.ref)}" target="_blank" rel="noopener">wwmath/wwmath-finance-options</a> · ${esc(DATA.ref)}`;
  $("asof-hint").textContent = "Drag the red line on the timeline, click the timeline background, or choose a year (negative for BC).";
  const unfiled = DATA.unfiled.map((u) => `${esc(u.title)} (${esc(u.reason)})`).join("; ");
  $("footer").innerHTML = `${works.length} works, ${works.reduce((n, w) => n + w.formulas.length, 0)} formulas, generated from the as-of tree by timeline/build.py. ` +
    (unfiled ? `Not yet placed on the timeline: ${unfiled}. ` : "") +
    `Timeline: vis-timeline 8.5.4 (MIT / Apache-2.0). Formulas: MathJax 3.2.2 (Apache-2.0).`;

  setAsOf(today());
  const start = (location.hash || "").slice(1);
  select(byId[start] ? start : "bachelier1900", !!byId[start]);
})();
