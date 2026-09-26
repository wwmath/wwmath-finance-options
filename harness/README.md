# Cross-Language Heston WASM Conformance Harness

Four Monte Carlo step kernels (normal Heston, Heston, Bates, SABR). Each is
defined once, emitted to six languages and one direct backend.
Each target is compiled to its own WASM module and must reproduce the
reference **bit for bit**.

```
Domain AST   as-of leaves: Sidani 2014, Heston 1993, Bates 1996, Hagan 2002  SDEs
   ↓         Euler full-truncation scheme      research/tools/ir.py
Typed Math IR                                   generated/kernels.ir.json
   ├── C            clang 18 --target=wasm32                     Tier 1
   ├── C++          clang++ 18 --target=wasm32                   Tier 1
   ├── Zig          zig 0.13 wasm32-freestanding                 Tier 1
   ├── Rust         rustc wasm32-unknown-unknown (reference)     Tier 1
   ├── Fortran      flang-new 18 → LLVM IR → LLVM wasm32         Tier 2
   ├── Carbon       source only (no toolchain yet)               Tier 3
   └── direct WASM  binary encoder in research/tools/emitters.py
```

## Kernels

Four kernels, each lowered from its paper's SDE ASTs with an Euler full-truncation
step. Every language module exports all four.

| kernel | from | ABI (then `output_ptr`) | references on the page |
|---|---|---|---|
| `normal_heston_step` | `sidani2014` SDEs | `x, v, dt, kappa, theta, xi, rho, z1, z2` | Sidani Fourier price (derived CF); QuantLib has no normal-Heston engine |
| `heston_step` | `heston1993` (1), (4) | `s, v, dt, r, kappa, theta, sigma, rho, z1, z2` | `albrecher2007.call_trap`, QuantLib `AnalyticHestonEngine` |
| `bates_step` | `bates1996` SDEs + jumps | `s, v, dt, b, lambdastar, kbarstar, alpha, betastar, sigma_v, rho, z1, z2, dj` | `bates1996.call`, QuantLib `BatesEngine` |
| `sabr_step` | `hagan2002` (2.13) | `f, alpha, dt, beta, nu, rho, z1, z2` | Hagan (2.17)/(2.18) → Black-76, QuantLib `sabrVolatility` → `blackFormula` |

The ABI rule is `kernel(states…, dt, params…, randoms…, output_ptr)`, with
`output[i]` = the next value of state *i*. No structs are part of the contract.
The random inputs are sampled by the host:

* `z1, z2` are standard normals. The first drives its Brownian motion alone;
  the second is correlated through ρ by Cholesky.
* `dj` is the compound jump increment `Π(1 + kᵢ) − 1` over the step's Poisson
  jumps, where `ln(1 + k) ~ N(ln(1 + k̄*) − δ²/2, δ²)`. It replaces the mark `k`
  in Bates' `k S dq` term, so the kernel stays pure arithmetic.

The normal-Heston kernel is exactly the one specified originally:

```
v_pos   = max(v, 0)
sqrt_dt = sqrt(dt)
dw_v    = sqrt_dt * z1
dw_x    = sqrt_dt * (rho * z1 + sqrt(1 - rho * rho) * z2)
x_next  = x + sqrt(v_pos) * dw_x
v_next  = v + kappa * (theta - v_pos) * dt + xi * sqrt(v_pos) * dw_v
```

## exp and log are defined in the IR

SABR's `F^β` needs `exp` and `log`. Freestanding WASM has no libm, and each
language's own libm would break bit-identity. So the Typed Math IR has a small
`u64` layer (`bits`, `from_bits`, shifts, `and`/`or`, conversions), and
`exp`/`log` are written once in IR with the fdlibm/musl algorithms. The build
checks that they are within 1 ulp of the platform libm over 20,000 random points
each. `x^p` lowers to `exp(p · log(max(x, 1e-300)))`. Fortran reinterprets bits
with F77 `EQUIVALENCE`, because `TRANSFER` would call the Fortran runtime; the
build rejects any runtime call.

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

The host owns the random numbers (SplitMix64 + Box–Muller normals, Poisson by
inversion, lognormal compound jumps), so all engines see identical inputs. It
drives the Monte Carlo through the ABI only. For the selected kernel, it
reports the next states, elapsed time, the path difference and a per-strike
price table (Max |Δ|). Two reference columns sit alongside: the **WWMath
formula**, evaluated from the paper's AST, and **QuantLib** 1.43, both
precomputed at build time for the default parameters. So the WASM Monte Carlo
is checked against the paper-level formula and against an independent library.

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
