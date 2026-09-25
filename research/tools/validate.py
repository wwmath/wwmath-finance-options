"""Validate the Math AST library in research/papers/*.toml.

For every paper file this checks that:
  1. each `ast` is valid JSON and a well-formed Math AST;
  2. every symbol is declared in [[symbols]] or defined by a formula;
  3. the stored `latex` is exactly what the AST renders to;
  4. closed-form expressions convert to SymPy;
and then runs the [[checks]]:
  value / compare  -- numeric checks with the reference (Python) interpreter,
                      re-run through the FORTRAN 77 backend (AST -> .f -> gfortran);
  monte_carlo      -- simulate the paper's SDE ASTs and compare with its price formula;
  sde_reduction    -- symbolic (SymPy) check that one SDE reduces to another.

Usage: python research/tools/validate.py [--no-f77] [--no-mc] [paper_id ...]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import tempfile
import time
import tomllib

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import f77  # noqa: E402
from mathast import (  # noqa: E402
    Context, NotSymPyRepresentable, check_node, def_key, evaluate, evaluate_real, free_symbols,
    inline, latex, to_sympy,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GEN = os.path.join(ROOT, "generated")


class Paper:
    def __init__(self, path: str):
        with open(path, "rb") as fh:
            self.doc = tomllib.load(fh)
        self.path = path
        self.id = self.doc["paper"]["id"]
        self.symbols = {s["name"]: s for s in self.doc.get("symbols", [])}
        self.formulas = {}
        self.defs: dict[str, dict] = {}
        for f in self.doc.get("formulas", []):
            f = dict(f)
            f["ast"] = json.loads(f["ast"])
            self.formulas[f["id"]] = f
            a = f["ast"]
            if a["op"] in ("Eq", "Approx") and f.get("defines", True):
                key = def_key(a["args"][0])
                if key:
                    self.defs[key] = a["args"][1]
        self.ctx = Context(self.defs)

    def rhs(self, fid: str) -> dict:
        a = self.formulas[fid]["ast"]
        return a["args"][1] if a["op"] in ("Eq", "Approx") else a


class Library:
    def __init__(self):
        self.papers = {p.id: p for p in (Paper(x) for x in
                                         sorted(glob.glob(os.path.join(ROOT, "papers", "*.toml"))))}
        self.formula_owner = {fid: p for p in self.papers.values() for fid in p.formulas}

    def formula(self, fid: str) -> tuple[Paper, dict]:
        p = self.formula_owner[fid]
        return p, p.rhs(fid)


# ---------------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------------

def static_checks(p: Paper) -> list[str]:
    errs = []
    def_bases = {k.split("[")[0].split("(")[0] for k in p.defs}
    known = set(p.symbols) | def_bases
    sympy_ok = 0
    for fid, f in p.formulas.items():
        ast = f["ast"]
        for e in check_node(ast):
            errs.append(f"{fid}: {e}")
        undeclared = free_symbols(ast) - known
        if undeclared:
            errs.append(f"{fid}: undeclared symbols {sorted(undeclared)}")
        if latex(ast) != f["latex"].strip():
            errs.append(f"{fid}: stored latex is out of date with the AST")
        try:
            to_sympy(ast)
            sympy_ok += 1
        except NotSymPyRepresentable:
            pass
    p.sympy_ok = sympy_ok
    return errs


# ---------------------------------------------------------------------------
# Numeric checks
# ---------------------------------------------------------------------------

def parse_ast(s: str) -> dict:
    return json.loads(s)


def build_env(lib: Library, p: Paper, check: dict) -> dict:
    env = dict(check.get("inputs", {}))
    for name, spec in check.get("bind", {}).items():
        if spec.strip().startswith("{"):
            env[name] = float(evaluate_real(parse_ast(spec), env, p.ctx))
        else:
            q, rhs = lib.formula(spec)
            env[name] = float(evaluate_real(rhs, env, q.ctx))
    return env


def side(lib: Library, p: Paper, check: dict, which: str) -> tuple[Paper, dict] | None:
    if which in check:
        return lib.formula(check[which])
    if which + "_ast" in check:
        return p, parse_ast(check[which + "_ast"])
    return None


def close(a: float, b: float, check: dict) -> bool:
    rel, ab = check.get("rel_tol", 0.0), check.get("abs_tol", 0.0)
    return abs(a - b) <= max(ab, rel * max(abs(a), abs(b)))


class F77Runner:
    def __init__(self, enabled: bool, clean: bool = True):
        self.enabled = enabled and shutil.which("gfortran") is not None
        self.build = tempfile.mkdtemp(prefix="wwf77-")
        self.count = 0
        if self.enabled:
            if clean:
                shutil.rmtree(os.path.join(GEN, "f77"), ignore_errors=True)
            os.makedirs(os.path.join(GEN, "f77"), exist_ok=True)
            with open(os.path.join(GEN, "f77", "wwrt.f"), "w") as fh:
                fh.write(f77.runtime_source())

    def run(self, q: Paper, node: dict, env: dict, name: str) -> float:
        """Lower ``node`` (defined in paper ``q``) to F77, build, run; ``name`` is paper/check."""
        inputs = f77.required_inputs(node, q.defs)
        missing = [x for x in inputs if x not in env]
        if missing:
            raise KeyError(f"F77 inputs missing from check: {missing}")
        prog = f77.compile_formula(node, q.defs, inputs, name, self.build)
        dest = os.path.join(GEN, "f77", name.split("/")[0])
        os.makedirs(dest, exist_ok=True)
        shutil.copy(prog.src_path, os.path.join(dest, name.split("/")[-1] + ".f"))
        self.count += 1
        return prog(env)


def run_numeric(lib: Library, p: Paper, check: dict, fr: F77Runner) -> tuple[bool, str]:
    env = build_env(lib, p, check)
    tq, tnode = side(lib, p, check, "target")
    tval = float(evaluate_real(tnode, env, tq.ctx))
    if "expected" in check:
        aval, aside = float(check["expected"]), None
    else:
        aside = side(lib, p, check, "against")
        aval = float(evaluate_real(aside[1], env, aside[0].ctx))
    ok = close(tval, aval, check)
    msg = f"target={tval:.12g} against={aval:.12g}"
    if fr.enabled:
        name = f"{p.id}/{check['id']}"
        ft = fr.run(tq, tnode, env, name + "-target")
        # the F77 build must agree with the reference interpreter to the check's own
        # tolerance (its quadrature is fixed Gauss-Legendre, not adaptive), and never
        # worse than needed: 1e-9 is the floor.
        tol = dict(check, rel_tol=max(check.get("rel_tol", 0.0), 1e-9))
        f_ok = close(ft, tval, tol)
        msg += f" | f77 target={ft:.12g}"
        if aside is not None:
            fa = fr.run(aside[0], aside[1], env, name + "-against")
            f_ok &= close(fa, aval, tol)
            msg += f" against={fa:.12g}"
        msg += " (agrees with reference)" if f_ok else " (MISMATCH vs reference)"
        ok = ok and f_ok and close(ft, fa if aside is not None else aval, check)
    return ok, msg


# ---------------------------------------------------------------------------
# Monte Carlo from SDE ASTs
# ---------------------------------------------------------------------------

def run_monte_carlo(lib: Library, p: Paper, check: dict) -> tuple[bool, str]:
    import sympy as sp

    env0 = build_env(lib, p, check)
    rng = np.random.default_rng(check.get("seed", 0))
    npaths, nsteps = check["paths"], check["steps"]
    horizon = float(env0[check["horizon"]])
    dt = horizon / nsteps
    tsym = check["time"]

    sdes = [lib.formula_owner[s].formulas[s]["ast"] for s in check["sde"]]
    states = [s["state"]["name"] for s in sdes]
    drivers = []
    for s in sdes:
        for t in s["terms"]:
            nm = t["driver"]["name"]
            if nm != tsym and nm not in drivers:
                drivers.append(nm)
    kinds = {nm: p.symbols[nm]["kind"] for nm in drivers}
    bms = [nm for nm in drivers if kinds[nm] == "brownian_motion"]
    pois = [nm for nm in drivers if kinds[nm] == "poisson_process"]

    corr = np.eye(len(bms))
    for cid in check.get("correlation", []):
        c = p.formulas[cid]["ast"]
        a, b = (x["of"]["name"] for x in c["args"][0]["args"])
        rho_node = c["args"][1]["args"][0]
        rho = float(evaluate_real(rho_node, env0, p.ctx))
        i, j = bms.index(a), bms.index(b)
        corr[i, j] = corr[j, i] = rho
    chol = np.linalg.cholesky(corr)

    # random jump sizes: solve  g(k) ~ Normal(m, s2)  for k with SymPy
    samplers = {}
    for jid in check.get("jumps", []):
        dist = p.formulas[jid]["ast"]
        lhs, law = dist["args"]
        rv = [n for n in free_symbols(lhs) if p.symbols.get(n, {}).get("kind") == "random_variable"][0]
        m = float(evaluate_real(law["params"][0], env0, p.ctx))
        s2 = float(evaluate_real(law["params"][1], env0, p.ctx))
        y = sp.Symbol("_y")
        sol = sp.solve(sp.Eq(to_sympy(lhs), y), sp.Symbol(rv))[0]
        fn = sp.lambdify(y, sol, "numpy")
        samplers[rv] = (fn, m, np.sqrt(s2))

    x = {s: np.full(npaths, float(env0[s])) for s in states}
    for _ in range(nsteps):
        z = chol @ rng.standard_normal((len(bms), npaths)) * np.sqrt(dt)
        incr = {nm: z[i] for i, nm in enumerate(bms)}
        for nm in pois:
            lam = float(evaluate_real({"op": "Symbol", "name": p.symbols[nm]["intensity"]}, env0, p.ctx))
            incr[nm] = rng.poisson(lam * dt, npaths).astype(float)
        incr[tsym] = dt
        env = dict(env0)
        for s in states:
            dom = p.symbols[s].get("domain")
            env[s] = np.maximum(x[s], 0.0) if dom in ("nonnegative", "positive") else x[s]
        for rv, (fn, m, sd) in samplers.items():
            env[rv] = fn(rng.normal(m, sd, npaths))
        new = {}
        for s, sde in zip(states, sdes):
            dx = 0.0
            for t in sde["terms"]:
                dx = dx + np.real(evaluate(t["coef"], env, p.ctx)) * incr[t["driver"]["name"]]
            new[s] = x[s] + dx
        x = new
    env = dict(env0)
    env.update(x)
    pay = np.asarray(evaluate_real(parse_ast(check["payoff_ast"]), env, p.ctx), dtype=float)
    mc, se = pay.mean(), pay.std(ddof=1) / np.sqrt(npaths)
    q, rhs = lib.formula(check["against"])
    ref = float(evaluate_real(rhs, env0, q.ctx))
    tol = 4 * se + check.get("abs_tol", 0.0)
    ok = abs(mc - ref) <= tol
    return ok, (f"mc={mc:.6f} +/- {se:.6f} (1 s.e.) formula={ref:.6f} "
                f"|diff|={abs(mc - ref):.6f} tol={tol:.6f}")


# ---------------------------------------------------------------------------
# Symbolic SDE reduction
# ---------------------------------------------------------------------------

def run_sde_reduction(lib: Library, p: Paper, check: dict) -> tuple[bool, str]:
    import sympy as sp

    a = lib.formula_owner[check["target"]].formulas[check["target"]]["ast"]
    b = lib.formula_owner[check["against"]].formulas[check["against"]]["ast"]
    subs = {sp.Symbol(k): v for k, v in check.get("subs", {}).items()}
    ren = check.get("rename", {})
    rs = {sp.Symbol(k): sp.Symbol(v) for k, v in ren.items()}
    name = lambda n: ren.get(n["name"], n["name"])  # noqa: E731
    if name(a["state"]) != b["state"]["name"]:
        return False, "states differ"
    ta = {name(t["driver"]): to_sympy(t["coef"]).subs(subs).subs(rs, simultaneous=True)
          for t in a["terms"]}
    tb = {t["driver"]["name"]: to_sympy(t["coef"]) for t in b["terms"]}
    if set(ta) != set(tb):
        return False, f"drivers differ: {sorted(ta)} vs {sorted(tb)}"
    bad = [k for k in ta if sp.simplify(ta[k] - tb[k]) != 0]
    return (not bad), ("coefficients match" if not bad else f"coefficients differ for {bad}")


# ---------------------------------------------------------------------------
# Symbolic identities (definitions inlined, then SymPy)
# ---------------------------------------------------------------------------

def run_sympy_identity(lib: Library, p: Paper, check: dict) -> tuple[bool, str]:
    import sympy as sp

    abstract = frozenset(check.get("abstract", []))
    sides = []
    for which in ("target", "against"):
        q, node = side(lib, p, check, which)
        sides.append(to_sympy(inline(node, q.defs, abstract)).doit())
    subs = {sp.Symbol(k): (sp.Symbol(v) if isinstance(v, str) else v)
            for k, v in check.get("subs", {}).items()}
    diff = (sides[0] - sides[1]).subs(subs)
    if sp.simplify(diff) == 0:
        return True, "identity holds symbolically"
    # fall back to exact-arithmetic spot checks at random rational points
    rng = np.random.default_rng(7)
    free = sorted(diff.free_symbols, key=str)
    funcs = {f.func for f in diff.atoms(sp.core.function.AppliedUndef)}
    worst = 0.0
    for _ in range(6):
        pt = {x: sp.Rational(int(rng.integers(2, 40)), int(rng.integers(41, 60))) for x in free}
        if sp.Symbol("rho") in pt:
            pt[sp.Symbol("rho")] = -pt[sp.Symbol("rho")]
        e = diff
        for fcls in funcs:
            e = e.replace(fcls, sp.Lambda(sp.Symbol("_w"), 1 + sp.Symbol("_w") ** 2))
        val = complex(sp.N(e.doit().subs(pt), 30))
        worst = max(worst, abs(val))
    ok = worst < 1e-20
    return ok, (f"simplify inconclusive; max |lhs - rhs| at 6 random points = {worst:.1e}"
                + ("" if ok else " (FAILS)"))


# ---------------------------------------------------------------------------
# Short-maturity implied volatility (level and skew at the money)
# ---------------------------------------------------------------------------

def run_implied_vol(lib: Library, p: Paper, check: dict) -> tuple[bool, str]:
    from scipy.optimize import brentq

    env0 = build_env(lib, p, check)
    q, price_rhs = lib.formula(check["price"])
    bac = parse_ast(check["bachelier_ast"])
    vol, kname, atm = check["vol"], check["strike"], check["atm"]
    rows, ok = [], True
    for T in check["maturities"]:
        env = dict(env0, T=T)
        k0 = float(env[atm])
        h = check["bump"] * k0

        def implied(kk):
            e = dict(env, **{kname: kk})
            target = float(evaluate_real(price_rhs, e, q.ctx))
            f = lambda s: float(evaluate_real(bac, dict(e, **{vol: s}), p.ctx)) - target  # noqa
            return brentq(f, 1e-10, 1e4, xtol=1e-14, rtol=1e-14)

        level = implied(k0)
        skew = (implied(k0 + h) - implied(k0 - h)) / (2 * h)
        rows.append((T, level, skew))
    e_level = float(evaluate_real(parse_ast(check["expected_level_ast"]), env0, p.ctx))
    e_skew = float(evaluate_real(parse_ast(check["expected_skew_ast"]), env0, p.ctx))
    T, level, skew = rows[-1]
    ok = close(level, e_level, check) and close(skew, e_skew, check)
    trend = "; ".join(f"T={T:g}: I={lv:.6f} dI/dk={sk:.6f}" for T, lv, sk in rows)
    return ok, f"{trend} | limits: I -> {e_level:.6f}, dI/dk -> {e_skew:.6f}"


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("papers", nargs="*")
    ap.add_argument("--no-f77", action="store_true")
    ap.add_argument("--no-mc", action="store_true")
    args = ap.parse_args()

    lib = Library()
    fr = F77Runner(not args.no_f77, clean=not args.papers)
    failures = 0
    rows = []
    for pid, p in lib.papers.items():
        if args.papers and pid not in args.papers:
            continue
        errs = static_checks(p)
        print(f"\n== {pid}: {len(p.formulas)} formulas, {p.sympy_ok} SymPy-convertible, "
              f"status={p.doc['paper'].get('transcription_status')}")
        for e in errs:
            print("  STATIC FAIL", e)
        failures += len(errs)
        for check in p.doc.get("checks", []):
            kind = check["kind"]
            t0 = time.time()
            try:
                if kind in ("value", "compare"):
                    ok, msg = run_numeric(lib, p, check, fr)
                elif kind == "monte_carlo":
                    if args.no_mc:
                        continue
                    ok, msg = run_monte_carlo(lib, p, check)
                elif kind == "sympy_identity":
                    ok, msg = run_sympy_identity(lib, p, check)
                elif kind == "implied_vol":
                    ok, msg = run_implied_vol(lib, p, check)
                elif kind == "sde_reduction":
                    ok, msg = run_sde_reduction(lib, p, check)
                else:
                    ok, msg = False, f"unknown check kind {kind}"
            except Exception as e:  # report and keep going
                ok, msg = False, f"{type(e).__name__}: {e}"
            failures += not ok
            status = "PASS" if ok else "FAIL"
            print(f"  {status} [{kind}] {check['id']}: {msg} ({time.time() - t0:.1f}s)")
            rows.append((pid, check["id"], kind, status, msg))
    with open(os.path.join(ROOT, "models", "taxonomy.toml"), "rb") as fh:
        tax = tomllib.load(fh)
    for m in tax["models"]:
        for axis in ("underlying", "volatility", "jumps", "correlation"):
            if m[axis] not in tax["axes"][axis]["values"]:
                print(f"  TAXONOMY FAIL {m['id']}: {axis}={m[axis]!r} is not a declared value")
                failures += 1
        for sid in m["sde"]:
            f = lib.formula_owner.get(sid)
            if f is None or f.formulas[sid]["kind"] != "sde":
                print(f"  TAXONOMY FAIL {m['id']}: {sid} is not an SDE formula")
                failures += 1
    print(f"\ntaxonomy: {len(tax['models'])} models checked")
    if fr.enabled:
        print(f"\nF77: compiled and ran {fr.count} generated programs "
              f"(sources in {os.path.relpath(os.path.join(GEN, 'f77'), os.getcwd())})")
    os.makedirs(GEN, exist_ok=True)
    with open(os.path.join(GEN, "validation_report.md"), "w") as fh:
        fh.write("# Validation report\n\nGenerated by `python research/tools/validate.py`.\n\n")
        fh.write("| paper | check | kind | result | detail |\n|---|---|---|---|---|\n")
        for r in rows:
            fh.write("| " + " | ".join(str(x).replace("|", "\\|") for x in r) + " |\n")
    print(f"\n{'OK' if failures == 0 else f'{failures} FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
