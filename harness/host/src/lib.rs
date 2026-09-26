//! Rust host / orchestrator for the Cross-Language Heston WASM Conformance Harness.
//!
//! Each engine (C, C++, Fortran, Zig, Rust, direct WASM) is an independently compiled
//! wasm32 module exporting every kernel with the same flat ABI:
//!
//!     kernel(states..., dt, params..., randoms..., output_ptr)
//!     output[i] = next value of state i
//!
//! The page instantiates each module and hands its exports to this host. The host owns
//! the random numbers (normals and compound jumps), so every engine sees bit-identical
//! inputs; it drives the Monte Carlo through the ABI only and reports outputs, timings
//! and differences against the reference engine.

use js_sys::{Array, Float64Array, Function, Reflect, WebAssembly};
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;

const NORMAL: u32 = 0;
const COMPOUND_JUMP: u32 = 1;

struct Engine {
    name: String,
    exports: JsValue,
    memory: WebAssembly::Memory,
    out_ptr: u32,
}

impl Engine {
    fn kernel(&self, name: &str) -> Result<Function, JsValue> {
        Reflect::get(&self.exports, &name.into())?
            .dyn_into::<Function>()
            .map_err(|_| JsValue::from_str(&format!("{} does not export {name}", self.name)))
    }

    fn call(&self, f: &Function, args: &Array, inputs: &[f64], n_out: u32) -> Vec<f64> {
        for (i, x) in inputs.iter().enumerate() {
            args.set(i as u32, JsValue::from_f64(*x));
        }
        args.set(inputs.len() as u32, JsValue::from(self.out_ptr));
        f.apply(&JsValue::NULL, args).expect("engine call failed");
        let view =
            Float64Array::new_with_byte_offset_and_length(&self.memory.buffer(), self.out_ptr, n_out);
        view.to_vec()
    }
}

/// SplitMix64 + Box-Muller normals, Poisson by inversion, lognormal compound jumps.
struct Rng {
    state: u64,
    spare: Option<f64>,
}

impl Rng {
    fn new(seed: u64) -> Self {
        Rng { state: seed, spare: None }
    }
    fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn uniform(&mut self) -> f64 {
        ((self.next_u64() >> 11) as f64 + 0.5) * (1.0 / (1u64 << 53) as f64)
    }
    fn normal(&mut self) -> f64 {
        if let Some(s) = self.spare.take() {
            return s;
        }
        let (u1, u2) = (self.uniform(), self.uniform());
        let r = (-2.0 * u1.ln()).sqrt();
        let th = 2.0 * std::f64::consts::PI * u2;
        self.spare = Some(r * th.sin());
        r * th.cos()
    }
    fn poisson(&mut self, mean: f64) -> u32 {
        let (limit, mut p, mut n) = ((-mean).exp(), 1.0, 0u32);
        loop {
            p *= self.uniform();
            if p <= limit {
                return n;
            }
            n += 1;
        }
    }
    /// dJ = prod(1 + k_i) - 1 with ln(1 + k_i) ~ N(m, sd^2), N ~ Poisson(mean)
    fn compound_jump(&mut self, mean: f64, m: f64, sd: f64) -> f64 {
        let n = self.poisson(mean);
        if n == 0 {
            return 0.0;
        }
        let s: f64 = (0..n).map(|_| m + sd * self.normal()).sum();
        s.exp() - 1.0
    }
}

fn now() -> f64 {
    let perf = Reflect::get(&js_sys::global(), &"performance".into()).unwrap();
    let f: Function = Reflect::get(&perf, &"now".into()).unwrap().dyn_into().unwrap();
    f.call0(&perf).unwrap().as_f64().unwrap()
}

fn num(x: f64) -> String {
    if x.is_finite() {
        format!("{x:e}")
    } else {
        "null".into()
    }
}

fn nums(xs: &[f64]) -> String {
    xs.iter().map(|x| num(*x)).collect::<Vec<_>>().join(",")
}

#[wasm_bindgen]
pub struct Harness {
    engines: Vec<Engine>,
}

#[wasm_bindgen]
impl Harness {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Harness {
        Harness { engines: Vec::new() }
    }

    /// Register an instantiated engine module by its exports object.
    pub fn add_engine(&mut self, name: String, exports: JsValue) -> Result<(), JsValue> {
        let memory: WebAssembly::Memory = Reflect::get(&exports, &"memory".into())?.dyn_into()?;
        // A fresh page nobody else uses holds the outputs.
        let old_pages = memory.grow(1);
        self.engines.push(Engine { name, exports, memory, out_ptr: old_pages * 65536 });
        Ok(())
    }

    pub fn engine_names(&self) -> Vec<String> {
        self.engines.iter().map(|e| e.name.clone()).collect()
    }

    /// One call of `kernel` in every engine on the same inputs: JSON {engine: [outputs]}.
    pub fn step_all(&self, kernel: String, inputs: Vec<f64>, n_out: u32) -> Result<String, JsValue> {
        let args = Array::new_with_length(inputs.len() as u32 + 1);
        let mut parts = Vec::new();
        for e in &self.engines {
            let f = e.kernel(&kernel)?;
            parts.push(format!("\"{}\":[{}]", e.name, nums(&e.call(&f, &args, &inputs, n_out))));
        }
        Ok(format!("{{{}}}", parts.join(",")))
    }

    /// Monte Carlo of `kernel` through every engine with shared random inputs.
    ///
    /// `init`: initial states; `params`: kernel parameters; `random_kinds`: 0 = normal,
    /// 1 = compound jump; `jump`: [intensity, mean log jump, log jump sd]. Prices are
    /// `discount * E[(state_0(T) - K)^+]`. Returns JSON.
    #[allow(clippy::too_many_arguments)]
    pub fn run(&self, kernel: String, init: Vec<f64>, params: Vec<f64>, random_kinds: Vec<u32>,
               jump: Vec<f64>, t_end: f64, paths: u32, steps: u32, seed: u64,
               strikes: Vec<f64>, discount: f64, reference: String) -> Result<String, JsValue> {
        let dt = t_end / steps as f64;
        let n_states = init.len();
        let n_rand = random_kinds.len();
        let mut rng = Rng::new(seed);
        let total = paths as usize * steps as usize;
        let mut randoms = vec![0.0; total * n_rand];
        for s in 0..total {
            for (j, kind) in random_kinds.iter().enumerate() {
                randoms[s * n_rand + j] = match *kind {
                    NORMAL => rng.normal(),
                    COMPOUND_JUMP => rng.compound_jump(jump[0] * dt, jump[1], jump[2]),
                    _ => return Err("unknown random kind".into()),
                };
            }
        }
        let n_in = n_states + 1 + params.len() + n_rand;
        let args = Array::new_with_length(n_in as u32 + 1);
        let mut inputs = vec![0.0; n_in];
        inputs[n_states] = dt;
        inputs[n_states + 1..n_states + 1 + params.len()].copy_from_slice(&params);

        struct Res { name: String, elapsed: f64, terminal: Vec<f64>, prices: Vec<f64>, se: Vec<f64> }
        let mut results: Vec<Res> = Vec::new();
        for e in &self.engines {
            let f = e.kernel(&kernel)?;
            let mut terminal = vec![0.0; paths as usize];
            let t0 = now();
            for p in 0..paths as usize {
                let mut state = init.clone();
                for s in 0..steps as usize {
                    inputs[..n_states].copy_from_slice(&state);
                    let k = (p * steps as usize + s) * n_rand;
                    inputs[n_in - n_rand..].copy_from_slice(&randoms[k..k + n_rand]);
                    state = e.call(&f, &args, &inputs, n_states as u32);
                }
                terminal[p] = state[0];
            }
            let elapsed = now() - t0;
            let (prices, se): (Vec<f64>, Vec<f64>) = strikes
                .iter()
                .map(|&k| {
                    let pay: Vec<f64> = terminal.iter().map(|&x| discount * (x - k).max(0.0)).collect();
                    let m = pay.iter().sum::<f64>() / paths as f64;
                    let var = pay.iter().map(|p| (p - m) * (p - m)).sum::<f64>() / (paths as f64 - 1.0);
                    (m, (var / paths as f64).sqrt())
                })
                .unzip();
            results.push(Res { name: e.name.clone(), elapsed, terminal, prices, se });
        }

        let ri = results.iter().position(|r| r.name == reference).unwrap_or(0);
        let body: Vec<String> = results
            .iter()
            .map(|r| {
                let diff = r.terminal.iter().zip(&results[ri].terminal)
                    .map(|(a, b)| (a - b).abs()).fold(0.0, f64::max);
                let same = r.terminal.iter().zip(&results[ri].terminal)
                    .all(|(a, b)| a.to_bits() == b.to_bits());
                format!(
                    "{{\"name\":\"{}\",\"elapsed_ms\":{},\"calls\":{},\"max_abs_path_diff\":{},\
                     \"bit_identical\":{same},\"prices\":[{}],\"se\":[{}]}}",
                    r.name, num(r.elapsed), total, num(diff), nums(&r.prices), nums(&r.se))
            })
            .collect();
        Ok(format!("{{\"kernel\":\"{kernel}\",\"reference\":\"{}\",\"strikes\":[{}],\"engines\":[{}]}}",
                   results[ri].name, nums(&strikes), body.join(",")))
    }
}

impl Default for Harness {
    fn default() -> Self {
        Self::new()
    }
}
