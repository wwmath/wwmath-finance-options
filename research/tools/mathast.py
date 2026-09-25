"""Canonical Math AST: node constructors, JSON formatting, LaTeX rendering,
SymPy conversion and a numeric evaluator.

Every node is a JSON object with an ``op`` field. See ``research/schema/math_ast.md``.
"""
from __future__ import annotations

import functools
import json
import math
from typing import Any, Callable

import numpy as np
from scipy import integrate, special

Node = dict[str, Any]

# ---------------------------------------------------------------------------
# Node vocabulary
# ---------------------------------------------------------------------------

LEAF_OPS = {"Number", "Symbol", "Constant"}
NARY_OPS = {"Add", "Mul", "Tuple"}
BINARY_OPS = {"Sub", "Div", "Pow", "Eq", "Approx", "Ne", "Lt", "Le", "Gt", "Ge", "Distributed"}
UNARY_OPS = {"Neg", "Sqrt", "Abs", "Expectation", "Variance", "Probability"}
STRUCT_OPS = {
    "Call", "Apply", "Index", "Differential", "Integral", "Sum", "Product", "Limit",
    "Derivative", "PartialDerivative", "Piecewise", "SDE", "Distribution", "MalliavinDerivative",
}
ALL_OPS = LEAF_OPS | NARY_OPS | BINARY_OPS | UNARY_OPS | STRUCT_OPS

CONSTANTS = {"pi", "e", "i", "inf"}
FUNCTIONS = {"exp", "log", "sin", "cos", "N", "n", "Phi", "varphi", "Re", "Im", "max", "min",
             "arctan", "factorial"}
DISTRIBUTIONS = {"Normal", "Poisson"}


# ---------------------------------------------------------------------------
# Authoring DSL
# ---------------------------------------------------------------------------

def _n(x: Any) -> Node:
    if isinstance(x, dict):
        return x
    if isinstance(x, (int, float)):
        return {"op": "Number", "value": x}
    if isinstance(x, str):
        return sym(x)
    raise TypeError(f"cannot coerce {x!r} to a node")


def sym(name: str) -> Node: return {"op": "Symbol", "name": name}
def num(v: float) -> Node: return {"op": "Number", "value": v}
def const(name: str) -> Node: return {"op": "Constant", "name": name}
def add(*a) -> Node: return {"op": "Add", "args": [_n(x) for x in a]}
def mul(*a) -> Node: return {"op": "Mul", "args": [_n(x) for x in a]}
def sub(a, b) -> Node: return {"op": "Sub", "args": [_n(a), _n(b)]}
def div(a, b) -> Node: return {"op": "Div", "args": [_n(a), _n(b)]}
def pow_(a, b) -> Node: return {"op": "Pow", "args": [_n(a), _n(b)]}
def neg(a) -> Node: return {"op": "Neg", "args": [_n(a)]}
def sqrt(a) -> Node: return {"op": "Sqrt", "args": [_n(a)]}
def call(fn: str, *a) -> Node: return {"op": "Call", "fn": fn, "args": [_n(x) for x in a]}
def apply(fn: str, *a) -> Node: return {"op": "Apply", "fn": fn, "args": [_n(x) for x in a]}
def exp(a) -> Node: return call("exp", a)
def log(a) -> Node: return call("log", a)
def eq(a, b) -> Node: return {"op": "Eq", "args": [_n(a), _n(b)]}
def approx(a, b) -> Node: return {"op": "Approx", "args": [_n(a), _n(b)]}
def idx(base: str, *i) -> Node: return {"op": "Index", "base": base, "index": [_n(x) for x in i]}
def d(x) -> Node: return {"op": "Differential", "of": _n(x)}
def expect(x) -> Node: return {"op": "Expectation", "args": [_n(x)]}
def integral(f, var: str, lo, hi) -> Node:
    return {"op": "Integral", "integrand": _n(f), "var": sym(var), "lower": _n(lo), "upper": _n(hi)}
def sde(state, *terms) -> Node:
    return {"op": "SDE", "state": _n(state),
            "terms": [{"coef": _n(c), "driver": _n(drv)} for c, drv in terms]}
def distributed(x, family: str, *params) -> Node:
    return {"op": "Distributed", "args": [_n(x), {"op": "Distribution", "family": family,
                                                    "params": [_n(p) for p in params]}]}

I = const("i")
PI = const("pi")
INF = const("inf")


# ---------------------------------------------------------------------------
# JSON formatting: short subtrees inline, long ones broken over lines
# ---------------------------------------------------------------------------

def to_json(node: Any, indent: int = 0, width: int = 88) -> str:
    flat = json.dumps(node, ensure_ascii=False, separators=(", ", ": "))
    if len(flat) + indent <= width or not isinstance(node, (dict, list)):
        return flat
    pad = " " * (indent + 2)
    if isinstance(node, list):
        items = [pad + to_json(v, indent + 2, width) for v in node]
        return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"
    items = [f'{pad}"{k}": ' + to_json(v, indent + 2, width).lstrip() for k, v in node.items()]
    return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"


# ---------------------------------------------------------------------------
# Structural walking / validation
# ---------------------------------------------------------------------------

def children(node: Node) -> list[Node]:
    op = node["op"]
    if op in LEAF_OPS:
        return []
    if op == "Index":
        return list(node["index"])
    if op == "Differential":
        return [node["of"]]
    if op in ("Integral", "Sum", "Product"):
        key = "integrand" if op == "Integral" else "body"
        return [node[key], node["lower"], node["upper"]] + [
            node[k] for k in ("measure", "region") if k in node]
    if op == "MalliavinDerivative":
        return [node["expr"], node["at"]]
    if op in UNARY_OPS and "given" in node:
        return list(node["args"]) + [node["given"]]
    if op == "Limit":
        return [node["expr"], node["to"]]
    if op in ("Derivative", "PartialDerivative"):
        return [node["expr"]] + ([node["at"]] if "at" in node else [])
    if op == "Piecewise":
        out = []
        for p in node["pieces"]:
            out += [p["value"], p["cond"]]
        return out + [node["otherwise"]]
    if op == "SDE":
        out = [node["state"]]
        for t in node["terms"]:
            out += [t["coef"], t["driver"]]
        return out
    if op == "Distribution":
        return list(node["params"])
    return list(node["args"])


def check_node(node: Any, path: str = "$") -> list[str]:
    """Return a list of structural errors (empty when the tree is well formed)."""
    errs: list[str] = []
    if not isinstance(node, dict) or "op" not in node:
        return [f"{path}: not a node"]
    op = node["op"]
    if op not in ALL_OPS:
        return [f"{path}: unknown op {op!r}"]
    if op == "Number" and not isinstance(node.get("value"), (int, float)):
        errs.append(f"{path}: Number.value must be numeric")
    if op == "Symbol" and not isinstance(node.get("name"), str):
        errs.append(f"{path}: Symbol.name must be a string")
    if op == "Constant" and node.get("name") not in CONSTANTS:
        errs.append(f"{path}: unknown constant {node.get('name')!r}")
    if op == "Call" and node.get("fn") not in FUNCTIONS:
        errs.append(f"{path}: unknown function {node.get('fn')!r}")
    if op == "Distribution" and node.get("family") not in DISTRIBUTIONS:
        errs.append(f"{path}: unknown distribution {node.get('family')!r}")
    if op in BINARY_OPS and len(node.get("args", [])) != 2:
        errs.append(f"{path}: {op} takes exactly 2 args")
    if op in UNARY_OPS and len(node.get("args", [])) != 1:
        errs.append(f"{path}: {op} takes exactly 1 arg")
    try:
        kids = children(node)
    except KeyError as e:
        return errs + [f"{path}: {op} missing field {e}"]
    for i, c in enumerate(kids):
        errs += check_node(c, f"{path}/{op}[{i}]")
    return errs


def free_symbols(node: Node, bound: frozenset[str] = frozenset()) -> set[str]:
    op = node["op"]
    if op == "Symbol":
        return set() if node["name"] in bound else {node["name"]}
    if op in ("Integral", "Sum", "Product"):
        inner = bound | {node["var"]["name"]}
        key = "integrand" if op == "Integral" else "body"
        out = (free_symbols(node[key], inner) | free_symbols(node["lower"], bound)
               | free_symbols(node["upper"], bound))
        if "region" in node:
            out |= free_symbols(node["region"], inner)
        if "measure" in node:
            out |= free_symbols(node["measure"], bound)
        return out
    out = {node["base"]} if op == "Index" else {node["fn"]} if op == "Apply" else set()
    for c in children(node):
        out |= free_symbols(c, bound)
    return out


def def_key(lhs: Node) -> str | None:
    """Key under which an equation's left-hand side defines a quantity."""
    if lhs["op"] == "Symbol":
        return lhs["name"]
    if lhs["op"] == "Index":
        parts = []
        for i in lhs["index"]:
            if i["op"] == "Number":
                parts.append(str(i["value"]))
            elif i["op"] == "Symbol":
                parts.append(i["name"])
            else:
                return None
        return f"{lhs['base']}[{','.join(parts)}]"
    if lhs["op"] == "Apply" and all(x["op"] == "Symbol" for x in lhs["args"]):
        return f"{lhs['fn']}({','.join(x['name'] for x in lhs['args'])})"
    return None


def def_params(lhs: Node) -> list[str]:
    """Names bound by a definition's left-hand side (function parameters, generic indices)."""
    if lhs["op"] == "Apply":
        return [x["name"] for x in lhs["args"]]
    if lhs["op"] == "Index":
        return [x["name"] for x in lhs["index"] if x["op"] == "Symbol"]
    return []


# ---------------------------------------------------------------------------
# LaTeX rendering (Display IR)
# ---------------------------------------------------------------------------

GREEK = {"alpha", "beta", "gamma", "delta", "epsilon", "kappa", "lambda", "mu", "nu", "xi",
         "rho", "sigma", "tau", "phi", "theta", "psi", "omega", "eta", "zeta", "chi",
         "varepsilon", "vartheta", "varphi", "Phi"}
FN_TEX = {"exp": r"\exp", "log": r"\ln", "sin": r"\sin", "cos": r"\cos", "Re": r"\operatorname{Re}",
          "Im": r"\operatorname{Im}", "max": r"\max", "min": r"\min", "N": "N", "n": "n", "Phi": r"\Phi", "varphi": r"\varphi",
          "arctan": r"\arctan"}
PREC = {"Add": 1, "Sub": 1, "Neg": 2, "Mul": 3, "Div": 4, "Pow": 5}


def _name_tex(name: str) -> str:
    if "^" in name:
        main, _, sup = name.partition("^")
        return f"{_name_tex(main)}^{{{_name_tex(sup)}}}"
    base, _, subscript = name.partition("_")
    b = "\\" + base if base in GREEK else base
    if base.endswith("bar"):
        core = base[:-3]
        b = r"\bar{" + ("\\" + core if core in GREEK else core) + "}"
    if base.endswith("star"):
        core = base[:-4]
        b = ("\\" + core if core in GREEK else core) + "^{*}"
    if base.endswith("hat"):
        core = base[:-3]
        b = r"\hat{" + ("\\" + core if core in GREEK else core) + "}"
    if subscript:
        sub_t = "\\" + subscript if subscript in GREEK else subscript
        return f"{b}_{{{sub_t}}}"
    return b


def latex(node: Node, parent: int = 0) -> str:
    op = node["op"]
    wrap = lambda s, p: f"\\left({s}\\right)" if p < parent else s  # noqa: E731
    if op == "Number":
        v = node["value"]
        s = str(int(v)) if float(v).is_integer() else repr(v)
        return wrap(s, 6 if v >= 0 else 2)
    if op == "Symbol":
        return _name_tex(node["name"])
    if op == "Constant":
        return {"pi": r"\pi", "e": "e", "i": "i", "inf": r"\infty"}[node["name"]]
    a = node.get("args", [])
    if op == "Add":
        s = latex(a[0], 1)
        for x in a[1:]:
            t = latex(x, 1)
            s += t if t.startswith("-") else " + " + t
        return wrap(s, 1)
    if op == "Sub":
        return wrap(f"{latex(a[0], 1)} - {latex(a[1], 2)}", 1)
    if op == "Neg":
        return wrap("-" + latex(a[0], 3), 2)
    if op == "Mul":
        return wrap(" ".join(latex(x, 3) for x in a), 3)
    if op == "Div":
        return wrap(f"\\frac{{{latex(a[0])}}}{{{latex(a[1])}}}", 6)
    if op == "Pow":
        return wrap(f"{{{latex(a[0], 6)}}}^{{{latex(a[1])}}}", 5)
    if op == "Sqrt":
        return f"\\sqrt{{{latex(a[0])}}}"
    if op == "Abs":
        return f"\\left|{latex(a[0])}\\right|"
    if op == "Call":
        fn = FN_TEX.get(node["fn"], node["fn"])
        inner = ", ".join(latex(x) for x in a)
        if node["fn"] == "factorial":
            return f"{latex(a[0], 6)}!"
        if node["fn"] == "max" and len(a) == 2 and a[1] == num(0):
            return f"\\left({latex(a[0])}\\right)^{{+}}"
        return f"{fn}\\left({inner}\\right)"
    if op == "Apply":
        return f"{_name_tex(node['fn'])}\\left({', '.join(latex(x) for x in a)}\\right)"
    if op == "Index":
        return f"{_name_tex(node['base'])}_{{{','.join(latex(i) for i in node['index'])}}}"
    rel = {"Eq": "=", "Approx": r"\approx", "Ne": r"\neq", "Lt": "<", "Le": r"\le",
           "Gt": ">", "Ge": r"\ge", "Distributed": r"\sim"}
    if op in rel:
        return f"{latex(a[0])} {rel[op]} {latex(a[1])}"
    if op == "Differential":
        return f"d{latex(node['of'], 6)}"
    if op == "Integral":
        if "region" in node:
            lim = f"\\int_{{{latex(node['region'])}}} "
        else:
            lim = f"\\int_{{{latex(node['lower'])}}}^{{{latex(node['upper'])}}} "
        dv = f"d{latex(node['var'])}"
        if "measure" in node:
            dv = f"{latex(node['measure'])}\\left({dv}\\right)"
        return f"{lim}{latex(node['integrand'], 1)} \\, {dv}"
    if op == "MalliavinDerivative":
        return f"D_{{{latex(node['at'])}}} {latex(node['expr'], 6)}"
    if op in ("Sum", "Product"):
        cmd = r"\sum" if op == "Sum" else r"\prod"
        return (f"{cmd}_{{{latex(node['var'])}={latex(node['lower'])}}}^{{{latex(node['upper'])}}} "
                f"{latex(node['body'], 3)}")
    if op == "Limit":
        return f"\\lim_{{{latex(node['var'])} \\to {latex(node['to'])}}} {latex(node['expr'], 3)}"
    if op in ("Derivative", "PartialDerivative"):
        dd = "d" if op == "Derivative" else r"\partial"
        out = f"\\frac{{{dd} {latex(node['expr'])}}}{{{dd} {latex(node['var'])}}}"
        if "at" in node:
            out = f"\\left.{out}\\right|_{{{latex(node['var'])} = {latex(node['at'])}}}"
        return out
    if op in ("Expectation", "Variance", "Probability"):
        letter = {"Expectation": r"\mathbb{E}", "Variance": r"\operatorname{Var}",
                  "Probability": r"\mathbb{P}"}[op]
        sub_ = f"_{{{latex(node['given'])}}}" if "given" in node else ""
        return f"{letter}{sub_}\\left[{latex(a[0])}\\right]"
    if op == "Piecewise":
        rows = [f"{latex(p['value'])} & {latex(p['cond'])}" for p in node["pieces"]]
        rows.append(f"{latex(node['otherwise'])} & \\text{{otherwise}}")
        return r"\begin{cases}" + r" \\ ".join(rows) + r"\end{cases}"
    if op == "SDE":
        terms = [f"{latex(t['coef'], 3)} \\, {latex(t['driver'])}" for t in node["terms"]]
        return f"d{latex(node['state'], 6)} = " + " + ".join(terms)
    if op == "Distribution":
        fam = {"Normal": r"\mathcal{N}", "Poisson": r"\operatorname{Poisson}"}[node["family"]]
        return f"{fam}\\left({', '.join(latex(p) for p in node['params'])}\\right)"
    if op == "Tuple":
        return "\\left(" + ", ".join(latex(x) for x in a) + "\\right)"
    raise ValueError(f"no LaTeX rule for {op}")


# ---------------------------------------------------------------------------
# SymPy bridge (verification layer)
# ---------------------------------------------------------------------------

class NotSymPyRepresentable(Exception):
    pass


def to_sympy(node: Node, defs: dict[str, Node] | None = None):
    import sympy as sp

    op = node["op"]
    r = lambda n: to_sympy(n, defs)  # noqa: E731
    a = node.get("args", [])
    if op == "Number":
        v = node["value"]
        return sp.Integer(v) if isinstance(v, int) else sp.Float(v)
    if op == "Symbol":
        return sp.Symbol(node["name"])
    if op == "Constant":
        return {"pi": sp.pi, "e": sp.E, "i": sp.I, "inf": sp.oo}[node["name"]]
    if op == "Add":
        return sp.Add(*map(r, a))
    if op == "Mul":
        return sp.Mul(*map(r, a))
    if op == "Sub":
        return r(a[0]) - r(a[1])
    if op == "Div":
        return r(a[0]) / r(a[1])
    if op == "Neg":
        return -r(a[0])
    if op == "Pow":
        return r(a[0]) ** r(a[1])
    if op == "Sqrt":
        return sp.sqrt(r(a[0]))
    if op == "Abs":
        return sp.Abs(r(a[0]))
    if op == "Call":
        fn = node["fn"]
        args = list(map(r, a))
        z = sp.Symbol("_z")
        table: dict[str, Callable] = {
            "exp": sp.exp, "log": sp.log, "sin": sp.sin, "cos": sp.cos, "Re": sp.re, "Im": sp.im,
            "max": sp.Max, "min": sp.Min, "arctan": sp.atan,
            "N": lambda x: (1 + sp.erf(x / sp.sqrt(2))) / 2,
            "n": lambda x: sp.exp(-x ** 2 / 2) / sp.sqrt(2 * sp.pi),
            "factorial": sp.factorial,
        }
        table["Phi"], table["varphi"] = table["N"], table["n"]
        _ = z
        return table[fn](*args)
    if op == "Apply":
        return sp.Function(node["fn"])(*map(r, a))
    if op == "Index":
        return sp.Symbol(f"{node['base']}_{'_'.join(str(r(i)) for i in node['index'])}")
    if op in ("Eq", "Approx"):
        return sp.Eq(r(a[0]), r(a[1]), evaluate=False)
    if op in ("Lt", "Le", "Gt", "Ge", "Ne"):
        return {"Lt": sp.Lt, "Le": sp.Le, "Gt": sp.Gt, "Ge": sp.Ge, "Ne": sp.Ne}[op](r(a[0]), r(a[1]))
    if op == "Integral":
        return sp.Integral(r(node["integrand"]), (r(node["var"]), r(node["lower"]), r(node["upper"])))
    if op in ("Sum", "Product"):
        cls = sp.Sum if op == "Sum" else sp.Product
        return cls(r(node["body"]), (r(node["var"]), r(node["lower"]), r(node["upper"])))
    if op == "Piecewise":
        pieces = [(r(p["value"]), r(p["cond"])) for p in node["pieces"]]
        return sp.Piecewise(*pieces, (r(node["otherwise"]), True))
    if op in ("Derivative", "PartialDerivative"):
        out = sp.Derivative(r(node["expr"]), r(node["var"]))
        return out.subs(r(node["var"]), r(node["at"])) if "at" in node else out
    if op == "Limit":
        return sp.Limit(r(node["expr"]), r(node["var"]), r(node["to"]))
    raise NotSymPyRepresentable(op)


# ---------------------------------------------------------------------------
# Numeric evaluator (reference interpreter, numpy-vectorised, complex-safe)
# ---------------------------------------------------------------------------

class Context:
    """Holds the definitions (lhs key -> rhs AST) visible while evaluating."""

    def __init__(self, defs: dict[str, Node]):
        self.defs = defs

    def lookup(self, key: str) -> Node | None:
        return self.defs.get(key)


def _real_if_close(x):
    x = np.asarray(x)
    if np.iscomplexobj(x) and np.all(np.abs(x.imag) <= 1e-12 * np.maximum(1.0, np.abs(x.real))):
        x = x.real
    return x[()] if x.ndim == 0 else x


NUMERIC_FUNCS: dict[str, Callable] = {
    "exp": np.exp,
    "log": lambda x: np.log(x + 0j) if np.any(np.real(x) <= 0) or np.iscomplexobj(x) else np.log(x),
    "sin": np.sin, "cos": np.cos, "arctan": np.arctan,
    "Re": np.real, "Im": np.imag,
    "max": lambda *a: functools.reduce(np.maximum, [np.real(v) for v in a]),
    "min": lambda *a: functools.reduce(np.minimum, [np.real(v) for v in a]),
    "N": lambda x: special.ndtr(np.real(x)),
    "Phi": lambda x: special.ndtr(np.real(x)),
    "varphi": lambda x: np.exp(-np.real(x) ** 2 / 2) / math.sqrt(2 * math.pi),
    "factorial": lambda x: special.gamma(np.real(x) + 1.0),
    "n": lambda x: np.exp(-np.real(x) ** 2 / 2) / math.sqrt(2 * math.pi),
}


def bind(env: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """New scope with ``values`` bound (they shadow definitions of the same name)."""
    return {**env, **values, "__bound__": frozenset(env.get("__bound__", ())) | values.keys()}


def evaluate(node: Node, env: dict[str, Any], ctx: Context):
    op = node["op"]
    ev = lambda n: evaluate(n, env, ctx)  # noqa: E731
    a = node.get("args", [])
    if op == "Number":
        return node["value"]
    if op == "Constant":
        return {"pi": math.pi, "e": math.e, "i": 1j, "inf": math.inf}[node["name"]]
    if op == "Symbol":
        # scope: bound variables (parameters, integration/summation variables), then
        # the paper's definitions, then the caller's inputs
        name = node["name"]
        if name in env.get("__bound__", ()):
            return env[name]
        rhs = ctx.lookup(name)
        if rhs is not None:
            return evaluate(rhs, env, ctx)
        if name in env:
            return env[name]
        raise KeyError(f"unbound symbol {name!r}")
    if op == "Index":
        vals = [ev(i) for i in node["index"]]
        concrete = f"{node['base']}[{','.join(str(int(v)) for v in vals)}]"
        rhs = ctx.lookup(concrete)
        if rhs is not None:
            return evaluate(rhs, env, ctx)
        for key, rhs in ctx.defs.items():
            if key.startswith(node["base"] + "[") and not key[len(node["base"]) + 1:-1][0].isdigit():
                names = key[len(node["base"]) + 1:-1].split(",")
                return evaluate(rhs, bind(env, dict(zip(names, vals))), ctx)
        raise KeyError(f"no definition for {concrete}")
    if op == "Apply":
        vals = [ev(x) for x in a]
        for key, rhs in ctx.defs.items():
            if key.startswith(node["fn"] + "("):
                names = key[len(node["fn"]) + 1:-1].split(",")
                return evaluate(rhs, bind(env, dict(zip(names, vals))), ctx)
        raise KeyError(f"no definition for function {node['fn']!r}")
    if op == "Add":
        out = ev(a[0])
        for x in a[1:]:
            out = out + ev(x)
        return out
    if op == "Mul":
        out = ev(a[0])
        for x in a[1:]:
            out = out * ev(x)
        return out
    if op == "Sub":
        return ev(a[0]) - ev(a[1])
    if op == "Div":
        return ev(a[0]) / ev(a[1])
    if op == "Neg":
        return -ev(a[0])
    if op == "Pow":
        base, ex = ev(a[0]), ev(a[1])
        if np.iscomplexobj(base) or np.iscomplexobj(ex) or np.any(np.asarray(base) < 0):
            return np.power(np.asarray(base, dtype=complex), ex)
        return np.power(base, ex)
    if op == "Sqrt":
        x = ev(a[0])
        return np.sqrt(x + 0j) if np.iscomplexobj(x) or np.any(np.asarray(x) < 0) else np.sqrt(x)
    if op == "Abs":
        return np.abs(ev(a[0]))
    if op == "Call":
        return NUMERIC_FUNCS[node["fn"]](*[ev(x) for x in a])
    if op == "Integral":
        var = node["var"]["name"]
        lo, hi = float(np.real(ev(node["lower"]))), float(np.real(ev(node["upper"])))

        infinite = math.isinf(lo) or math.isinf(hi)

        def f(x):
            with np.errstate(all="ignore"):
                y = float(np.real(evaluate(node["integrand"], bind(env, {var: x}), ctx)))
            # Integrands on infinite ranges decay to zero; a non-finite value there can
            # only be overflow in the far tail (e.g. exp(d tau) in Heston's form).
            return 0.0 if infinite and not math.isfinite(y) else y

        val, _err = integrate.quad(f, lo, hi, limit=500, epsabs=1e-11, epsrel=1e-10)
        return val
    if op in ("Sum", "Product"):
        var = node["var"]["name"]
        lo, hi = int(ev(node["lower"])), int(ev(node["upper"]))
        vals = [evaluate(node["body"], bind(env, {var: k}), ctx) for k in range(lo, hi + 1)]
        return sum(vals) if op == "Sum" else math.prod(vals)
    if op == "Piecewise":
        for p in node["pieces"]:
            if bool(ev(p["cond"])):
                return ev(p["value"])
        return ev(node["otherwise"])
    if op in ("Lt", "Le", "Gt", "Ge"):
        l, r = np.real(ev(a[0])), np.real(ev(a[1]))
        return {"Lt": l < r, "Le": l <= r, "Gt": l > r, "Ge": l >= r}[op]
    raise NotImplementedError(f"cannot numerically evaluate {op}")


def evaluate_real(node: Node, env: dict[str, Any], ctx: Context):
    return _real_if_close(evaluate(node, env, ctx))


# ---------------------------------------------------------------------------
# AST substitution and definition inlining (used by symbolic checks)
# ---------------------------------------------------------------------------

def substitute(node: Node, mapping: dict[str, Node]) -> Node:
    """Replace free Symbols by ASTs, respecting variables bound by Integral/Sum/Product."""
    op = node["op"]
    if op == "Symbol":
        return mapping.get(node["name"], node)
    if op in ("Integral", "Sum", "Product") and node["var"]["name"] in mapping:
        mapping = {k: v for k, v in mapping.items() if k != node["var"]["name"]}
    out = {}
    for key, val in node.items():
        if isinstance(val, dict) and "op" in val:
            out[key] = substitute(val, mapping)
        elif isinstance(val, list):
            out[key] = [substitute(x, mapping) if isinstance(x, dict) and "op" in x else
                        {k2: substitute(v2, mapping) for k2, v2 in x.items()}
                        if isinstance(x, dict) else x for x in val]
        else:
            out[key] = val
    return out


def inline(node: Node, defs: dict[str, Node], abstract: frozenset[str] = frozenset(),
           depth: int = 0) -> Node:
    """Expand Symbol and Apply definitions recursively (Index definitions are left alone)."""
    if depth > 60:
        raise RecursionError("definition cycle")
    op = node["op"]
    rec = lambda n: inline(n, defs, abstract, depth + 1)  # noqa: E731
    if op == "Symbol" and node["name"] in defs and node["name"] not in abstract:
        return rec(defs[node["name"]])
    if op == "Apply" and node["fn"] not in abstract:
        for key, rhs in defs.items():
            if key.startswith(node["fn"] + "("):
                names = key[len(node["fn"]) + 1:-1].split(",")
                args = [rec(a) for a in node["args"]]
                return rec(substitute(rhs, dict(zip(names, args))))
    out = {}
    for key, val in node.items():
        if isinstance(val, dict) and "op" in val:
            out[key] = rec(val) if key != "var" else val
        elif isinstance(val, list):
            out[key] = [rec(x) if isinstance(x, dict) and "op" in x else
                        {k2: rec(v2) for k2, v2 in x.items()} if isinstance(x, dict) else x
                        for x in val]
        else:
            out[key] = val
    return out
