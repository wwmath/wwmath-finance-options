// Model 3: Black-76 shifted lognormal  vs  QuantLib::blackFormula(..., displacement)
// Shifted Black is Black-76 on (F + d, K + d); our side applies the shift to the inputs.
#include <ql/pricingengines/blackformula.hpp>
#include "common.hpp"

TEST(Black76Shifted, MatchesBlackFormulaWithDisplacement) {
    Tracker tr("Shifted Black-76 vs blackFormula(displ.)", 1e-12, 1e-14);
    for (double d : grids::displacements())
        for (auto c : grids::black()) {
            const double ours = wwmath::gen::black1976_call(c.F + d, c.K + d, c.s, c.t, c.r);
            const double theirs = ql::blackFormula(ql::Option::Call, c.K, c.F,
                                                   c.s * std::sqrt(c.t), std::exp(-c.r * c.t), d);
            tr.check(ours, theirs, "d=" + std::to_string(d));
        }
}
