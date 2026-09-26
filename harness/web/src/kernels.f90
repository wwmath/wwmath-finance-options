! Generated from the Math AST via the Typed Math IR -- do not edit.
! F77-style numerics. BIND(C)/VALUE (F2003) fix the flat ABI; bit reinterpretation
! for the IR's exp/log uses F77 EQUIVALENCE (TRANSFER would call the Fortran
! runtime); SHIFTL/SHIFTR/IAND/IOR are F2008 elementals. No runtime calls.

subroutine normal_heston_step(x, v, dt, kappa, theta, xi, rho, z1, z2, output) &
    bind(c, name="normal_heston_step")
  use iso_c_binding, only: c_double, c_int64_t
  implicit none
  real(c_double), value :: x, v, dt, kappa, theta, xi, rho, z1, z2
  real(c_double), intent(out) :: output(2)
  real(c_double) :: v_pos, sqrt_dt, dw_v, dw_x
  v_pos = max(v, 0.0_c_double)
  sqrt_dt = sqrt(dt)
  dw_v = (sqrt_dt * z1)
  dw_x = (sqrt_dt * ((rho * z1) + (sqrt((1.0_c_double - (rho * rho))) * z2)))
  output(1) = (x + (sqrt(v_pos) * dw_x))
  output(2) = ((v + ((kappa * (theta - v_pos)) * dt)) + ((xi * sqrt(v_pos)) * dw_v))
end subroutine normal_heston_step

subroutine heston_step(s, v, dt, r, kappa, theta, sigma, rho, z1, z2, output) &
    bind(c, name="heston_step")
  use iso_c_binding, only: c_double, c_int64_t
  implicit none
  real(c_double), value :: s, v, dt, r, kappa, theta, sigma, rho, z1, z2
  real(c_double), intent(out) :: output(2)
  real(c_double) :: s_pos, v_pos, sqrt_dt, dw_v, dw_s
  s_pos = max(s, 0.0_c_double)
  v_pos = max(v, 0.0_c_double)
  sqrt_dt = sqrt(dt)
  dw_v = (sqrt_dt * z1)
  dw_s = (sqrt_dt * ((rho * z1) + (sqrt((1.0_c_double - (rho * rho))) * z2)))
  output(1) = ((s + ((r * s_pos) * dt)) + ((sqrt(v_pos) * s_pos) * dw_s))
  output(2) = ((v + ((kappa * (theta - v_pos)) * dt)) + ((sigma * sqrt(v_pos)) * dw_v))
end subroutine heston_step

subroutine bates_step(s, v, dt, b, lambdastar, kbarstar, alpha, betastar, sigma_v, rho, z1, z2, dj, &
      & output) &
    bind(c, name="bates_step")
  use iso_c_binding, only: c_double, c_int64_t
  implicit none
  real(c_double), value :: s, v, dt, b, lambdastar, kbarstar, alpha, betastar, sigma_v, rho, z1, z2, &
      & dj
  real(c_double), intent(out) :: output(2)
  real(c_double) :: s_pos, v_pos, sqrt_dt, dw_v, dw_s
  s_pos = max(s, 0.0_c_double)
  v_pos = max(v, 0.0_c_double)
  sqrt_dt = sqrt(dt)
  dw_v = (sqrt_dt * z1)
  dw_s = (sqrt_dt * ((rho * z1) + (sqrt((1.0_c_double - (rho * rho))) * z2)))
  output(1) = (((s + (((b - (lambdastar * kbarstar)) * s_pos) * dt)) + ((sqrt(v_pos) * s_pos) * &
      & dw_s)) + (dj * s_pos))
  output(2) = ((v + ((alpha - (betastar * v_pos)) * dt)) + ((sigma_v * sqrt(v_pos)) * dw_v))
end subroutine bates_step

subroutine sabr_step(f, alpha, dt, beta, nu, rho, z1, z2, output) &
    bind(c, name="sabr_step")
  use iso_c_binding, only: c_double, c_int64_t
  implicit none
  real(c_double), value :: f, alpha, dt, beta, nu, rho, z1, z2
  real(c_double), intent(out) :: output(2)
  real(c_double) :: f_pos, alpha_pos, sqrt_dt, dw_alpha, dw_f, pow_log_k
  real(c_double) :: pow_log_m, pow_log_f, pow_log_hfsq, pow_log_s, pow_log_z, pow_log_w
  real(c_double) :: pow_log_R, pow_log_res, pow_x, pow_k, pow_hi, pow_lo
  real(c_double) :: pow_r, pow_t, pow_c, pow_y, pow_2k, pow_res
  integer(c_int64_t) :: pow_log_ix, pow_log_hx
  real(c_double) :: ww_r
  integer(c_int64_t) :: ww_i
  equivalence (ww_r, ww_i)
  f_pos = max(f, 0.0_c_double)
  alpha_pos = max(alpha, 0.0_c_double)
  sqrt_dt = sqrt(dt)
  dw_alpha = (sqrt_dt * z1)
  dw_f = (sqrt_dt * ((rho * z1) + (sqrt((1.0_c_double - (rho * rho))) * z2)))
  ww_r = max(f_pos, 1e-300_c_double)
  pow_log_ix = ww_i
  pow_log_hx = (shiftr(pow_log_ix, 32) + int(z'95F62', c_int64_t))
  pow_log_k = (real(shiftr(pow_log_hx, 20), c_double) - 1023.0_c_double)
  ww_i = ior(shiftl((iand(pow_log_hx, int(z'FFFFF', c_int64_t)) + int(z'3FE6A09E', c_int64_t)), 32), &
      & iand(pow_log_ix, int(z'FFFFFFFF', c_int64_t)))
  pow_log_m = ww_r
  pow_log_f = (pow_log_m - 1.0_c_double)
  pow_log_hfsq = ((0.5_c_double * pow_log_f) * pow_log_f)
  pow_log_s = (pow_log_f / (2.0_c_double + pow_log_f))
  pow_log_z = (pow_log_s * pow_log_s)
  pow_log_w = (pow_log_z * pow_log_z)
  pow_log_R = ((pow_log_z * (0.6666666666666735_c_double + (pow_log_w * &
      & (0.2857142874366239_c_double + (pow_log_w * (0.1818357216161805_c_double + (pow_log_w * &
      & 0.14798198605116586_c_double))))))) + (pow_log_w * (0.3999999999940942_c_double + &
      & (pow_log_w * (0.22222198432149784_c_double + (pow_log_w * 0.15313837699209373_c_double))))))
  pow_log_res = (((((pow_log_s * (pow_log_hfsq + pow_log_R)) + (pow_log_k * &
      & 1.9082149292705877e-10_c_double)) - pow_log_hfsq) + pow_log_f) + (pow_log_k * &
      & 0.6931471803691238_c_double))
  pow_x = (beta * pow_log_res)
  pow_k = real(floor(((pow_x * 1.4426950408889634_c_double) + 0.5_c_double), c_int64_t), c_double)
  pow_hi = (pow_x - (pow_k * 0.6931471803691238_c_double))
  pow_lo = (pow_k * 1.9082149292705877e-10_c_double)
  pow_r = (pow_hi - pow_lo)
  pow_t = (pow_r * pow_r)
  pow_c = (pow_r - (pow_t * (0.16666666666666602_c_double + (pow_t * &
      & (-0.0027777777777015593_c_double + (pow_t * (6.613756321437934e-05_c_double + (pow_t * &
      & (-1.6533902205465252e-06_c_double + (pow_t * 4.1381367970572385e-08_c_double))))))))))
  pow_y = (1.0_c_double + ((((pow_r * pow_c) / (2.0_c_double - pow_c)) - pow_lo) + pow_hi))
  ww_i = shiftl(int((pow_k + 1023.0_c_double), c_int64_t), 52)
  pow_2k = ww_r
  pow_res = (pow_y * pow_2k)
  output(1) = (f + ((alpha_pos * pow_res) * dw_f))
  output(2) = (alpha + ((nu * alpha_pos) * dw_alpha))
end subroutine sabr_step
