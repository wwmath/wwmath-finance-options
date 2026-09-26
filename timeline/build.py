"""Build the WWMath time machine: timeline/data.js from the as-of tree.

Every item on the timeline is a leaf (research/tools/asof.py); every formula shown is
read from that leaf's formulas.toml. Nothing about a work is typed into the page.

    python timeline/build.py                      # links point at the current git branch
    python timeline/build.py --ref main           # links point at another branch or tag
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "research", "tools"))

import asof  # noqa: E402

GITHUB = "https://github.com/wwmath/wwmath-finance-options"

LANES = [
    {"id": "foundations", "label": "Foundations", "note": "Geometry, number, merchant arithmetic"},
    {"id": "normal", "label": "Normal dynamics", "note": "Arithmetic (Bachelier) price processes"},
    {"id": "lognormal", "label": "Lognormal dynamics", "note": "Black, Heston, Bates"},
    {"id": "smile", "label": "Smile expansions", "note": "SABR and its extensions"},
]


def iso(date: str) -> str:
    """As-of date -> ISO 8601 expanded year that JavaScript's Date parses (1 BC = year 0)."""
    y, m, d, bc = asof.parse(date)
    astro = 1 - y if bc else y
    return f"{'-' if astro < 0 else '+'}{abs(astro):06d}-{m:02d}-{d:02d}"


def label(date: str, precision: str) -> str:
    y, m, d, bc = asof.parse(date)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    year = f"{y} BC" if bc else f"{y}"
    if precision == "circa":
        return f"c. {year}"
    if precision == "year":
        return year
    if precision in ("month", "issue"):
        return f"{months[m - 1]} {year}"
    return f"{d} {months[m - 1]} {year}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", help="git branch or tag the links point at (default: current branch)")
    args = ap.parse_args()
    ref = args.ref or subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO,
                                     capture_output=True, text=True).stdout.strip()
    index = asof.leaves()
    works = []
    for wid, leaf in index.items():
        meta = leaf["asof"]
        rel = os.path.relpath(leaf["dir"], REPO)
        files = meta.get("files", {})
        paper, formulas, findings = {}, [], []
        if "formulas" in files:
            with open(os.path.join(leaf["dir"], files["formulas"]), "rb") as fh:
                doc = tomllib.load(fh)
            paper = doc["paper"]
            for f in doc.get("formulas", []):
                src = f.get("source", {})
                formulas.append({
                    "id": f["id"], "name": f["name"], "kind": f["kind"], "latex": f["latex"].strip(),
                    "equation": src.get("equation"), "page": src.get("page"),
                    "fidelity": src.get("fidelity"), "verified": src.get("verified_against_pdf", False),
                    "reference": src.get("reference"), "notes": f.get("notes"),
                    "uses_later_work": f.get("uses_later_work", [])})
            for c in doc.get("checks", []):
                if "expect_difference" in c:
                    findings.append(c["description"])
            n_checks = len(doc.get("checks", []))
        else:
            n_checks = 0
        pub = meta.get("publication", {})
        works.append({
            "id": wid, "name": meta["work"]["name"], "title": meta["work"]["title"],
            "authors": meta["work"].get("authors", []), "lane": meta["timeline"]["lane"],
            "date": meta["as_of"]["date"], "start": iso(meta["as_of"]["date"]),
            "precision": meta["as_of"]["precision"],
            "label": label(meta["as_of"]["date"], meta["as_of"]["precision"]),
            "event": meta["as_of"]["event"],
            "later": [{"date": e["date"], "start": iso(e["date"] if " " in e["date"] or
                                                        len(e["date"]) == 10 else e["date"] + "-01-01"),
                       "label": label(e["date"] if len(e["date"]) == 10 else e["date"] + "-01-01",
                                      e["precision"]),
                       "event": e["event"]} for e in meta.get("later_events", [])],
            "status": paper.get("transcription_status", "record only"),
            "imports": paper.get("imports", []), "imported_by": [],
            "formulas": formulas, "checks": n_checks, "findings": findings,
            "path": rel, "url": f"{GITHUB}/tree/{ref}/{rel}",
            "pdf": f"{GITHUB}/blob/{ref}/{rel}/{files['pdf']}" if "pdf" in files else None,
            "venue": " ".join(str(pub[k]) for k in ("venue", "volume") if k in pub),
            "pages": pub.get("pages"), "doi": pub.get("doi"), "landing": pub.get("landing"),
            "access": pub.get("access"), "role": pub.get("role"), "notes": pub.get("notes"),
        })
    by_id = {w["id"]: w for w in works}
    for w in works:
        for imp in w["imports"]:
            by_id[imp]["imported_by"].append(w["id"])
    with open(os.path.join(REPO, "research", "unfiled.toml"), "rb") as fh:
        unfiled = tomllib.load(fh).get("works", [])
    data = {"repository": GITHUB, "ref": ref, "lanes": LANES, "works": works,
            "unfiled": [{"id": u["id"], "title": u["title"], "reason": u["reason"]} for u in unfiled]}
    out = os.path.join(HERE, "data.js")
    with open(out, "w") as fh:
        fh.write("// GENERATED by timeline/build.py from the as-of tree. Do not edit.\n")
        fh.write("window.WWMATH = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print(f"wrote {os.path.relpath(out, REPO)}: {len(works)} works, "
          f"{sum(len(w['formulas']) for w in works)} formulas, links at {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
