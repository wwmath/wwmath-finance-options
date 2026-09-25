! Generated from the Math AST via the Typed Math IR -- do not edit.
! F77 numerics; BIND(C)/VALUE (Fortran 2003) are used only to fix the flat ABI.
subroutine normal_heston_step(x, v, dt, kappa, theta, xi, rho, z1, z2, output) &
    bind(c, name="normal_heston_step")
  use iso_c_binding, only: c_double
  implicit none
  real(c_double), value :: x, v, dt, kappa, theta, xi, rho, z1, z2
  real(c_double), intent(out) :: output(2)
  real(c_double) :: v_pos, sqrt_dt, dw_v, dw_x
  v_pos = max(v, 0.0d0)
  sqrt_dt = sqrt(dt)
  dw_v = (sqrt_dt * z1)
  dw_x = (sqrt_dt * ((rho * z1) + (sqrt((1.0d0 - (rho * rho))) * z2)))
  output(1) = (x + (sqrt(v_pos) * dw_x))  ! x_next
  output(2) = ((v + ((kappa * (theta - v_pos)) * dt)) + ((xi * sqrt(v_pos)) * dw_v))  ! v_next
end subroutine normal_heston_step
