// wwmath runtime for code generated from the Math AST (research/tools/cpp.py).
// Header-only, standard library only: no QuantLib, no Boost. Everything a generated
// formula needs beyond <cmath>/<complex> lives here.
#pragma once

#include <algorithm>
#include <cmath>
#include <complex>
#include <functional>
#include <limits>

namespace ww {

inline const std::complex<double> I{0.0, 1.0};
inline constexpr double PI = 3.141592653589793238462643383279502884;
inline constexpr double E = 2.718281828459045235360287471352662498;
inline constexpr double INF = std::numeric_limits<double>::infinity();

/// Standard normal CDF and PDF (the papers' N / Phi and n / varphi).
inline double N(double x) { return 0.5 * std::erfc(-x / std::sqrt(2.0)); }
inline double n(double x) { return std::exp(-0.5 * x * x) / std::sqrt(2.0 * PI); }
template <class A, class B> inline double max(A a, B b) {
    return std::max(std::real(a), std::real(b));
}
template <class A, class B> inline double min(A a, B b) {
    return std::min(std::real(a), std::real(b));
}

namespace detail {
// Gauss-Kronrod (7, 15) nodes and weights, as in QUADPACK qk15.
inline constexpr double XGK[8] = {
    0.991455371120812639206854697526329, 0.949107912342758524526189684047851,
    0.864864423359769072789712788640926, 0.741531185599394439863864773280788,
    0.586087235467691130294144845693013, 0.405845151377397166906606412076961,
    0.207784955007898467600689403773245, 0.000000000000000000000000000000000};
inline constexpr double WGK[8] = {
    0.022935322010529224963732008058970, 0.063092092629978553290700663189204,
    0.104790010322250183839876322541518, 0.140653259715525918745189590510238,
    0.169004726639267902826583426598550, 0.190350578064785409913256402421014,
    0.204432940075298892414161999234649, 0.209482141084727828012999174891714};
inline constexpr double WG[4] = {
    0.129484966168869693270611432679082, 0.279705391489276667901467771423780,
    0.381830050505118944950369775488975, 0.417959183673469387755102040816327};

struct Rule { double kronrod, gauss; };

template <class F> Rule gk15(const F& f, double a, double b) {
    const double c = 0.5 * (a + b), h = 0.5 * (b - a);
    const double fc = f(c);
    double k = fc * WGK[7], g = fc * WG[3];
    for (int j = 0; j < 7; ++j) {
        const double dx = h * XGK[j];
        const double s = f(c - dx) + f(c + dx);
        k += WGK[j] * s;
        if (j % 2 == 1) g += WG[j / 2] * s;
    }
    return {k * h, g * h};
}

template <class F>
double adapt(const F& f, double a, double b, double tol, int depth, Rule whole) {
    const double m = 0.5 * (a + b);
    const Rule l = gk15(f, a, m), r = gk15(f, m, b);
    const double k = l.kronrod + r.kronrod;
    const double err = std::abs(l.kronrod - l.gauss) + std::abs(r.kronrod - r.gauss);
    if (depth <= 0 || err <= tol || !(std::abs(k - whole.kronrod) > 1e-300 || err > 0))
        return k;
    return adapt(f, a, m, 0.5 * tol, depth - 1, l) + adapt(f, m, b, 0.5 * tol, depth - 1, r);
}
}  // namespace detail

/// Adaptive Gauss-Kronrod integral of f over [a, b]; either bound may be infinite.
/// Infinite ranges are mapped to (0, 1) or (-1, 1); there the integrand is known to decay,
/// so a non-finite value (overflow far in the tail) is treated as zero, exactly as the
/// Python reference interpreter does.
template <class F>
double integrate(const F& f, double a, double b, double abs_tol = 1e-13, double rel_tol = 1e-12) {
    std::function<double(double)> g;
    double lo, hi;
    const bool inf_hi = std::isinf(b) && b > 0, inf_lo = std::isinf(a) && a < 0;
    if (inf_lo && inf_hi) {
        g = [&](double t) { const double d = 1.0 - t * t;
                            const double y = f(t / d) * (1.0 + t * t) / (d * d);
                            return std::isfinite(y) ? y : 0.0; };
        lo = -1.0; hi = 1.0;
    } else if (inf_hi) {
        g = [&](double t) { const double d = 1.0 - t;
                            const double y = f(a + t / d) / (d * d);
                            return std::isfinite(y) ? y : 0.0; };
        lo = 0.0; hi = 1.0;
    } else {
        g = [&](double x) { return f(x); };
        lo = a; hi = b;
    }
    const detail::Rule whole = detail::gk15(g, lo, hi);
    const double tol = std::max(abs_tol, rel_tol * std::abs(whole.kronrod));
    return detail::adapt(g, lo, hi, tol, 40, whole);
}

}  // namespace ww
