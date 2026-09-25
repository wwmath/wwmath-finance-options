# Cross-Language Heston WASM Conformance Harness

One kernel, defined once, emitted to six languages and one direct backend.
Each target is compiled to its own WASM module and must reproduce the
reference **bit for bit**.

```
Domain AST   research/papers/sidani2014.toml  (forward_sde, variance_sde, correlation)
   ↓         Euler full-truncation scheme      research/tools/ir.py
Typed Math IR                                   generated/kernel.ir.json
   ├── C            clang 18 --target=wasm32                     Tier 1
   ├── C++          clang++ 18 --target=wasm32                   Tier 1
   ├── Zig          zig 0.13 wasm32-freestanding                 Tier 1
   ├── Rust         rustc wasm32-unknown-unknown (reference)     Tier 1
   ├── Fortran      flang-new 18 → LLVM IR → LLVM wasm32         Tier 2
   ├── Carbon       source only (no toolchain yet)               Tier 3
   └── direct WASM  binary encoder in research/tools/emitters.py
```

## The ABI

The same flat ABI for every language. No structs are part of the contract.

```
normal_heston_step(x, v, dt, kappa, theta, xi, rho, z1, z2, output_ptr)
output[0] = x_next
output[1] = v_next
```

The kernel is one Euler full-truncation step of Sidani's normal-Heston SDEs:

```
v_pos   = max(v, 0)
sqrt_dt = sqrt(dt)
dw_v    = sqrt_dt * z1
dw_x    = sqrt_dt * (rho * z1 + sqrt(1 - rho * rho) * z2)
x_next  = x + sqrt(v_pos) * dw_x
v_next  = v + kappa * (theta - v_pos) * dt + xi * sqrt(v_pos) * dw_v
```

## Why the results are bit-identical, not just close

The IR contains only binary operations, so every n-ary sum or product is
folded once, left to right, before any emitter runs. Each emitter prints the
same fully parenthesised tree. Every build uses `-ffp-contract=off`, and wasm32
has no fused multiply-add, so every engine performs exactly the same IEEE-754
operations in the same order. Any difference would be a real bug.

## Browser architecture

```
index.html + app.js
    ↓  fetch + WebAssembly.instantiate each engine
Rust host (wasm-bindgen, host/src/lib.rs)
    ├── C module        ├── Zig module
    ├── C++ module      ├── Rust module (reference)
    ├── Fortran module  └── direct WASM module
```

The host owns the random numbers (SplitMix64 + Box–Muller), so all engines see
identical inputs. It drives the Monte Carlo through the ABI only. It then
reports x_next/v_next, elapsed time, the path difference and a per-strike
price table (Max |Δ|). The page also shows the `sidani2014.call` Fourier price
for the defaults, so the WASM Monte Carlo is checked against the paper-level
formula too.

## Build, test, view

```bash
python harness/build.py                 # emit, compile 6 engines, build the host
node harness/test/conformance.mjs       # headless: vs IR interpreter + host MC
(cd harness/test && npm install && node browser.mjs)   # real page in headless Chromium
python3 -m http.server -d harness/web 8000   # then open http://localhost:8000
```

Toolchain: clang/lld 18, flang-new-18, zig 0.13 (`pip install ziglang==0.13.0`),
rustc with `wasm32-unknown-unknown`, `wasm-bindgen-cli 0.2.100`, wabt.

## Notes on specific backends

* **Fortran.** flang 18 has no wasm32 code generator (LFortran's WASM backend
  dropped the kernel), so `build.py` uses flang's front end to produce LLVM IR
  and lowers that IR with LLVM's wasm32 back end. This is sound only because
  the kernel is scalar straight-line code with no Fortran runtime calls. The
  build asserts that and fails otherwise. The numerics are F77; `BIND(C)` and
  `VALUE` are used only to pin the ABI.
* **C++.** Built without a libc++ sysroot, so `std::sqrt` is written
  `__builtin_sqrt`; clang lowers both to `f64.sqrt`.
* **Carbon.** Emitted from the same IR (the same semantic subset), but not
  compiled: there is no stable Carbon toolchain or WASM target yet. The page
  shows the source and marks the column "source only".
* **Direct WASM.** Encoded straight from the IR to a 173-byte module, with no
  compiler involved. The WAT text is emitted alongside and checked by `wat2wasm`.
* Every engine module is checked for no imports, the exact signature
  `(f64 × 9, i32) → ()`, and an exported `memory`.
