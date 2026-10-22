# Project 2 presentation outline

Target length: 5–6 minutes, six slides. Replace team placeholders and adapt the peer-review question after reading the paired group's report.

## Slide 1 — Question and audience (about 40 seconds)

- Question: do low-idiosyncratic-volatility stocks outperform high-volatility stocks after market adjustment?
- Audience: a quantitative portfolio manager considering a low-volatility tilt.
- State the factor: monthly equal-weighted `LMH = Q1 - Q5`.

## Slide 2 — Factor construction (about 50 seconds)

- Estimate idiosyncratic volatility from a trailing 60-month CAPM regression, requiring at least 36 valid observations.
- Form five equal-count groups from information through month `t-1`; use their returns in month `t`.
- Note the limitations: no market capitalization for value weighting and no delisting-return field.

## Slide 3 — Data and methods (about 55 seconds)

- Monthly S&P 500 stock total returns, market returns, and risk-free rates, 2000–2025; tests start in 2005.
- Report the data-cleaning counts: zero duplicate rows, five missing stock returns removed, 3,394 returns and 2,530 volatility values changed in the 1st/99th winsorized check.
- Explain the portfolio CAPM regression and the two-pass Fama-MacBeth method with six-lag Newey-West errors.

## Slide 4 — Main results (about 70 seconds)

- Raw portfolio CAPM alpha: 0.321% monthly, p = 0.172.
- Fama-MacBeth joint LMH premium: -0.090% monthly, p = 0.691.
- MKT + LMH average adjusted cross-sectional R² is 0.0830 versus 0.0624 for MKT only; improved fit does not mean LMH is priced.
- Show the cumulative excess-return figure in `project2_report.md`.

## Slide 5 — Robustness and interpretation (about 70 seconds)

- Winsorized CAPM alpha is 0.451% (p = 0.039), while raw alpha is insignificant; highlight this sensitivity instead of presenting only the significant case.
- The Fama-MacBeth LMH premium remains insignificant for raw, winsorized-dependent-return, and crisis-only tests.
- LMH performs better in down-market months, but recession/COVID average returns do not differ significantly from other months.

## Slide 6 — Conclusion and limitations (about 45 seconds)

- No robust evidence of an LMH premium that a manager can rely on after costs.
- Evidence does not decisively choose between risk-based and behavioral explanations.
- CAPM is the only available factor benchmark; supplied data have no SMB/HML/UMD. Confirm that this project factor meets the assignment's "beyond standard factors" requirement.

## Q&A preparation

Be ready to explain why the characteristic is lagged, how missing returns and extreme observations are handled, why Newey-West errors are used, why a higher R² is not proof of a priced factor, and why the crisis estimate has low precision.

**Draft peer-review question:** How does your factor's risk premium and added explanatory power change when tested against a stronger multifactor benchmark, and does that result survive the stated outlier treatment?
