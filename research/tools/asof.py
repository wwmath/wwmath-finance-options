"""The as-of tree: every work lives in the folder of the date it became public.

    <century>/<decade>/<year>/<yyyymm>/<yyyymmdd>/<Name>/
    1900-99 / 1900-1909 / 1900 / 190003 / 19000329 / Bachelier /
    1200-99 / 1200-1209 / 1202 / 120201 / 12020101 / Fibonacci /
    0300-99BC / 0300-0309BC / 0300BC / 0300BC01 / 0300BC0101 / Euclid /

        asof.toml       the work: as-of date + precision, the event on that date, later
                        events, bibliographic record, files
        formulas.toml   the Math AST library entry (only for works we transcribe)
        *.pdf           the source, when we hold a copy

Dates are 'YYYY-MM-DD' (AD) or 'YYYY-MM-DD BC'. BC years are counted as historians
count them (there is no year 0); folders carry a BC suffix and chronological order comes
from sort_key(), not from folder names. When only the month, issue, year or an
approximate date is known, the missing parts are 01 and asof.toml records the precision.

A leaf may import only leaves whose as-of date is on or before its own, so a snapshot
at any date never sees later mathematics.
"""
from __future__ import annotations

import glob
import os
import re
import tomllib

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOP = re.compile(r"^\d{4}-99(BC)?$")
PRECISIONS = {"day", "month", "issue", "year", "circa"}


def parse(date: str) -> tuple[int, int, int, bool]:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})( BC)?", date)
    if not m:
        raise ValueError(f"bad as-of date {date!r}: use 'YYYY-MM-DD' or 'YYYY-MM-DD BC'")
    y, mo, d = int(m[1]), int(m[2]), int(m[3])
    if y == 0:
        raise ValueError("there is no year 0: 1 BC is followed by AD 1")
    return y, mo, d, bool(m[4])


def sort_key(date: str) -> tuple[int, int, int]:
    """Chronological order: BC years are negative (300 BC -> -300)."""
    y, mo, d, bc = parse(date)
    return (-y if bc else y, mo, d)


def leaf_path(date: str, name: str) -> str:
    """'1900-03-29', 'Bachelier' -> '1900-99/1900-1909/1900/190003/19000329/Bachelier'."""
    y, m, d, bc = parse(date)
    sfx = "BC" if bc else ""
    century, decade = y // 100 * 100, y // 10 * 10
    return os.path.join(f"{century:04d}-99{sfx}", f"{decade:04d}-{decade + 9:04d}{sfx}",
                        f"{y:04d}{sfx}", f"{y:04d}{sfx}{m:02d}", f"{y:04d}{sfx}{m:02d}{d:02d}", name)


def leaves() -> dict[str, dict]:
    """work id -> {"dir": absolute leaf dir, "asof": parsed asof.toml}, in date order."""
    found = []
    for p in glob.glob(os.path.join(REPO, "*", "*", "*", "*", "*", "*", "asof.toml")):
        if not TOP.match(os.path.relpath(p, REPO).split(os.sep)[0]):
            continue
        with open(p, "rb") as fh:
            meta = tomllib.load(fh)
        d = os.path.dirname(p)
        date = meta["as_of"]["date"]
        expected = os.path.join(REPO, leaf_path(date, meta["work"]["name"]))
        if os.path.normpath(d) != os.path.normpath(expected):
            raise ValueError(f"{p}: as_of.date / work.name do not match its folder")
        if meta["as_of"]["precision"] not in PRECISIONS:
            raise ValueError(f"{p}: precision must be one of {sorted(PRECISIONS)}")
        found.append((sort_key(date), meta["work"]["id"], d, meta))
    out = {}
    for _, wid, d, meta in sorted(found):
        if wid in out:
            raise ValueError(f"duplicate work id {wid}")
        out[wid] = {"dir": d, "asof": meta}
    return out


def as_of(wid: str, index: dict | None = None) -> str:
    index = index if index is not None else leaves()
    return index[wid]["asof"]["as_of"]["date"]
