# CFM 301 – Project 2: Finding and Testing a Factor
## Requirements guide for the downside-beta project

This guide explains what the course expects for Project 2, requirement by requirement, and what that means for **our** project (downside beta, CAPM as the benchmark, S&P 500 monthly data, 2000–2025). Section 9 is a to-do list of what is still missing.

---

## 1. The project at a glance

| Item | What the handout says |
|---|---|
| Goal | Propose at least one factor **beyond** market, SMB, HML, UMD that helps explain the cross-section of returns, and give empirical evidence for it |
| What is really graded | Whether the group **correctly applies class tools**: return construction, data cleaning, building a factor, regressions, sensitivity checks, rational-vs-behavioral interpretation, market efficiency |
| Group | 3–5 students; same group all term |
| Report | **Max 4 pages** |
| Code deadline | LEARN Dropbox, **2 days before** the presentation: report, code, README, trimmed data files |
| Slides deadline | Separate Dropbox folder, **1 hour before** the session |
| Presentation | 5–6 minutes, every member present and able to answer questions; at least one question/comment for the paired group |
| Points | 15 total: 12 for analysis/report/code, 3 for presentation and peer review |

**Important rule:** if a technique does not apply to your setting, you must *explain why in the report*. A technique skipped without explanation counts as missing.

---

## 2. Our project in one paragraph

**Question:** Do investors earn a higher return for holding stocks that fall hardest *when the market is already falling* (high downside beta), after accounting for ordinary CAPM beta?

**Audience:** quantitative fund managers or pension funds deciding whether to tilt toward (or away from) downside-beta exposure.

**Factor:** downside beta, β⁻ = Cov(Rᵢ−R_f, Rₘ−R_f | Rₘ−R_f < 0) / Var(Rₘ−R_f | Rₘ−R_f < 0), estimated over a rolling 60-month window using only months where the market excess return is strictly negative (at least 12 such months required).

**Benchmark:** CAPM (ordinary beta).

**Models (estimated month by month on the cross-section of stocks, Fama–MacBeth):**

| Name | Regression for next-month excess return Rᵉᵢ,t+1 |
|---|---|
| CAPM benchmark | a + γ_β · βᵢ,t |
| Model 1 | a + γ_D · β⁻ᵢ,t |
| Model 2 | a + γ_β · βᵢ,t + γ_D · β⁻ᵢ,t |

The key test is **H₀: γ_D = 0**. All betas are measured at the end of month *t* and used to explain the return in month *t+1*.

---

## 3. Rubric → what must be visible in the report

| Rubric item | Pts | What the grader looks for | Where it is in our work |
|---|---|---|---|
| Factor defined, economic rationale, audience | 2 | Precise definition, why exposure should earn a premium (how it defines "bad times"), who the audience is | Report §1 (to write) |
| Data sourcing, factor construction, returns, cleaning (incl. winsorization) documented | 2 | Source, universe, sample, return variable, dividend/split treatment, counts affected by each cleaning step, winsorization cut-offs | Notebook §3–5 (done); report §2 (to write) |
| Regressions correctly specified and reported | 2 | Coefficients, **t-stats, R²**, correct standard errors | Notebook §6 (done) |
| Benchmark comparison, correctly interpreted | 1 | CAPM vs. CAPM + factor; does the factor add explanatory power? | Notebook §6 (done); interpretation (to write) |
| Sensitivity: ≥2 alternative assumptions | 2 | Compact table; do premium, significance and added power hold up? | Notebook §8 (done); discussion (to write) |
| Interpretation: rational vs. behavioral, efficiency, audience | 2 | Argument backed by evidence (e.g., bad-times behavior), efficiency form, why not arbitraged away, what it means for the audience | Notebook §9 evidence (done); text (to write) |
| Reproducibility | 1 | Instructor runs code on submitted files and gets the report's numbers | README + notebook (needs final test) |
| Presentation | 2 | Question, method, results, conclusion; each member answers questions | To prepare |
| Peer review | 1 | One substantive question/comment on the paired group | To prepare |

---

## 4. Requirement-by-requirement guide

### Requirement 1 – Propose the factor and give an economic rationale

**What is expected**
- Define the factor precisely (formula, window, conditioning rule).
- Explain **why exposure should earn a risk premium**, in the multifactor framework from class: a factor earns a premium if exposure to it makes you do badly in "bad times" (when marginal utility is high), so investors demand extra return for holding it.
- State the audience and let it shape your framing and conclusion.

**For us**
- Rationale: stocks with high downside beta lose more when the market is already down, so they are poor hedges in bad times. Rational investors, especially loss-averse ones, should require extra return for them. This is the downside-risk idea (e.g., Ang, Chen and Xing 2006; Bawa and Lindenberg 1977); check the references your course covers before citing.
- Be explicit about the *bad-time definition*: market excess return below zero.
- Check with your instructor whether downside beta counts as "beyond market, SMB, HML, UMD" for this project. It is a conditional version of market beta, so be ready to explain what it adds beyond ordinary beta (that is exactly what Model 2 tests).

### Requirement 2 – Construct or source the factor and test assets

**What is expected:** a factor time series and a set of test assets built from CRSP/Compustat-type data.

**For us:** the test assets are individual S&P 500 stocks (about 434 per month in the regression sample) and the factor is each stock's downside beta (a characteristic). Because we test with Fama–MacBeth cross-sectional regressions, individual stocks are the test assets.

**Gap to be aware of:** requirement 5 literally says "regress test-asset returns on your factor (and the market factor as a control)". That is a time-series regression on a factor *return*. Our approach is the standard test for a characteristic/beta premium, but if the instructor expects the literal version, add a long-short portfolio (high minus low downside-beta stocks) and regress its returns on the market return. Ask or hedge in the report, and say which design you chose and why.

### Requirement 3 – Construct returns correctly

**What is expected**
- Returns must be **total returns that include dividends** and are adjusted for splits and other distributions.
- CRSP's `RET` includes dividends; `RETX` does not. Raw `PRC` is not split-adjusted (use `CFACPR` if computing returns from prices).
- **State which variable or formula you used and the return frequency.**

**For us**
- Variable: the supplied `total_return` column, monthly, decimals (0.05 = 5%). It is used as is. It is **not** recomputed from `price`, which is not split-adjusted.
- Excess return = stock total return − risk-free return in the same month; market excess return = market return − risk-free.
- No separate delisting-return field exists in the file, so no delisting adjustment is possible. Say so in the report as a limitation.
- Make sure all three files use the same units (decimals) and month-end dates (the notebook checks this).

### Requirement 4 – Clean the data

**Minimum required:** address **missing values, duplicates, outliers**; **winsorize** returns and the sorting characteristics (state cut-offs) or explain why not; **report how many observations each step affects**.

**What we did (from the latest notebook run)**

| Step | Rows affected | Rows remaining |
|---|---|---|
| Raw stock-month rows | 156,560 | 156,560 |
| Duplicate PERMNO-month rows dropped | 0 | 156,560 |
| Missing `total_return` dropped (never set to zero) | 5 | 156,555 |
| Returns with \|R\| > 100% flagged and inspected (kept) | 17 | 156,555 |

**Sample attrition for the regressions**

| Step | Rows affected | Rows remaining |
|---|---|---|
| Stock-months with a return from 2005-01 (first month with a full 60-month window) | – | 126,555 |
| Dropped: no usable ordinary beta (< 36 valid months) | 16,120 | 110,435 |
| Dropped: no usable downside beta (< 12 down-market months) | 1,074 | 109,361 |
| **Final regression sample** | | **109,361 stock-months, 857 securities, 252 months** |

**Winsorization**
- Dependent variable and both beta characteristics are winsorized at the **1st/99th percentile within each month**, for the regressions only; 2,510 values per variable are changed.
- The betas themselves are estimated from **raw** returns. Reason: the downside-beta spec says not to winsorize valid extreme returns by default and to investigate possible data errors first, while the course requires winsorizing returns and sorting characteristics. The two are reconciled by keeping extreme returns when estimating betas and winsorizing in the final regression. Explain this in the report.
- Outlier inspection: the largest returns cluster in crisis periods (2002, 2008–09, 2020, 2023), so they were treated as real rather than data errors.

**Other cleaning decisions to document**
- Dates must be month-ends and aligned across files; stocks are identified by `PERMNO`, not ticker.
- Months with a missing stock or market return are dropped from a beta window, never treated as zero.
- Universe note: the file contains S&P 500 members only while they were in the index, so recent additions have short histories (selection effect).

### Requirement 5 – Test the factor with OLS

**What is expected:** regress test-asset returns on the factor (with the market as control) and report **estimated loadings, t-statistics, and R²**.

**Our regressions** (Fama–MacBeth)
1. Each month, run a cross-sectional OLS of next-month excess returns on the betas.
2. The reported coefficient is the **average of the monthly slopes**.
3. Standard errors are **Newey–West (6 lags)** on the monthly slope series, which handles serial correlation and heteroskedasticity.
4. R² is the average cross-sectional R² across months.

**Why this connects to the OLS slides**
- Default (homoskedastic) standard errors are usually wrong for financial data. Heteroskedasticity does not bias coefficients, it makes standard errors wrong. Use robust errors, and if they come out smaller than the default, use the larger ones.
- Pooling all stock-months in one OLS gives standard errors that are far too small because stocks move together in each month. We use clustering by month only as a cross-check.
- Multicollinearity does not bias coefficients but inflates standard errors. Ordinary and downside beta are correlated (average cross-sectional correlation about 0.71, variance inflation factor about 2), so judge Model 2's t-statistics with that in mind.
- **Statistical vs. economic significance:** always say how large the effect is (our estimate: about 0.10% per month for a 1-standard-deviation higher downside beta in Model 2), not just whether it is significant.

**What to put in the report table**
- Rows: intercept, ordinary beta, downside beta. Columns: CAPM benchmark, Model 1, Model 2.
- Show the coefficient, the t-statistic in parentheses, stars for significance, the average R² (and adjusted R²), the number of months and average stocks per month.
- State the units (% per month) and the standard-error method under the table.

### Requirement 6 – Compare to a benchmark model

**What is expected:** compare explanatory power against a standard benchmark and say whether the factor **adds** explanatory power.

**For us:** CAPM is the benchmark (allowed by the handout). Compare Model 2 with the CAPM benchmark on:
1. The significance of γ_D (does the factor have a priced premium?).
2. Adjusted R² (does it fit the cross-section better?).

**Interpretation trap:** a higher R² does not mean the factor is *priced*. Downside beta is a second, noisy measure of market sensitivity, so it can raise R² while earning no premium. The t-statistic on γ_D answers the pricing question, the R² gain answers the fit question, and the report should say both.

**Weakness to acknowledge:** beating CAPM is an easier bar than beating a multifactor model such as Fama–French. Say so, and consider listing the correlation with SMB/HML/UMD or adding a multifactor benchmark as one of the sensitivity checks.

### Requirement 7 – Sensitivity analysis (at least two alternatives)

**What is expected:** re-run the main tests under at least two alternative assumptions and report whether the premium, its significance and its added explanatory power hold up. A compact table is enough.

**What the notebook already covers**
- Excluding 2008–09 and excluding 2020.
- Early (2005–2012) vs. late (2013–2025) sample.
- Winsorization at 5/95 and none.
- A 36-month beta window instead of 60.

Other options if you want more: terciles vs. quintiles or equal- vs. value-weighted legs (if you add a long-short portfolio), and a different benchmark model.

**What to write:** one or two sentences per row group on whether the sign, size and significance of γ_D change. Do not just paste the table.

### Requirement 8 – Rational (risk-based) vs. behavioral

**What is expected:** argue which explanation fits better, using the theories from class, **supported by evidence**.

**Framework**
- *Rational:* the premium compensates for risk, so the factor should do badly in bad times (recessions, market downturns) when marginal utility is high.
- *Behavioral/mispricing:* the premium comes from investor biases or limits to arbitrage; it need not be tied to bad states.

**Evidence from the notebook (§9)**
- Average monthly downside-beta slope in down-market vs. up-market months.
- NBER recession (Dec 2007–Jun 2009, Feb–Apr 2020) vs. expansion months.
- A regression of the monthly slope on the market excess return.
- Which individual months drive the average.

Be honest if the evidence is weak: a premium that is not statistically significant supports neither story strongly.

### Requirement 9 – Market efficiency

Answer these three points in the report:

1. **Which form of efficiency does it speak to?** Our factor is built only from past public prices and returns, so it speaks to **weak-form** efficiency (can past price information predict returns?).
2. **Is the premium consistent with efficiency?** If a premium exists, is it compensation for bearing bad-time risk (consistent) or evidence of an inefficiency? If no significant premium is found, that is consistent with weak-form efficiency, and you should say so.
3. **If it points to an inefficiency, why isn't it traded away?** Costly information and trading, short-sale constraints, barriers to capital, arbitrage risk; and whether this fits a "near-efficient" market in the Grossman–Stiglitz (1980) sense, where some mispricing must persist to compensate those who gather information.

### Audience conclusion

End with a direct recommendation for the audience: can they earn the premium **after costs**, and should they tilt? For example: S&P 500 stocks are large and liquid, so trading costs are modest, but if the estimated premium is statistically indistinguishable from zero, a tilt is hard to justify.

---

## 5. Suggested 4-page report outline

| Section | Length | Contents |
|---|---|---|
| 1. Question, factor, rationale, audience | ~0.5 page | Definition, bad-times argument, who it is for |
| 2. Data and methods | ~1 page | Source, universe (S&P 500 members), sample 2005–2025, `total_return` and units, cleaning counts, winsorization, beta construction, timing (t → t+1), Fama–MacBeth and Newey–West |
| 3. Results | ~1 page | Main regression table (CAPM, Model 1, Model 2), one figure, economic size, benchmark comparison |
| 4. Sensitivity | ~0.5 page | Compact table plus 3–4 sentences |
| 5. Interpretation | ~1 page | Rational vs. behavioral evidence, market efficiency, audience conclusion, limitations |

Tips: one regression table, one sensitivity table, one figure. Cite packages (numpy, pandas, matplotlib) and the data sources.

---

## 6. Reproducibility checklist

- [ ] Code runs from a clean start ("Restart & Run All") and produces every table and figure in the report
- [ ] Only the data actually used is submitted (the three CSVs); no WRDS login, internet, or manual steps needed
- [ ] Relative paths only (e.g., `data/…csv`), no `C:\Users\…`
- [ ] README lists language/version, packages with versions, and the order to run files
- [ ] A group member who did **not** write the code runs the submission from a new folder start to finish
- [ ] Numbers in the report match the notebook output exactly (re-copy them after the final run)

---

## 7. Presentation and peer review

**5–6 minutes, about 5–6 slides:** (1) question and audience, (2) factor and rationale, (3) data and method, (4) main results table/figure, (5) sensitivity and interpretation, (6) conclusion for the audience.

- Every member must be present; the instructor asks every member at least one question, and absent members get a lower grade.
- Be ready for: why lag the betas? why Fama–MacBeth? why Newey–West? why is CAPM enough as the benchmark? why is a high R² not the same as a priced factor? what are the limits of an S&P 500-only sample?
- **Peer review:** read the paired group's report after the deadline and prepare one substantive question about their methodology, assumptions, or conclusions (e.g., look-ahead bias, outlier treatment, whether their benchmark is demanding enough).

---

## 8. Current results snapshot (latest notebook run, 2005-01 to 2025-12)

Coefficients in % per month, Newey–West t-statistics in parentheses.

| | CAPM benchmark | Model 1: downside beta | Model 2: CAPM + downside |
|---|---|---|---|
| Intercept | 0.545 (2.53) | 0.514 (2.06) | 0.543 (2.50) |
| Ordinary beta | 0.217 (0.81) | | 0.089 (0.34) |
| Downside beta | | 0.245 (1.41) | 0.133 (1.11) |
| Avg adjusted R² | 0.0615 | 0.0390 | 0.0694 |
| Avg R² | 0.0637 | 0.0412 | 0.0737 |
| Months / avg stocks | 252 / 434 | 252 / 434 | 252 / 434 |

- The downside-beta coefficient is positive but **not statistically significant** (Model 2: p = 0.27, 95% CI about −0.10 to +0.37).
- The average market excess return over the same months is 0.82% per month, while the estimated CAPM slope is only 0.22.
- Adjusted R² rises from 0.0615 (CAPM) to 0.0694 (Model 2), a statistically significant gain in fit, but that is not evidence of a priced premium.
- Sensitivity: the sign stays positive and the significance stays weak across all alternatives; Model 1 reaches 10% significance in two of them (no winsorization and the 36-month window).
- Bad times: the recession-month average slope is larger (+1.16% vs. +0.03% in expansions) but it rests on 22 months and is driven by a few extreme months in 2008–09; it is not statistically reliable.

Re-run the notebook before quoting these; the report must use the numbers from the final run.

---

## 9. To-do list and common mistakes

**Still to do**
1. Decide whether to add the long-short factor-portfolio regression to satisfy requirement 5 literally (ask the instructor if unsure).
2. Decide whether to add a multifactor benchmark (e.g., Fama–French) as a sensitivity check.
3. Write the 4-page report (sections above) using final notebook numbers.
4. Final reproducibility test by a group member who did not write the code.
5. Prepare slides, the 5–6 minute talk and the peer-review question.

**Common mistakes the rubric punishes**
- Using `RETX` or raw prices (no dividends / no split adjustment).
- Silent data cleaning with no counts, or filling missing returns with zero.
- Winsorizing without stating cut-offs (or skipping it without explanation).
- Look-ahead bias: beta window includes the return being predicted.
- Default (homoskedastic) standard errors, or pooled standard errors that ignore dependence across stocks.
- Treating a higher R² as proof that the factor is priced.
- Calling a statistically insignificant coefficient a "finding", or ignoring economic size.
- Skipping the efficiency discussion, or not saying what the result means for the audience.
- A sensitivity table with no discussion of whether conclusions changed.
- Hard-coded file paths or results that cannot be reproduced.

---

## 10. Symbol glossary

| Symbol | Meaning |
|---|---|
| Rᵢ, Rₘ, R_f | Stock, market and risk-free returns (monthly, decimals) |
| Rᵉᵢ,t+1 | Stock *i*'s excess return in month t+1 (Rᵢ − R_f) |
| βᵢ,t | Ordinary beta from the 60 months ending in month t |
| β⁻ᵢ,t | Downside beta from the same window, using only months with market excess return < 0 |
| γ_β, γ_D | Average monthly cross-sectional slopes on ordinary and downside beta |
| Fama–MacBeth | Run one cross-sectional regression per month, then average the slopes over time |
| Newey–West | Standard errors robust to heteroskedasticity and serial correlation (6 lags here) |
| Winsorize | Replace values beyond the chosen percentiles (1st/99th) with the percentile values |
