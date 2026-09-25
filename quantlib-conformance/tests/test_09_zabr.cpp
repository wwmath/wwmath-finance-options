// Model 9: ZABR (Andreasen-Huge 2011)  vs  QuantLib::ZabrModel::normalVolatility
// Our side: y from the paper's y = z^{gamma-2} int_k^s du / sigma(u)  (generated),
// f from the paper's ODE f' = F(y, f), f(0) = 0  (F generated, integrated here by RK4),
// then x = z^{1-gamma} f(y) and v = (s - k) / x.
// Parameter mapping: QuantLib rescales its input nu to nu * alpha^{1 - gamma} before using
// it as the ODE's vol-of-vol, so the paper's epsilon = nu_QL * alpha^{1 - gamma}.
#include <ql/termstructures/volatility/zabr.hpp>
#include "common.hpp"

namespace {

double solve_f(double y_end, double rho, double eps, double gamma) {
    const int n = 20000;
    const double h = y_end / n;
    double y = 0.0, f = 0.0;
    auto F = [&](double yy, double ff) { return wwmath::gen::zabr_F(rho, eps, gamma, ff, yy); };
    for (int i = 0; i < n; ++i) {
        const double k1 = F(y, f), k2 = F(y + h / 2, f + h * k1 / 2),
                     k3 = F(y + h / 2, f + h * k2 / 2), k4 = F(y + h, f + h * k3);
        f += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6;
        y += h;
    }
    return f;
}

}  // namespace

TEST(Zabr, OdeSolutionMatchesZabrModelNormalVolatility) {
    // QuantLib integrates with AdaptiveRungeKutta(eps = 1e-8), which bounds the agreement.
    Tracker tr("ZABR ODE (8) vs ZabrModel normalVol", 1e-6);
    for (auto c : grids::zabr()) {
        const double eps = c.nu * std::pow(c.alpha, 1.0 - c.gamma);
        const double y = wwmath::gen::zabr_zabr_y(c.f, c.alpha, c.K, c.gamma, 1.0, c.beta);
        const double x = std::pow(c.alpha, 1.0 - c.gamma) * solve_f(y, c.rho, eps, c.gamma);
        const double ours = (c.f - c.K) / x;
        ql::ZabrModel m(c.T, c.f, c.alpha, c.beta, c.nu, c.rho, c.gamma);
        tr.check(ours, m.normalVolatility(c.K), "gamma=" + std::to_string(c.gamma));
    }
}

TEST(Zabr, GammaOneClosedFormMatchesOdeSolution) {
    // At gamma = 1 the paper's (7) closed form must equal the ODE route above.
    Tracker tr("ZABR (7) closed form vs ODE at g=1", 1e-9);
    for (auto c : grids::zabr()) {
        if (c.gamma != 1.0) continue;
        const double y = wwmath::gen::zabr_zabr_y(c.f, c.alpha, c.K, 1.0, 1.0, c.beta);
        const double x = solve_f(y, c.rho, c.nu, 1.0);
        tr.check(wwmath::gen::zabr_sabr_v(c.f, c.alpha, c.K, c.rho, c.nu, 1.0, c.beta),
                 (c.f - c.K) / x, "");
    }
}
