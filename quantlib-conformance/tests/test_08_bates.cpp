// Model 8: Bates (1996)  vs  QuantLib::BatesEngine
#include "common.hpp"

TEST(Bates, CallMatchesBatesEngine) {
    Tracker tr("Bates call vs BatesEngine", 1e-9, 1e-10);
    for (auto c : grids::bates())
        tr.check(wwmath::gen::bates1996_call(c.S, c.V, c.T, c.X, c.b, c.r, c.lambda, c.kbar,
                                             c.alpha, c.betastar, c.sigma_v, c.rho, c.delta),
                 qlsetup::bates_call(c), "T=" + std::to_string(c.T));
}
