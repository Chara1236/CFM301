\[
\beta_{i,t}^{-}
=
\frac{
\operatorname{Cov}\left(
R_{i,\tau}-R_{f,\tau},
R_{m,\tau}-R_{f,\tau}
\mid R_{m,\tau}-R_{f,\tau}<0
\right)
}{
\operatorname{Var}\left(
R_{m,\tau}-R_{f,\tau}
\mid R_{m,\tau}-R_{f,\tau}<0
\right)
}
\]Implement a monthly downside beta calculation for each stock using the following methodology:

1. Use monthly stock returns, monthly market returns, and monthly risk-free rates. Calculate stock excess return as Ri - Rf and market excess return as Rm - Rf. Ensure all returns use consistent units.
2. At each month t, estimate downside beta using a rolling window of the previous 60 calendar months, including month t and excluding all future observations. For example, the beta formed at December 2020 uses January 2016 through December 2020.
3. Within that window, retain only months where market excess return (Rm - Rf) is strictly less than zero. Use the same retained months for both stock and market excess returns.
4. Calculate downside beta as sample covariance of stock excess returns and market excess returns over those retained months, divided by the sample variance of market excess returns over those same months:

beta_downside = Cov(Ri - Rf, Rm - Rf | Rm - Rf < 0) / Var(Rm - Rf | Rm - Rf < 0).

5. Require at least 12 valid down-market observations in the 60-month window. If fewer than 12 exist, or market variance is zero or missing, return NaN rather than an unreliable estimate. Make the minimum-observation threshold configurable.
6. Handle missing values by dropping months where any required return is missing. Do not treat missing returns as zero. Do not winsorize valid extreme returns by default; investigate possible data errors first. Include delisting returns when available and correctly adjust CRSP returns for delisting events to avoid double-counting.
7. Recalculate downside beta at every month-end for each stock with sufficient data. Store the stock identifier, estimation month, downside beta, number of qualifying down-market observations, and estimation-window start/end dates.
8. Avoid look-ahead bias: downside beta estimated at month t may only use data available by month t. Use it to form portfolios for month t+1. Ensure monthly dates are aligned
Explain the implementation and document any assumptions. Do not silently substitute ordinary beta for downside beta.