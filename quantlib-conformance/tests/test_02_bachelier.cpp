// Model 2: Bachelier (normal)  vs  QuantLib::bachelierBlackFormula
#include <ql/pricingengines/blackformula.hpp>
#include "common.hpp"

TEST(Bachelier, CallAndPutMatchBachelierBlackFormula) {
    Tracker tr("Bachelier call/put vs bachelierBlackFormula", 1e-12, 1e-14);
    for (auto c : grids::bachelier()) {
        const double sd = c.sigma * std::sqrt(c.T);
        tr.check(wwmath::gen::bachelier1900_call(c.F, c.K, c.sigma, c.T),
                 ql::bachelierBlackFormula(ql::Option::Call, c.K, c.F, sd, 1.0), "call");
        tr.check(wwmath::gen::bachelier1900_put(c.F, c.K, c.sigma, c.T),
                 ql::bachelierBlackFormula(ql::Option::Put, c.K, c.F, sd, 1.0), "put");
    }
}
