"""QuantLib adapters for `kind = "oracle"` checks (see research/references/quantlib.toml).

Each adapter takes QuantLib-named arguments (already evaluated from the check's
AST argument map) and returns one number. Nothing here is a model implementation.
"""
from __future__ import annotations

import QuantLib as ql

DAYS = 365


def _dates(T: float):
    today = ql.Date(15, ql.January, 2026)
    ql.Settings.instance().evaluationDate = today
    days = round(T * DAYS)
    if abs(days / DAYS - T) > 1e-12:
        raise ValueError(f"T = {T} is not a whole number of days under Actual/365 (Fixed)")
    return today, today + days


def _curve(today, rate: float):
    return ql.YieldTermStructureHandle(ql.FlatForward(today, rate, ql.Actual365Fixed(),
                                                      ql.Continuous))


def _opt(kind: str):
    return {"call": ql.Option.Call, "put": ql.Option.Put}[kind]


def black_formula(a: dict) -> float:
    return ql.blackFormula(_opt(a.get("type", "call")), a["strike"], a["forward"], a["stdDev"],
                           a["discount"])


def bachelier_formula(a: dict) -> float:
    return ql.bachelierBlackFormula(_opt(a.get("type", "call")), a["strike"], a["forward"],
                                    a["stdDev"], a["discount"])


def sabr_volatility(a: dict) -> float:
    return ql.sabrVolatility(a["strike"], a["forward"], a["expiryTime"], a["alpha"], a["beta"],
                             a["nu"], a["rho"])


def _european(today, maturity, strike: float, kind: str = "call"):
    return ql.VanillaOption(ql.PlainVanillaPayoff(_opt(kind), strike),
                            ql.EuropeanExercise(maturity))


def heston_call(a: dict) -> float:
    today, maturity = _dates(a["T"])
    process = ql.HestonProcess(_curve(today, a["r"]), _curve(today, a["q"]),
                               ql.QuoteHandle(ql.SimpleQuote(a["s0"])),
                               a["v0"], a["kappa"], a["theta"], a["sigma"], a["rho"])
    opt = _european(today, maturity, a["strike"])
    opt.setPricingEngine(ql.AnalyticHestonEngine(ql.HestonModel(process), 1e-12, 1_000_000))
    return opt.NPV()


def bates_call(a: dict) -> float:
    today, maturity = _dates(a["T"])
    process = ql.BatesProcess(_curve(today, a["r"]), _curve(today, a["q"]),
                              ql.QuoteHandle(ql.SimpleQuote(a["s0"])),
                              a["v0"], a["kappa"], a["theta"], a["sigma"], a["rho"],
                              a["lambda"], a["nu"], a["delta"])
    opt = _european(today, maturity, a["strike"])
    opt.setPricingEngine(ql.BatesEngine(ql.BatesModel(process), 192))
    return opt.NPV()


ADAPTERS = {f.__name__: f for f in (black_formula, bachelier_formula, sabr_volatility,
                                    heston_call, bates_call)}
