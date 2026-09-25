;; Generated from the Math AST via the Typed Math IR -- do not edit.
(module
  (memory (export "memory") 1)
  (func (export "normal_heston_step") (param $x f64) (param $v f64) (param $dt f64) (param $kappa f64) (param $theta f64) (param $xi f64) (param $rho f64) (param $z1 f64) (param $z2 f64) (param $output i32)
    (local $v_pos f64) (local $sqrt_dt f64) (local $dw_v f64) (local $dw_x f64)
    local.get $v
    f64.const 0.0
    f64.max
    local.set $v_pos
    local.get $dt
    f64.sqrt
    local.set $sqrt_dt
    local.get $sqrt_dt
    local.get $z1
    f64.mul
    local.set $dw_v
    local.get $sqrt_dt
    local.get $rho
    local.get $z1
    f64.mul
    f64.const 1.0
    local.get $rho
    local.get $rho
    f64.mul
    f64.sub
    f64.sqrt
    local.get $z2
    f64.mul
    f64.add
    f64.mul
    local.set $dw_x
    local.get $output  ;; x_next
    local.get $x
    local.get $v_pos
    f64.sqrt
    local.get $dw_x
    f64.mul
    f64.add
    f64.store offset=0
    local.get $output  ;; v_next
    local.get $v
    local.get $kappa
    local.get $theta
    local.get $v_pos
    f64.sub
    f64.mul
    local.get $dt
    f64.mul
    f64.add
    local.get $xi
    local.get $v_pos
    f64.sqrt
    f64.mul
    local.get $dw_v
    f64.mul
    f64.add
    f64.store offset=8
  )
)
