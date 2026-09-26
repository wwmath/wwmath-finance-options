"""The as-of tree: every work lives in the folder of the date it became public.

    <century>/<decade>/<year>/<yyyymm>/<yyyymmdd>/<Name>/
    1900-99 / 1900-1909 / 1900 / 190003 / 19000329 / Bachelier /
        asof.toml       the work: as-of date + precision, the event on that date, later
                        events, bibliographic record, files
        formulas.toml   the Math AST library entry (only for works we transcribe)
        *.pdf           the source, when we hold a copy

A leaf may import only leaves whose as-of date is on or before its own, so a snapshot
at any date never sees later mathematics. When only the month (or issue) is known the
day folder is 01 and asof.toml records the precision.
"""
from __future__ import annotations

import glob
import os
import tomllib

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEAF_GLOB = os.path.join(REPO, "[0-9][0-9][0-9][0-9]-99", "*", "*", "*", "*", "*", "asof.toml")


def leaf_path(date: str, name: str) -> str:
    """'1900-03-29', 'Bachelier' -> '1900-99/1900-1909/1900/190003/19000329/Bachelier'."""
    y, m, d = (int(x) for x in date.split("-"))
    century, decade = y // 100 * 100, y // 10 * 10
    return os.path.join(f"{century}-99", f"{decade}-{decade + 9}", f"{y}", f"{y}{m:02d}",
                        f"{y}{m:02d}{d:02d}", name)


def leaves() -> dict[str, dict]:
    """work id -> {"dir": absolute leaf dir, "asof": parsed asof.toml}."""
    out = {}
    for p in sorted(glob.glob(LEAF_GLOB)):
        with open(p, "rb") as fh:
            meta = tomllib.load(fh)
        wid = meta["work"]["id"]
        if wid in out:
            raise ValueError(f"duplicate work id {wid}: {p}")
        d = os.path.dirname(p)
        expected = os.path.join(REPO, leaf_path(meta["as_of"]["date"], meta["work"]["name"]))
        if os.path.normpath(d) != os.path.normpath(expected):
            raise ValueError(f"{p}: as_of.date / work.name do not match its folder")
        out[wid] = {"dir": d, "asof": meta}
    return out


def as_of(wid: str, index: dict | None = None) -> str:
    index = index if index is not None else leaves()
    return index[wid]["asof"]["as_of"]["date"]
