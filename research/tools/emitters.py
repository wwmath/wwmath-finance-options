"""Language emitters for Typed Math IR kernels.

Every emitter prints the same binary operation tree, fully parenthesised, so the
floating-point operations and their order are identical in every language.
Tiers:
  1 (required conformance)  C, C++, Rust, Zig
  2 (numerical heritage)    Fortran
  3 (experimental)          Carbon  (source only until a toolchain is available)
  direct backend            WASM (binary encoded here, plus WAT text)
Flat ABI per kernel:  name(f64 states..., f64 dt, f64 params..., f64 randoms..., f64* out)
with out[i] = next value of state i. One module per language exports every kernel.
"""
from __future__ import annotations

import struct

from ir import IR, U64

HEADER = "Generated from the Math AST via the Typed Math IR -- do not edit."


def _num(v: float, lang: str) -> str:
    s = repr(float(v))
    if lang == "fortran":
        m, _, e = s.partition("e")
        return f"{m}_c_double" if not e else f"{m}e{e}_c_double"
    if lang == "zig" and "e" in s and "." not in s.split("e")[0]:
        m, _, e = s.partition("e")
        return f"{m}.0e{e}"
    return s


def expr(e: IR, lang: str) -> str:
    op = e["op"]
    if op == "const":
        return _num(e["value"], lang)
    if op == "u64":
        v = e["value"]
        return {"c": f"0x{v:X}ULL", "cpp": f"0x{v:X}ULL", "rust": f"0x{v:X}u64",
                "zig": f"@as(u64, 0x{v:X})", "carbon": f"0x{v:X}",
                "fortran": f"int(z'{v:X}', c_int64_t)"}[lang]
    if op == "var":
        return e["name"]
    a = [expr(x, lang) for x in e["args"]]
    if op in ("add", "sub", "mul", "div"):
        sym = {"add": "+", "sub": "-", "mul": "*", "div": "/"}[op]
        return f"({a[0]} {sym} {a[1]})"
    if op == "neg":
        return f"(-{a[0]})"
    fn = {
        "sqrt": {"c": "__builtin_sqrt({0})", "cpp": "__builtin_sqrt({0})", "fortran": "sqrt({0})",
                 "zig": "@sqrt({0})", "rust": "{0}.sqrt()", "carbon": "Math.Sqrt({0})"},
        "floor": {"c": "__builtin_floor({0})", "cpp": "__builtin_floor({0})",
                  "fortran": "real(floor({0}, c_int64_t), c_double)", "zig": "@floor({0})",
                  "rust": "{0}.floor()", "carbon": "Math.Floor({0})"},
        "max": {"c": "({0} > {1} ? {0} : {1})", "cpp": "({0} > {1} ? {0} : {1})",
                "fortran": "max({0}, {1})", "zig": "@max({0}, {1})", "rust": "{0}.max({1})",
                "carbon": "(if {0} > {1} then {0} else {1})"},
        "bits": {"c": "ww_bits({0})", "cpp": "ww_bits({0})", "fortran": None, "zig": "@as(u64, @bitCast({0}))",
                 "rust": "{0}.to_bits()", "carbon": "Core.BitCast({0}, u64)"},
        "from_bits": {"c": "ww_from_bits({0})", "cpp": "ww_from_bits({0})", "fortran": None, "zig": "@as(f64, @bitCast({0}))",
                      "rust": "f64::from_bits({0})", "carbon": "Core.BitCast({0}, f64)"},
        "u2f": {"c": "((double)({0}))", "cpp": "static_cast<double>({0})",
                "fortran": "real({0}, c_double)", "zig": "@as(f64, @floatFromInt({0}))",
                "rust": "({0} as f64)", "carbon": "({0} as f64)"},
        "f2u": {"c": "((unsigned long long)({0}))", "cpp": "static_cast<unsigned long long>({0})",
                "fortran": "int({0}, c_int64_t)", "zig": "@as(u64, @intFromFloat({0}))",
                "rust": "({0} as u64)", "carbon": "({0} as u64)"},
        "uadd": {"c": "({0} + {1})", "cpp": "({0} + {1})", "fortran": "({0} + {1})",
                 "zig": "({0} +% {1})", "rust": "{0}.wrapping_add({1})", "carbon": "({0} + {1})"},
        "uand": {"c": "({0} & {1})", "cpp": "({0} & {1})", "fortran": "iand({0}, {1})",
                 "zig": "({0} & {1})", "rust": "({0} & {1})", "carbon": "({0} & {1})"},
        "uor": {"c": "({0} | {1})", "cpp": "({0} | {1})", "fortran": "ior({0}, {1})",
                "zig": "({0} | {1})", "rust": "({0} | {1})", "carbon": "({0} | {1})"},
        "ushl": {"c": "({0} << {n})", "cpp": "({0} << {n})", "fortran": "shiftl({0}, {n})",
                 "zig": "({0} << {n})", "rust": "({0} << {n})", "carbon": "({0} << {n})"},
        "ushr": {"c": "({0} >> {n})", "cpp": "({0} >> {n})", "fortran": "shiftr({0}, {n})",
                 "zig": "({0} >> {n})", "rust": "({0} >> {n})", "carbon": "({0} >> {n})"},
    }[op][lang]
    if fn is None:
        raise ValueError(f"{op} must be a whole let in {lang} (emitted via EQUIVALENCE)")
    return fn.format(*a, n=e.get("amount"))


def _scalars(k: IR) -> list[str]:
    return [p["name"] for p in k["params"] if p["type"] == "f64"]


def _needs_bits(kernels: list[IR]) -> bool:
    return any(l["type"] == U64 for k in kernels for l in k["lets"])


C_HELPERS = """static inline unsigned long long ww_bits(double x) {
    unsigned long long u; __builtin_memcpy(&u, &x, 8); return u;
}
static inline double ww_from_bits(unsigned long long u) {
    double x; __builtin_memcpy(&x, &u, 8); return x;
}
"""


def _c_like(kernels: list[IR], lang: str) -> str:
    cpp = lang == "cpp"
    out = [f"// {HEADER}" if cpp else f"/* {HEADER} */"]
    if cpp:
        out.append("// Deliberately boring C++ subset; __builtin_sqrt is std::sqrt without a "
                   "libc++ sysroot.")
    out.append("")
    if _needs_bits(kernels):
        out.append(C_HELPERS)
    ty = {"f64": "double", U64: "unsigned long long"}
    for k in kernels:
        src = k["source"]
        out.append(("// " if cpp else "/* ") + f"{k['name']}: {src['scheme']} step of "
                   f"{', '.join(src['sde'])}" + ("" if cpp else " */"))
        args = ",\n    ".join([f"double {p}" for p in _scalars(k)] +
                              ["double* output" if cpp else "double *output"])
        ext = 'extern "C" ' if cpp else ""
        out.append(f"{ext}__attribute__((export_name(\"{k['name']}\")))\n"
                   f"void {k['name']}(\n    {args})\n{{")
        out += [f"    const {ty[l['type']]} {l['name']} = {expr(l['expr'], lang)};"
                for l in k["lets"]]
        out += [f"    output[{s['index']}] = {expr(s['expr'], lang)};" for s in k["stores"]]
        out.append("}\n")
    return "\n".join(out)


def emit_c(kernels: list[IR]) -> str:
    return _c_like(kernels, "c")


def emit_cpp(kernels: list[IR]) -> str:
    return _c_like(kernels, "cpp")


def _wrap_f90(line: str, width: int = 100) -> str:
    if len(line) <= width or line.lstrip().startswith("!"):
        return line
    out, cur = [], line
    while len(cur) > width:
        cut = max(cur.rfind(" ", 0, width), cur.rfind(",", 0, width) + 1)
        out.append(cur[:cut] + " &")
        cur = "      & " + cur[cut:].lstrip()
    return "\n".join(out + [cur])


def emit_fortran(kernels: list[IR]) -> str:
    lines = [f"! {HEADER}",
             "! F77-style numerics. BIND(C)/VALUE (F2003) fix the flat ABI; bit reinterpretation",
             "! for the IR's exp/log uses F77 EQUIVALENCE (TRANSFER would call the Fortran",
             "! runtime); SHIFTL/SHIFTR/IAND/IOR are F2008 elementals. No runtime calls."]
    for k in kernels:
        sc = _scalars(k)
        lines += ["", f"subroutine {k['name']}({', '.join(sc)}, output) &",
                  f"    bind(c, name=\"{k['name']}\")",
                  "  use iso_c_binding, only: c_double, c_int64_t",
                  "  implicit none",
                  f"  real(c_double), value :: {', '.join(sc)}",
                  f"  real(c_double), intent(out) :: output({len(k['stores'])})"]
        reals = [l["name"] for l in k["lets"] if l["type"] == "f64"]
        ints = [l["name"] for l in k["lets"] if l["type"] == U64]
        for i in range(0, len(reals), 6):
            lines.append("  real(c_double) :: " + ", ".join(reals[i:i + 6]))
        for i in range(0, len(ints), 6):
            lines.append("  integer(c_int64_t) :: " + ", ".join(ints[i:i + 6]))
        if ints:
            lines += ["  real(c_double) :: ww_r", "  integer(c_int64_t) :: ww_i",
                      "  equivalence (ww_r, ww_i)"]
        for l in k["lets"]:
            op = l["expr"]["op"]
            if op == "bits":
                lines += [f"  ww_r = {expr(l['expr']['args'][0], 'fortran')}",
                          f"  {l['name']} = ww_i"]
            elif op == "from_bits":
                lines += [f"  ww_i = {expr(l['expr']['args'][0], 'fortran')}",
                          f"  {l['name']} = ww_r"]
            else:
                lines.append(f"  {l['name']} = {expr(l['expr'], 'fortran')}")
        lines += [f"  output({s['index'] + 1}) = {expr(s['expr'], 'fortran')}"
                  for s in k["stores"]]
        lines.append(f"end subroutine {k['name']}")
    return "\n".join(_wrap_f90(x) for x in lines) + "\n"


def emit_zig(kernels: list[IR]) -> str:
    out = [f"// {HEADER}", ""]
    for k in kernels:
        args = ",\n    ".join([f"{p}: f64" for p in _scalars(k)] + ["output: [*]f64"])
        out.append(f"export fn {k['name']}(\n    {args},\n) void {{")
        out += [f"    const {l['name']}: {l['type']} = {expr(l['expr'], 'zig')};"
                for l in k["lets"]]
        out += [f"    output[{s['index']}] = {expr(s['expr'], 'zig')};" for s in k["stores"]]
        out.append("}\n")
    return "\n".join(out)


def emit_rust(kernels: list[IR]) -> str:
    out = [f"// {HEADER}", "// Rust is the conformance reference.", ""]
    for k in kernels:
        args = ",\n    ".join([f"{p}: f64" for p in _scalars(k)] + ["output: *mut f64"])
        out.append("#[no_mangle]\n#[allow(clippy::too_many_arguments, clippy::all)]\n"
                   f"pub extern \"C\" fn {k['name']}(\n    {args},\n) {{")
        out += [f"    let {l['name']}: {l['type']} = {expr(l['expr'], 'rust')};"
                for l in k["lets"]]
        out += [f"    unsafe {{ *output.add({s['index']}) = {expr(s['expr'], 'rust')}; }}"
                for s in k["stores"]]
        out.append("}\n")
    return "\n".join(out)


def emit_carbon(kernels: list[IR]) -> str:
    out = [f"// {HEADER}",
           "// EXPERIMENTAL (Tier 3): Carbon has no stable toolchain or WASM target; this is",
           "// emitted from the same IR but is not compiled or run yet.", "",
           "package WwmathKernels api;", "", "import Math;", ""]
    for k in kernels:
        camel = "".join(w.capitalize() for w in k["name"].split("_"))
        args = ",\n    ".join([f"{p}: f64" for p in _scalars(k)] + ["output: f64*"])
        out.append(f"fn {camel}(\n    {args}) {{")
        out += [f"  let {l['name']}: {l['type']} = {expr(l['expr'], 'carbon')};"
                for l in k["lets"]]
        out += [f"  output[{s['index']}] = {expr(s['expr'], 'carbon')};" for s in k["stores"]]
        out.append("}\n")
    return "\n".join(out)


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


def _sleb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if (n == 0 and not b & 0x40) or (n == -1 and b & 0x40):
            out.append(b)
            return bytes(out)
        out.append(b | 0x80)


def _vec(items: list[bytes]) -> bytes:
    return _uleb(len(items)) + b"".join(items)


def _name(s: str) -> bytes:
    return _uleb(len(s.encode())) + s.encode()


def _section(sid: int, payload: bytes) -> bytes:
    return bytes([sid]) + _uleb(len(payload)) + payload


F64T, I64T, I32T = 0x7C, 0x7E, 0x7F
OPC = {"add": (0xA0, "f64.add"), "sub": (0xA1, "f64.sub"), "mul": (0xA2, "f64.mul"),
       "div": (0xA3, "f64.div"), "neg": (0x9A, "f64.neg"), "sqrt": (0x9F, "f64.sqrt"),
       "floor": (0x9C, "f64.floor"), "max": (0xA5, "f64.max"),
       "from_bits": (0xBF, "f64.reinterpret_i64"), "u2f": (0xBA, "f64.convert_i64_u"),
       "bits": (0xBD, "i64.reinterpret_f64"), "f2u": (0xB1, "i64.trunc_f64_u"),
       "uadd": (0x7C, "i64.add"), "uand": (0x83, "i64.and"), "uor": (0x84, "i64.or")}


def _func_body(k: IR) -> tuple[bytes, list[str], bytes]:
    sc = _scalars(k)
    idx = {p: i for i, p in enumerate(sc)}
    out_idx = len(sc)
    f_lets = [l for l in k["lets"] if l["type"] == "f64"]
    u_lets = [l for l in k["lets"] if l["type"] == U64]
    for j, l in enumerate(f_lets + u_lets):
        idx[l["name"]] = out_idx + 1 + j
    code, wat = bytearray(), []

    def gen(e: IR):
        op = e["op"]
        if op == "const":
            code.extend(b"\x44" + struct.pack("<d", e["value"]))
            wat.append(f"    f64.const {e['value']!r}")
        elif op == "u64":
            v = e["value"] - (1 << 64) if e["value"] >= 1 << 63 else e["value"]
            code.extend(b"\x42" + _sleb(v))
            wat.append(f"    i64.const {v}")
        elif op == "var":
            code.extend(b"\x20" + _uleb(idx[e["name"]]))
            wat.append(f"    local.get ${e['name']}")
        elif op in ("ushl", "ushr"):
            gen(e["args"][0])
            code.extend(b"\x42" + _sleb(e["amount"]))
            code.append(0x86 if op == "ushl" else 0x88)
            wat.append(f"    i64.const {e['amount']}")
            wat.append("    i64.shl" if op == "ushl" else "    i64.shr_u")
        else:
            for a in e["args"]:
                gen(a)
            code.append(OPC[op][0])
            wat.append(f"    {OPC[op][1]}")

    for l in k["lets"]:
        gen(l["expr"])
        code.extend(b"\x21" + _uleb(idx[l["name"]]))
        wat.append(f"    local.set ${l['name']}")
    for s in k["stores"]:
        code.extend(b"\x20" + _uleb(out_idx))
        wat.append(f"    local.get $output  ;; {s['name']}")
        gen(s["expr"])
        code.extend(b"\x39" + _uleb(3) + _uleb(8 * s["index"]))
        wat.append(f"    f64.store offset={8 * s['index']}")
    code.append(0x0B)
    groups = []
    if f_lets:
        groups.append(_uleb(len(f_lets)) + bytes([F64T]))
    if u_lets:
        groups.append(_uleb(len(u_lets)) + bytes([I64T]))
    body = _vec(groups) + bytes(code)
    params = " ".join(f"(param ${p} f64)" for p in sc) + " (param $output i32)"
    locs = " ".join([f"(local ${l['name']} f64)" for l in f_lets] +
                    [f"(local ${l['name']} i64)" for l in u_lets])
    header = f"  (func (export \"{k['name']}\") {params}\n    {locs}"
    ftype = b"\x60" + _vec([bytes([F64T])] * len(sc) + [bytes([I32T])]) + _vec([])
    return body, [header] + wat + ["  )"], ftype


def emit_wasm(kernels: list[IR]) -> tuple[bytes, str]:
    bodies, wats, types = [], [], []
    for k in kernels:
        body, wat, ftype = _func_body(k)
        bodies.append(_uleb(len(body)) + body)
        wats += wat
        types.append(ftype)
    exports = [_name(k["name"]) + b"\x00" + _uleb(i) for i, k in enumerate(kernels)]
    exports.append(_name("memory") + b"\x02" + _uleb(0))
    module = (b"\x00asm\x01\x00\x00\x00"
              + _section(1, _vec(types))
              + _section(3, _vec([_uleb(i) for i in range(len(kernels))]))
              + _section(5, _vec([b"\x00" + _uleb(1)]))
              + _section(7, _vec(exports))
              + _section(10, _vec(bodies)))
    wat_text = (f";; {HEADER}\n(module\n  (memory (export \"memory\") 1)\n"
                + "\n".join(wats) + "\n)\n")
    return module, wat_text


EMITTERS = {
    "c": ("c", emit_c), "cpp": ("cpp", emit_cpp), "fortran": ("f90", emit_fortran),
    "zig": ("zig", emit_zig), "rust": ("rs", emit_rust), "carbon": ("carbon", emit_carbon),
}
