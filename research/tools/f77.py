"""Lower a Math AST formula to a self-contained FORTRAN 77 program.

This is the first Compute IR backend. It follows the Math AST -> Compute IR ->
backend pipeline in miniature:

* each referenced definition becomes one assignment to a temporary (so
  shared subexpressions such as Heston's ``d_j`` are computed once);
* ``Index`` and ``Apply`` definitions are instantiated at lowering time;
* ``Integral`` becomes an EXTERNAL integrand FUNCTION plus a call to the
  runtime quadrature routine ``WWQUAD``;
* ``N``/``n`` lower to runtime routines ``WWNCDF``/``WWNPDF``.

Source is fixed-form with 6-character identifiers, statements in columns
7-72 and at most 19 continuation lines. It uses DOUBLE PRECISION throughout.
Its one departure from ANSI X3.9-1978 is ``DOUBLE COMPLEX`` (with ``DIMAG``),
which every production F77 compiler supports and the Heston/Bates/Sidani
characteristic functions need. Generated programs read inputs X(1..n) from
standard input and print the result.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field

import numpy as np

from mathast import Node, def_key

SPILL = 240  # expressions longer than this are moved into a temporary


@dataclass
class Val:
    expr: str
    cplx: bool


@dataclass
class Unit:
    name: str
    arg: str | None
    decls: dict[str, bool] = field(default_factory=dict)  # name -> is_complex
    stmts: list[str] = field(default_factory=list)
    memo: dict[str, Val] = field(default_factory=dict)
    commons: list[str] = field(default_factory=list)
    externals: list[str] = field(default_factory=list)


def f77_real(v: float) -> str:
    s = repr(float(v))
    if "e" in s:
        mant, ex = s.split("e")
        return f"{mant}D{int(ex)}"
    return s + "D0"


class Lowerer:
    def __init__(self, defs: dict[str, Node], inputs: list[str]):
        self.defs = defs
        self.inputs = {name: i + 1 for i, name in enumerate(inputs)}
        self.units: list[Unit] = []
        self.counter = 0
        self.symbol_map: dict[str, str] = {}

    # -- helpers -----------------------------------------------------------
    def fresh(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}{self.counter:03d}"

    def assign(self, unit: Unit, v: Val, comment: str | None = None) -> Val:
        name = self.fresh("Z" if v.cplx else "R")
        unit.decls[name] = v.cplx
        if comment:
            unit.stmts.append(f"C     {comment}"[:72])
        unit.stmts.append(f"{name} = {v.expr}")
        return Val(name, v.cplx)

    def spill(self, unit: Unit, v: Val) -> Val:
        return self.assign(unit, v) if len(v.expr) > SPILL else v

    # -- definitions -------------------------------------------------------
    def instantiate(self, unit: Unit, key: str, rhs: Node, subst: dict, label: str) -> Val:
        if key in unit.memo:
            return unit.memo[key]
        v = self.assign(unit, self.lower(rhs, unit, subst), label)
        unit.memo[key] = v
        return v

    def find_generic(self, prefix: str) -> tuple[str, list[str]] | None:
        for key in self.defs:
            if key.startswith(prefix) and not key[len(prefix):-1][:1].isdigit():
                return key, key[len(prefix):-1].split(",")
        return None

    # -- expressions -------------------------------------------------------
    def lower(self, node: Node, unit: Unit, subst: dict) -> Val:
        op = node["op"]
        a = node.get("args", [])
        L = lambda n: self.spill(unit, self.lower(n, unit, subst))  # noqa: E731

        if op == "Number":
            return Val(f77_real(node["value"]), False)
        if op == "Constant":
            if node["name"] == "i":
                return Val("(0.0D0,1.0D0)", True)
            if node["name"] == "pi":
                return Val("3.14159265358979324D0", False)
            if node["name"] == "e":
                return Val("2.71828182845904524D0", False)
            raise ValueError("infinity only allowed as an integration bound")
        if op == "Symbol":
            name = node["name"]
            if name in subst:
                return subst[name]
            if name in self.inputs:
                self.symbol_map[f"X({self.inputs[name]})"] = name
                return Val(f"X({self.inputs[name]})", False)
            if name in self.defs:
                return self.instantiate(unit, name, self.defs[name], subst, name)
            raise KeyError(f"unbound symbol {name!r}")
        if op == "Index":
            vals = []
            for i in node["index"]:
                v = self.lower(i, unit, subst)
                vals.append(str(int(float(v.expr.replace("D", "e")))))
            concrete = f"{node['base']}[{','.join(vals)}]"
            if concrete in self.defs:
                return self.instantiate(unit, concrete, self.defs[concrete], subst, concrete)
            gen = self.find_generic(node["base"] + "[")
            if gen is None:
                raise KeyError(f"no definition for {concrete}")
            key, names = gen
            inner = {n: Val(f77_real(float(v)), False) for n, v in zip(names, vals)}
            return self.instantiate(unit, concrete, self.defs[key], {**subst, **inner}, concrete)
        if op == "Apply":
            args = []
            for x in a:
                v = self.lower(x, unit, subst)
                args.append(v if v.expr.isalnum() or v.expr == "XV" else self.assign(unit, v))
            gen = self.find_generic(node["fn"] + "(")
            if gen is None:
                raise KeyError(f"no definition for function {node['fn']}")
            key, names = gen
            inst = f"{node['fn']}({','.join(v.expr for v in args)})"
            return self.instantiate(unit, inst, self.defs[key], {**subst, **dict(zip(names, args))},
                                    inst)

        if op in ("Add", "Mul"):
            vs = [L(x) for x in a]
            sep = " + " if op == "Add" else "*"
            return Val("(" + sep.join(v.expr for v in vs) + ")", any(v.cplx for v in vs))
        if op in ("Sub", "Div"):
            x, y = L(a[0]), L(a[1])
            sep = " - " if op == "Sub" else "/"
            return Val(f"({x.expr}{sep}{y.expr})", x.cplx or y.cplx)
        if op == "Neg":
            x = L(a[0])
            return Val(f"(-{x.expr})", x.cplx)
        if op == "Pow":
            x = L(a[0])
            e = a[1]
            if e["op"] == "Number" and float(e["value"]).is_integer():
                return Val(f"({x.expr}**{int(e['value'])})", x.cplx)
            y = L(e)
            return Val(f"({x.expr}**{y.expr})", x.cplx or y.cplx)
        if op == "Sqrt":
            x = L(a[0])
            return Val(f"SQRT({x.expr})", x.cplx)
        if op == "Abs":
            x = L(a[0])
            return Val(f"ABS({x.expr})", False)
        if op == "Call":
            fn = node["fn"]
            xs = [L(x) for x in a]
            re = lambda v: f"DBLE({v.expr})" if v.cplx else v.expr  # noqa: E731
            if fn in ("exp", "log", "sin", "cos"):
                return Val(f"{fn.upper()}({xs[0].expr})", xs[0].cplx)
            if fn == "arctan":
                return Val(f"ATAN({re(xs[0])})", False)
            if fn == "Re":
                return Val(re(xs[0]), False)
            if fn == "Im":
                return Val(f"DIMAG({xs[0].expr})" if xs[0].cplx else "0.0D0", False)
            if fn in ("max", "min"):
                return Val(f"{fn.upper()}({', '.join(re(v) for v in xs)})", False)
            if fn == "N":
                return Val(f"WWNCDF({re(xs[0])})", False)
            if fn == "n":
                return Val(f"WWNPDF({re(xs[0])})", False)
            raise NotImplementedError(fn)
        if op == "Integral":
            return self.lower_integral(node, unit, subst)
        raise NotImplementedError(f"F77 lowering for {op}")

    def lower_integral(self, node: Node, unit: Unit, subst: dict) -> Val:
        lo, hi = node["lower"], node["upper"]
        inf = lambda n: n["op"] == "Constant" and n["name"] == "inf"  # noqa: E731
        neg_inf = lambda n: n["op"] == "Neg" and inf(n["args"][0])  # noqa: E731
        if inf(hi) and neg_inf(lo):
            mode, a_expr, b_expr = 2, "0.0D0", "0.0D0"
        elif inf(hi):
            mode, a_expr, b_expr = 1, self.lower(lo, unit, subst).expr, "0.0D0"
        else:
            mode = 0
            a_expr = self.lower(lo, unit, subst).expr
            b_expr = self.lower(hi, unit, subst).expr

        fname = self.fresh("WF")
        inner = Unit(fname, "XV")
        # outer bound values the integrand needs travel through a COMMON block
        inner_subst: dict[str, Val] = {node["var"]["name"]: Val("XV", False)}
        for k, v in subst.items():
            if v.expr[:1] in "RZQ" and v.expr.isalnum():
                cname = self.fresh("Q")
                unit.stmts.append(f"{cname} = {v.expr}")
                unit.decls[cname] = v.cplx
                inner.decls[cname] = v.cplx
                unit.commons.append(f"/{fname}C/ {cname}")
                inner.commons.append(f"/{fname}C/ {cname}")
                inner_subst[k] = Val(cname, v.cplx)
            else:
                inner_subst[k] = v
        body = self.lower(node["integrand"], inner, inner_subst)
        inner.stmts.append(f"{fname} = {'DBLE(' + body.expr + ')' if body.cplx else body.expr}")
        self.units.append(inner)
        unit.externals.append(fname)
        return self.assign(unit, Val(f"WWQUAD({fname}, {a_expr}, {b_expr}, {mode})", False),
                           f"integral over {node['var']['name']}")

    # -- emission ----------------------------------------------------------
    def emit_unit(self, u: Unit, header: str) -> list[str]:
        out = [header]
        if u.arg:
            out.append(f"DOUBLE PRECISION {u.arg}")
        out.append("DOUBLE PRECISION X(NIN)")
        out.append("COMMON /WWIN/ X")
        reals = [n for n, c in u.decls.items() if not c]
        cplx = [n for n, c in u.decls.items() if c]
        for i in range(0, len(reals), 8):
            out.append("DOUBLE PRECISION " + ", ".join(reals[i:i + 8]))
        for i in range(0, len(cplx), 8):
            out.append("DOUBLE COMPLEX " + ", ".join(cplx[i:i + 8]))
        commons: dict[str, list[str]] = {}
        for c in u.commons:
            blk, var = c.split(" ", 1)
            commons.setdefault(blk, []).append(var)
        for blk, vars_ in commons.items():
            out.append(f"COMMON {blk} " + ", ".join(vars_))
        out.append("DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD")
        for f in u.externals:
            out.append(f"DOUBLE PRECISION {f}")
            out.append(f"EXTERNAL {f}")
        out += u.stmts
        out += ["RETURN", "END"]
        return out

    def program(self, target: Node, title: str) -> str:
        main = Unit("WWEVAL", None)
        v = self.lower(target, main, {})
        main.stmts.append(f"WWEVAL = {'DBLE(' + v.expr + ')' if v.cplx else v.expr}")
        nin = max(len(self.inputs), 1)
        lines = [f"C     {title}"[:72], "C     Generated from the Math AST by research/tools/f77.py",
                 "C     Inputs (read from standard input in this order):"]
        for name, i in self.inputs.items():
            lines.append(f"C       X({i}) = {name}")
        body = ["PROGRAM WWMAIN", f"INTEGER NIN", f"PARAMETER (NIN = {nin})",
                "DOUBLE PRECISION X(NIN)", "COMMON /WWIN/ X",
                "DOUBLE PRECISION WWEVAL, RES", "EXTERNAL WWEVAL", "INTEGER I",
                "READ (*,*) (X(I), I = 1, NIN)", "RES = WWEVAL()",
                "WRITE (*,'(1X,E25.17)') RES", "END"]
        units = [body, self.with_nin(self.emit_unit(main, "DOUBLE PRECISION FUNCTION WWEVAL()"), nin)]
        for u in self.units:
            units.append(self.with_nin(self.emit_unit(u, f"DOUBLE PRECISION FUNCTION {u.name}(XV)"),
                                       nin))
        for u in units:
            for s in u:
                lines += fixed_form(s)
        return "\n".join(lines) + "\n"

    @staticmethod
    def with_nin(lines: list[str], nin: int) -> list[str]:
        return [lines[0], "INTEGER NIN", f"PARAMETER (NIN = {nin})"] + lines[1:]


def fixed_form(stmt: str) -> list[str]:
    if stmt.startswith("C "):
        return [stmt]
    stmt = stmt.replace(" ", "") if len(stmt) > 66 else stmt
    chunks = [stmt[i:i + 66] for i in range(0, len(stmt), 66)]
    if len(chunks) > 20:
        raise ValueError("statement exceeds 19 continuation lines")
    return ["      " + chunks[0]] + ["     &" + c for c in chunks[1:]]


# ---------------------------------------------------------------------------
# Runtime library (pure F77 + DOUBLE PRECISION)
# ---------------------------------------------------------------------------

def runtime_source(order: int = 16, panels: int = 1024) -> str:
    xs, ws = np.polynomial.legendre.leggauss(order)
    data_x = [f"{x:.17e}".replace("e", "D") for x in xs]
    data_w = [f"{w:.17e}".replace("e", "D") for w in ws]
    lines = [
        "C     wwmath F77 runtime: normal CDF/PDF and quadrature",
        "      DOUBLE PRECISION FUNCTION WWNPDF(X)",
        "      DOUBLE PRECISION X",
        "      WWNPDF = EXP(-0.5D0*X*X)/2.50662827463100050D0",
        "      RETURN",
        "      END",
        "C     Standard normal CDF, Hart (1968) double-precision algorithm",
        "C     as given by G. West, Wilmott Magazine (2005).",
        "      DOUBLE PRECISION FUNCTION WWNCDF(X)",
        "      DOUBLE PRECISION X, XA, E, B, C",
        "      XA = ABS(X)",
        "      IF (XA .GT. 37.0D0) THEN",
        "        C = 0.0D0",
        "      ELSE",
        "        E = EXP(-XA*XA/2.0D0)",
        "        IF (XA .LT. 7.07106781186547D0) THEN",
        "          B = 3.52624965998911D-02*XA + 0.700383064443688D0",
        "          B = B*XA + 6.37396220353165D0",
        "          B = B*XA + 33.912866078383D0",
        "          B = B*XA + 112.079291497871D0",
        "          B = B*XA + 221.213596169931D0",
        "          B = B*XA + 220.206867912376D0",
        "          C = E*B",
        "          B = 8.83883476483184D-02*XA + 1.75566716318264D0",
        "          B = B*XA + 16.064177579207D0",
        "          B = B*XA + 86.7807322029461D0",
        "          B = B*XA + 296.564248779674D0",
        "          B = B*XA + 637.333633378831D0",
        "          B = B*XA + 793.826512519948D0",
        "          B = B*XA + 440.413735824752D0",
        "          C = C/B",
        "        ELSE",
        "          B = XA + 0.65D0",
        "          B = XA + 4.0D0/B",
        "          B = XA + 3.0D0/B",
        "          B = XA + 2.0D0/B",
        "          B = XA + 1.0D0/B",
        "          C = E/B/2.506628274631D0",
        "        END IF",
        "      END IF",
        "      IF (X .GT. 0.0D0) C = 1.0D0 - C",
        "      WWNCDF = C",
        "      RETURN",
        "      END",
        "C     Composite Gauss-Legendre quadrature.",
        "C     MODE 0: [A,B]; MODE 1: [A,inf) via x = A + t/(1-t);",
        "C     MODE 2: (-inf,inf) via x = t/(1-t*t).",
        "      DOUBLE PRECISION FUNCTION WWQUAD(F, A, B, MODE)",
        "      DOUBLE PRECISION F, A, B",
        "      INTEGER MODE",
        "      EXTERNAL F",
        f"      INTEGER NG, NP",
        f"      PARAMETER (NG = {order}, NP = {panels})",
        "      DOUBLE PRECISION GX(NG), GW(NG)",
        "      DOUBLE PRECISION LO, HI, H, C, T, XX, JAC, S, FX",
        "      INTEGER I, K",
    ]
    for name, vals in (("GX", data_x), ("GW", data_w)):
        for i, v in enumerate(vals):
            lines.append(f"      DATA {name}({i + 1}) /{v}/")
    lines += [
        "      IF (MODE .EQ. 0) THEN",
        "        LO = A",
        "        HI = B",
        "      ELSE IF (MODE .EQ. 1) THEN",
        "        LO = 0.0D0",
        "        HI = 1.0D0",
        "      ELSE",
        "        LO = -1.0D0",
        "        HI = 1.0D0",
        "      END IF",
        "      H = (HI - LO)/NP",
        "      S = 0.0D0",
        "      DO 20 K = 1, NP",
        "        C = LO + (K - 0.5D0)*H",
        "        DO 10 I = 1, NG",
        "          T = C + 0.5D0*H*GX(I)",
        "          IF (MODE .EQ. 0) THEN",
        "            XX = T",
        "            JAC = 1.0D0",
        "          ELSE IF (MODE .EQ. 1) THEN",
        "            XX = A + T/(1.0D0 - T)",
        "            JAC = 1.0D0/(1.0D0 - T)**2",
        "          ELSE",
        "            XX = T/(1.0D0 - T*T)",
        "            JAC = (1.0D0 + T*T)/(1.0D0 - T*T)**2",
        "          END IF",
        "          FX = F(XX)",
        "C         Infinite-range integrands decay to zero: treat overflow",
        "C         (NaN or huge values) in the far tail as zero.",
        "          IF (MODE .NE. 0) THEN",
        "            IF (FX .NE. FX .OR. ABS(FX) .GT. 1.0D300) FX = 0.0D0",
        "          END IF",
        "          S = S + 0.5D0*H*GW(I)*JAC*FX",
        "   10   CONTINUE",
        "   20 CONTINUE",
        "      WWQUAD = S",
        "      RETURN",
        "      END",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Build and run
# ---------------------------------------------------------------------------

class F77Program:
    def __init__(self, source: str, inputs: list[str], workdir: str):
        self.source, self.inputs = source, inputs
        os.makedirs(workdir, exist_ok=True)
        self.workdir = workdir
        rt = os.path.join(workdir, "wwrt.f")
        if not os.path.exists(rt):
            with open(rt, "w") as fh:
                fh.write(runtime_source())
        fd, self.src_path = tempfile.mkstemp(suffix=".f", dir=workdir)
        os.close(fd)
        with open(self.src_path, "w") as fh:
            fh.write(source)
        self.exe = self.src_path[:-2]
        subprocess.run(["gfortran", "-std=legacy", "-ffixed-form", "-O2", "-o", self.exe,
                        self.src_path, rt], check=True, capture_output=True, text=True)

    def __call__(self, env: dict[str, float]) -> float:
        data = " ".join(repr(float(env[n])) for n in self.inputs) or "0"
        out = subprocess.run([self.exe], input=data + "\n", capture_output=True, text=True,
                             check=True)
        return float(out.stdout.strip().replace("D", "E"))


def compile_formula(target: Node, defs: dict[str, Node], inputs: list[str], title: str,
                    workdir: str) -> F77Program:
    src = Lowerer(defs, inputs).program(target, title)
    return F77Program(src, inputs, workdir)


def required_inputs(node: Node, defs: dict[str, Node], bound: frozenset[str] = frozenset(),
                    seen: set[str] | None = None) -> list[str]:
    """Undefined free symbols reachable from ``node`` through definitions (stable order)."""
    from mathast import children

    seen = set() if seen is None else seen
    out: list[str] = []

    def add(n):
        if n not in out:
            out.append(n)

    def visit(n: Node, bnd: frozenset[str]):
        op = n["op"]
        if op == "Symbol":
            name = n["name"]
            if name in bnd:
                return
            if name in defs:
                if name not in seen:
                    seen.add(name)
                    visit(defs[name], bnd)
            else:
                add(name)
            return
        if op in ("Index", "Apply"):
            base = n.get("base") or n.get("fn")
            for key, rhs in defs.items():
                if key.startswith(base + ("[" if op == "Index" else "(")) and key not in seen:
                    seen.add(key)
                    params = key[len(base) + 1:-1].split(",")
                    visit(rhs, bnd | frozenset(p for p in params if not p.isdigit()))
        if op == "Integral":
            visit(n["integrand"], bnd | {n["var"]["name"]})
            visit(n["lower"], bnd)
            visit(n["upper"], bnd)
            return
        for c in children(n):
            visit(c, bnd)

    visit(node, bound)
    _ = def_key
    return out
