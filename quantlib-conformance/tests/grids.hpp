// Parameter grids shared by the conformance tests and tools/export_fixtures.cpp, so the
// fixture CSVs contain exactly the cases the tests check.
#pragma once

#include <vector>

namespace grids {

struct Black { double F, K, s, t, r; };
struct Bachelier { double F, K, sigma, T; };
struct Sabr { double f, K, alpha, beta, nu, rho, T; };
struct Heston { double S, v, kappa, theta, sigma, rho, r, K, T; };
struct Bates { double S, V, T, b, r, X, lambda, kbar, delta, alpha, betastar, sigma_v, rho; };
struct Zabr { double f, K, alpha, beta, nu, rho, gamma, T; };

inline std::vector<Black> black() {
    std::vector<Black> g;
    for (double K : {60.0, 80.0, 95.0, 100.0, 105.0, 120.0, 160.0})
        for (double s : {0.05, 0.25, 0.8})
            for (double t : {0.02, 1.0, 10.0}) g.push_back({100.0, K, s, t, 0.03});
    g.push_back({0.035, 0.03, 0.4, 10.0, 0.02});    // rates-style forward
    return g;
}

inline std::vector<Bachelier> bachelier() {
    std::vector<Bachelier> g;
    for (double K : {70.0, 90.0, 100.0, 110.0, 140.0})
        for (double sigma : {2.0, 12.0, 40.0})
            for (double T : {0.1, 0.75, 5.0}) g.push_back({100.0, K, sigma, T});
    g.push_back({0.01, -0.005, 0.008, 5.0});          // negative strike, rates units
    return g;
}

inline std::vector<double> displacements() { return {0.0, 0.01, 0.03}; }

inline std::vector<Sabr> sabr() {
    std::vector<Sabr> g;
    const struct { double beta, alpha, f; } legs[] = {
        {0.0, 0.0035, 0.03}, {0.5, 0.035, 0.03}, {0.7, 0.0873, 0.05}, {1.0, 0.2, 100.0}};
    for (auto l : legs)
        for (double m : {0.5, 0.8, 0.95, 1.05, 1.3, 2.0})
            for (auto p : {Sabr{0, 0, 0, 0, 0.5, -0.4, 1.0}, Sabr{0, 0, 0, 0, 0.9, 0.3, 5.0}})
                g.push_back({l.f, l.f * m, l.alpha, l.beta, p.nu, p.rho, p.T});
    return g;
}

inline std::vector<Heston> heston() {
    std::vector<Heston> g;
    const double sets[][5] = {{1.5, 0.04, 0.3, -0.7, 0.04}, {3.0, 0.09, 0.8, -0.3, 0.05},
                              {0.5, 0.06, 0.2, 0.2, 0.03}};
    for (auto& p : sets)                                   // kappa, theta, sigma, rho, v0
        for (double T : {0.2, 1.0, 2.0, 5.0})             // whole days under Act/365
            for (double K : {80.0, 100.0, 125.0})
                g.push_back({100.0, p[4], p[0], p[1], p[2], p[3], 0.03, K, T});
    return g;
}

inline std::vector<Bates> bates() {
    std::vector<Bates> g;
    const double jumps[][3] = {{0.5, -0.1, 0.15}, {2.0, 0.02, 0.05}, {0.1, -0.3, 0.4}};
    for (auto& j : jumps)                                  // lambda*, kbar*, delta
        for (double T : {0.2, 1.0, 2.0})
            for (double X : {85.0, 100.0, 115.0})
                g.push_back({100.0, 0.04, T, 0.01, 0.03, X, j[0], j[1], j[2], 0.06, 1.5, 0.4, -0.6});
    return g;
}

inline std::vector<Zabr> zabr() {
    std::vector<Zabr> g;
    for (double gamma : {0.0, 0.5, 1.0, 1.5})
        for (double beta : {0.5, 0.7})
            for (double m : {0.4, 0.7, 0.9, 1.1, 1.5, 2.5})
                g.push_back({0.05, 0.05 * m, 0.0873, beta, 0.47, -0.48, gamma, 10.0});
    return g;
}

}  // namespace grids
