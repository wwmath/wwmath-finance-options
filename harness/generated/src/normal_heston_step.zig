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
    output[0] = (x + (@sqrt(v_pos) * dw_x)); // x_next
    output[1] = ((v + ((kappa * (theta - v_pos)) * dt)) + ((xi * @sqrt(v_pos)) * dw_v)); // v_next
}
