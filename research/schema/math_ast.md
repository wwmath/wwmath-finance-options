# Math AST — JSON node reference

Every node is a JSON object with an `op` field. The AST keeps the mathematical
meaning as the paper writes it (for example `Sub` and `Div` are kept, not
turned into `Add`/`Pow` the way SymPy does). Execution details only appear
later, when the AST is lowered to the Compute IR.

## Leaves

| op | fields | example |
|---|---|---|
| `Number` | `value` (JSON number) | `{"op": "Number", "value": 2}` |
| `Symbol` | `name` | `{"op": "Symbol", "name": "kappa"}` |
| `Constant` | `name` ∈ `pi`, `e`, `i`, `inf` | `{"op": "Constant", "name": "i"}` |

Symbol names use `_` for subscripts (`z_1`, `sigma_v`) and the suffixes
`bar`, `star` and `hat` for decorations (`kbarstar` → k̄\*, `Fhat` → F̂).

## Arithmetic

`Add`, `Mul`, `Tuple` take `args` (n-ary). `Sub`, `Div` and `Pow` take exactly
2 args. `Neg`, `Sqrt` and `Abs` take 1 arg.

## Functions

| op | fields | meaning |
|---|---|---|
| `Call` | `fn`, `args` | built-in: `exp log sin cos arctan N n Re Im max min` (`N`/`n` = standard normal CDF/PDF; `max(x, 0)` renders as `(x)^+`) |
| `Apply` | `fn`, `args` | a function defined in the same paper, e.g. `psi(u)` or `x(z)` |
| `Index` | `base`, `index` | an indexed quantity, e.g. Heston's `P_j`, `b_1` |

## Relations

`Eq`, `Approx` (asymptotic formulas such as Hagan's), `Ne`, `Lt`, `Le`, `Gt`,
`Ge`, and `Distributed` (`X ~ D`). Each takes 2 `args`.

A formula whose AST is `Eq`/`Approx` **defines** its left-hand side:

* `Symbol` lhs: defines that name (`d_1 = ...`);
* `Index` lhs with numbers: a concrete entry (`b_1 = kappa + lambda - rho sigma`);
* `Index` lhs with symbols: a generic entry (`P_j = ...`, with `j` bound when used);
* `Apply` lhs with symbols: a function (`psi(u) = ...`).

Evaluation uses dynamic scope: an integration variable or function parameter
is visible inside the definitions it reaches. If a definition depends on a
function parameter, it must itself be written as a function (`d(u)`, not `d`).

## Calculus

| op | fields |
|---|---|
| `Integral` | `integrand`, `var` (Symbol), `lower`, `upper` |
| `Sum`, `Product` | `body`, `var`, `lower`, `upper` |
| `Limit` | `expr`, `var`, `to` |
| `Derivative`, `PartialDerivative` | `expr`, `var` |
| `Differential` | `of` (renders as `dX`) |
| `Piecewise` | `pieces: [{value, cond}]`, `otherwise` |

## Probability and stochastic calculus

| op | fields | meaning |
|---|---|---|
| `SDE` | `state`, `terms: [{coef, driver}]` | `d state = Σ coef · d driver`. The driver's kind (time, `brownian_motion`, `poisson_process`, `levy_process`) comes from the paper's `[[symbols]]` |
| `Distribution` | `family` ∈ `Normal`, `Poisson`; `params` | a law; `Normal(m, s²)` takes the variance |
| `Expectation`, `Variance`, `Probability` | `args` (1) | |

A correlation is an `Eq` between differentials: `dz_1 dz_2 = ρ dt`.

## TOML entry layout (`formulas.toml` in an as-of leaf)

```toml
[paper]                 # id (= the leaf's work id), short name, transcription_status,
                        #   title, as_of, imports (earlier leaves whose definitions it uses)
[[symbols]]             # name, kind, description, optional domain / intensity
[[formulas]]            # id, name, kind, source{equation, page, fidelity,
                        #   verified_against_pdf}, depends_on, latex, ast
[[checks]]              # executable checks (see tools/validate.py)
```

`source.fidelity` is one of:

* `verbatim-notation`: the paper's own equation, in its own notation;
* `restated`: the paper's content, reorganised or in changed notation;
* `modern-restatement`: a modern textbook form of the paper's result;
* `derived`: derived by us from the paper's model and marked for comparison
  with the paper.

A formula may carry `uses_later_work = ["<work id>"]` when it cannot yet be
separated from a later work (for example Bates' CF, written in the 2007 little-trap
form until the Bates PDF is transcribed). The validator lists these as as-of
exceptions; an `imports` entry that points forward in time is an error.

`verified_against_pdf` stays `false` until someone has compared the entry
line by line against the PDF.

`latex` is generated from `ast` (the Display IR), and the validator fails if
the two drift apart.
