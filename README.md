wwmath-finance-options
/
README.md

## Research

`research/` holds the Math AST formula library: the core option-pricing papers
(Bachelier, Black-76, Heston, Bates, SABR, ZABR, Sidani, Alòs–Burés–Vives), each
transcribed to TOML with JSON Math ASTs. The library is validated numerically,
by Monte Carlo from the SDE ASTs, and through a FORTRAN 77 backend. See
[research/README.md](research/README.md).

## QuantLib conformance (C++)

`quantlib-conformance/` is a CMake/GoogleTest project that tests the 9 ledger
models QuantLib implements. It compares C++ generated from the paper ASTs with
the QuantLib C++ library, and exports golden vectors to
`quantlib-conformance/fixtures/quantlib/`. See
[quantlib-conformance/README.md](quantlib-conformance/README.md).
