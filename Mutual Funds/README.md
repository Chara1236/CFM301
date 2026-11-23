# CFM 301 Project 5: Comparing Mutual Funds — Are the Fees Justified?

This project tests whether four actively managed US large-cap growth funds earn enough gross-of-fee alpha to leave investors a non-negative net-of-fee alpha. The funds are Fidelity Contrafund (FCNTX), T. Rowe Price Blue Chip Growth (TRBCX), American Funds Growth Fund of America A (AGTHX) and Fidelity Magellan (FMAGX), over July 1993 – December 2025. It covers:
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
   ├── mutualfunds.ipynb  <- all analysis (run this)
   ├── pull_data.py       <- how the data were downloaded (optional; needs internet)
   ├── README.md
   ├── requirements.txt
   └── Data/              <- the 4 input files listed below
   ```
2. Install the packages: `pip install -r requirements.txt`.
3. Open `mutualfunds.ipynb` in Jupyter or VS Code. It works from this folder or from the repository root.
4. Run **Restart & Run All**. There is only one file to run.

The notebook reads only the local files in `Data/`, using relative paths. It needs no WRDS login, no internet connection and no manual steps. It shows every table and figure inline and also saves them to `output/`, which it creates. Runtime: about a minute.

## Software

- **Python 3.11** (developed with 3.11.9)
- **Packages:** `pandas`, `numpy`, `scipy`, `statsmodels`, `matplotlib`, `ipykernel` (to run the notebook)
- **Install:** `pip install -r requirements.txt`
- **Versions used:** pandas 2.2.3, numpy 2.4.6, scipy 1.17.1, statsmodels 0.15.0, matplotlib 3.11.2, ipykernel 7.4.0. The first code cell prints these.

## Input data (`Data/`)

We have no WRDS/CRSP mutual-fund access, so all data come from free public sources. `pull_data.py` downloaded them once and merged them into `panel_monthly.csv` (see "Re-downloading the data" below). Each file holds only the funds, variables and months the notebook uses.

| File | Source | Series | Used for |
|---|---|---|---|
| `panel_monthly.csv` | See the next table | One row per fund-month, 8 funds, Feb 1993 – Dec 2025 (3,155 rows) | Every analysis in the notebook |
| `distribution_corrections.csv` | SEC EDGAR, Form N-SAR item 73 (distributions per share) | 6 Yahoo distribution errors and the evidence for each correction. They are already applied to `ret` in the panel. | Cleaning log (§5) |
| `nport_class_returns.csv` | SEC EDGAR, Form N-PORT | Each fund's official monthly return, 2019–2025, in % | Check of our return construction (§5) |
| `fee_distribution_all_funds_2025.csv` | SEC prospectus risk/return summary data sets (2025 filings) | 2025 expense ratio of every US mutual fund share class (`class`, `value`; net of waivers when reported) | Fee distribution (§9) |

Columns of `panel_monthly.csv`:

| Column | Source | Description |
|---|---|---|
| `date`, `ticker` | — | Month-end date; fund ticker |
| `ret` | Yahoo Finance (daily NAV, dividends, capital gains), corrected with `distribution_corrections.csv` | Monthly total return with distributions reinvested: (NAV + dividends + capital gains) / previous NAV − 1, compounded daily |
| `mktrf`, `smb`, `hml`, `umd`, `rf` | Kenneth French Data Library | Fama-French 3 factors, momentum and the 1-month T-bill rate (monthly, decimals) |
| `exp_ratio`, `exp_source` | SEC prospectus risk/return data sets (fiscal 2010–2025); SEC Form N-SAR expenses ÷ average net assets (1993–2009) | Annual expense ratio of that fiscal year (decimal), and its source. `filled` or `carried` means interpolated between years or carried from the nearest year. |
| `turnover`, `turnover_source` | SEC Form N-SAR item 71D (1993–2018); prospectus data (2010+) | Portfolio turnover for that fiscal year (decimal) and its source |
| `net_flow` | SEC Forms N-SAR (to 2018) and N-PORT (2019+) | Monthly sales minus redemptions, in $ (fund level, active funds only) |
| `tna` | SEC Forms N-SAR (semi-annual) and N-PORT (quarterly) | Total net assets in $, at the dates the fund reported them (fund level, active funds only) |

## Re-downloading the data (optional, needs internet)

You don't need this to reproduce the results: the notebook runs on the files in `Data/`. `pull_data.py` shows how those files were built from the raw sources, and it can rebuild them. It downloads from:
- Yahoo Finance (via yfinance);
- the Kenneth French Data Library;
- SEC EDGAR (Forms N-SAR and N-PORT, and the prospectus risk/return data sets).

The SEC requires a user agent with a name and email, so set one first. A full run takes about 20–40 minutes, mostly for the SEC filings.

```powershell
pip install requests==2.34.2 yfinance==1.8.0
$env:SEC_USER_AGENT = "Your Name your@email"
python pull_data.py
```

You can run single steps, for example `python pull_data.py yahoo panel`. Each step skips files that already exist.

`distribution_corrections.csv` is not downloaded. It records six Yahoo distribution errors we found by checking against SEC N-SAR item 73, and `pull_data.py` applies them when it builds returns.

The script also writes a download cache (`Data/raw/`) and intermediate CSVs. These are listed in `.gitignore`, and the notebook doesn't need them.

## Outputs

The notebook shows all results inline. It also writes them to `output/`, which is not part of the submission because every run recreates it:

| File | Contents |
|---|---|
| `table0_cleaning.csv` | Cleaning log: observations affected by each step |
| `table1_factor_regressions.csv` | CAPM, FF3 and Carhart alpha, t-statistic, tracking error, information ratio and R² |
| `table2_fees_gross_net_index.csv` | Fees, gross and net alpha, index-benchmark alpha, verdict |
| `table3a_persistence_halves.csv`, `table3b_flows.csv` | Persistence by half-sample; flow-performance regressions |
| `table4_sensitivity.csv` | Verdict under each alternative assumption |
| `fig1_rolling_alpha_tna.png`, `fig2_fees_flows.png` | Rolling alpha with fund size; fee distribution and flows |
| other `table_*.csv`, `check_nport.csv`, `summary_numbers.csv` | Supporting tables and the numbers quoted in the report |

## Method summary

- **Returns:**
  - total returns with distributions reinvested;
  - one retail share class per fund;
  - excess returns over the T-bill rate;
  - gross return = net return + annual expense ratio / 12.
- **Cleaning:**
  - common sample from TRBCX's inception (July 1993);
  - duplicates and missing values checked (none found);
  - 6 distribution errors corrected against SEC filings;
  - returns verified against N-PORT (median difference 0.002 percentage points);
  - missing fees and turnover interpolated or carried, with counts reported;
  - outliers flagged but not winsorized, because crash months are real market moves.
- **Regressions:**
  - OLS with Newey-West standard errors (6 lags);
  - alpha × 12; tracking error = residual standard deviation × √12; information ratio = alpha / tracking error.
- **Index-fund benchmark:** constrained least squares with weights ≥ 0 that sum to 1, plus an intercept.
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
