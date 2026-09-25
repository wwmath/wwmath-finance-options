// Model 6: SABR shifted lognormal and normal.
//  * shifted: (2.17) on (f + d, K + d)  vs  QuantLib::shiftedSabrVolatility
//  * normal: the paper-level normal-vol expansion we hold is Andreasen-Huge (7), the exact
//    short-maturity solution (their ZABR paper, gamma = 1). QuantLib's own SABR-with-gamma=1,
//    ZabrModel::normalVolatility, uses the same closed form, so it must agree tightly.
//    QuantLib's unsafeSabrNormalVolatility is a different (Hagan-style, time-corrected)
//    expansion; at T -> 0 it must agree near the money, and its gap in the wings is pinned.
#include <ql/termstructures/volatility/sabr.hpp>
#include <ql/termstructures/volatility/zabr.hpp>
#include "common.hpp"

TEST(SabrShifted, Hagan217OnShiftedInputsMatchesShiftedSabrVolatility) {
    Tracker tr("SABR shifted vs shiftedSabrVolatility", 1e-12);
    for (double d : grids::displacements())
        for (auto c : grids::sabr())
            tr.check(wwmath::gen::hagan2002_sigma_B(c.f + d, c.K + d, c.alpha, c.beta, c.nu,
                                                    c.rho, c.T),
                     ql::shiftedSabrVolatility(c.K, c.f, c.T, c.alpha, c.beta, c.nu, c.rho, d),
                     "d=" + std::to_string(d));
}

TEST(SabrNormal, AndreasenHuge7MatchesZabrAtGammaOne) {
    Tracker tr("SABR normal: A-H (7) vs ZabrModel(g=1)", 1e-10);
    for (auto c : grids::sabr()) {
        if (c.beta >= 1.0) continue;                         // ZabrModel y() needs beta < 1 here
        ql::ZabrModel m(c.T, c.f, c.alpha, c.beta, c.nu, c.rho, 1.0);
        // paper: z = alpha (today's vol), sigma(s) = c s^beta with c = 1, epsilon = nu
        tr.check(wwmath::gen::zabr_sabr_v(c.f, c.alpha, c.K, c.rho, c.nu, 1.0, c.beta),
                 m.normalVolatility(c.K), "");
    }
}

TEST(SabrNormal, AgreesWithUnsafeSabrNormalVolatilityNearTheMoney) {
    // Two different expansions agree to leading order near the money (measured <= 1e-5).
    Tracker tr("SABR normal: A-H (7) vs sabrNormal, ATM+-5%", 2e-5);
    for (auto c : grids::sabr()) {
        if (c.beta >= 1.0 || std::abs(c.K / c.f - 1.0) > 0.051) continue;
        tr.check(wwmath::gen::zabr_sabr_v(c.f, c.alpha, c.K, c.rho, c.nu, 1.0, c.beta),
                 ql::unsafeSabrNormalVolatility(c.K, c.f, 0.0, c.alpha, c.beta, c.nu, c.rho), "");
    }
}

TEST(SabrNormal, ExpansionGapInTheWingsIsBounded) {
    // NOT a conformance check. A-H (7) integrates sigma(u) = u^beta exactly; QuantLib's
    // unsafeSabrNormalVolatility (Hagan-style, via the Deloitte note) uses geometric-average
    // approximations, so the two diverge away from the money: measured max 1.2e-2 at
    // K/f = 0.5 or 2 with beta = 0, 2.5e-3 at beta = 0.5, 8.7e-4 at beta = 0.7. This pins the
    // gap so a change in either expansion shows up.
    Tracker tr("SABR normal: expansion gap, wings", 1.5e-2);
    for (auto c : grids::sabr()) {
        if (c.beta >= 1.0 || std::abs(c.K / c.f - 1.0) <= 0.051) continue;
        tr.check(wwmath::gen::zabr_sabr_v(c.f, c.alpha, c.K, c.rho, c.nu, 1.0, c.beta),
                 ql::unsafeSabrNormalVolatility(c.K, c.f, 0.0, c.alpha, c.beta, c.nu, c.rho), "");
    }
}
