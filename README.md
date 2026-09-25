wwmath-finance-options
/
README.md

## Research

`research/` holds the Math AST formula library: the core option-pricing papers
(Bachelier, Black-76, Heston, Bates, SABR, ZABR, Sidani, Alòs–Burés–Vives), each
transcribed to TOML with JSON Math ASTs. The library is validated numerically,
by Monte Carlo from the SDE ASTs, and through a FORTRAN 77 backend. See
[research/README.md](research/README.md).
