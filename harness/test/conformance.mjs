// Headless conformance test (Node >= 18), every kernel, no browser:
//  1. each compiled engine reproduces the Python Typed-Math-IR interpreter bit for bit
//     on the manifest's sample step;
//  2. through the Rust wasm-bindgen host, every engine's Monte Carlo paths are
//     bit-identical to the Rust reference; and
//  3. the reference Monte Carlo prices agree with our formula AST and with QuantLib
//     within 4 s.e. + the kernel's Euler/approximation bias allowance.
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const web = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "web");
const manifest = JSON.parse(await readFile(path.join(web, "manifest.json"), "utf8"));
const { default: init, Harness } = await import(path.join(web, "pkg", "conformance_host.js"));
const { runArgs } = await import(path.join(web, "runconfig.js"));
await init({ module_or_path: await readFile(path.join(web, "pkg", "conformance_host_bg.wasm")) });

let failures = 0;
const fail = (msg) => { failures++; console.log("FAIL", msg); };
const bits = (x) => Buffer.from(new Float64Array([x]).buffer).toString("hex");
const harness = new Harness();
const modules = {};
for (const key of manifest.order) {
  const e = manifest.engines[key];
  if (!e.wasm) continue;
  modules[key] = await readFile(path.join(web, e.wasm));
  harness.add_engine(key, (await WebAssembly.instantiate(modules[key], {})).instance.exports);
}
console.log(`IR exp/log max error vs libm: ${JSON.stringify(manifest.ir_exp_log_max_ulp)} ulp`);

for (const k of manifest.kernels) {
  console.log(`\n=== ${k.label}  (${k.name}: ${k.abi.length} x f64 -> ${k.states.length} outputs)`);
  const inputs = k.abi.map((n) => k.ir_sample.inputs[n]);
  const outs = [];
  for (const [key, bytes] of Object.entries(modules)) {
    const { instance } = await WebAssembly.instantiate(bytes, {});
    const ex = instance.exports;
    const ptr = ex.memory.grow(1) * 65536;
    ex[k.name](...inputs, ptr);
    const out = [...new Float64Array(ex.memory.buffer, ptr, k.states.length)];
    const same = out.every((v, i) => bits(v) === bits(k.ir_sample.outputs[i]));
    outs.push(`${key}:${same ? "=" : "≠"}`);
    if (!same) fail(`${k.name}/${key} sample step differs from the IR interpreter: ${out}`);
  }
  console.log(`sample step vs IR interpreter: ${outs.join(" ")}  (= bit-identical)`);

  const d = k.defaults;
  const a = runArgs(k, d);
  const res = JSON.parse(harness.run(k.name, new Float64Array(a.init), new Float64Array(a.params),
    new Uint32Array(a.kinds), new Float64Array(a.jump), d.T, d.paths, d.steps, BigInt(d.seed),
    new Float64Array(d.strikes), a.discount, manifest.reference));
  const eng = res.engines;
  const ref = eng.find((e) => e.name === res.reference);
  const R = k.references;
  console.log("Strike " + eng.map((e) => e.name.padStart(9)).join("") + "   Max|Δ|  formula" +
    (R.quantlib ? " QuantLib" : "") + "   s.e.");
  res.strikes.forEach((K, i) => {
    const maxd = Math.max(...eng.map((e) => Math.abs(e.prices[i] - ref.prices[i])));
    const fp = R.formula.prices[i], qp = R.quantlib?.prices[i];
    console.log(String(K).padEnd(7) + eng.map((e) => e.prices[i].toFixed(4).padStart(9)).join("") +
      maxd.toExponential(0).padStart(9) + fp.toFixed(4).padStart(9) +
      (qp === undefined ? "" : qp.toFixed(4).padStart(9)) + ref.se[i].toFixed(4).padStart(7));
    const tol = 4 * ref.se[i] + k.mc_bias_allowance;
    if (Math.abs(ref.prices[i] - fp) > tol) fail(`${k.name} K=${K}: MC ${ref.prices[i]} vs formula ${fp}`);
    if (qp !== undefined && Math.abs(ref.prices[i] - qp) > tol) fail(`${k.name} K=${K}: MC vs QuantLib ${qp}`);
    if (qp !== undefined && Math.abs(fp - qp) > 1e-7 * Math.max(1, Math.abs(qp)))
      fail(`${k.name} K=${K}: formula ${fp} vs QuantLib ${qp}`);
  });
  console.log(eng.map((e) => `${e.name} ${e.elapsed_ms.toFixed(0)}ms ${e.name === res.reference ? "(ref)" : e.bit_identical ? "✓" : "✗"}`).join("  "));
  for (const e of eng) if (!e.bit_identical) fail(`${k.name}/${e.name} paths differ from ${res.reference}`);
}
console.log(failures ? `\n${failures} FAILURE(S)` : "\nOK");
process.exit(failures ? 1 : 0);
