# wwmath-finance-options

**World Wide Math: the historical record of the mathematics behind option pricing, from Euclid to today.**

Browse it in the **[WWMath Time Machine](timeline/README.md)**: a vis-timeline view of
every leaf, with an as-of line that replays the record on any date. Live at
**https://wwmath.github.io/wwmath-finance-options/** (GitHub Pages, deployed from `main`
by `.github/workflows/pages.yml`). It is a single self-contained file, so a clone can
also open `timeline/wwmath-time-machine.html` directly, with no web server.

Every work lives in the folder of the date it became public, and each folder
holds the work as it stood on that date. That means the paper's own formulas,
in its own notation, with its own errors, alongside provenance and
period-appropriate implementations. The current, "believed correct today" body
of code is `wwmath/wwm-finance-options`. The `wwmath-*` repos are the
historical record; the `wwm-*` repos are the living implementation.

## The as-of tree

```
<century>/<decade>/<year>/<yyyymm>/<yyyymmdd>/<Name>/      AD: 1900-99/1900-1909/1900/190003/19000329/Bachelier
                                                         BC: 0300-99BC/0300-0309BC/0300BC/0300BC01/0300BC0101/Euclid
    asof.toml       as-of date + precision, the event on that date, later events,
                    bibliographic record, files
    formulas.toml   Math AST library entry (the work's formulas as JSON ASTs in TOML)
    *.pdf           the source, when we hold a copy
```

| as-of | leaf | event | formulas |
|---|---|---|---|
| c. 300 BC | [`0300-99BC/0300-0309BC/0300BC/0300BC01/0300BC0101/Euclid`](0300-99BC/0300-0309BC/0300BC/0300BC01/0300BC0101/Euclid) | *Elements* compiled in Alexandria | I.47 (Pythagoras), IX.35 (geometric progression) and its closed-form sum (restated; text pending) |
| 1202 | [`1200-99/1200-1209/1202/120201/12020101/Fibonacci`](1200-99/1200-1209/1202/120201/12020101/Fibonacci) | *Liber Abaci* completed (the surviving text is the 1228 revision) | the rabbit recurrence, 377 pairs after a year (restated; merchant and interest chapters pending) |
| 1900-03-29 | [`1900-99/1900-1909/1900/190003/19000329/Bachelier`](1900-99/1900-1909/1900/190003/19000329/Bachelier) | thesis defended at the Sorbonne | density, positive expectation, a = k√t (verified, pp. 38, 53) |
| 1976-01 (issue) | [`1900-99/1970-1979/1976/197601/19760101/Black`](1900-99/1970-1979/1976/197601/19760101/Black) | JFE 3(1–2), Jan–Mar 1976 | Black-76 call, put, d1, d2, intrinsic |
| 1993-04 | [`1900-99/1990-1999/1993/199304/19930401/Heston`](1900-99/1990-1999/1993/199304/19930401/Heston) | RFS 6(2) | (1), (4), (5), (10), (11), (12), (17), (18), verified pp. 328–331 |
| 1996-01 | [`1900-99/1990-1999/1996/199601/19960101/Bates`](1900-99/1990-1999/1996/199601/19960101/Bates) | RFS 9(1) | SDEs, jumps, CF, call (CF pending the PDF; see as-of exceptions) |
| 2002-09 | [`2000-99/2000-2009/2002/200209/20020901/Hagan-Kumar-Lesniewski-Woodward`](2000-99/2000-2009/2002/200209/20020901/Hagan-Kumar-Lesniewski-Woodward) | Wilmott | SABR (2.13), (2.17a–c), (2.18) |
| 2007-01 | [`2000-99/2000-2009/2007/200701/20070101/Albrecher-Mayer-Schoutens-Tistaert`](2000-99/2000-2009/2007/200701/20070101/Albrecher-Mayer-Schoutens-Tistaert) | Wilmott | branch-safe Heston CF and call (imports Heston 1993) |
| 2008-01 | [`2000-99/2000-2009/2008/200801/20080101/Schachermayer-Teichmann`](2000-99/2000-2009/2008/200801/20080101/Schachermayer-Teichmann) | Mathematical Finance 18(1) | modern Bachelier call/put (imports Bachelier 1900) |
| 2011-12-24 | [`2000-99/2010-2019/2011/201112/20111224/Andreasen-Huge`](2000-99/2010-2019/2011/201112/20111224/Andreasen-Huge) | SSRN posting | ZABR: model, eikonal, (5)–(9), ODE (verified pp. 3–9) |
| 2014-07-09 | [`2000-99/2010-2019/2014/201407/20140709/Sidani`](2000-99/2010-2019/2014/201407/20140709/Sidani) | SSRN | normal Heston SDEs, derived CF and call (PDF still needed) |
| 2015-11-19 | [`2000-99/2010-2019/2015/201511/20151119/Caspers`](2000-99/2010-2019/2015/201511/20151119/Caspers) | SSRN | record only |
| 2025-03-28 | [`2000-99/2020-2029/2025/202503/20250328/Alos-Bures-Vives`](2000-99/2020-2029/2025/202503/20250328/Alos-Bures-Vives) | arXiv v1 (SIAM version 2026-06-04 recorded as a later event) | model (2.1), (3.1), Theorem 3.2 |

**Rules.**

- **Imports only look back.** A leaf may import definitions only from leaves
  dated on or before it, so a snapshot at any date never sees later mathematics.
  The 2007 little-trap form and the 2008 modern Bachelier formula therefore live
  in their own leaves.
- **Mixed formulas are flagged, not moved.** A formula that can't yet be
  separated from later work carries `uses_later_work` and is reported as an
  as-of exception. Today that's Bates' CF, written in the 2007 form until the
  Bates PDF is transcribed.
- **Precision is recorded.** When only the month, issue, year or an approximate
  (`circa`) date is known, the missing parts are `01` and `asof.toml` says so.
- **BC dates** use a `BC` suffix on each folder and count years as historians do
  (there is no year 0). Chronological order comes from the date, not the folder name.
- **Unverified works stay out of the tree.** A work with an unverified date or
  identity waits in `research/unfiled.toml`.

`python research/tools/validate.py` checks every leaf. That covers structure,
numeric and Monte Carlo checks, SymPy proofs, the FORTRAN 77 build, QuantLib
oracles and the as-of audit.

## Also in this repo

- `research/`: tooling (Math AST, validator, F77 backend, authoring), the model
  taxonomy, QuantLib provenance and the unfiled register. See
  [research/README.md](research/README.md).
- `harness/`: the cross-language WASM conformance harness, lowered from the
  leaves' SDEs. See [harness/README.md](harness/README.md).
- `quantlib-conformance/`: a C++ project testing the 9 QuantLib-implemented
  models against code generated from the leaves. See
  [quantlib-conformance/README.md](quantlib-conformance/README.md).
