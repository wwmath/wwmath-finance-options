// Shared by the page and the Node test: turn a kernel's manifest entry plus parameter
// values into the host's run() arguments.
export function runArgs(kernel, p) {
  const init = kernel.states.map((s) => p[s]);
  const params = kernel.params.map((s) => p[s]);
  const kinds = kernel.randoms.map((r) => (r.kind === "normal" ? 0 : 1));
  const j = kernel.jump;
  const jump = j
    ? [p[j.intensity], Math.log1p(p[j.mean_jump]) - 0.5 * p[j.log_sd] ** 2, p[j.log_sd]]
    : [0, 0, 0];
  const discount = kernel.discount_rate ? Math.exp(-p[kernel.discount_rate] * p.T) : 1.0;
  return { init, params, kinds, jump, discount };
}

// Every numeric input a kernel's page form needs (states, params, extras, run controls).
export function formFields(kernel) {
  return [...kernel.states, ...kernel.params, ...kernel.extra, "T", "paths", "steps", "seed"];
}
