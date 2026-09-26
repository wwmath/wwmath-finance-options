// Cross-Language Heston WASM Conformance Harness: page logic.
// Instantiates each independently compiled engine module and hands its exports to the
// Rust wasm-bindgen host, which drives the conformance run for the selected kernel.
import init, { Harness } from "./pkg/conformance_host.js";
import { runArgs, formFields } from "./runconfig.js";

const $ = (id) => document.getElementById(id);
const fmt = (x, d = 4) => (x === null || x === undefined ? "—" : Number(x).toFixed(d));
const sci = (x) => (x === 0 ? "0" : Number(x).toExponential(1));
const GREEK = { kappa: "κ", theta: "θ", xi: "ξ", rho: "ρ", sigma: "σ", alpha: "α", beta: "β",
  nu: "ν", delta: "δ", lambdastar: "λ*", kbarstar: "k̄*", betastar: "β*", sigma_v: "σᵥ" };

let manifest, harness, kernel, sources = {};

async function boot() {
  manifest = await (await fetch("manifest.json")).json();
  await init();
  harness = new Harness();
  for (const key of manifest.order) {
    const e = manifest.engines[key];
    sources[key] = await (await fetch(e.source)).text();
    if (!e.wasm) continue;
    const bytes = await (await fetch(e.wasm)).arrayBuffer();
    const { instance } = await WebAssembly.instantiate(bytes, {});
    harness.add_engine(key, instance.exports);
  }
  $("subtitle").textContent =
    `${manifest.kernels.length} kernels lowered from the papers' SDE ASTs, each compiled ` +
    `independently by ${harness.engine_names().length} toolchains into one module per language.`;
  const tabs = $("kernel-tabs");
  for (const k of manifest.kernels) {
    const b = document.createElement("button");
    b.textContent = k.label;
    b.dataset.name = k.name;
    b.setAttribute("role", "tab");
    b.addEventListener("click", () => selectKernel(k.name, true));
    tabs.appendChild(b);
  }
  renderSourceTabs();
  $("run").addEventListener("click", run);
  selectKernel(manifest.kernels[0].name, true);
}

function selectKernel(name, autorun) {
  kernel = manifest.kernels.find((k) => k.name === name);
  for (const b of $("kernel-tabs").children) b.setAttribute("aria-selected", String(b.dataset.name === name));
  const s = kernel.source;
  $("kernel-source").innerHTML = `<code>${kernel.name}(${kernel.abi.join(", ")}, out)</code> — ` +
    `${s.scheme} step of ${s.sde.join(" + ")}`;
  const form = $("params");
  form.innerHTML = formFields(kernel).map((f) =>
    `<label>${GREEK[f] ?? f}<input name="${f}" type="number" step="any" value="${kernel.defaults[f]}"></label>`).join("");
  ["engines", "prices"].forEach((id) => ($(id).innerHTML = ""));
  $("fourier-note").textContent = "";
  $("run").disabled = false;
  if (autorun) run();
}

function params() {
  const f = Object.fromEntries(new FormData($("params")).entries());
  for (const k in f) f[k] = Number(f[k]);
  return f;
}

const label = (k) => manifest.labels[k] ?? k;

function run() {
  const p = params();
  $("run").disabled = true;
  $("status").textContent = `Running ${kernel.label}…`;
  setTimeout(() => {
    const a = runArgs(kernel, p);
    const sampleInputs = kernel.abi.map((n) => (n === "dt" ? p.T / p.steps :
      n in p ? p[n] : kernel.ir_sample.inputs[n]));
    const step = JSON.parse(harness.step_all(kernel.name, new Float64Array(sampleInputs), kernel.states.length));
    const res = JSON.parse(harness.run(kernel.name, new Float64Array(a.init), new Float64Array(a.params),
      new Uint32Array(a.kinds), new Float64Array(a.jump), p.T, p.paths, p.steps, BigInt(p.seed),
      new Float64Array(kernel.defaults.strikes), a.discount, manifest.reference));
    window.__conformance = { kernel: kernel.name, step, res, params: p };
    renderEngines(step, res);
    renderPrices(res, p);
    const others = res.engines.filter((e) => e.name !== res.reference);
    const bad = others.filter((e) => !e.bit_identical);
    $("status").innerHTML = bad.length === 0
      ? `<span class="ok">✔ All ${others.length} engines are bit-identical to the ${label(res.reference)} ` +
        `reference on ${(p.paths * p.steps).toLocaleString()} steps each.</span>`
      : `<span class="bad">✘ Engines disagree: ${bad.map((e) => label(e.name)).join(", ")}</span>`;
    $("run").disabled = false;
  }, 20);
}

function renderEngines(step, res) {
  const byName = Object.fromEntries(res.engines.map((e) => [e.name, e]));
  const cols = manifest.order;
  const row = (name, f) => `<tr><th>${name}</th>${cols.map((k) => `<td>${f(k)}</td>`).join("")}</tr>`;
  const tierName = { 1: "1 · required", 2: "2 · heritage", 3: "3 · experimental", 4: "direct" };
  let html = `<thead><tr><th></th>${cols.map((k) => `<th>${label(k)}</th>`).join("")}</tr></thead><tbody>` +
    row("tier", (k) => `<span class="tier">${tierName[manifest.tiers[k]]}</span>`) +
    row("module", (k) => (manifest.engines[k].wasm ? `${manifest.engines[k].bytes} B` : "—"));
  kernel.states.forEach((s, i) => {
    html += row(`${s}_next`, (k) => (step[k] ? fmt(step[k][i], 10) : i === 0 ? "not compiled" : "—"));
  });
  html += row("elapsed", (k) => (byName[k] ? `${fmt(byName[k].elapsed_ms, 1)} ms` : "—")) +
    row("path diff", (k) =>
      k === res.reference ? `<span class="ref">reference</span>`
        : byName[k] ? `<span class="${byName[k].bit_identical ? "ok" : "bad"}">${byName[k].bit_identical ? "bit-identical" : sci(byName[k].max_abs_path_diff)}</span>`
        : `<span class="warn">source only</span>`);
  $("engines").innerHTML = html + "</tbody>";
}

function renderPrices(res, p) {
  const eng = res.engines;
  const ref = eng.find((e) => e.name === res.reference);
  const d = kernel.defaults;
  const keys = formFields(kernel).filter((f) => !["paths", "steps", "seed"].includes(f));
  const isDefault = keys.every((k) => p[k] === d[k]);
  const R = kernel.references;
  let html = `<thead><tr><th>Strike</th>${eng.map((e) => `<th>${label(e.name)}</th>`).join("")}` +
    `<th>Max |Δ|</th><th>MC s.e.</th><th class="oracle">WWMath formula</th>` +
    (R.quantlib ? `<th>QuantLib</th>` : "") + `</tr></thead><tbody>`;
  res.strikes.forEach((k, i) => {
    const maxd = Math.max(...eng.map((e) => Math.abs(e.prices[i] - ref.prices[i])));
    const fp = isDefault ? R.formula.prices[i] : null;
    const qp = isDefault && R.quantlib ? R.quantlib.prices[i] : null;
    html += `<tr><td>${k}</td>${eng.map((e) => `<td>${fmt(e.prices[i])}</td>`).join("")}` +
      `<td class="${maxd === 0 ? "ok" : "bad"}">${sci(maxd)}</td><td>${fmt(ref.se[i])}</td>` +
      `<td class="oracle">${fmt(fp)}</td>` + (R.quantlib ? `<td>${fmt(qp)}</td>` : "") + `</tr>`;
  });
  $("prices").innerHTML = html + "</tbody>";
  $("fourier-note").innerHTML = isDefault
    ? `WWMath formula: <code>${R.formula.id}</code> (${R.formula.label}), evaluated from the paper's AST. ` +
      (R.quantlib ? `QuantLib: ${R.quantlib.label} (QuantLib 1.43). ` : "QuantLib has no normal-Heston engine. ") +
      `Monte Carlo should agree within a few standard errors plus the Euler bias` +
      (kernel.name === "sabr_step" ? "; both SABR columns are Hagan's asymptotic formula, so they also carry its expansion error." : ".")
    : "Formula and QuantLib prices are precomputed for the default parameters only.";
}

function renderSourceTabs() {
  const tabs = $("tabs");
  for (const key of manifest.order) {
    const b = document.createElement("button");
    b.textContent = label(key);
    b.setAttribute("role", "tab");
    b.dataset.key = key;
    b.addEventListener("click", () => showTab(key));
    tabs.appendChild(b);
  }
  showTab(manifest.order[0]);
}

function showTab(key) {
  for (const b of $("tabs").children) b.setAttribute("aria-selected", String(b.dataset.key === key));
  $("source").textContent = sources[key];
  const e = manifest.engines[key];
  $("toolchain").textContent = `${e.source} · ${e.toolchain}`;
}

boot().catch((err) => {
  $("status").innerHTML = `<span class="bad">Failed to load: ${err}</span>`;
  console.error(err);
});
