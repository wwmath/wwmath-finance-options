//! Rust host / orchestrator for the Cross-Language Heston WASM Conformance Harness.
//!
//! Each engine (C, C++, Fortran, Zig, Rust, direct WASM) is an independently compiled
//! wasm32 module exporting the same flat ABI:
//!
//!     normal_heston_step(x, v, dt, kappa, theta, xi, rho, z1, z2, output_ptr)
//!     output[0] = x_next, output[1] = v_next
//!
//! The page instantiates each module and hands its exports to this host. The host owns
//! the random numbers, so every engine sees bit-identical inputs, drives the Monte
//! Carlo through the ABI only, and reports outputs, timings and differences against
//! the reference engine.

use js_sys::{Array, Float64Array, Function, Reflect, WebAssembly};
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;

const KERNEL: &str = "normal_heston_step";

struct Engine {
    name: String,
    func: Function,
    memory: WebAssembly::Memory,
    out_ptr: u32,
}

impl Engine {
    fn step(&self, a: &[f64; 9], args: &Array) -> (f64, f64) {
        for (i, x) in a.iter().enumerate() {
            args.set(i as u32, JsValue::from_f64(*x));
        }
        args.set(9, JsValue::from(self.out_ptr));
        self.func
            .apply(&JsValue::NULL, args)
            .expect("engine call failed");
        let view = Float64Array::new_with_byte_offset_and_length(
            &self.memory.buffer(),
            self.out_ptr,
            2,
        );
        (view.get_index(0), view.get_index(1))
    }
}

/// SplitMix64 + Box-Muller: deterministic standard normals shared by all engines.
struct Normals {
    state: u64,
    spare: Option<f64>,
}

impl Normals {
    fn new(seed: u64) -> Self {
        Normals { state: seed, spare: None }
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
}

fn now() -> f64 {
    let perf = Reflect::get(&js_sys::global(), &"performance".into()).unwrap();
    let f: Function = Reflect::get(&perf, &"now".into()).unwrap().dyn_into().unwrap();
    f.call0(&perf).unwrap().as_f64().unwrap()
}

fn js_num(x: f64) -> String {
    if x.is_finite() {
        format!("{x:e}")
    } else {
        "null".into()
    }
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

    /// Register an instantiated engine by its exports object.
    pub fn add_engine(&mut self, name: String, exports: JsValue) -> Result<(), JsValue> {
        let func: Function = Reflect::get(&exports, &KERNEL.into())?.dyn_into()?;
        let memory: WebAssembly::Memory = Reflect::get(&exports, &"memory".into())?.dyn_into()?;
        // A fresh page nobody else uses holds the two outputs.
        let old_pages = memory.grow(1);
        self.engines.push(Engine { name, func, memory, out_ptr: old_pages * 65536 });
        Ok(())
    }

    pub fn engine_names(&self) -> Vec<String> {
        self.engines.iter().map(|e| e.name.clone()).collect()
    }

    /// One call of every engine on the same inputs: JSON {name: [x_next, v_next]}.
    #[allow(clippy::too_many_arguments)]
    pub fn step_all(&self, x: f64, v: f64, dt: f64, kappa: f64, theta: f64, xi: f64,
                    rho: f64, z1: f64, z2: f64) -> String {
        let args = Array::new_with_length(10);
        let a = [x, v, dt, kappa, theta, xi, rho, z1, z2];
        let parts: Vec<String> = self
            .engines
            .iter()
            .map(|e| {
                let (xn, vn) = e.step(&a, &args);
                format!("\"{}\":[{},{}]", e.name, js_num(xn), js_num(vn))
            })
            .collect();
        format!("{{{}}}", parts.join(","))
    }

    /// Monte Carlo through every engine with shared normals. Returns JSON.
    #[allow(clippy::too_many_arguments)]
    pub fn run(&self, x0: f64, v0: f64, t_end: f64, kappa: f64, theta: f64, xi: f64,
               rho: f64, paths: u32, steps: u32, seed: u64, strikes: Vec<f64>,
               reference: String) -> String {
        let dt = t_end / steps as f64;
        let mut rng = Normals::new(seed);
        let n = (paths * steps) as usize;
        let z: Vec<f64> = (0..2 * n).map(|_| rng.normal()).collect();
        let args = Array::new_with_length(10);

        let mut results: Vec<(String, f64, Vec<f64>, Vec<f64>, Vec<f64>)> = Vec::new();
        for e in &self.engines {
            let mut terminal = vec![0.0; paths as usize];
            let t0 = now();
            for p in 0..paths as usize {
                let (mut x, mut v) = (x0, v0);
                for s in 0..steps as usize {
                    let k = 2 * (p * steps as usize + s);
                    let out = e.step(&[x, v, dt, kappa, theta, xi, rho, z[k], z[k + 1]], &args);
                    x = out.0;
                    v = out.1;
                }
                terminal[p] = x;
            }
            let elapsed = now() - t0;
            let (prices, ses): (Vec<f64>, Vec<f64>) = strikes
                .iter()
                .map(|&k| {
                    let pay: Vec<f64> = terminal.iter().map(|&x| (x - k).max(0.0)).collect();
                    let m = pay.iter().sum::<f64>() / paths as f64;
                    let var = pay.iter().map(|p| (p - m) * (p - m)).sum::<f64>()
                        / (paths as f64 - 1.0);
                    (m, (var / paths as f64).sqrt())
                })
                .unzip();
            results.push((e.name.clone(), elapsed, terminal, prices, ses));
        }

        let ref_idx = results.iter().position(|r| r.0 == reference).unwrap_or(0);
        let (ref_terminal, ref_prices) = (results[ref_idx].2.clone(), results[ref_idx].3.clone());
        let body: Vec<String> = results
            .iter()
            .map(|(name, elapsed, terminal, prices, ses)| {
                let path_diff = terminal
                    .iter()
                    .zip(&ref_terminal)
                    .map(|(a, b)| (a - b).abs())
                    .fold(0.0, f64::max);
                let bit_identical = terminal
                    .iter()
                    .zip(&ref_terminal)
                    .all(|(a, b)| a.to_bits() == b.to_bits());
                let price_diff: Vec<String> = prices
                    .iter()
                    .zip(&ref_prices)
                    .map(|(a, b)| js_num((a - b).abs()))
                    .collect();
                format!(
                    "{{\"name\":\"{name}\",\"elapsed_ms\":{},\"calls\":{},\"max_abs_path_diff\":{},\
                     \"bit_identical\":{bit_identical},\"prices\":[{}],\"se\":[{}],\"price_diff\":[{}]}}",
                    js_num(*elapsed),
                    paths as u64 * steps as u64,
                    js_num(path_diff),
                    prices.iter().map(|p| js_num(*p)).collect::<Vec<_>>().join(","),
                    ses.iter().map(|p| js_num(*p)).collect::<Vec<_>>().join(","),
                    price_diff.join(",")
                )
            })
            .collect();
        format!(
            "{{\"reference\":\"{}\",\"strikes\":[{}],\"engines\":[{}]}}",
            results[ref_idx].0,
            strikes.iter().map(|k| js_num(*k)).collect::<Vec<_>>().join(","),
            body.join(",")
        )
    }
}

impl Default for Harness {
    fn default() -> Self {
        Self::new()
    }
}
