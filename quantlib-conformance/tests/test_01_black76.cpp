// Model 1: Black-76 lognormal  vs  QuantLib::blackFormula
#include <ql/pricingengines/blackformula.hpp>
#include "common.hpp"

TEST(Black76, CallMatchesBlackFormula) {
    Tracker tr("Black-76 call vs blackFormula", 1e-12, 1e-14);
    for (auto c : grids::black()) {
        const double ours = wwmath::gen::black1976_call(c.F, c.K, c.s, c.t, c.r);
        const double theirs = ql::blackFormula(ql::Option::Call, c.K, c.F, c.s * std::sqrt(c.t),
                                               std::exp(-c.r * c.t));
        tr.check(ours, theirs, "call K=" + std::to_string(c.K));
    }
}

TEST(Black76, PutMatchesBlackFormula) {
    Tracker tr("Black-76 put vs blackFormula", 1e-12, 1e-14);
    for (auto c : grids::black()) {
        const double ours = wwmath::gen::black1976_put(c.F, c.K, c.s, c.t, c.r);
        const double theirs = ql::blackFormula(ql::Option::Put, c.K, c.F, c.s * std::sqrt(c.t),
                                               std::exp(-c.r * c.t));
        tr.check(ours, theirs, "put K=" + std::to_string(c.K));
    }
}
