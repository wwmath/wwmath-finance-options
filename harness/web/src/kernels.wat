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
  (func (export "heston_step") (param $s f64) (param $v f64) (param $dt f64) (param $r f64) (param $kappa f64) (param $theta f64) (param $sigma f64) (param $rho f64) (param $z1 f64) (param $z2 f64) (param $output i32)
    (local $s_pos f64) (local $v_pos f64) (local $sqrt_dt f64) (local $dw_v f64) (local $dw_s f64)
    local.get $s
    f64.const 0.0
    f64.max
    local.set $s_pos
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
    local.set $dw_s
    local.get $output  ;; s_next
    local.get $s
    local.get $r
    local.get $s_pos
    f64.mul
    local.get $dt
    f64.mul
    f64.add
    local.get $v_pos
    f64.sqrt
    local.get $s_pos
    f64.mul
    local.get $dw_s
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
    local.get $sigma
    local.get $v_pos
    f64.sqrt
    f64.mul
    local.get $dw_v
    f64.mul
    f64.add
    f64.store offset=8
  )
  (func (export "bates_step") (param $s f64) (param $v f64) (param $dt f64) (param $b f64) (param $lambdastar f64) (param $kbarstar f64) (param $alpha f64) (param $betastar f64) (param $sigma_v f64) (param $rho f64) (param $z1 f64) (param $z2 f64) (param $dj f64) (param $output i32)
    (local $s_pos f64) (local $v_pos f64) (local $sqrt_dt f64) (local $dw_v f64) (local $dw_s f64)
    local.get $s
    f64.const 0.0
    f64.max
    local.set $s_pos
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
    local.set $dw_s
    local.get $output  ;; s_next
    local.get $s
    local.get $b
    local.get $lambdastar
    local.get $kbarstar
    f64.mul
    f64.sub
    local.get $s_pos
    f64.mul
    local.get $dt
    f64.mul
    f64.add
    local.get $v_pos
    f64.sqrt
    local.get $s_pos
    f64.mul
    local.get $dw_s
    f64.mul
    f64.add
    local.get $dj
    local.get $s_pos
    f64.mul
    f64.add
    f64.store offset=0
    local.get $output  ;; v_next
    local.get $v
    local.get $alpha
    local.get $betastar
    local.get $v_pos
    f64.mul
    f64.sub
    local.get $dt
    f64.mul
    f64.add
    local.get $sigma_v
    local.get $v_pos
    f64.sqrt
    f64.mul
    local.get $dw_v
    f64.mul
    f64.add
    f64.store offset=8
  )
  (func (export "sabr_step") (param $f f64) (param $alpha f64) (param $dt f64) (param $beta f64) (param $nu f64) (param $rho f64) (param $z1 f64) (param $z2 f64) (param $output i32)
    (local $f_pos f64) (local $alpha_pos f64) (local $sqrt_dt f64) (local $dw_alpha f64) (local $dw_f f64) (local $pow_log_k f64) (local $pow_log_m f64) (local $pow_log_f f64) (local $pow_log_hfsq f64) (local $pow_log_s f64) (local $pow_log_z f64) (local $pow_log_w f64) (local $pow_log_R f64) (local $pow_log_res f64) (local $pow_x f64) (local $pow_k f64) (local $pow_hi f64) (local $pow_lo f64) (local $pow_r f64) (local $pow_t f64) (local $pow_c f64) (local $pow_y f64) (local $pow_2k f64) (local $pow_res f64) (local $pow_log_ix i64) (local $pow_log_hx i64)
    local.get $f
    f64.const 0.0
    f64.max
    local.set $f_pos
    local.get $alpha
    f64.const 0.0
    f64.max
    local.set $alpha_pos
    local.get $dt
    f64.sqrt
    local.set $sqrt_dt
    local.get $sqrt_dt
    local.get $z1
    f64.mul
    local.set $dw_alpha
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
    local.set $dw_f
    local.get $f_pos
    f64.const 1e-300
    f64.max
    i64.reinterpret_f64
    local.set $pow_log_ix
    local.get $pow_log_ix
    i64.const 32
    i64.shr_u
    i64.const 614242
    i64.add
    local.set $pow_log_hx
    local.get $pow_log_hx
    i64.const 20
    i64.shr_u
    f64.convert_i64_u
    f64.const 1023.0
    f64.sub
    local.set $pow_log_k
    local.get $pow_log_hx
    i64.const 1048575
    i64.and
    i64.const 1072079006
    i64.add
    i64.const 32
    i64.shl
    local.get $pow_log_ix
    i64.const 4294967295
    i64.and
    i64.or
    f64.reinterpret_i64
    local.set $pow_log_m
    local.get $pow_log_m
    f64.const 1.0
    f64.sub
    local.set $pow_log_f
    f64.const 0.5
    local.get $pow_log_f
    f64.mul
    local.get $pow_log_f
    f64.mul
    local.set $pow_log_hfsq
    local.get $pow_log_f
    f64.const 2.0
    local.get $pow_log_f
    f64.add
    f64.div
    local.set $pow_log_s
    local.get $pow_log_s
    local.get $pow_log_s
    f64.mul
    local.set $pow_log_z
    local.get $pow_log_z
    local.get $pow_log_z
    f64.mul
    local.set $pow_log_w
    local.get $pow_log_z
    f64.const 0.6666666666666735
    local.get $pow_log_w
    f64.const 0.2857142874366239
    local.get $pow_log_w
    f64.const 0.1818357216161805
    local.get $pow_log_w
    f64.const 0.14798198605116586
    f64.mul
    f64.add
    f64.mul
    f64.add
    f64.mul
    f64.add
    f64.mul
    local.get $pow_log_w
    f64.const 0.3999999999940942
    local.get $pow_log_w
    f64.const 0.22222198432149784
    local.get $pow_log_w
    f64.const 0.15313837699209373
    f64.mul
    f64.add
    f64.mul
    f64.add
    f64.mul
    f64.add
    local.set $pow_log_R
    local.get $pow_log_s
    local.get $pow_log_hfsq
    local.get $pow_log_R
    f64.add
    f64.mul
    local.get $pow_log_k
    f64.const 1.9082149292705877e-10
    f64.mul
    f64.add
    local.get $pow_log_hfsq
    f64.sub
    local.get $pow_log_f
    f64.add
    local.get $pow_log_k
    f64.const 0.6931471803691238
    f64.mul
    f64.add
    local.set $pow_log_res
    local.get $beta
    local.get $pow_log_res
    f64.mul
    local.set $pow_x
    local.get $pow_x
    f64.const 1.4426950408889634
    f64.mul
    f64.const 0.5
    f64.add
    f64.floor
    local.set $pow_k
    local.get $pow_x
    local.get $pow_k
    f64.const 0.6931471803691238
    f64.mul
    f64.sub
    local.set $pow_hi
    local.get $pow_k
    f64.const 1.9082149292705877e-10
    f64.mul
    local.set $pow_lo
    local.get $pow_hi
    local.get $pow_lo
    f64.sub
    local.set $pow_r
    local.get $pow_r
    local.get $pow_r
    f64.mul
    local.set $pow_t
    local.get $pow_r
    local.get $pow_t
    f64.const 0.16666666666666602
    local.get $pow_t
    f64.const -0.0027777777777015593
    local.get $pow_t
    f64.const 6.613756321437934e-05
    local.get $pow_t
    f64.const -1.6533902205465252e-06
    local.get $pow_t
    f64.const 4.1381367970572385e-08
    f64.mul
    f64.add
    f64.mul
    f64.add
    f64.mul
    f64.add
    f64.mul
    f64.add
    f64.mul
    f64.sub
    local.set $pow_c
    f64.const 1.0
    local.get $pow_r
    local.get $pow_c
    f64.mul
    f64.const 2.0
    local.get $pow_c
    f64.sub
    f64.div
    local.get $pow_lo
    f64.sub
    local.get $pow_hi
    f64.add
    f64.add
    local.set $pow_y
    local.get $pow_k
    f64.const 1023.0
    f64.add
    i64.trunc_f64_u
    i64.const 52
    i64.shl
    f64.reinterpret_i64
    local.set $pow_2k
    local.get $pow_y
    local.get $pow_2k
    f64.mul
    local.set $pow_res
    local.get $output  ;; f_next
    local.get $f
    local.get $alpha_pos
    local.get $pow_res
    f64.mul
    local.get $dw_f
    f64.mul
    f64.add
    f64.store offset=0
    local.get $output  ;; alpha_next
    local.get $alpha
    local.get $nu
    local.get $alpha_pos
    f64.mul
    local.get $dw_alpha
    f64.mul
    f64.add
    f64.store offset=8
  )
)
