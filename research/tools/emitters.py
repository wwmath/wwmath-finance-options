"""Language emitters for Typed Math IR kernels.

Every emitter prints the same binary operation tree, fully parenthesised, so the
floating-point operations and their order are identical in every language.
Tiers:
  1 (required conformance)  C, C++, Rust, Zig
  2 (numerical heritage)    Fortran
  3 (experimental)          Carbon  (source only until a toolchain is available)
  direct backend            WASM (binary encoded here, plus WAT text)
The flat ABI is  name(f64 x 9 ..., f64* output)  with output[i] = stores[i].
"""
from __future__ import annotations

import struct

from ir import IR

HEADER = "Generated from the Math AST via the Typed Math IR -- do not edit."


def _num(v: float, lang: str) -> str:
    s = repr(float(v))
    if lang == "fortran":
        m, _, e = s.partition("e")
        return f"{m}d{e or 0}" if "." in m or e else f"{m}.0d0"
    return s


def expr(e: IR, lang: str) -> str:
    op = e["op"]
    if op == "const":
        return _num(e["value"], lang)
    if op == "var":
        return e["name"]
    a = [expr(x, lang) for x in e["args"]]
    if op in ("add", "sub", "mul", "div"):
        sym = {"add": "+", "sub": "-", "mul": "*", "div": "/"}[op]
        return f"({a[0]} {sym} {a[1]})"
    if op == "neg":
        return f"(-{a[0]})"
    if op == "sqrt":
        return {"c": f"__builtin_sqrt({a[0]})", "cpp": f"__builtin_sqrt({a[0]})",
                "fortran": f"sqrt({a[0]})", "zig": f"@sqrt({a[0]})",
                "rust": f"{a[0]}.sqrt()", "carbon": f"Math.Sqrt({a[0]})"}[lang]
    if op == "max":
        return {"c": f"({a[0]} > {a[1]} ? {a[0]} : {a[1]})",
                "cpp": f"({a[0]} > {a[1]} ? {a[0]} : {a[1]})",
                "fortran": f"max({a[0]}, {a[1]})", "zig": f"@max({a[0]}, {a[1]})",
                "rust": f"{a[0]}.max({a[1]})",
                "carbon": f"(if {a[0]} > {a[1]} then {a[0]} else {a[1]})"}[lang]
    raise NotImplementedError(op)


def _scalars(k: IR) -> list[str]:
    return [p["name"] for p in k["params"] if p["type"] == "f64"]


def emit_c(k: IR) -> str:
    args = ",\n    ".join([f"double {p}" for p in _scalars(k)] + ["double *output"])
    body = [f"    const double {l['name']} = {expr(l['expr'], 'c')};" for l in k["lets"]]
    body += [f"    output[{s['index']}] = {expr(s['expr'], 'c')};  /* {s['name']} */"
             for s in k["stores"]]
    return (f"/* {HEADER} */\n/* Source: {k['source']['paper']} {', '.join(k['source']['sde'])}, "
            f"{k['source']['scheme']} */\n\n"
            f"__attribute__((export_name(\"{k['name']}\")))\n"
            f"void {k['name']}(\n    {args})\n{{\n" + "\n".join(body) + "\n}\n")


def emit_cpp(k: IR) -> str:
    args = ",\n    ".join([f"double {p}" for p in _scalars(k)] + ["double* output"])
    body = [f"    const double {l['name']} = {expr(l['expr'], 'cpp')};" for l in k["lets"]]
    body += [f"    output[{s['index']}] = {expr(s['expr'], 'cpp')};  // {s['name']}"
             for s in k["stores"]]
    return (f"// {HEADER}\n// Deliberately boring C++ subset; __builtin_sqrt is std::sqrt without "
            f"a libc++ sysroot.\n\n"
            f"extern \"C\" __attribute__((export_name(\"{k['name']}\")))\n"
            f"void {k['name']}(\n    {args})\n{{\n" + "\n".join(body) + "\n}\n")


def emit_fortran(k: IR) -> str:
    sc = _scalars(k)
    lines = [f"! {HEADER}",
             "! F77 numerics; BIND(C)/VALUE (Fortran 2003) are used only to fix the flat ABI.",
             f"subroutine {k['name']}({', '.join(sc)}, output) &",
             f"    bind(c, name=\"{k['name']}\")",
             "  use iso_c_binding, only: c_double",
             "  implicit none",
             f"  real(c_double), value :: {', '.join(sc)}",
             f"  real(c_double), intent(out) :: output({len(k['stores'])})",
             "  real(c_double) :: " + ", ".join(l["name"] for l in k["lets"])]
    for l in k["lets"]:
        lines.append(f"  {l['name']} = {expr(l['expr'], 'fortran')}")
    for s in k["stores"]:
        lines.append(f"  output({s['index'] + 1}) = {expr(s['expr'], 'fortran')}  ! {s['name']}")
    lines.append(f"end subroutine {k['name']}")
    return "\n".join(_wrap_f90(x) for x in lines) + "\n"


def _wrap_f90(line: str, width: int = 100) -> str:
    if len(line) <= width or line.lstrip().startswith("!"):
        return line
    out, cur = [], line
    while len(cur) > width:
        cut = cur.rfind(" ", 0, width)
        out.append(cur[:cut] + " &")
        cur = "      " + cur[cut + 1:]
    return "\n".join(out + [cur])


def emit_zig(k: IR) -> str:
    args = ",\n    ".join([f"{p}: f64" for p in _scalars(k)] + ["output: [*]f64"])
    body = [f"    const {l['name']}: f64 = {expr(l['expr'], 'zig')};" for l in k["lets"]]
    body += [f"    output[{s['index']}] = {expr(s['expr'], 'zig')}; // {s['name']}"
             for s in k["stores"]]
    return (f"// {HEADER}\n\nexport fn {k['name']}(\n    {args},\n) void {{\n"
            + "\n".join(body) + "\n}\n")


def emit_rust(k: IR) -> str:
    args = ",\n    ".join([f"{p}: f64" for p in _scalars(k)] + ["output: *mut f64"])
    body = [f"    let {l['name']}: f64 = {expr(l['expr'], 'rust')};" for l in k["lets"]]
    body += [f"    unsafe {{ *output.add({s['index']}) = {expr(s['expr'], 'rust')}; }} "
             f"// {s['name']}" for s in k["stores"]]
    return (f"// {HEADER}\n// Rust is the conformance reference.\n\n"
            "#[no_mangle]\n#[allow(clippy::too_many_arguments)]\n"
            f"pub extern \"C\" fn {k['name']}(\n    {args},\n) {{\n" + "\n".join(body) + "\n}\n")


def emit_carbon(k: IR) -> str:
    camel = "".join(w.capitalize() for w in k["name"].split("_"))
    args = ",\n    ".join([f"{p}: f64" for p in _scalars(k)] + ["output: f64*"])
    body = [f"  let {l['name']}: f64 = {expr(l['expr'], 'carbon')};" for l in k["lets"]]
    body += [f"  output[{s['index']}] = {expr(s['expr'], 'carbon')};  // {s['name']}"
             for s in k["stores"]]
    return (f"// {HEADER}\n// EXPERIMENTAL (Tier 3): Carbon has no stable toolchain or WASM target;\n"
            f"// this is emitted from the same IR but is not compiled or run yet.\n\n"
            f"package WwmathKernels api;\n\nimport Math;\n\n"
            f"fn {camel}(\n    {args}) {{\n" + "\n".join(body) + "\n}\n")


# ---------------------------------------------------------------------------
# Direct WASM backend (binary encoder) and WAT text
# ---------------------------------------------------------------------------

def _uleb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _vec(items: list[bytes]) -> bytes:
    return _uleb(len(items)) + b"".join(items)


def _name(s: str) -> bytes:
    return _uleb(len(s.encode())) + s.encode()


def _section(sid: int, payload: bytes) -> bytes:
    return bytes([sid]) + _uleb(len(payload)) + payload


F64T, I32T = 0x7C, 0x7F
OPC = {"add": 0xA0, "sub": 0xA1, "mul": 0xA2, "div": 0xA3, "neg": 0x9A, "sqrt": 0x9F,
       "max": 0xA5}


def emit_wasm(k: IR) -> tuple[bytes, str]:
    sc = _scalars(k)
    local_index = {p: i for i, p in enumerate(sc)}
    out_idx = len(sc)
    for j, l in enumerate(k["lets"]):
        local_index[l["name"]] = out_idx + 1 + j
    code = bytearray()
    wat: list[str] = []

    def gen(e: IR, depth: int = 2):
        op = e["op"]
        pad = "  " * depth
        if op == "const":
            code.extend(b"\x44" + struct.pack("<d", e["value"]))
            wat.append(f"{pad}f64.const {e['value']!r}")
        elif op == "var":
            code.extend(b"\x20" + _uleb(local_index[e["name"]]))
            wat.append(f"{pad}local.get ${e['name']}")
        else:
            for a in e["args"]:
                gen(a, depth)
            code.append(OPC[op])
            wat.append(f"{pad}f64.{op}")

    for l in k["lets"]:
        gen(l["expr"])
        code.extend(b"\x21" + _uleb(local_index[l["name"]]))
        wat.append(f"    local.set ${l['name']}")
    for s in k["stores"]:
        code.extend(b"\x20" + _uleb(out_idx))
        wat.append(f"    local.get $output  ;; {s['name']}")
        gen(s["expr"])
        code.extend(b"\x39" + _uleb(3) + _uleb(8 * s["index"]))   # f64.store align=8 offset
        wat.append(f"    f64.store offset={8 * s['index']}")
    code.append(0x0B)

    ftype = b"\x60" + _vec([bytes([F64T])] * len(sc) + [bytes([I32T])]) + _vec([])
    locals_ = _vec([_uleb(len(k["lets"])) + bytes([F64T])]) if k["lets"] else _vec([])
    body = locals_ + bytes(code)
    module = (b"\x00asm\x01\x00\x00\x00"
              + _section(1, _vec([ftype]))
              + _section(3, _vec([_uleb(0)]))
              + _section(5, _vec([b"\x00" + _uleb(1)]))                   # memory min 1 page
              + _section(7, _vec([_name(k["name"]) + b"\x00" + _uleb(0),
                                  _name("memory") + b"\x02" + _uleb(0)]))
              + _section(10, _vec([_uleb(len(body)) + body])))
    params = " ".join(f"(param ${p} f64)" for p in sc) + " (param $output i32)"
    locs = " ".join(f"(local ${l['name']} f64)" for l in k["lets"])
    wat_text = (f";; {HEADER}\n(module\n  (memory (export \"memory\") 1)\n"
                f"  (func (export \"{k['name']}\") {params}\n    {locs}\n"
                + "\n".join(wat) + "\n  )\n)\n")
    return module, wat_text


EMITTERS = {
    "c": ("c", emit_c), "cpp": ("cpp", emit_cpp), "fortran": ("f90", emit_fortran),
    "zig": ("zig", emit_zig), "rust": ("rs", emit_rust), "carbon": ("carbon", emit_carbon),
}
