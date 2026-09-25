// Generated from the Math AST via the Typed Math IR -- do not edit.
// Rust is the conformance reference.

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub extern "C" fn normal_heston_step(
    x: f64,
    v: f64,
    dt: f64,
    kappa: f64,
    theta: f64,
    xi: f64,
    rho: f64,
    z1: f64,
    z2: f64,
    output: *mut f64,
) {
    let v_pos: f64 = v.max(0.0);
    let sqrt_dt: f64 = dt.sqrt();
    let dw_v: f64 = (sqrt_dt * z1);
    let dw_x: f64 = (sqrt_dt * ((rho * z1) + ((1.0 - (rho * rho)).sqrt() * z2)));
    unsafe { *output.add(0) = (x + (v_pos.sqrt() * dw_x)); } // x_next
    unsafe { *output.add(1) = ((v + ((kappa * (theta - v_pos)) * dt)) + ((xi * v_pos.sqrt()) * dw_v)); } // v_next
}
