# CFM 301 Project 3: Reproducing the Equity Return Predictability Table

Replicates and extends the predictability table from Ch. 8 (Equities): correlations and t-statistics between 14 predictors and future excess market returns at 1-quarter, 1-year, 2-year and 5-year horizons. It also includes a comparison with the slides, a dividend-yield bucket analysis, a GARCH(1,1) volatility analysis and a sensitivity analysis.

## How to run

1. Keep the folder structure as submitted:
   ```
   predictors.ipynb
   README.md
   Predictor Data/      <- all input CSV files
   ```
2. Open `predictors.ipynb` in Jupyter (or VS Code) from this folder.
3. Run **Kernel → Restart & Run All**. The notebook runs top to bottom and reads only the local files in `Predictor Data/` (relative paths). It needs no WRDS login, internet connection or manual steps.

Runtime: under a minute on a laptop.

## Software

- **Python 3.11** (developed with 3.11.4)
- Packages: `pandas`, `numpy`, `statsmodels`, `scipy`, `matplotlib`, `jinja2` (for styled tables)

The first code cell prints the exact Python and package versions used. **Exact versions:** `TODO: paste the first output line of the notebook here`

Install with: `pip install pandas numpy statsmodels scipy matplotlib jinja2`

## Input data (`Predictor Data/`)

| File | Source | Series | Used for |
|---|---|---|---|
| `Market_Dividends_Returns.csv` | CRSP via WRDS, Monthly Stock File Indexes | `vwretd` (value-weighted return incl. dividends), `vwretx` | Market returns (dependent variable), past 1-year return, past volatility, GARCH |
| `market_data_full_history_2025.csv` | `TODO: state source` (S&P 500 price, dividends and earnings from 1871; appears to be Robert Shiller's online data) | Dividend yield, earnings yield, 1-month T-bill | Dividend yield and earnings yield predictors |
| `TB3MS.csv` | FRED | 3-month T-bill rate | Risk-free rate for excess returns; term spread; risk-free-rate predictor |
| `GS10.csv` | FRED | 10-year Treasury yield | Term spread |
| `AAA.csv`, `BAA.csv` | FRED (Moody's) | Corporate bond yields | Credit spread |
| `UNRATE.csv` | FRED | Unemployment rate | Unemployment predictor |
| `GDPC1.csv` | FRED | Real GDP (quarterly) | GDP growth |
| `INDPRO.csv` | FRED | Industrial production index | Industrial production growth |
| `CPIAUCSL.csv` | FRED | CPI, all urban consumers | Inflation |
| `DCOILWTICO (1).csv` | FRED | WTI crude oil spot price (daily) | Oil price change |
| `VIXCLS.csv` | FRED | CBOE VIX (daily) | VIX predictor; volatility forecasting |
| `cay_current.csv` | Martin Lettau's website | Consumption–wealth ratio *cay* (quarterly, 1952–2019) | *cay* predictor |

All series are converted to month-end dates. Daily series use the last observation of each month.

## Outputs

Running the notebook writes these files to the project folder:

| File | Contents |
|---|---|
| `slides_vs_project.csv` | Side-by-side table: slide values vs. our estimates |
| `sensitivity_summary.csv` | Number of significant horizons per predictor under each alternative assumption |
| `sensitivity_detail.csv` | Full correlation (t-stat) table under each alternative assumption |

## Method summary

- **Returns:** CRSP `vwretd` minus the monthly T-bill rate, compounded over months *t+1 … t+h*.
- **t-statistics:** OLS of the future return on each predictor, with Newey-West (HAC) standard errors and *h − 1* lags to handle overlapping observations.
- **Cleaning:** duplicates removed; predictors winsorized at the 1st/99th percentile within each estimation sample.
- **Sensitivity:** sub-periods, Newey-West lag choice, non-overlapping returns, nominal returns and winsorization cut-offs.
