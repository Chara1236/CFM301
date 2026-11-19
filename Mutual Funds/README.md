# CFM 301 Project 5: Comparing Mutual Funds — Are the Fees Justified?

We test whether four actively managed US large-cap growth funds earn enough gross-of-fee alpha to leave investors a non-negative net-of-fee alpha. The four funds are Fidelity Contrafund (FCNTX), T. Rowe Price Blue Chip Growth (TRBCX), American Funds Growth Fund of America A (AGTHX) and Fidelity Magellan (FMAGX). The sample runs from July 1993 to December 2025. The project covers:
- CAPM, Fama-French 3-factor and Carhart 4-factor alphas;
- gross vs. net alpha;
- an implementable benchmark of Vanguard index funds (500 Index VFINX, Small-Cap NAESX, Value VIVAX, Growth VIGRX), estimated by constrained regression;
- fees and turnover vs. performance;
- persistence, fund flows and Berk and Green (2004);
- a sensitivity analysis.

## How to run

1. Keep this folder structure:
   ```
   Mutual Funds/
   ├── mutualfunds.ipynb     <- all analysis
   ├── make_report.py        <- builds report.docx from output/
   ├── pull_data.py          <- downloads the data (optional; needs internet)
   ├── README.md
   ├── requirements.txt
   └── Data/                 <- the CSV files listed below
   ```
2. Open `mutualfunds.ipynb` in Jupyter or VS Code. It works from this folder or from the repository root.
3. Run **Restart & Run All**.
4. Run `python make_report.py` to rebuild `report.docx`. Its tables and key numbers are read from `output/`.

The notebook reads only the local files in `Data/`, using relative paths. It needs no WRDS login, no internet connection and no manual steps. Runtime: about a minute.

## Software

- **Python 3.11** (developed with 3.11.9)
- **Packages:** `pandas`, `numpy`, `scipy`, `statsmodels`, `matplotlib`, `ipykernel`, `python-docx` (for `make_report.py`)
- **Install:** `pip install -r requirements.txt`
- **Versions used:** pandas 2.2.3, numpy 2.4.6, scipy 1.17.1, statsmodels 0.15.0, matplotlib 3.11.2, ipykernel 7.4.0, python-docx 1.2.0. The first code cell prints these. `pull_data.py` also needs requests 2.34.2 and yfinance 1.8.0.

## Input data (`Data/`)

All data come from free public sources, because we have no WRDS/CRSP access. `pull_data.py` downloaded them once. `python pull_data.py panel` rebuilds `panel_monthly.csv` from the other files offline.

| File | Source | Series | Used for |
|---|---|---|---|
| `panel_monthly.csv` | Built by `pull_data.py` from the files below | One row per fund-month: total return, factors, risk-free rate, expense ratio, gross return, turnover, net flow, reported TNA | Every analysis in the notebook |
| `returns_monthly.csv` | Yahoo Finance (via yfinance) | Monthly total return = (NAV + dividends + capital gains) / previous NAV, compounded daily | Fund and index-fund returns |
| `distribution_corrections.csv` | SEC Form N-SAR item 73 (distributions per share) | 6 corrections to Yahoo distributions, with reasons | Return construction and cleaning |
| `ff_factors.csv` | Kenneth French Data Library | Mkt-RF, SMB, HML, UMD, RF (monthly) | CAPM, FF3, Carhart; excess returns |
| `expense_ratio_by_year.csv` | Built from the next two rows | One expense ratio per fund-year, with its source | Gross vs. net alpha; fee analysis |
| `expense_ratios_sec.csv` | SEC prospectus risk/return summary data sets | Expense ratio by share class (2011–2026 filings) | Fees for 2010–2025 |
| `nsar_semiannual.csv` | SEC Form N-SAR | Net assets, expenses, turnover, distributions per share (1993–2018) | Fees and TNA before 2019; distribution check |
| `turnover_by_year.csv`, `turnover_sec.csv` | SEC N-SAR item 71D; prospectus data | Portfolio turnover | Turnover vs. performance |
| `nsar_monthly_flows.csv`, `nport_monthly.csv` | SEC Forms N-SAR and N-PORT | Monthly sales and redemptions; quarterly net assets (2019+) | Monthly TNA and flows |
| `nport_class_returns.csv` | SEC Form N-PORT | Official monthly return by share class (2019+) | Check of our returns |
| `fee_distribution_all_funds_2025.csv` | SEC prospectus risk/return summary data sets | 2025 expense ratio of every US fund share class | Fee distribution |
| `sec_ticker_map.csv` | SEC `company_tickers_mf.json` | Ticker → SEC company, series and class IDs | Links the SEC data to the funds |

These values are hard-coded in the notebook, with citations:
- the ICI equity-fund fee averages from lecture: 1.09% simple, 0.40% asset-weighted, top 10% of growth funds ≥ 1.75%;
- AGTHX's maximum front-end load of 5.75%.

Not needed to run the notebook, so not part of the submission:
- `Data/raw/`: the download cache;
- `fees_download_log.csv` and `check_annual_returns.csv`: download log and check.

## Outputs

The notebook writes these files to `output/`:

| File | Contents |
|---|---|
| `table0_cleaning.csv` | Cleaning log: observations affected by each step |
| `table1_factor_regressions.csv` | Report Table 1: CAPM, FF3 and Carhart alpha, t, tracking error, IR and R² |
| `table2_fees_gross_net_index.csv` | Report Table 2: fees, gross/net alpha, index-benchmark alpha, verdict |
| `table3a_persistence_halves.csv`, `table3b_flows.csv` | Report Table 3 and the flow regressions |
| `table4_sensitivity.csv` | Report Table 4: verdict under alternative assumptions |
| `fig1_rolling_alpha_tna.png`, `fig2_fees_flows.png` | Report Figures 1 and 2 |
| other `table_*.csv`, `check_nport.csv`, `summary_numbers.csv` | Supporting tables and the numbers quoted in the report |

## Method summary

- **Returns:**
  - total returns with distributions reinvested, from NAV, dividends and capital gains;
  - one retail share class per fund;
  - excess returns over the T-bill rate;
  - gross return = net return + annual expense ratio / 12.
- **Cleaning:**
  - common sample from TRBCX's inception;
  - duplicates and missing values checked (none);
  - 6 distribution errors corrected against SEC filings;
  - returns verified against N-PORT (median difference 0.002 pp);
  - missing fees and turnover interpolated or carried, with counts reported;
  - outliers flagged, not winsorized, because crash months are real.
- **Regressions:**
  - OLS with Newey-West standard errors (6 lags);
  - alpha × 12, tracking error (residual s.d.) × √12, IR = alpha / TE.
- **Index-fund benchmark:** constrained least squares with weights ≥ 0 summing to 1, plus an intercept.
- **Flows:**
  - monthly TNA rolled forward from SEC-reported TNA using returns and reported net sales, and matched to every reported TNA;
  - flow(t) = TNA(t) − TNA(t−1)(1 + r(t)), regressed on the past 12-month return.
- **Sensitivity:** one assumption changed at a time:
  - FF3 model;
  - index-fund benchmark;
  - sample halves;
  - 1%/99% winsorization;
  - rolling 36-month windows;
  - AGTHX's sales load.
