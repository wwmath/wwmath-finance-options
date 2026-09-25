# QuantLib conformance (C++)

A C++ test project for the **9 ledger models that QuantLib implements**. It
compares **WWMath C++ generated from the paper ASTs** with the **QuantLib C++
library**, two implementations that share no code.

```
research/papers/*.toml ──(research/tools/cpp.py)──► include/wwmath/generated/formulas.hpp
                                                          │   header-only, std library only
                                                          ▼
                              tests/test_*.cpp  ◄──►  QuantLib (C++, pinned commit 0191ca7)
                                                          │
                              tools/export_fixtures ──►  fixtures/quantlib/*.csv (golden vectors)
```

## The 9 models

| # | Ledger model | WWMath (generated from) | QuantLib | Tolerance |
|---|---|---|---|---|
| 1 | Black-76 lognormal | `black1976.call` / `.put` | `blackFormula` | 1e-12 rel |
| 2 | Bachelier | `bachelier1900.call` / `.put` | `bachelierBlackFormula` | 1e-12 rel |
| 3 | Black-76 shifted | `black1976.call` on (F+d, K+d) | `blackFormula(…, displacement)` | 1e-12 rel |
| 4 | Black-76 intrinsic | `black1976.intrinsic` | `blackFormula` with `stdDev = 0` | 1e-15 |
| 5 | SABR Hagan lognormal | `hagan2002.sigma_B` (2.17), `sigma_ATM` (2.18) | `sabrVolatility` | 1e-12 rel |
| 6 | SABR shifted / normal | (2.17) on shifted inputs; A–H (7) normal vol | `shiftedSabrVolatility`; `ZabrModel(γ=1)`; `unsafeSabrNormalVolatility` | 1e-12 / 1e-10 / see below |
| 7 | Heston | `heston1993.call_trap`, `heston1993.call` | `AnalyticHestonEngine` | 1e-9 rel |
| 8 | Bates | `bates1996.call` | `BatesEngine` | 1e-9 rel |
| 9 | ZABR | `zabr.zabr_y` + ODE `zabr.F`, integrated by RK4 | `ZabrModel::normalVolatility` | 1e-6 rel (QuantLib's RK tolerance is 1e-8) |

Each test prints the worst relative difference it saw, so a run doubles as a
conformance report.

## Latest run

QuantLib master at commit `0191ca7` (1.44-dev), built from source; 21 tests, all passing.

| check | cases | worst difference |
|---|---|---|
| Black-76 call / put vs `blackFormula` | 64 + 64 | 1.7e-14 rel; near-zero prices 3.7e-15 abs |
| Bachelier call / put vs `bachelierBlackFormula` | 92 | 1.7e-14 rel; near-zero 2.4e-15 abs |
| Shifted Black-76 vs `blackFormula(displacement)` | 192 | 5.1e-14 rel |
| Black-76 intrinsic vs `blackFormula(stdDev = 0)` | 64 | exact |
| SABR (2.17) vs `sabrVolatility` | 48 | 1.9e-16 rel |
| SABR (2.18) vs `sabrVolatility` at K = f | 48 | exact |
| SABR shifted vs `shiftedSabrVolatility` | 144 | 3.4e-16 rel |
| SABR normal, A–H (7) vs `ZabrModel(γ = 1)` | 36 | 4.9e-15 rel |
| SABR normal, A–H (7) vs `unsafeSabrNormalVolatility`, K/f within ±5% | 12 | 8.3e-6 rel (different expansions) |
| Heston `call_trap` vs `AnalyticHestonEngine` | 36 | 2.1e-14 rel |
| Heston eq. (17) as printed, T ≤ 1 | 18 | 6.3e-15 rel |
| Bates vs `BatesEngine` | 27 | 2.2e-13 rel |
| ZABR ODE (8) via RK4 vs `ZabrModel::normalVolatility` | 48 | 4.9e-9 rel (QuantLib's RK tolerance) |

**Parameter mappings** (the only hand-written glue, each stated in the test):

- **Bates jumps.** QuantLib's log jump `N(ν, δ²)` maps to `ν = ln(1+k̄*) − δ²/2`, and `q = r − b`.
- **ZABR vol-of-vol.** QuantLib rescales its input to `ν·α^{1−γ}` internally, so the paper's `ε = ν_QL·α^{1−γ}`.
- **Shifts.** A shifted model is the unshifted formula applied to `(F+d, K+d)`.

**Known, pinned discrepancies:**

- **Heston eq. (17) as printed** crosses the complex-log branch cut at τ = 2,
  which moves the price by 0.064. A test asserts the size of that gap. The
  branch-safe form `call_trap` matches everywhere.
- **Normal SABR.** QuantLib's `unsafeSabrNormalVolatility` is a different,
  time-corrected expansion from Andreasen–Huge (7). At T → 0 the two agree to
  within 1e-5 near the money (K/f within ±5%), which is tested. In the wings they
  diverge because A–H integrates σ(u) exactly while QuantLib uses geometric-average
  approximations: the gap reaches 1.2% at K/f = 0.5 or 2 with β = 0 (2.5e-3 at
  β = 0.5, 8.7e-4 at β = 0.7). A separate test pins that gap; it is not a
  conformance check.

## Build and run

Needs a C++17 compiler, CMake ≥ 3.20, Boost headers, GoogleTest (found or
fetched) and QuantLib.

```bash
# with QuantLib installed (e.g. built from the pinned commit into /opt/quantlib)
cmake -S quantlib-conformance -B build/qlc -DCMAKE_PREFIX_PATH=/opt/quantlib
# or let CMake fetch and build QuantLib at the pinned commit (slow the first time)
cmake -S quantlib-conformance -B build/qlc -DWWMATH_FETCH_QUANTLIB=ON

cmake --build build/qlc -j
ctest --test-dir build/qlc --output-on-failure        # or ./build/qlc/conformance_tests
./build/qlc/export_fixtures quantlib-conformance/fixtures/quantlib
```

Regenerate the WWMath side after editing a paper TOML:

```bash
python quantlib-conformance/tools/generate.py
```

## Layout

```
include/wwmath/runtime.hpp              normal CDF/PDF + adaptive Gauss–Kronrod (7,15) integrator
include/wwmath/generated/formulas.hpp   GENERATED: one inline function per paper formula
tests/grids.hpp                         parameter grids shared by tests and fixtures
tests/common.hpp                        QuantLib setup (Heston/Bates engines) + Tracker
tests/test_0N_*.cpp                     one file per model, plus a runtime self-test
tools/generate.py                       paper ASTs -> formulas.hpp
tools/export_fixtures.cpp               QuantLib -> fixtures/quantlib/*.csv
fixtures/quantlib/                      committed golden vectors
```
