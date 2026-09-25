"""Lower Math AST formulas to standalone C++17 (a header of inline functions).

This is the "numerical" C++ backend, for pricing formulas: it keeps complex
arithmetic (std::complex<double>) and Fourier integrals, which the bit-exact
Typed Math IR (ir.py) deliberately does not have. Structure mirrors f77.py:

* each referenced definition becomes one `const auto` temporary, computed once per scope;
* `Index` and `Apply` definitions are instantiated at lowering time;
* an `Integral` becomes a lambda integrand passed to `ww::integrate` (adaptive
  Gauss-Kronrod, see include/wwmath/runtime.hpp); the lambda captures outer temporaries
  by reference, so nothing needs COMMON-style plumbing.

The generated code depends only on the C++ standard library and wwmath/runtime.hpp.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from mathast import Node, children, latex

KEYWORDS = {"auto", "bool", "break", "case", "char", "class", "const", "continue", "default",
            "delete", "do", "double", "else", "enum", "extern", "float", "for", "goto", "if",
            "int", "long", "new", "operator", "private", "public", "register", "return",
            "short", "signed", "sizeof", "static", "struct", "switch", "template", "this",
            "throw", "try", "typedef", "union", "unsigned", "void", "volatile", "while"}


def ident(name: str) -> str:
    s = re.sub(r"\W", "_", name)
    return s + "_" if s in KEYWORDS or s[0].isdigit() else s


def cnum(v: float) -> str:
    s = repr(float(v))
    return s if ("." in s or "e" in s or "inf" in s or "nan" in s) else s + ".0"


@dataclass
class Block:
    stmts: list[str] = field(default_factory=list)
    memo: dict[str, str] = field(default_factory=dict)
    indent: str = "    "


class CppLowerer:
    def __init__(self, defs: dict[str, Node], inputs: list[str]):
        self.defs = defs
        self.inputs = set(inputs)
        self.counter = 0

    def fresh(self) -> str:
        self.counter += 1
        return f"tmp_{self.counter}"

    def assign(self, blk: Block, expr: str, comment: str | None = None) -> str:
        name = self.fresh()
        c = f"  // {comment}" if comment else ""
        blk.stmts.append(f"{blk.indent}const auto {name} = {expr};{c}")
        return name

    def instantiate(self, blk: Block, key: str, rhs: Node, subst: dict) -> str:
        if key not in blk.memo:
            blk.memo[key] = self.assign(blk, self.lower(rhs, blk, subst), key)
        return blk.memo[key]

    def generic(self, prefix: str) -> tuple[str, list[str]] | None:
        for key in self.defs:
            if key.startswith(prefix) and not key[len(prefix):-1][:1].isdigit():
                return key, key[len(prefix):-1].split(",")
        return None

    def lower(self, node: Node, blk: Block, subst: dict) -> str:
        op = node["op"]
        a = node.get("args", [])
        L = lambda n: self.lower(n, blk, subst)  # noqa: E731
        if op == "Number":
            return cnum(node["value"])
        if op == "Constant":
            return {"i": "ww::I", "pi": "ww::PI", "e": "ww::E", "inf": "ww::INF"}[node["name"]]
        if op == "Symbol":
            name = node["name"]
            if name in subst:
                return subst[name]
            if name in self.defs:
                return self.instantiate(blk, name, self.defs[name], subst)
            if name in self.inputs:
                return ident(name)
            raise KeyError(f"unbound symbol {name!r}")
        if op == "Index":
            vals = []
            for i in node["index"]:
                v = self.lower(i, blk, subst)
                vals.append(str(int(float(v))))
            concrete = f"{node['base']}[{','.join(vals)}]"
            if concrete in self.defs:
                return self.instantiate(blk, concrete, self.defs[concrete], subst)
            gen = self.generic(node["base"] + "[")
            if gen is None:
                raise KeyError(f"no definition for {concrete}")
            key, names = gen
            inner = {**subst, **{n: cnum(float(v)) for n, v in zip(names, vals)}}
            return self.instantiate(blk, concrete, self.defs[key], inner)
        if op == "Apply":
            args = []
            for x in a:
                v = self.lower(x, blk, subst)
                args.append(v if re.fullmatch(r"[A-Za-z_]\w*|[-+0-9.e]+", v) else
                            self.assign(blk, v))
            gen = self.generic(node["fn"] + "(")
            if gen is None:
                raise KeyError(f"no definition for function {node['fn']}")
            key, names = gen
            inst = f"{node['fn']}({','.join(args)})"
            return self.instantiate(blk, inst, self.defs[key], {**subst, **dict(zip(names, args))})
        if op in ("Add", "Mul"):
            sep = " + " if op == "Add" else " * "
            return "(" + sep.join(L(x) for x in a) + ")"
        if op == "Sub":
            return f"({L(a[0])} - {L(a[1])})"
        if op == "Div":
            return f"({L(a[0])} / {L(a[1])})"
        if op == "Neg":
            return f"(-{L(a[0])})"
        if op == "Pow":
            return f"std::pow({L(a[0])}, {L(a[1])})"
        if op == "Sqrt":
            return f"std::sqrt({L(a[0])})"
        if op == "Abs":
            return f"std::abs({L(a[0])})"
        if op == "Call":
            fn = node["fn"]
            xs = [L(x) for x in a]
            simple = {"exp": "std::exp", "log": "std::log", "sin": "std::sin", "cos": "std::cos",
                      "Re": "std::real", "Im": "std::imag", "arctan": "std::atan",
                      "N": "ww::N", "Phi": "ww::N", "n": "ww::n", "varphi": "ww::n",
                      "max": "ww::max", "min": "ww::min"}
            if fn == "factorial":
                return f"std::tgamma(std::real({xs[0]}) + 1.0)"
            return f"{simple[fn]}({', '.join(xs)})"
        if op == "Integral":
            return self.lower_integral(node, blk, subst)
        raise NotImplementedError(f"C++ lowering for {op}")

    def lower_integral(self, node: Node, blk: Block, subst: dict) -> str:
        var = node["var"]["name"]
        v = f"{ident(var)}_"
        inner = Block(indent=blk.indent + "    ")
        body = self.lower(node["integrand"], inner, {**subst, var: v})
        lo = self.lower(node["lower"], blk, subst)
        hi = self.lower(node["upper"], blk, subst)
        lines = "\n".join(inner.stmts)
        lam = (f"ww::integrate([&](double {v}) -> double {{\n{lines}\n"
               f"{inner.indent}return std::real({body});\n{blk.indent}}}, {lo}, {hi})")
        return self.assign(blk, lam, f"integral over {var}")


def required_inputs(node: Node, defs: dict[str, Node], order: list[str]) -> list[str]:
    """Undefined free symbols reachable through definitions, in paper declaration order."""
    found: list[str] = []
    seen: set[str] = set()

    def visit(n: Node, bound: frozenset[str]):
        op = n["op"]
        if op == "Symbol":
            name = n["name"]
            if name in bound:
                return
            if name in defs:
                if name not in seen:
                    seen.add(name)
                    visit(defs[name], bound)
            elif name not in found:
                found.append(name)
            return
        if op in ("Index", "Apply"):
            base = n.get("base") or n.get("fn")
            for key, rhs in defs.items():
                if key.startswith(base + ("[" if op == "Index" else "(")) and key not in seen:
                    seen.add(key)
                    params = key[len(base) + 1:-1].split(",")
                    visit(rhs, bound | frozenset(p for p in params if not p.isdigit()))
        if op == "Integral":
            visit(n["integrand"], bound | {n["var"]["name"]})
            visit(n["lower"], bound)
            visit(n["upper"], bound)
            return
        for c in children(n):
            visit(c, bound)

    visit(node, frozenset())
    rank = {s: i for i, s in enumerate(order)}
    return sorted(found, key=lambda s: (rank.get(s, len(rank)), s))


def emit_function(fid: str, formula: dict, defs: dict[str, Node], order: list[str],
                  params: list[str] | None = None, bind: dict[str, Node] | None = None) -> str:
    """One inline C++ function computing the formula's right-hand side.

    ``params``/``bind`` let a caller expose a definition's own parameters (e.g. the y, f of
    F(y, f)) as function arguments.
    """
    ast = formula["ast"]
    rhs = ast["args"][1] if ast["op"] in ("Eq", "Approx") else ast
    ins = params if params is not None else required_inputs(rhs, defs, order)
    lw = CppLowerer(defs, ins)
    blk = Block()
    subst = {p: ident(p) for p in ins}
    result = lw.lower(rhs, blk, subst)
    src = formula.get("source", {})
    where = ", ".join(x for x in (src.get("reference"), src.get("equation") and
                                  f"eq. {src['equation']}", src.get("page") and
                                  f"p. {src['page']}") if x)
    doc = [f"/// {fid}: {formula.get('name', '')}",
           f"/// {where or 'source in the paper TOML'} ({src.get('fidelity', '?')}, "
           f"verified against PDF: {'yes' if src.get('verified_against_pdf') else 'no'})",
           f"/// LaTeX: {latex(ast).replace(chr(10), ' ')}"]
    sig = ", ".join(f"double {ident(p)}" for p in ins)
    name = ident(fid.replace(".", "_"))
    return ("\n".join(doc) + f"\ninline double {name}({sig}) {{\n" + "\n".join(blk.stmts) +
            f"\n    return std::real({result});\n}}\n")
