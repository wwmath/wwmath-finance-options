// Model 5: SABR Hagan lognormal  vs  QuantLib::sabrVolatility (unsafeSabrLogNormalVolatility)
// (2.17) is 0/0 at K = f exactly; there the paper's own ATM formula (2.18) is compared.
#include <ql/termstructures/volatility/sabr.hpp>
#include "common.hpp"

TEST(SabrLognormal, Hagan217MatchesSabrVolatility) {
    Tracker tr("SABR (2.17) vs sabrVolatility", 1e-12);
    for (auto c : grids::sabr())
        tr.check(wwmath::gen::hagan2002_sigma_B(c.f, c.K, c.alpha, c.beta, c.nu, c.rho, c.T),
                 ql::sabrVolatility(c.K, c.f, c.T, c.alpha, c.beta, c.nu, c.rho), "");
}

TEST(SabrLognormal, AtmFormula218MatchesAtTheMoney) {
    Tracker tr("SABR (2.18) vs sabrVolatility at K=f", 1e-12);
    for (auto c : grids::sabr())
        tr.check(wwmath::gen::hagan2002_sigma_ATM(c.f, c.alpha, c.beta, c.nu, c.rho, c.T),
                 ql::sabrVolatility(c.f, c.f, c.T, c.alpha, c.beta, c.nu, c.rho), "");
}
