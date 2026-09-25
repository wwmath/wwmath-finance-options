// Shared helpers: QuantLib instrument setup, and a tracker that reports the worst
// relative difference per test so every run prints how close each model is.
#pragma once

#include <gtest/gtest.h>

#include <ql/exercise.hpp>
#include <ql/instruments/vanillaoption.hpp>
#include <ql/models/equity/batesmodel.hpp>
#include <ql/models/equity/hestonmodel.hpp>
#include <ql/pricingengines/vanilla/analytichestonengine.hpp>
#include <ql/pricingengines/vanilla/batesengine.hpp>
#include <ql/processes/batesprocess.hpp>
#include <ql/processes/hestonprocess.hpp>
#include <ql/quotes/simplequote.hpp>
#include <ql/settings.hpp>
#include <ql/termstructures/yield/flatforward.hpp>
#include <ql/time/daycounters/actual365fixed.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>

#include "wwmath/generated/formulas.hpp"
#include "grids.hpp"

namespace ql = QuantLib;

/// Accumulates |ours - theirs| against tolerance max(abs_tol, rel_tol * |theirs|)
/// and prints the worst relative difference when the test ends.
class Tracker {
  public:
    Tracker(std::string name, double rel_tol, double abs_tol = 0.0)
        : name_(std::move(name)), rel_(rel_tol), abs_(abs_tol) {}
    ~Tracker() {
        std::printf("  [%-38s] %4d cases, max rel diff %.1e (tol %.0e)\n", name_.c_str(), n_,
                    worst_, rel_);
    }
    void check(double ours, double theirs, const std::string& what) {
        ++n_;
        const double diff = std::abs(ours - theirs);
        const double rel = diff / std::max(std::abs(theirs), 1e-300);
        if (std::abs(theirs) > abs_) worst_ = std::max(worst_, rel);
        EXPECT_LE(diff, std::max(abs_, rel_ * std::abs(theirs)))
            << what << ": ours " << ours << " QuantLib " << theirs;
    }
  private:
    std::string name_;
    double rel_, abs_, worst_ = 0.0;
    int n_ = 0;
};

namespace qlsetup {

/// Maturity date for a year fraction that must be a whole number of days (Act/365F).
inline ql::Date maturity(double T, ql::Date& today) {
    today = ql::Date(15, ql::January, 2026);
    ql::Settings::instance().evaluationDate() = today;
    const auto days = static_cast<ql::Integer>(std::lround(T * 365.0));
    EXPECT_NEAR(days / 365.0, T, 1e-12) << "T must be whole days under Act/365F";
    return today + days;
}

inline ql::Handle<ql::YieldTermStructure> flat(const ql::Date& today, double rate) {
    return ql::Handle<ql::YieldTermStructure>(
        ql::ext::make_shared<ql::FlatForward>(today, rate, ql::Actual365Fixed()));
}

inline double heston_call(const grids::Heston& c) {
    ql::Date today;
    const ql::Date mat = maturity(c.T, today);
    auto process = ql::ext::make_shared<ql::HestonProcess>(
        flat(today, c.r), flat(today, 0.0),
        ql::Handle<ql::Quote>(ql::ext::make_shared<ql::SimpleQuote>(c.S)),
        c.v, c.kappa, c.theta, c.sigma, c.rho);
    ql::VanillaOption opt(ql::ext::make_shared<ql::PlainVanillaPayoff>(ql::Option::Call, c.K),
                          ql::ext::make_shared<ql::EuropeanExercise>(mat));
    opt.setPricingEngine(ql::ext::make_shared<ql::AnalyticHestonEngine>(
        ql::ext::make_shared<ql::HestonModel>(process), 1e-12, 1000000));
    return opt.NPV();
}

inline double bates_call(const grids::Bates& c) {
    ql::Date today;
    const ql::Date mat = maturity(c.T, today);
    // Bates: ln(1+k) ~ N(ln(1+kbar) - delta^2/2, delta^2); QuantLib: log jump ~ N(nu, delta^2)
    const double nu = std::log1p(c.kbar) - 0.5 * c.delta * c.delta;
    auto process = ql::ext::make_shared<ql::BatesProcess>(
        flat(today, c.r), flat(today, c.r - c.b),
        ql::Handle<ql::Quote>(ql::ext::make_shared<ql::SimpleQuote>(c.S)),
        c.V, c.betastar, c.alpha / c.betastar, c.sigma_v, c.rho, c.lambda, nu, c.delta);
    ql::VanillaOption opt(ql::ext::make_shared<ql::PlainVanillaPayoff>(ql::Option::Call, c.X),
                          ql::ext::make_shared<ql::EuropeanExercise>(mat));
    opt.setPricingEngine(ql::ext::make_shared<ql::BatesEngine>(
        ql::ext::make_shared<ql::BatesModel>(process), 192));
    return opt.NPV();
}

}  // namespace qlsetup
