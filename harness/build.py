"""Build the Cross-Language Heston WASM Conformance Harness.

    Domain AST (the as-of tree (*/formulas.toml) SDEs)
       -> Typed Math IR (research/tools/ir.py; Euler, full truncation)
       -> C, C++, Fortran, Zig, Rust, Carbon sources + direct WASM (research/tools/emitters.py)
       -> engines/<lang>.wasm (one independently compiled module per language, exporting
          every kernel) plus the Rust wasm-bindgen host
       -> manifest.json with per-kernel reference prices from our formula ASTs and QuantLib

Usage:  python harness/build.py            # emit + compile + host + reference prices
        python harness/build.py --no-host  # skip the cargo/wasm-bindgen host build
Needs: clang/wasm-ld 18, flang-new-18, zig 0.13 (pip ziglang), rustc with
wasm32-unknown-unknown, wasm-bindgen-cli 0.2.100, wabt; QuantLib (pip) for the
QuantLib reference column (optional).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "research", "tools"))

import emitters  # noqa: E402
import ir  # noqa: E402
from mathast import evaluate_real  # noqa: E402
from validate import Library  # noqa: E402

GEN = os.path.join(HERE, "generated")
WEB = os.path.join(HERE, "web")
ENG = os.path.join(WEB, "engines")
BASENAME = "kernels"


def sh(cmd: list[str], **kw) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def zig() -> list[str]:
    return [shutil.which("zig")] if shutil.which("zig") else [sys.executable, "-m", "ziglang"]


def compile_engine(lang: str, src: str, names: list[str], out: str) -> str:
    """Compile one emitted source to a standalone wasm32 module. Returns a toolchain note."""
    tmp = os.path.join(GEN, "obj")
    os.makedirs(tmp, exist_ok=True)
    common = ["-O2", "-ffp-contract=off", "-fno-math-errno", "-nostdlib",
              "-Wl,--no-entry", "-Wl,--export-memory"]
    if lang == "c":
        sh(["clang-18", "--target=wasm32", *common, src, "-o", out])
        return "clang 18 --target=wasm32"
    if lang == "cpp":
        sh(["clang++-18", "--target=wasm32", "-fno-exceptions", *common, src, "-o", out])
        return "clang++ 18 --target=wasm32"
    if lang == "fortran":
        # flang 18 has no wasm32 code generator: use its front end to produce LLVM IR, then
        # LLVM's wasm32 back end. Sound only because the kernels are straight-line scalar code
        # with no Fortran runtime calls, which is asserted here.
        ll = os.path.join(tmp, "fortran.ll")
        sh(["flang-new-18", "-fc1", "-emit-llvm", "-O2", src, "-o", ll])
        text = open(ll).read()
        calls = set(re.findall(r"call [^@]*@([A-Za-z_][\w.]*)", text))
        bad = {c for c in calls if not c.startswith("llvm.")}
        if bad or "_Fortran" in text:
            raise RuntimeError(f"Fortran kernels need runtime symbols {bad}; cannot retarget")
        text = re.sub(r"^target (datalayout|triple) = .*$", "", text, flags=re.M)
        ll_wasm = os.path.join(tmp, "fortran_wasm.ll")
        open(ll_wasm, "w").write(text)
        obj = os.path.join(tmp, "fortran.o")
        sh(["clang-18", "--target=wasm32", "-O2", "-Wno-override-module", "-c", ll_wasm, "-o", obj])
        sh(["wasm-ld-18", "--no-entry", *[f"--export={n}" for n in names], "--export-memory",
            obj, "-o", out])
        return "flang-new 18 (LLVM IR) -> LLVM wasm32 back end"
    if lang == "zig":
        sh([*zig(), "build-exe", src, "-target", "wasm32-freestanding", "-fno-entry", "-rdynamic",
            "-O", "ReleaseFast", "-fstrip", f"-femit-bin={out}"], cwd=tmp)
        if os.path.exists(out + ".o"):
            os.remove(out + ".o")
        return "zig 0.13 wasm32-freestanding"
    if lang == "rust":
        sh(["rustc", "--edition=2021", "--crate-type=cdylib", "--target=wasm32-unknown-unknown",
            "-C", "opt-level=3", "-C", "panic=abort", "-C", "strip=debuginfo", src, "-o", out])
        return "rustc --target wasm32-unknown-unknown"
    raise ValueError(lang)


def check_module(path: str, kernels: list[dict]) -> None:
    dump = sh(["wasm-objdump", "-x", path])
    if "Import[" in dump:
        raise RuntimeError(f"{path} imports symbols; engines must be self-contained\n{dump}")
    if '-> "memory"' not in dump:
        raise RuntimeError(f"{path} does not export memory")
    for k in kernels:
        n = sum(1 for p in k["params"] if p["type"] == "f64")
        sig = "(" + ", ".join(["f64"] * n + ["i32"]) + ") -> nil"
        if sig not in dump or f'-> "{k["name"]}"' not in dump:
            raise RuntimeError(f"{path} does not export {k['name']}{sig}\n{dump}")
    sh(["wasm-validate", path])


# ---------------------------------------------------------------------------
# Reference prices: our formula ASTs and QuantLib
# ---------------------------------------------------------------------------

def formula(lib: Library, fid: str, env: dict) -> float:
    paper, rhs = lib.formula(fid)
    return float(evaluate_real(rhs, env, paper.ctx))


def references(lib: Library, name: str, d: dict) -> dict:
    try:
        import quantlib_oracle as qo
    except ImportError:
        qo = None
    strikes = d["strikes"]
    out: dict = {"strikes": strikes}
    if name == "normal_heston_step":
        out["formula"] = {"id": "sidani2014.call", "label": "Sidani Fourier (derived)",
                          "prices": [formula(lib, "sidani2014.call", {
                              "F": d["x"], "K": K, "v": d["v"], "T": d["T"], "kappa": d["kappa"],
                              "theta": d["theta"], "xi": d["xi"], "rho": d["rho"]})
                              for K in strikes]}
        out["quantlib"] = None
    elif name == "heston_step":
        out["formula"] = {"id": "albrecher2007.call_trap", "label": "Heston (10), little-trap CF",
                          "prices": [formula(lib, "albrecher2007.call_trap", {
                              "S": d["s"], "v": d["v"], "kappa": d["kappa"], "theta": d["theta"],
                              "sigma": d["sigma"], "rho": d["rho"], "lambda": 0.0, "r": d["r"],
                              "K": K, "tau": d["T"]}) for K in strikes]}
        if qo:
            out["quantlib"] = {"label": "QuantLib AnalyticHestonEngine", "prices": [
                qo.heston_call({"s0": d["s"], "v0": d["v"], "kappa": d["kappa"],
                                "theta": d["theta"], "sigma": d["sigma"], "rho": d["rho"],
                                "r": d["r"], "q": 0.0, "strike": K, "T": d["T"]})
                for K in strikes]}
    elif name == "bates_step":
        out["formula"] = {"id": "bates1996.call", "label": "Bates Fourier",
                          "prices": [formula(lib, "bates1996.call", {
                              "S": d["s"], "V": d["v"], "T": d["T"], "b": d["b"], "r": d["r"],
                              "X": K, "lambdastar": d["lambdastar"], "kbarstar": d["kbarstar"],
                              "delta": d["delta"], "alpha": d["alpha"], "betastar": d["betastar"],
                              "sigma_v": d["sigma_v"], "rho": d["rho"]}) for K in strikes]}
        if qo:
            out["quantlib"] = {"label": "QuantLib BatesEngine", "prices": [
                qo.bates_call({"s0": d["s"], "v0": d["v"], "kappa": d["betastar"],
                               "theta": d["alpha"] / d["betastar"], "sigma": d["sigma_v"],
                               "rho": d["rho"], "r": d["r"], "q": d["r"] - d["b"],
                               "lambda": d["lambdastar"],
                               "nu": math.log1p(d["kbarstar"]) - d["delta"] ** 2 / 2,
                               "delta": d["delta"], "strike": K, "T": d["T"]})
                for K in strikes]}
    elif name == "sabr_step":
        prices, ql_prices = [], []
        for K in strikes:
            # (2.17) is 0/0 at exactly K = f; the paper's own ATM formula (2.18) covers it
            fid = "hagan2002.sigma_ATM" if K == d["f"] else "hagan2002.sigma_B"
            vol = formula(lib, fid, {"f": d["f"], "K": K, "alpha": d["alpha"],
                                     "beta": d["beta"], "nu": d["nu"], "rho": d["rho"],
                                     "t_ex": d["T"]})
            prices.append(formula(lib, "black1976.call", {"F": d["f"], "cstar": K, "s": vol,
                                                          "t": d["T"], "r": 0.0}))
            if qo:
                qv = qo.sabr_volatility({"strike": K, "forward": d["f"], "expiryTime": d["T"],
                                         "alpha": d["alpha"], "beta": d["beta"], "nu": d["nu"],
                                         "rho": d["rho"]})
                ql_prices.append(qo.black_formula({"strike": K, "forward": d["f"],
                                                   "stdDev": qv * math.sqrt(d["T"]),
                                                   "discount": 1.0}))
        out["formula"] = {"id": "hagan2002.sigma_B + black1976.call",
                          "label": "Hagan (2.17)/(2.18) -> Black-76", "prices": prices}
        if qo:
            out["quantlib"] = {"label": "QuantLib sabrVolatility -> blackFormula",
                               "prices": ql_prices}
    out.setdefault("quantlib", None)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-host", action="store_true")
    args = ap.parse_args()
    spec = tomllib.load(open(os.path.join(HERE, "kernel.toml"), "rb"))
    engines = spec["engines"]

    ulps = ir.ulp_check()
    if max(ulps.values()) > 1.0:
        raise RuntimeError(f"IR exp/log exceed 1 ulp: {ulps}")

    lib = Library()
    kernels = []
    for ks in spec["kernels"]:
        k = ir.euler_full_truncation(ks, lib.papers[ks["paper"]])
        unused = {p["name"] for p in k["params"] if p["type"] == "f64"} - ir.used_params(k)
        if unused:
            raise RuntimeError(f"{ks['name']}: ABI parameters not used: {unused}")
        kernels.append(k)
    names = [k["name"] for k in kernels]

    shutil.rmtree(GEN, ignore_errors=True)
    os.makedirs(os.path.join(GEN, "src"))
    shutil.rmtree(ENG, ignore_errors=True)
    os.makedirs(ENG)
    shutil.rmtree(os.path.join(WEB, "src"), ignore_errors=True)
    os.makedirs(os.path.join(WEB, "src"))
    with open(os.path.join(GEN, "kernels.ir.json"), "w") as fh:
        json.dump(kernels, fh, indent=1)

    manifest = {"order": engines["order"], "reference": engines["reference"],
                "labels": engines["labels"], "tiers": engines["tiers"], "engines": {},
                "ir_exp_log_max_ulp": ulps, "kernels": []}
    for lang in engines["order"]:
        if lang == "wasm":
            binary, wat = emitters.emit_wasm(kernels)
            src_name = f"{BASENAME}.wat"
            open(os.path.join(GEN, "src", src_name), "w").write(wat)
            out = os.path.join(ENG, "wasm.wasm")
            open(out, "wb").write(binary)
            sh(["wat2wasm", os.path.join(GEN, "src", src_name), "-o",
                os.path.join(GEN, "obj_wat.wasm")])
            note = "direct binary encoder (research/tools/emitters.py); WAT checked by wat2wasm"
        else:
            ext, fn = emitters.EMITTERS[lang]
            src_name = f"{BASENAME}.{ext}"
            src = os.path.join(GEN, "src", src_name)
            open(src, "w").write(fn(kernels))
            if lang == "carbon":
                shutil.copy(src, os.path.join(WEB, "src", src_name))
                manifest["engines"][lang] = {"wasm": None, "source": f"src/{src_name}",
                                             "toolchain": "none available (experimental tier)"}
                print(f"  {lang:8s} source only")
                continue
            out = os.path.join(ENG, f"{lang}.wasm")
            note = compile_engine(lang, src, names, out)
        check_module(out, kernels)
        shutil.copy(os.path.join(GEN, "src", src_name), os.path.join(WEB, "src", src_name))
        manifest["engines"][lang] = {"wasm": f"engines/{os.path.basename(out)}",
                                     "source": f"src/{src_name}", "toolchain": note,
                                     "bytes": os.path.getsize(out)}
        print(f"  {lang:8s} {os.path.getsize(out):6d} bytes  {note}")

    for ks, k in zip(spec["kernels"], kernels):
        d = ks["defaults"]
        abi = [p["name"] for p in k["params"] if p["type"] == "f64"]
        n_states = len(ks["sde"])
        sample = {p: d.get(p, 0.0) for p in abi}
        sample["dt"] = d["T"] / d["steps"]
        for i, r in enumerate(ks["randoms"]):
            sample[r["name"]] = [0.3, -1.1, -0.05][i]
        manifest["kernels"].append({
            "name": k["name"], "label": ks["label"], "source": k["source"], "abi": abi,
            "states": abi[:n_states], "params": ks["params"],
            "randoms": ks["randoms"], "jump": ks.get("jump"), "extra": ks.get("extra", []),
            "discount_rate": ks.get("discount_rate"), "defaults": d,
            "mc_bias_allowance": ks["mc_bias_allowance"],
            "ir_sample": {"inputs": sample, "outputs": ir.run(k, sample)},
            "references": references(lib, k["name"], d)})
        print(f"  kernel   {k['name']}: {len(k['lets'])} lets, ABI {len(abi)} x f64")
    with open(os.path.join(WEB, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)

    if not args.no_host:
        host = os.path.join(HERE, "host")
        sh(["cargo", "build", "--release", "--target", "wasm32-unknown-unknown"], cwd=host)
        wasm = os.path.join(host, "target", "wasm32-unknown-unknown", "release",
                            "conformance_host.wasm")
        sh(["wasm-bindgen", "--target", "web", "--no-typescript", "--out-dir",
            os.path.join(WEB, "pkg"), wasm])
        print("  host     wasm-bindgen -> web/pkg")
    shutil.rmtree(os.path.join(GEN, "obj"), ignore_errors=True)
    p = os.path.join(GEN, "obj_wat.wasm")
    if os.path.exists(p):
        os.remove(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
