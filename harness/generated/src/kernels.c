/* Generated from the Math AST via the Typed Math IR -- do not edit. */

static inline unsigned long long ww_bits(double x) {
    unsigned long long u; __builtin_memcpy(&u, &x, 8); return u;
}
static inline double ww_from_bits(unsigned long long u) {
    double x; __builtin_memcpy(&x, &u, 8); return x;
}

/* normal_heston_step: euler-full-truncation step of sidani2014.forward_sde, sidani2014.variance_sde */
__attribute__((export_name("normal_heston_step")))
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
    double *output)
{
    const double v_pos = (v > 0.0 ? v : 0.0);
    const double sqrt_dt = __builtin_sqrt(dt);
    const double dw_v = (sqrt_dt * z1);
    const double dw_x = (sqrt_dt * ((rho * z1) + (__builtin_sqrt((1.0 - (rho * rho))) * z2)));
    output[0] = (x + (__builtin_sqrt(v_pos) * dw_x));
    output[1] = ((v + ((kappa * (theta - v_pos)) * dt)) + ((xi * __builtin_sqrt(v_pos)) * dw_v));
}

/* heston_step: euler-full-truncation step of heston1993.spot_sde, heston1993.variance_sde */
__attribute__((export_name("heston_step")))
void heston_step(
    double s,
    double v,
    double dt,
    double r,
    double kappa,
    double theta,
    double sigma,
    double rho,
    double z1,
    double z2,
    double *output)
{
    const double s_pos = (s > 0.0 ? s : 0.0);
    const double v_pos = (v > 0.0 ? v : 0.0);
    const double sqrt_dt = __builtin_sqrt(dt);
    const double dw_v = (sqrt_dt * z1);
    const double dw_s = (sqrt_dt * ((rho * z1) + (__builtin_sqrt((1.0 - (rho * rho))) * z2)));
    output[0] = ((s + ((r * s_pos) * dt)) + ((__builtin_sqrt(v_pos) * s_pos) * dw_s));
    output[1] = ((v + ((kappa * (theta - v_pos)) * dt)) + ((sigma * __builtin_sqrt(v_pos)) * dw_v));
}

/* bates_step: euler-full-truncation step of bates1996.spot_sde, bates1996.variance_sde */
__attribute__((export_name("bates_step")))
void bates_step(
    double s,
    double v,
    double dt,
    double b,
    double lambdastar,
    double kbarstar,
    double alpha,
    double betastar,
    double sigma_v,
    double rho,
    double z1,
    double z2,
    double dj,
    double *output)
{
    const double s_pos = (s > 0.0 ? s : 0.0);
    const double v_pos = (v > 0.0 ? v : 0.0);
    const double sqrt_dt = __builtin_sqrt(dt);
    const double dw_v = (sqrt_dt * z1);
    const double dw_s = (sqrt_dt * ((rho * z1) + (__builtin_sqrt((1.0 - (rho * rho))) * z2)));
    output[0] = (((s + (((b - (lambdastar * kbarstar)) * s_pos) * dt)) + ((__builtin_sqrt(v_pos) * s_pos) * dw_s)) + (dj * s_pos));
    output[1] = ((v + ((alpha - (betastar * v_pos)) * dt)) + ((sigma_v * __builtin_sqrt(v_pos)) * dw_v));
}

/* sabr_step: euler-full-truncation step of hagan2002.forward_sde, hagan2002.vol_sde */
__attribute__((export_name("sabr_step")))
void sabr_step(
    double f,
    double alpha,
    double dt,
    double beta,
    double nu,
    double rho,
    double z1,
    double z2,
    double *output)
{
    const double f_pos = (f > 0.0 ? f : 0.0);
    const double alpha_pos = (alpha > 0.0 ? alpha : 0.0);
    const double sqrt_dt = __builtin_sqrt(dt);
    const double dw_alpha = (sqrt_dt * z1);
    const double dw_f = (sqrt_dt * ((rho * z1) + (__builtin_sqrt((1.0 - (rho * rho))) * z2)));
    const unsigned long long pow_log_ix = ww_bits((f_pos > 1e-300 ? f_pos : 1e-300));
    const unsigned long long pow_log_hx = ((pow_log_ix >> 32) + 0x95F62ULL);
    const double pow_log_k = (((double)((pow_log_hx >> 20))) - 1023.0);
    const double pow_log_m = ww_from_bits(((((pow_log_hx & 0xFFFFFULL) + 0x3FE6A09EULL) << 32) | (pow_log_ix & 0xFFFFFFFFULL)));
    const double pow_log_f = (pow_log_m - 1.0);
    const double pow_log_hfsq = ((0.5 * pow_log_f) * pow_log_f);
    const double pow_log_s = (pow_log_f / (2.0 + pow_log_f));
    const double pow_log_z = (pow_log_s * pow_log_s);
    const double pow_log_w = (pow_log_z * pow_log_z);
    const double pow_log_R = ((pow_log_z * (0.6666666666666735 + (pow_log_w * (0.2857142874366239 + (pow_log_w * (0.1818357216161805 + (pow_log_w * 0.14798198605116586))))))) + (pow_log_w * (0.3999999999940942 + (pow_log_w * (0.22222198432149784 + (pow_log_w * 0.15313837699209373))))));
    const double pow_log_res = (((((pow_log_s * (pow_log_hfsq + pow_log_R)) + (pow_log_k * 1.9082149292705877e-10)) - pow_log_hfsq) + pow_log_f) + (pow_log_k * 0.6931471803691238));
    const double pow_x = (beta * pow_log_res);
    const double pow_k = __builtin_floor(((pow_x * 1.4426950408889634) + 0.5));
    const double pow_hi = (pow_x - (pow_k * 0.6931471803691238));
    const double pow_lo = (pow_k * 1.9082149292705877e-10);
    const double pow_r = (pow_hi - pow_lo);
    const double pow_t = (pow_r * pow_r);
    const double pow_c = (pow_r - (pow_t * (0.16666666666666602 + (pow_t * (-0.0027777777777015593 + (pow_t * (6.613756321437934e-05 + (pow_t * (-1.6533902205465252e-06 + (pow_t * 4.1381367970572385e-08))))))))));
    const double pow_y = (1.0 + ((((pow_r * pow_c) / (2.0 - pow_c)) - pow_lo) + pow_hi));
    const double pow_2k = ww_from_bits((((unsigned long long)((pow_k + 1023.0))) << 52));
    const double pow_res = (pow_y * pow_2k);
    output[0] = (f + ((alpha_pos * pow_res) * dw_f));
    output[1] = (alpha + ((nu * alpha_pos) * dw_alpha));
}
