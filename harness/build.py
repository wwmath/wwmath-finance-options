"""Build the Cross-Language Heston WASM Conformance Harness.

    Domain AST (research/papers/sidani2014.toml)
       -> Typed Math IR (research/tools/ir.py)
       -> C, C++, Fortran, Zig, Rust, Carbon sources + direct WASM (research/tools/emitters.py)
       -> engines/*.wasm, compiled independently, plus the Rust wasm-bindgen host

Usage:  python harness/build.py            # emit + compile + host + reference prices
        python harness/build.py --no-host  # skip the cargo/wasm-bindgen host build
Needs: clang/wasm-ld 18, flang-new-18, zig 0.13 (pip ziglang), rustc with
wasm32-unknown-unknown, wasm-bindgen-cli 0.2.100, wabt.
"""
from __future__ import annotations

import argparse
import json
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
from validate import Library  # noqa: E402
from mathast import evaluate_real  # noqa: E402

GEN = os.path.join(HERE, "generated")
WEB = os.path.join(HERE, "web")
ENG = os.path.join(WEB, "engines")


def sh(cmd: list[str], **kw) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def zig() -> list[str]:
    return [shutil.which("zig")] if shutil.which("zig") else [sys.executable, "-m", "ziglang"]


def compile_engine(lang: str, src: str, name: str, out: str) -> str:
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
        # flang 18 has no wasm32 code generator yet: use its front end to produce LLVM IR,
        # then let LLVM's wasm32 back end lower that IR. Sound here because the kernel is
        # scalar-only straight-line code with no Fortran runtime calls (asserted below).
        ll = os.path.join(tmp, "fortran.ll")
        sh(["flang-new-18", "-fc1", "-emit-llvm", "-O2", src, "-o", ll])
        text = open(ll).read()
        calls = set(re.findall(r"call [^@]*@([A-Za-z_][\w.]*)", text))
        bad = {c for c in calls if not c.startswith("llvm.")}
        if bad or "_Fortran" in text:
            raise RuntimeError(f"Fortran kernel needs runtime symbols {bad}; cannot retarget")
        text = re.sub(r"^target (datalayout|triple) = .*$", "", text, flags=re.M)
        ll_wasm = os.path.join(tmp, "fortran_wasm.ll")
        open(ll_wasm, "w").write(text)
        obj = os.path.join(tmp, "fortran.o")
        sh(["clang-18", "--target=wasm32", "-O2", "-Wno-override-module", "-c", ll_wasm, "-o", obj])
        sh(["wasm-ld-18", "--no-entry", f"--export={name}", "--export-memory", obj, "-o", out])
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


def check_module(path: str, name: str, nparams: int) -> None:
    dump = sh(["wasm-objdump", "-x", path])
    if "Import[" in dump:
        raise RuntimeError(f"{path} imports symbols; engines must be self-contained\n{dump}")
    sig = "(" + ", ".join(["f64"] * nparams + ["i32"]) + ") -> nil"
    if sig not in dump or f'-> "{name}"' not in dump or '-> "memory"' not in dump:
        raise RuntimeError(f"{path} does not export {name}{sig} and memory\n{dump}")
    sh(["wasm-validate", path])


def reference_prices(lib: Library, d: dict) -> list[float]:
    """Sidani (derived) Fourier price for the default parameters, per strike."""
    paper, rhs = lib.formula("sidani2014.call")
    out = []
    for K in d["strikes"]:
        env = {"F": d["x"], "K": K, "v": d["v"], "T": d["T"], "kappa": d["kappa"],
               "theta": d["theta"], "xi": d["xi"], "rho": d["rho"]}
        out.append(float(evaluate_real(rhs, env, paper.ctx)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-host", action="store_true")
    args = ap.parse_args()
    spec = tomllib.load(open(os.path.join(HERE, "kernel.toml"), "rb"))
    kspec, abi, engines = spec["kernel"], spec["abi"], spec["engines"]

    lib = Library()
    paper = lib.papers[kspec["paper"]]
    kernel = ir.euler_full_truncation(kspec["name"], paper, kspec["sde"], kspec["correlation"],
                                      abi["params"], abi["rename"], abi["brownian"],
                                      abi["outputs"])
    unused = set(abi["params"]) - ir.used_params(kernel)
    if unused:
        raise RuntimeError(f"ABI parameters not used by the kernel: {unused}")

    shutil.rmtree(GEN, ignore_errors=True)
    os.makedirs(os.path.join(GEN, "src"))
    os.makedirs(ENG, exist_ok=True)
    os.makedirs(os.path.join(WEB, "src"), exist_ok=True)
    with open(os.path.join(GEN, "kernel.ir.json"), "w") as fh:
        json.dump(kernel, fh, indent=1)

    manifest = {"kernel": kspec["name"], "abi": abi, "order": engines["order"],
                "reference": engines["reference"], "labels": engines["labels"],
                "tiers": engines["tiers"], "engines": {}, "defaults": spec["defaults"],
                "source": kernel["source"]}
    for lang in engines["order"]:
        if lang == "wasm":
            binary, wat = emitters.emit_wasm(kernel)
            src_name = f"{kspec['name']}.wat"
            open(os.path.join(GEN, "src", src_name), "w").write(wat)
            out = os.path.join(ENG, "wasm.wasm")
            open(out, "wb").write(binary)
            sh(["wat2wasm", os.path.join(GEN, "src", src_name), "-o",
                os.path.join(GEN, "obj_wat.wasm")])
            note = "direct binary encoder (research/tools/emitters.py); WAT checked by wat2wasm"
        else:
            ext, fn = emitters.EMITTERS[lang]
            src_name = f"{kspec['name']}.{ext}"
            src = os.path.join(GEN, "src", src_name)
            open(src, "w").write(fn(kernel))
            if lang == "carbon":
                shutil.copy(src, os.path.join(WEB, "src", src_name))
                manifest["engines"][lang] = {"wasm": None, "source": f"src/{src_name}",
                                             "toolchain": "none available (experimental tier)"}
                print(f"  {lang:8s} source only")
                continue
            out = os.path.join(ENG, f"{lang}.wasm")
            note = compile_engine(lang, src, kspec["name"], out)
        check_module(out, kspec["name"], len(abi["params"]))
        shutil.copy(os.path.join(GEN, "src", src_name), os.path.join(WEB, "src", src_name))
        manifest["engines"][lang] = {"wasm": f"engines/{os.path.basename(out)}",
                                     "source": f"src/{src_name}", "toolchain": note,
                                     "bytes": os.path.getsize(out)}
        print(f"  {lang:8s} {os.path.getsize(out):6d} bytes  {note}")

    d = spec["defaults"]
    manifest["fourier_reference"] = {"strikes": d["strikes"], "prices": reference_prices(lib, d),
                                     "formula": "sidani2014.call"}
    sample = {"x": d["x"], "v": d["v"], "dt": d["T"] / d["steps"], "kappa": d["kappa"],
              "theta": d["theta"], "xi": d["xi"], "rho": d["rho"], "z1": 0.3, "z2": -1.1}
    manifest["ir_sample"] = {"inputs": sample, "outputs": ir.run(kernel, sample)}
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
    for f in ("obj_wat.wasm",):
        p = os.path.join(GEN, f)
        if os.path.exists(p):
            os.remove(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
