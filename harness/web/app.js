// Cross-Language Heston WASM Conformance Harness: page logic.
// Instantiates each independently compiled engine and hands its exports to the
// Rust wasm-bindgen host, which drives the conformance run.
import init, { Harness } from "./pkg/conformance_host.js";

const $ = (id) => document.getElementById(id);
const fmt = (x, d = 4) => (x === null || x === undefined ? "—" : Number(x).toFixed(d));
const sci = (x) => (x === 0 ? "0" : Number(x).toExponential(1));

let manifest, harness, sources = {};

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
  const d = manifest.defaults;
  for (const el of $("params").elements) if (el.name && d[el.name] !== undefined) el.value = d[el.name];
  const src = manifest.source;
  $("subtitle").textContent =
    `Kernel ${manifest.kernel}: ${src.scheme} step of ${src.sde.join(" + ")} (${src.paper}), ` +
    `compiled independently by ${harness.engine_names().length} toolchains.`;
  renderTabs();
  $("run").disabled = false;
  $("run").addEventListener("click", run);
  run();
}

function params() {
  const f = Object.fromEntries(new FormData($("params")).entries());
  for (const k in f) f[k] = Number(f[k]);
  return f;
}

function run() {
  const p = params();
  $("run").disabled = true;
  $("status").textContent = "Running…";
  setTimeout(() => {
    const dt = p.T / p.steps;
    const step = JSON.parse(harness.step_all(p.x, p.v, dt, p.kappa, p.theta, p.xi, p.rho, 0.3, -1.1));
    const res = JSON.parse(harness.run(p.x, p.v, p.T, p.kappa, p.theta, p.xi, p.rho, p.paths,
      p.steps, BigInt(p.seed), new Float64Array(manifest.defaults.strikes), manifest.reference));
    window.__conformance = { step, res, params: p };
    renderEngines(step, res);
    renderPrices(res, p);
    const compiled = res.engines.filter((e) => e.name !== res.reference);
    const allSame = compiled.every((e) => e.bit_identical);
    $("status").innerHTML = allSame
      ? `<span class="ok">✔ All ${compiled.length} engines are bit-identical to the ${label(res.reference)} ` +
        `reference on ${(p.paths * p.steps).toLocaleString()} steps each.</span>`
      : `<span class="bad">✘ Engines disagree: ${compiled.filter((e) => !e.bit_identical).map((e) => label(e.name)).join(", ")}</span>`;
    $("run").disabled = false;
  }, 20);
}

const label = (k) => manifest.labels[k] ?? k;

function renderEngines(step, res) {
  const byName = Object.fromEntries(res.engines.map((e) => [e.name, e]));
  const cols = manifest.order;
  const row = (name, f) => `<tr><th>${name}</th>${cols.map((k) => `<td>${f(k)}</td>`).join("")}</tr>`;
  const tierName = { 1: "1 · required", 2: "2 · heritage", 3: "3 · experimental", 4: "direct" };
  $("engines").innerHTML =
    `<thead><tr><th></th>${cols.map((k) => `<th>${label(k)}</th>`).join("")}</tr></thead><tbody>` +
    row("tier", (k) => `<span class="tier">${tierName[manifest.tiers[k]]}</span>`) +
    row("module", (k) => (manifest.engines[k].wasm ? `${manifest.engines[k].bytes} B` : "—")) +
    row("x_next", (k) => (step[k] ? fmt(step[k][0], 10) : "not compiled")) +
    row("v_next", (k) => (step[k] ? fmt(step[k][1], 10) : "—")) +
    row("elapsed", (k) => (byName[k] ? `${fmt(byName[k].elapsed_ms, 1)} ms` : "—")) +
    row("path diff", (k) =>
      k === res.reference ? `<span class="ref">reference</span>`
        : byName[k] ? `<span class="${byName[k].bit_identical ? "ok" : "bad"}">${byName[k].bit_identical ? "bit-identical" : sci(byName[k].max_abs_path_diff)}</span>`
        : `<span class="warn">source only</span>`) +
    `</tbody>`;
}

function renderPrices(res, p) {
  const eng = res.engines;
  const ref = eng.find((e) => e.name === res.reference);
  const d = manifest.defaults;
  const isDefault = ["x", "v", "T", "kappa", "theta", "xi", "rho"].every((k) => p[k] === d[k]);
  let html = `<thead><tr><th>Strike</th>${eng.map((e) => `<th>${label(e.name)}</th>`).join("")}` +
    `<th>Max |Δ|</th><th>MC s.e.</th><th>Fourier</th></tr></thead><tbody>`;
  res.strikes.forEach((k, i) => {
    const maxd = Math.max(...eng.map((e) => Math.abs(e.prices[i] - ref.prices[i])));
    const four = isDefault ? manifest.fourier_reference.prices[i] : null;
    html += `<tr><td>${k}</td>${eng.map((e) => `<td>${fmt(e.prices[i])}</td>`).join("")}` +
      `<td class="${maxd === 0 ? "ok" : "bad"}">${sci(maxd)}</td><td>${fmt(ref.se[i])}</td>` +
      `<td>${four === null ? "—" : fmt(four)}</td></tr>`;
  });
  $("prices").innerHTML = html + "</tbody>";
  $("fourier-note").textContent = isDefault
    ? "Fourier: the sidani2014.call price (characteristic function derived from the model, " +
      "research/papers/sidani2014.toml) at the default parameters. The Monte Carlo prices should " +
      "agree within a few standard errors plus the Euler discretisation bias."
    : "Fourier reference is precomputed for the default parameters only.";
}

function renderTabs() {
  const tabs = $("tabs");
  tabs.innerHTML = "";
  for (const key of manifest.order) {
    const b = document.createElement("button");
    b.textContent = label(key);
    b.setAttribute("role", "tab");
    b.addEventListener("click", () => showTab(key));
    b.dataset.key = key;
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
