// Generated from the Math AST via the Typed Math IR -- do not edit.

export fn normal_heston_step(
    x: f64,
    v: f64,
    dt: f64,
    kappa: f64,
    theta: f64,
    xi: f64,
    rho: f64,
    z1: f64,
    z2: f64,
    output: [*]f64,
) void {
    const v_pos: f64 = @max(v, 0.0);
    const sqrt_dt: f64 = @sqrt(dt);
    const dw_v: f64 = (sqrt_dt * z1);
    const dw_x: f64 = (sqrt_dt * ((rho * z1) + (@sqrt((1.0 - (rho * rho))) * z2)));
    output[0] = (x + (@sqrt(v_pos) * dw_x));
    output[1] = ((v + ((kappa * (theta - v_pos)) * dt)) + ((xi * @sqrt(v_pos)) * dw_v));
}

export fn heston_step(
    s: f64,
    v: f64,
    dt: f64,
    r: f64,
    kappa: f64,
    theta: f64,
    sigma: f64,
    rho: f64,
    z1: f64,
    z2: f64,
    output: [*]f64,
) void {
    const s_pos: f64 = @max(s, 0.0);
    const v_pos: f64 = @max(v, 0.0);
    const sqrt_dt: f64 = @sqrt(dt);
    const dw_v: f64 = (sqrt_dt * z1);
    const dw_s: f64 = (sqrt_dt * ((rho * z1) + (@sqrt((1.0 - (rho * rho))) * z2)));
    output[0] = ((s + ((r * s_pos) * dt)) + ((@sqrt(v_pos) * s_pos) * dw_s));
    output[1] = ((v + ((kappa * (theta - v_pos)) * dt)) + ((sigma * @sqrt(v_pos)) * dw_v));
}

export fn bates_step(
    s: f64,
    v: f64,
    dt: f64,
    b: f64,
    lambdastar: f64,
    kbarstar: f64,
    alpha: f64,
    betastar: f64,
    sigma_v: f64,
    rho: f64,
    z1: f64,
    z2: f64,
    dj: f64,
    output: [*]f64,
) void {
    const s_pos: f64 = @max(s, 0.0);
    const v_pos: f64 = @max(v, 0.0);
    const sqrt_dt: f64 = @sqrt(dt);
    const dw_v: f64 = (sqrt_dt * z1);
    const dw_s: f64 = (sqrt_dt * ((rho * z1) + (@sqrt((1.0 - (rho * rho))) * z2)));
    output[0] = (((s + (((b - (lambdastar * kbarstar)) * s_pos) * dt)) + ((@sqrt(v_pos) * s_pos) * dw_s)) + (dj * s_pos));
    output[1] = ((v + ((alpha - (betastar * v_pos)) * dt)) + ((sigma_v * @sqrt(v_pos)) * dw_v));
}

export fn sabr_step(
    f: f64,
    alpha: f64,
    dt: f64,
    beta: f64,
    nu: f64,
    rho: f64,
    z1: f64,
    z2: f64,
    output: [*]f64,
) void {
    const f_pos: f64 = @max(f, 0.0);
    const alpha_pos: f64 = @max(alpha, 0.0);
    const sqrt_dt: f64 = @sqrt(dt);
    const dw_alpha: f64 = (sqrt_dt * z1);
    const dw_f: f64 = (sqrt_dt * ((rho * z1) + (@sqrt((1.0 - (rho * rho))) * z2)));
    const pow_log_ix: u64 = @as(u64, @bitCast(@max(f_pos, 1.0e-300)));
    const pow_log_hx: u64 = ((pow_log_ix >> 32) +% @as(u64, 0x95F62));
    const pow_log_k: f64 = (@as(f64, @floatFromInt((pow_log_hx >> 20))) - 1023.0);
    const pow_log_m: f64 = @as(f64, @bitCast(((((pow_log_hx & @as(u64, 0xFFFFF)) +% @as(u64, 0x3FE6A09E)) << 32) | (pow_log_ix & @as(u64, 0xFFFFFFFF)))));
    const pow_log_f: f64 = (pow_log_m - 1.0);
    const pow_log_hfsq: f64 = ((0.5 * pow_log_f) * pow_log_f);
    const pow_log_s: f64 = (pow_log_f / (2.0 + pow_log_f));
    const pow_log_z: f64 = (pow_log_s * pow_log_s);
    const pow_log_w: f64 = (pow_log_z * pow_log_z);
    const pow_log_R: f64 = ((pow_log_z * (0.6666666666666735 + (pow_log_w * (0.2857142874366239 + (pow_log_w * (0.1818357216161805 + (pow_log_w * 0.14798198605116586))))))) + (pow_log_w * (0.3999999999940942 + (pow_log_w * (0.22222198432149784 + (pow_log_w * 0.15313837699209373))))));
    const pow_log_res: f64 = (((((pow_log_s * (pow_log_hfsq + pow_log_R)) + (pow_log_k * 1.9082149292705877e-10)) - pow_log_hfsq) + pow_log_f) + (pow_log_k * 0.6931471803691238));
    const pow_x: f64 = (beta * pow_log_res);
    const pow_k: f64 = @floor(((pow_x * 1.4426950408889634) + 0.5));
    const pow_hi: f64 = (pow_x - (pow_k * 0.6931471803691238));
    const pow_lo: f64 = (pow_k * 1.9082149292705877e-10);
    const pow_r: f64 = (pow_hi - pow_lo);
    const pow_t: f64 = (pow_r * pow_r);
    const pow_c: f64 = (pow_r - (pow_t * (0.16666666666666602 + (pow_t * (-0.0027777777777015593 + (pow_t * (6.613756321437934e-05 + (pow_t * (-1.6533902205465252e-06 + (pow_t * 4.1381367970572385e-08))))))))));
    const pow_y: f64 = (1.0 + ((((pow_r * pow_c) / (2.0 - pow_c)) - pow_lo) + pow_hi));
    const pow_2k: f64 = @as(f64, @bitCast((@as(u64, @intFromFloat((pow_k + 1023.0))) << 52)));
    const pow_res: f64 = (pow_y * pow_2k);
    output[0] = (f + ((alpha_pos * pow_res) * dw_f));
    output[1] = (alpha + ((nu * alpha_pos) * dw_alpha));
}
