// Model 7: Heston (1993)  vs  QuantLib::AnalyticHestonEngine
#include "common.hpp"

TEST(Heston, BranchSafeCallMatchesAnalyticHestonEngine) {
    Tracker tr("Heston call_trap vs AnalyticHestonEngine", 1e-9, 1e-10);
    for (auto c : grids::heston())
        tr.check(wwmath::gen::albrecher2007_call_trap(c.S, c.v, c.kappa, c.theta, c.sigma, c.rho,
                                                   0.0, c.K, c.r, c.T),
                 qlsetup::heston_call(c), "T=" + std::to_string(c.T));
}

TEST(Heston, Eq17AsPrintedMatchesWhereNoBranchCrossing) {
    Tracker tr("Heston eq.(17) as printed, T<=1", 1e-9, 1e-10);
    for (auto c : grids::heston())
        if (c.T <= 1.0)
            tr.check(wwmath::gen::heston1993_call(c.S, c.v, c.kappa, c.theta, c.sigma, c.rho,
                                                  0.0, c.K, c.r, c.T),
                     qlsetup::heston_call(c), "T=" + std::to_string(c.T));
}

TEST(Heston, Eq17AsPrintedCrossesTheBranchCutAtTau2) {
    // The documented "little Heston trap": kappa=1.5, sigma=0.3, rho=-0.7, tau=2, ATM.
    const grids::Heston c{100.0, 0.04, 1.5, 0.04, 0.3, -0.7, 0.03, 100.0, 2.0};
    const double printed = wwmath::gen::heston1993_call(c.S, c.v, c.kappa, c.theta, c.sigma,
                                                        c.rho, 0.0, c.K, c.r, c.T);
    const double ql_price = qlsetup::heston_call(c);
    std::printf("  [Heston little trap] printed (17) %.6f, QuantLib %.6f, diff %.4f\n", printed,
                ql_price, printed - ql_price);
    EXPECT_NEAR(std::abs(printed - ql_price), 0.064, 0.001);
}
