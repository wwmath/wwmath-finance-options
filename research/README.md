# research/: authoritative papers → Math AST library

This folder holds the canonical formulas from the source papers for our option
models. Each formula is stored as TOML metadata (citation, symbols, notes),
with the formula itself as a **Math AST in JSON** embedded in the TOML. Every
formula is machine-checked. The first compute backend is **FORTRAN 77**.

```
Paper ──► papers/<id>.toml ──► Math AST (JSON)
                                   │
                  ┌────────────────┼──────────────────┐
                  ▼                ▼                  ▼
            SymPy bridge      LaTeX (Display IR)   Compute IR
            (verify/reduce)   (stored + checked)   └── FORTRAN 77 (gfortran), first backend
```

## The papers: download links

Source PDFs live in `pdfs/`, which the repo now tracks (they were uploaded
through GitHub). If the repository is or becomes public, check each publisher's
terms: Numdam and arXiv allow redistribution; RFS, JFE and SSRN copies may not.
`bibliography.toml` holds the full metadata.

| file in `pdfs/` | paper | status |
|---|---|---|
| `Bachalier_ASENS_1900_3_17__21_0.pdf` | `bachelier1900` | verified |
| `Heston-993.pdf` | `heston1993` | verified |
| `Andreasen-Hudge-ZABR-ssrn-1980726.pdf` | `andreasen2011` (Preliminary Version, Dec 2011) | verified |
| `Alòs-Burés-Vives-2503.22282v1.pdf` | `alos2026` (arXiv v1 preprint) | verified against the preprint |
| `Sidani_2014_1502.02963v2.pdf` | **not Sidani**: Crisóstomo, *An Analysis of the Heston Stochastic Volatility Model: Implementation and Calibration using Matlab*, arXiv:1502.02963 | Sidani's paper is SSRN 2445328 and is still needed |

Still to upload: Black 1976, Bates 1996, Hagan et al. 2002, Sidani 2014 (and
optionally Caspers 2015).

| id | paper | where to get it | access |
|---|---|---|---|
| `bachelier1900` | Bachelier, *Théorie de la spéculation*, Ann. Sci. ÉNS 3e sér. 17 (1900) 21–86 | [PDF (Numdam)](https://www.numdam.org/article/ASENS_1900_3_17__21_0.pdf) · [landing](https://www.numdam.org/item/ASENS_1900_3_17__21_0/) · [EuDML](http://eudml.org/doc/81146) | open, public domain |
| `black1976` | Black, *The pricing of commodity contracts*, JFE 3 (1976) 167–179 | [doi:10.1016/0304-405X(76)90024-6](https://doi.org/10.1016/0304-405X(76)90024-6) | subscription |
| `heston1993` | Heston, *A Closed-Form Solution for Options with Stochastic Volatility…*, RFS 6(2) (1993) 327–343 | [doi:10.1093/rfs/6.2.327](https://doi.org/10.1093/rfs/6.2.327) | subscription |
| `bates1996` | Bates, *Jumps and Stochastic Volatility: Exchange Rate Processes Implicit in Deutsche Mark Options*, RFS 9(1) (1996) 69–107 | [doi:10.1093/rfs/9.1.69](https://doi.org/10.1093/rfs/9.1.69) | subscription |
| `hagan2002` | Hagan, Kumar, Lesniewski & Woodward, *Managing Smile Risk*, Wilmott Magazine, Sep 2002, 84–108 | [ResearchGate](https://www.researchgate.net/publication/235622441_Managing_Smile_Risk) · [Princeton mirror (may be dead)](http://www.princeton.edu/~sircar/sabrall.pdf) | no DOI |
| `andreasen2011` | Andreasen & Huge, *ZABR – Expansions for the Masses* (SSRN, Dec 2011) | [SSRN 1980726](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1980726) | free login |
| `caspers2015` | Caspers, *Implementation of the ZABR Model* (SSRN, Nov 2015): the "ZABR 2015" reference | [SSRN 2692048](https://www.ssrn.com/abstract=2692048) | free login |
| `sidani2014` | Sidani, *A Normal Stochastic Volatility Model* (SSRN, Jul 2014) | [SSRN 2445328](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2445328) | free login |
| `alos2026` | Alòs, Burés & Vives, *Short-Time Behavior of the ATM Implied Volatility for the Jump-Diffusion SV Bachelier Model*, SIAM J. Financial Math. 17(2) (2026) 646–675 | [doi:10.1137/25M1776615](https://doi.org/10.1137/25M1776615) · [arXiv PDF](https://arxiv.org/pdf/2503.22282) · [arXiv abs](https://arxiv.org/abs/2503.22282) | arXiv open |

Supporting references: Albrecher et al. 2007, *The Little Heston Trap* (a
branch-safe Heston CF); Alòs, Burés & Vives 2025, IJTAF
([doi:10.1142/S0219024925500037](https://www.worldscientific.com/doi/10.1142/S0219024925500037)),
the no-jump predecessor of the 2026 paper; Obłój 2008,
[arXiv:0708.0998](https://arxiv.org/abs/0708.0998), a correction to Hagan.

## Why TOML with JSON ASTs inside

* **TOML** holds what people edit and review: the citation, equation number,
  `fidelity`, symbol table, notes and checks.
* **The AST is JSON inside a `'''` literal string.** TOML 1.0 inline tables must
  fit on one line, so a 30-level Heston tree written as native TOML tables would
  be unreadable. JSON in a literal block has no escaping and can be copied
  straight into any tool. It also maps 1:1 to the in-memory AST, the SymPy
  bridge and the compute lowering.
* The validator re-parses every block, so a broken JSON AST fails CI the same
  way a TOML syntax error would.

## Coverage

| paper | status | what's in the TOML |
|---|---|---|
| Bachelier 1900 | **verified** (pp. 38, 53) | his density p(x,t), ∫₀^∞ p x dx = k√t, simple-option value a = k√t; plus a modern normal call/put and ABM SDE |
| Black 1976 | core complete | futures SDE, call, d1, d2, put (via parity) |
| Heston 1993 | **verified** (pp. 328–331) | (1), (4), (5), (10), (11), u_j/a/b_j after (12), (17) with C, D, g, d, (18); plus the Albrecher "little trap" form (not yet verified) |
| Bates 1996 | core complete | jump-diffusion SDE, variance SDE, jump law, Poisson arrivals, CF ψ(u), P_1, P_2, call |
| SABR 2002 | core complete | SDEs (2.13), σ_B (2.17a–c), σ_ATM (2.18) |
| ZABR 2011 | **verified** (pp. 3–9) | model (1), Bachelier g (2), diffusion (eikonal) condition, local vol (5)–(6), SABR case (7), ZABR ODE with A, B, C, F, (9). Two typos in the preliminary version are corrected and noted: α printed for ε, and `+ C` for `+ C f²` |
| Sidani 2014 | **derived, pending PDF** | SDEs, plus a CF and call price **we derived** from the model's affine structure. These still need comparing with Sidani's own closed form |
| Alòs/Burés/Vives 2026 | **verified vs arXiv v1** (pp. 3–6) | model (2.1), martingale condition, c₁, Bac (3.1), vega, v_t/Y_t, implied vol, Theorem 3.2 (3.2)–(3.4) with the Malliavin term |

**Verification.** Entries with `verified_against_pdf = true` were read line by
line against the uploaded PDF, with page and equation numbers. Black 1976,
Bates 1996, Hagan 2002 and Sidani 2014 are still unverified: they are the
standard forms and pass every check, but their equation numbers are from memory.

## What the validator proves

Run `python tools/validate.py`. It needs numpy, scipy, sympy and gfortran.

* **Structure.** Every AST is well formed, every symbol is declared, and the
  stored LaTeX matches the AST.
* **Numeric identities.** Put-call parity; closed forms vs. direct payoff
  integrals; Bachelier's 1900 density vs. his `a = k√t`; Bachelier 1900 vs. the
  modern normal call; Heston's original CF vs. the little-trap form; SABR (2.17)
  → (2.18) as K → f.
* **Cross-paper limits.** Heston with vol-of-vol → 0 gives Black-76. Bates with
  λ\* = 0 gives Heston's eq. (10) to 1e-8. Sidani with ξ → 0 gives Bachelier.
* **Monte Carlo from the SDE ASTs.** The SDE nodes are simulated directly
  (correlated Brownian motions, Poisson jumps, jump sizes solved from the
  `ln(1+k) ~ N` AST with SymPy). The results match every pricing formula within
  4 standard errors.
* **Symbolic proofs (SymPy).** ZABR's SDEs at γ = 1 are exactly SABR's. The SABR
  solution (7) satisfies the eikonal diffusion condition for an *arbitrary*
  σ(s), and its boundary condition. The ZABR ODE at γ = 1 is solved by (7).
  F(y, f) is a root of the ODE's quadratic. The Bachelier vega in Alòs et al.
  is ∂Bac/∂σ.
* **Theorem 3.2, numerically.** With constant σ and Gaussian compound-Poisson
  jumps, the implied Bachelier ATM level → σ (3.2) and skew → c₁/σ (3.3) as
  T → 0.
* **FORTRAN 77.** Every numeric check's formula is lowered AST → fixed-form F77
  → gfortran → run, and must reproduce the Python reference interpreter.
  32 programs are generated; the sources are in `generated/f77/`.

## QuantLib as an independent oracle

`references/quantlib.toml` pins the QuantLib commit (`0191ca7`, 2026-09-25) and
the Python bindings (1.43). It records the C++ file, line and function for each
comparison. Checks with `kind = "oracle"` evaluate our AST formula, and its F77
build, next to the QuantLib function on a grid of cases. QuantLib is only a
test oracle; the ASTs stay sourced from the papers.

| our formula | QuantLib | cases | max rel. diff |
|---|---|---|---|
| `black1976.call` / `.put` | `blackFormula` (`ql/pricingengines/blackformula.cpp:59`) | 9 + 9 | 3e-13 |
| `bachelier1900.call` / `.put` | `bachelierBlackFormula` (`blackformula.cpp:705`) | 6 + 6 | 4e-12 |
| `hagan2002.sigma_B` (2.17) | `unsafeSabrLogNormalVolatility` (`ql/termstructures/volatility/sabr.cpp:37`) | 48 | 9e-16 |
| `heston1993.call_trap` | `AnalyticHestonEngine` | 27 | 3e-11 |
| `heston1993.call` (eq. 17 as printed) | `AnalyticHestonEngine` | 24 | 3e-11 |
| `bates1996.call` | `BatesEngine` (`batesengine.cpp:39`) | 18 | 6e-14 |

**Finding: the "little Heston trap".** Heston's eq. (17) is transcribed
verbatim, and it takes a principal-branch complex log. At κ = 1.5, σ = 0.3,
ρ = −0.7, τ = 2, the log's argument crosses the branch cut near φ ≈ 22. The
printed formula then misprices by up to 0.8% (13.733 vs 13.797 at the money).
`heston1993.call_trap`, which uses the Albrecher et al. (2007) form, matches
QuantLib to 1e-13 there. Use `call_trap` for pricing. The `little-heston-trap-finding`
check pins the size of the discrepancy, so a regression in either form shows up.

The Bates mapping: QuantLib's log jump `J ~ N(ν, δ²)` gives
`ν = ln(1 + k̄*) − δ²/2` in Bates' notation.

The SABR function here is (2.17) as printed, so it is undefined (0/0) at exactly
K = f. QuantLib switches to a series near the money; we keep (2.18) as the
separate ATM formula.

## FORTRAN 77 backend (`tools/f77.py`)

* Each definition becomes one temporary, so shared subexpressions are computed
  once. `Index`/`Apply` definitions (Heston's `_j`, Bates' `ψ(u)`) are
  instantiated at compile time.
* Each `Integral` becomes an `EXTERNAL` integrand `FUNCTION` plus a call to
  `WWQUAD`, a composite 16-point Gauss–Legendre rule with maps for [a,∞) and
  (−∞,∞). Captured values travel through `COMMON`.
* `N`/`n` call `WWNCDF`/`WWNPDF`. `WWNCDF` is Hart's double-precision
  algorithm (West 2005).
* The code is fixed form, with identifiers of 6 characters or fewer, columns
  7–72 and at most 19 continuation lines. Its one extension beyond ANSI F77 is
  `DOUBLE COMPLEX`/`DIMAG`, which the Fourier-based models need. Every F77
  compiler supports it.

## Layout

```
bibliography.toml     paper metadata + download links
papers/<id>.toml      one Math AST library entry per paper
models/taxonomy.toml  models as compositions: underlying × volatility × jumps × correlation
schema/math_ast.md    JSON node reference and TOML entry layout
tools/mathast.py      AST DSL, LaTeX, SymPy bridge, reference interpreter
tools/f77.py          AST → FORTRAN 77 lowering + runtime (WWQUAD, WWNCDF)
tools/validate.py     the checks above; writes generated/validation_report.md
tools/author_papers.py  DSL source used to write papers/*.toml (re-run after edits)
generated/            F77 sources and validation report (regenerated)
pdfs/                 your downloaded PDFs (git-ignored)
```

## Next steps

1. Upload Black 1976, Bates 1996, Hagan 2002 and the real Sidani 2014, then verify them.
2. Sidani: compare our derived CF/price with the paper's closed form.
3. Alòs et al.: compare the arXiv v1 transcription with the SIAM version of record.
