// Model 6: SABR shifted lognormal and normal.
//  * shifted: (2.17) on (f + d, K + d)  vs  QuantLib::shiftedSabrVolatility
//  * normal: the paper-level normal-vol expansion we hold is Andreasen-Huge (7), the exact
//    short-maturity solution (their ZABR paper, gamma = 1). QuantLib's own SABR-with-gamma=1,
//    ZabrModel::normalVolatility, uses the same closed form, so it must agree tightly.
//    QuantLib's unsafeSabrNormalVolatility is a different (Hagan-style, time-corrected)
//    expansion; it is compared at T -> 0 with a tolerance that records the expansion gap.
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

TEST(SabrNormal, ShortMaturityLimitOfUnsafeSabrNormalVolatility) {
    // Different expansions agree only to leading order; this pins the size of the gap.
    Tracker tr("SABR normal: A-H (7) vs sabrNormal T->0", 2e-3);
    for (auto c : grids::sabr()) {
        if (c.beta >= 1.0) continue;
        tr.check(wwmath::gen::zabr_sabr_v(c.f, c.alpha, c.K, c.rho, c.nu, 1.0, c.beta),
                 ql::unsafeSabrNormalVolatility(c.K, c.f, 0.0, c.alpha, c.beta, c.nu, c.rho), "");
    }
}
