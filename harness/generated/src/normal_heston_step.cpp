// Generated from the Math AST via the Typed Math IR -- do not edit.
// Deliberately boring C++ subset; __builtin_sqrt is std::sqrt without a libc++ sysroot.

extern "C" __attribute__((export_name("normal_heston_step")))
void normal_heston_step(
    double x,
    double v,
    double dt,
    double kappa,
    double theta,
    double xi,
    double rho,
    double z1,
    double z2,
    double* output)
{
    const double v_pos = (v > 0.0 ? v : 0.0);
    const double sqrt_dt = __builtin_sqrt(dt);
    const double dw_v = (sqrt_dt * z1);
    const double dw_x = (sqrt_dt * ((rho * z1) + (__builtin_sqrt((1.0 - (rho * rho))) * z2)));
    output[0] = (x + (__builtin_sqrt(v_pos) * dw_x));  // x_next
    output[1] = ((v + ((kappa * (theta - v_pos)) * dt)) + ((xi * __builtin_sqrt(v_pos)) * dw_v));  // v_next
}
