"""Typed Math IR: the layer between the Domain (Math) AST and the code emitters.

A kernel is a straight-line function:

    {"name", "params": [{"name", "type"}], "lets": [{"name", "type", "expr"}],
     "stores": [{"index", "name", "expr"}], "source": {...}}

Two value types, and deliberately few *binary* operations:

  f64   const  var  add sub mul div  neg sqrt floor  max  from_bits(u64)  u2f(u64)
  u64   u64(const)  bits(f64)  f2u(f64)  uadd  uand  uor  ushl(amount)  ushr(amount)

Every n-ary sum or product from the Math AST is folded left to right exactly once,
here, and every emitter prints the same tree. With IEEE-754 f64, no FMA contraction
and no libm, every backend executes the same operations in the same order, so the
results are bit-identical, not just close.

`exp` and `log` are not primitives: they are defined once below, in IR, with the
classic fdlibm algorithms (range reduction on the exponent bits plus a minimax
polynomial), so every language inherits the same bits.
"""
from __future__ import annotations

import math
import struct
from typing import Any

from mathast import Node, free_symbols

IR = dict[str, Any]
F64, U64 = "f64", "u64"
MASK = (1 << 64) - 1


def c(v: float) -> IR: return {"op": "const", "value": float(v)}
def u(v: int) -> IR: return {"op": "u64", "value": int(v) & MASK}
def var(n: str) -> IR: return {"op": "var", "name": n}
def bin_(op: str, a: IR, b: IR) -> IR: return {"op": op, "args": [a, b]}
def un(op: str, a: IR) -> IR: return {"op": op, "args": [a]}
def shl(a: IR, n: int) -> IR: return {"op": "ushl", "args": [a], "amount": n}
def shr(a: IR, n: int) -> IR: return {"op": "ushr", "args": [a], "amount": n}


def fold(op: str, items: list[IR]) -> IR:
    out = items[0]
    for x in items[1:]:
        out = bin_(op, out, x)
    return out


RESULT_TYPE = {"const": F64, "add": F64, "sub": F64, "mul": F64, "div": F64, "neg": F64,
               "sqrt": F64, "floor": F64, "max": F64, "from_bits": F64, "u2f": F64,
               "u64": U64, "bits": U64, "f2u": U64, "uadd": U64, "uand": U64, "uor": U64,
               "ushl": U64, "ushr": U64}
ARG_TYPES = {"from_bits": [U64], "u2f": [U64], "bits": [F64], "f2u": [F64],
             "uadd": [U64, U64], "uand": [U64, U64], "uor": [U64, U64], "ushl": [U64],
             "ushr": [U64]}


class Builder:
    """Collects let-bindings; ``let`` returns a var referring to the new binding."""

    def __init__(self):
        self.lets: list[IR] = []
        self.names: set[str] = set()

    def let(self, name: str, expr: IR, typ: str = F64) -> IR:
        base, i = name, 1
        while name in self.names:
            i += 1
            name = f"{base}_{i}"
        self.names.add(name)
        self.lets.append({"name": name, "type": typ, "expr": expr})
        return var(name)


# ---------------------------------------------------------------------------
# exp and log, defined once in IR (fdlibm e_exp.c / musl log.c)
# ---------------------------------------------------------------------------

LN2_HI, LN2_LO, INV_LN2 = 6.93147180369123816490e-01, 1.90821492927058770002e-10, 1.44269504088896338700e+00
EXP_P = [1.66666666666666019037e-01, -2.77777777770155933842e-03, 6.61375632143793436117e-05,
         -1.65339022054652515390e-06, 4.13813679705723846039e-08]
LOG_LG = [6.666666666666735130e-01, 3.999999999940941908e-01, 2.857142874366239149e-01,
          2.222219843214978396e-01, 1.818357216161805012e-01, 1.531383769920937332e-01,
          1.479819860511658591e-01]


def ir_exp(b: Builder, x: IR, tag: str = "exp") -> IR:
    """exp(x) for -708 < x < 709 (normal results). fdlibm: x = k ln2 + r, |r| <= ln2/2."""
    x = b.let(f"{tag}_x", x)
    k = b.let(f"{tag}_k", un("floor", bin_("add", bin_("mul", x, c(INV_LN2)), c(0.5))))
    hi = b.let(f"{tag}_hi", bin_("sub", x, bin_("mul", k, c(LN2_HI))))
    lo = b.let(f"{tag}_lo", bin_("mul", k, c(LN2_LO)))
    r = b.let(f"{tag}_r", bin_("sub", hi, lo))
    t = b.let(f"{tag}_t", bin_("mul", r, r))
    poly = c(EXP_P[4])
    for p in reversed(EXP_P[:4]):
        poly = bin_("add", c(p), bin_("mul", t, poly))
    cc = b.let(f"{tag}_c", bin_("sub", r, bin_("mul", t, poly)))
    y = b.let(f"{tag}_y", bin_("add", c(1.0), bin_("add", bin_("sub", bin_(
        "div", bin_("mul", r, cc), bin_("sub", c(2.0), cc)), lo), hi)))
    scale = b.let(f"{tag}_2k", un("from_bits", shl(un("f2u", bin_("add", k, c(1023.0))), 52)))
    return b.let(f"{tag}_res", bin_("mul", y, scale))


def ir_log(b: Builder, x: IR, tag: str = "log") -> IR:
    """log(x) for positive normal x (musl): reduce x = 2^k (1+f), sqrt(2)/2 < 1+f < sqrt(2)."""
    ix = b.let(f"{tag}_ix", un("bits", x), U64)
    hx = b.let(f"{tag}_hx", bin_("uadd", shr(ix, 32), u(0x3FF00000 - 0x3FE6A09E)), U64)
    k = b.let(f"{tag}_k", bin_("sub", un("u2f", shr(hx, 20)), c(1023.0)))
    hx2 = bin_("uadd", bin_("uand", hx, u(0x000FFFFF)), u(0x3FE6A09E))
    xr = b.let(f"{tag}_m", un("from_bits", bin_("uor", shl(hx2, 32),
                                                bin_("uand", ix, u(0xFFFFFFFF)))))
    f = b.let(f"{tag}_f", bin_("sub", xr, c(1.0)))
    hfsq = b.let(f"{tag}_hfsq", bin_("mul", bin_("mul", c(0.5), f), f))
    s = b.let(f"{tag}_s", bin_("div", f, bin_("add", c(2.0), f)))
    z = b.let(f"{tag}_z", bin_("mul", s, s))
    w = b.let(f"{tag}_w", bin_("mul", z, z))
    t1 = bin_("mul", w, bin_("add", c(LOG_LG[1]), bin_("mul", w, bin_(
        "add", c(LOG_LG[3]), bin_("mul", w, c(LOG_LG[5]))))))
    t2 = bin_("mul", z, bin_("add", c(LOG_LG[0]), bin_("mul", w, bin_("add", c(LOG_LG[2]), bin_(
        "mul", w, bin_("add", c(LOG_LG[4]), bin_("mul", w, c(LOG_LG[6]))))))))
    rr = b.let(f"{tag}_R", bin_("add", t2, t1))
    return b.let(f"{tag}_res", bin_("add", bin_("add", bin_("sub", bin_("add", bin_(
        "mul", s, bin_("add", hfsq, rr)), bin_("mul", k, c(LN2_LO))), hfsq), f),
        bin_("mul", k, c(LN2_HI))))


# ---------------------------------------------------------------------------
# Math AST -> IR expressions
# ---------------------------------------------------------------------------

TINY = 1e-300   # floor for log arguments: x^p -> exp(p log(max(x, TINY)))


def lower_expr(node: Node, names: dict[str, IR], b: Builder) -> IR:
    """Lower a real-valued Math AST expression. ``names`` maps AST symbols to IR."""
    op = node["op"]
    a = node.get("args", [])
    L = lambda n: lower_expr(n, names, b)  # noqa: E731
    if op == "Number":
        return c(node["value"])
    if op == "Symbol":
        if node["name"] not in names:
            raise KeyError(f"symbol {node['name']!r} has no IR binding")
        return names[node["name"]]
    if op == "Add":
        return fold("add", [L(x) for x in a])
    if op == "Mul":
        return fold("mul", [L(x) for x in a])
    if op in ("Sub", "Div"):
        return bin_(op.lower(), L(a[0]), L(a[1]))
    if op == "Neg":
        return un("neg", L(a[0]))
    if op == "Sqrt":
        return un("sqrt", L(a[0]))
    if op == "Pow":
        e = a[1]
        if e["op"] == "Number" and float(e["value"]).is_integer() and 1 <= e["value"] <= 4:
            base = L(a[0])
            return fold("mul", [base] * int(e["value"]))
        if e["op"] == "Number" and e["value"] == 0.5:
            return un("sqrt", L(a[0]))
        # general power of a nonnegative base: exp(p * log(max(x, TINY)))
        lg = ir_log(b, bin_("max", L(a[0]), c(TINY)), "pow_log")
        return ir_exp(b, bin_("mul", L(e), lg), "pow")
    if op == "Call" and node["fn"] == "max":
        return bin_("max", L(a[0]), L(a[1]))
    if op == "Call" and node["fn"] == "exp":
        return ir_exp(b, L(a[0]))
    if op == "Call" and node["fn"] == "log":
        return ir_log(b, L(a[0]))
    raise NotImplementedError(f"{op} is not in the real straight-line IR subset")


# ---------------------------------------------------------------------------
# SDE system -> one Euler step (full truncation)
# ---------------------------------------------------------------------------

def euler_full_truncation(spec: dict, paper) -> IR:
    """One explicit Euler step of an SDE system, as a Typed Math IR kernel.

    ABI: states..., dt, params..., randoms..., output  (output[i] = next state i).

    * states whose declared domain is nonnegative/positive are floored at zero inside
      every coefficient (full truncation, Lord-Koekkoek-van Dijk 2010); the state itself
      is advanced from its un-floored value;
    * Brownian increments come from independent normals by Cholesky:
      dB_1 = sqrt(dt) z_1,  dB_2 = sqrt(dt) (rho z_1 + sqrt(1 - rho^2) z_2);
    * a Poisson-driven term  (mark * coef) dq  becomes  coef * dJ,  where the host samples
      the compound jump increment dJ (e.g. prod(1 + k_i) - 1 over the step's jumps).
    """
    sdes = [paper.formulas[s]["ast"] for s in spec["sde"]]
    states = [s["state"]["name"] for s in sdes]
    rename = spec.get("rename", {})
    ren = lambda n: rename.get(n, n)  # noqa: E731
    randoms = spec["randoms"]
    b = Builder()
    abi = [ren(s) for s in states] + ["dt"] + spec["params"] + [r["name"] for r in randoms]
    b.names |= set(abi)

    names: dict[str, IR] = {p: var(p) for p in abi}
    for orig, new in rename.items():
        names[orig] = var(new)
    coef_names = dict(names)
    for s in states:
        if paper.symbols[s].get("domain") in ("nonnegative", "positive"):
            coef_names[s] = b.let(f"{ren(s)}_pos", bin_("max", var(ren(s)), c(0.0)))

    sqrt_dt = b.let("sqrt_dt", un("sqrt", var("dt")))
    driven_by: dict[str, str] = {}
    for sde, st in zip(sdes, states):
        for t in sde["terms"]:
            driven_by.setdefault(t["driver"]["name"], ren(st))

    incr: dict[str, IR | None] = {}
    rho_node = pair = None
    if spec.get("correlation"):
        cst = paper.formulas[spec["correlation"]]["ast"]
        pair = {x["of"]["name"] for x in cst["args"][0]["args"]}
        rho_node = cst["args"][1]["args"][0]
    normals = [r for r in randoms if r["kind"] == "normal"]
    for i, r in enumerate(normals):
        bm = r["drives"]
        if i == 0:
            e = bin_("mul", sqrt_dt, var(r["name"]))
        else:
            assert pair == {normals[0]["drives"], bm}, "correlation must pair the two BMs"
            rho = lower_expr(rho_node, names, b)
            e = bin_("mul", sqrt_dt, bin_(
                "add", bin_("mul", rho, var(normals[0]["name"])),
                bin_("mul", un("sqrt", bin_("sub", c(1.0), bin_("mul", rho, rho))),
                     var(r["name"]))))
        incr[bm] = b.let(f"dw_{driven_by[bm]}", e)
    jump_marks: dict[str, str] = {}
    for r in randoms:
        if r["kind"] == "compound_jump":
            incr[r["drives"]] = None              # the increment is folded into the mark
            jump_marks[r["mark"]] = r["name"]
    for tname, sym_ in paper.symbols.items():
        if sym_["kind"] == "time":
            incr[tname] = var("dt")

    stores = []
    for idx, (sde, st) in enumerate(zip(sdes, states)):
        terms = [var(ren(st))]
        for t in sde["terms"]:
            drv = t["driver"]["name"]
            if incr[drv] is None:                 # jump: replace the mark by dJ
                cn = dict(coef_names)
                for mark, rname in jump_marks.items():
                    cn[mark] = var(rname)
                terms.append(lower_expr(t["coef"], cn, b))
            else:
                terms.append(bin_("mul", lower_expr(t["coef"], coef_names, b), incr[drv]))
        stores.append({"index": idx, "name": f"{ren(st)}_next", "expr": fold("add", terms)})

    kernel = {"name": spec["name"],
              "params": [{"name": p, "type": F64} for p in abi] + [{"name": "output",
                                                                     "type": "ptr_f64"}],
              "lets": b.lets, "stores": stores,
              "source": {"paper": paper.id, "sde": spec["sde"],
                         "correlation": spec.get("correlation"),
                         "scheme": "euler-full-truncation"}}
    typecheck(kernel)
    return kernel


# ---------------------------------------------------------------------------
# Type checking and the reference interpreter
# ---------------------------------------------------------------------------

def ir_vars(e: IR) -> set[str]:
    if e["op"] == "var":
        return {e["name"]}
    out: set[str] = set()
    for a in e.get("args", []):
        out |= ir_vars(a)
    return out


def type_of(e: IR, scope: dict[str, str]) -> str:
    op = e["op"]
    if op == "var":
        if e["name"] not in scope:
            raise TypeError(f"unbound {e['name']}")
        return scope[e["name"]]
    args = [type_of(a, scope) for a in e.get("args", [])]
    want = ARG_TYPES.get(op, [F64] * len(args))
    if args != want:
        raise TypeError(f"{op} expects {want}, got {args}")
    return RESULT_TYPE[op]


def typecheck(k: IR) -> None:
    scope = {p["name"]: p["type"] for p in k["params"] if p["type"] in (F64, U64)}
    for let in k["lets"]:
        t = type_of(let["expr"], scope)
        if t != let["type"]:
            raise TypeError(f"let {let['name']}: declared {let['type']}, inferred {t}")
        scope[let["name"]] = t
    for st in k["stores"]:
        if type_of(st["expr"], scope) != F64:
            raise TypeError(f"store {st['index']} is not f64")


def _f2b(x: float) -> int: return struct.unpack("<Q", struct.pack("<d", x))[0]
def _b2f(n: int) -> float: return struct.unpack("<d", struct.pack("<Q", n & MASK))[0]


def eval_expr(e: IR, env: dict[str, Any]):
    op = e["op"]
    if op in ("const", "u64"):
        return e["value"]
    if op == "var":
        return env[e["name"]]
    x = [eval_expr(a, env) for a in e.get("args", [])]
    if op == "add": return x[0] + x[1]
    if op == "sub": return x[0] - x[1]
    if op == "mul": return x[0] * x[1]
    if op == "div": return x[0] / x[1]
    if op == "neg": return -x[0]
    if op == "sqrt": return math.sqrt(x[0])
    if op == "floor": return float(math.floor(x[0]))
    if op == "max": return x[0] if x[0] > x[1] else x[1]
    if op == "from_bits": return _b2f(x[0])
    if op == "u2f": return float(x[0])
    if op == "bits": return _f2b(x[0])
    if op == "f2u": return int(x[0]) & MASK
    if op == "uadd": return (x[0] + x[1]) & MASK
    if op == "uand": return x[0] & x[1]
    if op == "uor": return x[0] | x[1]
    if op == "ushl": return (x[0] << e["amount"]) & MASK
    if op == "ushr": return x[0] >> e["amount"]
    raise NotImplementedError(op)


def run(k: IR, args: dict[str, float]) -> list[float]:
    env = dict(args)
    for let in k["lets"]:
        env[let["name"]] = eval_expr(let["expr"], env)
    return [eval_expr(s["expr"], env) for s in k["stores"]]


def used_params(k: IR) -> set[str]:
    out: set[str] = set()
    for x in k["lets"] + k["stores"]:
        out |= ir_vars(x["expr"])
    return out


def ulp_check(n: int = 20000, seed: int = 1) -> dict[str, float]:
    """Max error of the IR exp/log against the platform libm, in ulps."""
    import random
    rnd = random.Random(seed)
    out = {}
    for name, build, ref, sampler in (
            ("exp", ir_exp, math.exp, lambda: rnd.uniform(-700.0, 700.0)),
            ("log", ir_log, math.log, lambda: math.exp(rnd.uniform(-690.0, 700.0)))):
        b = Builder()
        res = build(b, var("x"))
        k = {"lets": b.lets, "stores": [{"index": 0, "expr": res}],
             "params": [{"name": "x", "type": F64}]}
        worst = 0.0
        for _ in range(n):
            x = sampler()
            got, want = run(k, {"x": x})[0], ref(x)
            worst = max(worst, abs(got - want) / math.ulp(want))
        out[name] = worst
    return out


__all__ = ["Builder", "euler_full_truncation", "ir_exp", "ir_log", "lower_expr", "run",
           "typecheck", "ulp_check", "used_params", "free_symbols"]
