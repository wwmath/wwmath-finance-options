// Model 4: Black-76 intrinsic  vs  QuantLib::blackFormula with stdDev = 0
#include <ql/pricingengines/blackformula.hpp>
#include "common.hpp"

TEST(Black76Intrinsic, MatchesBlackFormulaAtZeroStdDev) {
    Tracker tr("Black-76 intrinsic vs blackFormula(sd=0)", 1e-15, 1e-15);
    for (auto c : grids::black())
        tr.check(wwmath::gen::black1976_intrinsic(c.F, c.K, c.t, c.r),
                 ql::blackFormula(ql::Option::Call, c.K, c.F, 0.0, std::exp(-c.r * c.t)), "");
}

TEST(Black76Intrinsic, IsTheSmallVolLimitOfTheCall) {
    Tracker tr("Black-76 call(s=1e-9) -> intrinsic", 1e-9, 1e-9);
    for (auto c : grids::black())
        if (std::abs(c.F - c.K) > 1e-6)
            tr.check(wwmath::gen::black1976_call(c.F, c.K, 1e-9, c.t, c.r),
                     wwmath::gen::black1976_intrinsic(c.F, c.K, c.t, c.r), "");
}
