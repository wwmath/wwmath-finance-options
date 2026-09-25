"""Typed Math IR: the layer between the Domain (Math) AST and the code emitters.

A kernel is a straight-line function over f64 scalars:

    {"name": ..., "params": [{"name", "type"}], "lets": [{"name", "type", "expr"}],
     "stores": [{"index", "name", "expr"}]}

IR expressions are deliberately tiny and *binary*:

    {"op": "const", "value": 1.0}          {"op": "var", "name": "x"}
    {"op": "add" | "sub" | "mul" | "div", "args": [a, b]}
    {"op": "neg" | "sqrt", "args": [a]}    {"op": "max", "args": [a, b]}

Every n-ary sum/product from the Math AST is folded left to right here, once, so
each emitter prints the same operations in the same order. With IEEE-754 f64
and no FMA contraction this makes every backend bit-identical, not just close.
"""
from __future__ import annotations

import math
from typing import Any

from mathast import Node, free_symbols

IR = dict[str, Any]
F64 = "f64"


def c(v: float) -> IR: return {"op": "const", "value": float(v)}
def var(n: str) -> IR: return {"op": "var", "name": n}
def bin_(op: str, a: IR, b: IR) -> IR: return {"op": op, "args": [a, b]}
def un(op: str, a: IR) -> IR: return {"op": op, "args": [a]}


def fold(op: str, items: list[IR]) -> IR:
    out = items[0]
    for x in items[1:]:
        out = bin_(op, out, x)
    return out


# ---------------------------------------------------------------------------
# Math AST -> IR expressions
# ---------------------------------------------------------------------------

def lower_expr(node: Node, names: dict[str, IR]) -> IR:
    """Lower a real-valued Math AST expression. ``names`` maps AST symbols to IR."""
    op = node["op"]
    a = node.get("args", [])
    L = lambda n: lower_expr(n, names)  # noqa: E731
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
        raise NotImplementedError("Pow with non-small-integer exponent is not in the IR subset")
    if op == "Call" and node["fn"] == "max":
        return bin_("max", L(a[0]), L(a[1]))
    raise NotImplementedError(f"{op} is not in the real straight-line IR subset")


# ---------------------------------------------------------------------------
# SDE system -> one Euler step (full truncation)
# ---------------------------------------------------------------------------

def euler_full_truncation(name: str, paper, sde_ids: list[str], corr_id: str | None,
                          abi_params: list[str], rename: dict[str, str],
                          brownian: list[dict], outputs: list[str]) -> IR:
    """One explicit Euler step of an SDE system, as a Typed Math IR kernel.

    * states whose declared domain is nonnegative/positive are floored at zero inside
      every coefficient (full truncation, Lord-Koekkoek-van Dijk 2010), but the state
      itself is advanced from its un-floored value;
    * Brownian increments are built from independent normals by Cholesky:
      dB_1 = sqrt(dt) z_1,  dB_2 = sqrt(dt) (rho z_1 + sqrt(1 - rho^2) z_2).
    """
    sdes = [paper.formulas[s]["ast"] for s in sde_ids]
    states = [s["state"]["name"] for s in sdes]
    ren = lambda n: rename.get(n, n)  # noqa: E731
    lets: list[IR] = []
    names: dict[str, IR] = {}

    # parameters: every symbol that is not a driver, bound by its ABI name
    for p in abi_params:
        names[p] = var(p)
    for orig, new in rename.items():
        names[orig] = var(new)

    # full truncation
    coef_names = dict(names)
    for s in states:
        if paper.symbols[s].get("domain") in ("nonnegative", "positive"):
            nm = f"{ren(s)}_pos"
            lets.append({"name": nm, "type": F64, "expr": bin_("max", var(ren(s)), c(0.0))})
            coef_names[s] = var(nm)

    lets.append({"name": "sqrt_dt", "type": F64, "expr": un("sqrt", var("dt"))})

    # correlated Brownian increments
    rho_node = None
    if corr_id:
        cst = paper.formulas[corr_id]["ast"]
        pair = [x["of"]["name"] for x in cst["args"][0]["args"]]
        rho_node = cst["args"][1]["args"][0]
    driven_by = {}
    for sde, st in zip(sdes, states):
        for t in sde["terms"]:
            driven_by.setdefault(t["driver"]["name"], ren(st))
    incr: dict[str, IR] = {}
    for i, b in enumerate(brownian):
        nm = f"dw_{driven_by[b['name']]}"
        if i == 0:
            e = bin_("mul", var("sqrt_dt"), var(b["normal"]))
        else:
            assert corr_id and set(pair) == {brownian[0]["name"], b["name"]}
            rho = lower_expr(rho_node, names)
            e = bin_("mul", var("sqrt_dt"), bin_(
                "add", bin_("mul", rho, var(brownian[0]["normal"])),
                bin_("mul", un("sqrt", bin_("sub", c(1.0), bin_("mul", rho, rho))),
                     var(b["normal"]))))
        lets.append({"name": nm, "type": F64, "expr": e})
        incr[b["name"]] = var(nm)
    time_sym = [s for s, sym_ in paper.symbols.items() if sym_["kind"] == "time"]
    for tname in time_sym:
        incr[tname] = var("dt")

    stores = []
    for idx, (sde, st) in enumerate(zip(sdes, states)):
        terms = [var(ren(st))]
        for t in sde["terms"]:
            coef = lower_expr(t["coef"], coef_names)
            terms.append(bin_("mul", coef, incr[t["driver"]["name"]]))
        stores.append({"index": idx, "name": outputs[idx], "expr": fold("add", terms)})

    kernel = {"name": name,
              "params": [{"name": p, "type": F64} for p in abi_params] +
                        [{"name": "output", "type": "ptr_f64"}],
              "lets": lets, "stores": stores,
              "source": {"paper": paper.id, "sde": sde_ids, "correlation": corr_id,
                         "scheme": "euler-full-truncation"}}
    typecheck(kernel)
    return kernel


# ---------------------------------------------------------------------------
# Checks and a reference interpreter
# ---------------------------------------------------------------------------

def ir_vars(e: IR) -> set[str]:
    if e["op"] == "var":
        return {e["name"]}
    return set().union(*(ir_vars(a) for a in e.get("args", []))) if e.get("args") else set()


def typecheck(k: IR) -> None:
    scope = {p["name"]: p["type"] for p in k["params"]}
    for let in k["lets"]:
        missing = ir_vars(let["expr"]) - {n for n, t in scope.items() if t == F64}
        if missing:
            raise TypeError(f"let {let['name']}: unbound or non-f64 {sorted(missing)}")
        scope[let["name"]] = let["type"]
    for st in k["stores"]:
        missing = ir_vars(st["expr"]) - {n for n, t in scope.items() if t == F64}
        if missing:
            raise TypeError(f"store {st['index']}: unbound {sorted(missing)}")


def run(k: IR, args: dict[str, float]) -> list[float]:
    env = dict(args)

    def ev(e: IR) -> float:
        op = e["op"]
        if op == "const":
            return e["value"]
        if op == "var":
            return env[e["name"]]
        x = [ev(a) for a in e["args"]]
        return {"add": lambda: x[0] + x[1], "sub": lambda: x[0] - x[1],
                "mul": lambda: x[0] * x[1], "div": lambda: x[0] / x[1],
                "neg": lambda: -x[0], "sqrt": lambda: math.sqrt(x[0]),
                "max": lambda: max(x[0], x[1])}[op]()

    for let in k["lets"]:
        env[let["name"]] = ev(let["expr"])
    return [ev(s["expr"]) for s in k["stores"]]


def used_params(k: IR) -> set[str]:
    out = set()
    for x in k["lets"] + k["stores"]:
        out |= ir_vars(x["expr"])
    return out


__all__ = ["euler_full_truncation", "lower_expr", "run", "typecheck", "used_params",
           "free_symbols"]
