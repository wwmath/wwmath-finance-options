// Generated from the Math AST via the Typed Math IR -- do not edit.
// EXPERIMENTAL (Tier 3): Carbon has no stable toolchain or WASM target;
// this is emitted from the same IR but is not compiled or run yet.

package WwmathKernels api;

import Math;

fn NormalHestonStep(
    x: f64,
    v: f64,
    dt: f64,
    kappa: f64,
    theta: f64,
    xi: f64,
    rho: f64,
    z1: f64,
    z2: f64,
    output: f64*) {
  let v_pos: f64 = (if v > 0.0 then v else 0.0);
  let sqrt_dt: f64 = Math.Sqrt(dt);
  let dw_v: f64 = (sqrt_dt * z1);
  let dw_x: f64 = (sqrt_dt * ((rho * z1) + (Math.Sqrt((1.0 - (rho * rho))) * z2)));
  output[0] = (x + (Math.Sqrt(v_pos) * dw_x));  // x_next
  output[1] = ((v + ((kappa * (theta - v_pos)) * dt)) + ((xi * Math.Sqrt(v_pos)) * dw_v));  // v_next
}
