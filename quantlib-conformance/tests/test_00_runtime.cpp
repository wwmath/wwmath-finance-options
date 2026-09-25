// The generated code's only numerical dependency: check the integrator and N/n directly.
#include "common.hpp"

TEST(Runtime, GaussKronrodWeightsSumToTwo) {
    double s = ww::detail::WGK[7];
    for (int j = 0; j < 7; ++j) s += 2 * ww::detail::WGK[j];
    EXPECT_NEAR(s, 2.0, 1e-15);
}

TEST(Runtime, IntegratesKnownIntegrals) {
    EXPECT_NEAR(ww::integrate([](double x) { return std::exp(-x); }, 0.0, ww::INF), 1.0, 1e-13);
    EXPECT_NEAR(ww::integrate([](double x) { return ww::n(x); }, -ww::INF, ww::INF), 1.0, 1e-13);
    EXPECT_NEAR(ww::integrate([](double x) { return std::sin(x); }, 0.0, ww::PI), 2.0, 1e-13);
    EXPECT_NEAR(ww::integrate([](double x) { return 1.0 / (1.0 + x * x); }, 0.0, ww::INF),
                ww::PI / 2, 1e-12);
}

TEST(Runtime, NormalCdf) {
    EXPECT_NEAR(ww::N(0.0), 0.5, 1e-16);
    EXPECT_NEAR(ww::N(1.959963984540054), 0.975, 1e-15);
    EXPECT_NEAR(ww::N(-8.0), 6.22096057427178e-16, 1e-28);
}
