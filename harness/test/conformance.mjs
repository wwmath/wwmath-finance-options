// Headless conformance test (Node >= 18). Checks, without a browser:
//  1. every compiled engine reproduces the Python Typed-Math-IR interpreter bit for bit
//     on the manifest's sample step;
//  2. through the Rust wasm-bindgen host, every engine's Monte Carlo paths are
//     bit-identical to the Rust reference, and prices sit within 4 s.e. + Euler bias of
//     the Fourier (sidani2014.call) price.
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const web = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "web");
const manifest = JSON.parse(await readFile(path.join(web, "manifest.json"), "utf8"));
const { default: init, Harness } = await import(path.join(web, "pkg", "conformance_host.js"));
await init({ module_or_path: await readFile(path.join(web, "pkg", "conformance_host_bg.wasm")) });

let failures = 0;
const fail = (msg) => { failures++; console.log("FAIL", msg); };
const harness = new Harness();
const s = manifest.ir_sample.inputs;
const args = [s.x, s.v, s.dt, s.kappa, s.theta, s.xi, s.rho, s.z1, s.z2];
const bits = (x) => Buffer.from(new Float64Array([x]).buffer).toString("hex");

console.log("engine   bytes  x_next              v_next              vs IR interpreter");
for (const key of manifest.order) {
  const e = manifest.engines[key];
  if (!e.wasm) { console.log(`${key.padEnd(8)} source only (${e.toolchain})`); continue; }
  const { instance } = await WebAssembly.instantiate(await readFile(path.join(web, e.wasm)), {});
  const ex = instance.exports;
  const ptr = ex.memory.grow(1) * 65536;
  ex.normal_heston_step(...args, ptr);
  const out = new Float64Array(ex.memory.buffer, ptr, 2);
  const same = [0, 1].every((i) => bits(out[i]) === bits(manifest.ir_sample.outputs[i]));
  console.log(`${key.padEnd(8)} ${String(e.bytes).padStart(5)}  ${out[0].toPrecision(17)}  ${out[1].toPrecision(17)}  ${same ? "bit-identical" : "DIFFERS"}`);
  if (!same) fail(`${key} sample step differs from the IR interpreter`);
  const again = await WebAssembly.instantiate(await readFile(path.join(web, e.wasm)), {});
  harness.add_engine(key, again.instance.exports);
}

const d = manifest.defaults;
const res = JSON.parse(harness.run(d.x, d.v, d.T, d.kappa, d.theta, d.xi, d.rho, d.paths, d.steps,
  BigInt(d.seed), new Float64Array(d.strikes), manifest.reference));
console.log(`\nMonte Carlo: ${d.paths} paths x ${d.steps} steps, reference = ${res.reference}`);
const eng = res.engines;
console.log("Strike  " + eng.map((e) => e.name.padStart(10)).join("") + "     Max|Δ|   Fourier   s.e.");
const ref = eng.find((e) => e.name === res.reference);
res.strikes.forEach((k, i) => {
  const maxd = Math.max(...eng.map((e) => Math.abs(e.prices[i] - ref.prices[i])));
  const four = manifest.fourier_reference.prices[i];
  console.log(String(k).padEnd(8) + eng.map((e) => e.prices[i].toFixed(4).padStart(10)).join("") +
    maxd.toExponential(1).padStart(11) + four.toFixed(4).padStart(10) + ref.se[i].toFixed(4).padStart(7));
  // Euler (100 steps) + finite-sample: allow 4 s.e. plus 0.02 absolute bias
  if (Math.abs(ref.prices[i] - four) > 4 * ref.se[i] + 0.02) fail(`strike ${k}: MC ${ref.prices[i]} vs Fourier ${four}`);
});
for (const e of eng) {
  console.log(`${e.name.padEnd(8)} elapsed ${e.elapsed_ms.toFixed(1).padStart(7)} ms for ${e.calls} calls, ` +
    `${e.name === res.reference ? "reference" : e.bit_identical ? "bit-identical paths" : "max |Δ| " + e.max_abs_path_diff}`);
  if (!e.bit_identical) fail(`${e.name} paths differ from ${res.reference}`);
}
console.log(failures ? `\n${failures} FAILURE(S)` : "\nOK");
process.exit(failures ? 1 : 0);
