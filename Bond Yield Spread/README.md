# CFM 301 Project 4: Credit Spreads and Treasury Liquidity

Reproduces and extends Ch. 9 (Bonds), slide 59: the Baa-Treasury credit spread vs. a Treasury liquidity proxy (on/off-the-run spread), Corr = 0.96. The project also covers:
- the extended 1986–2026 sample (excluding the 1987–93 `GS20` gap);
- a comparison with the slide's own chart data;
- liquidity vs. default-risk (VIX) regressions;
- the credit spread puzzle decomposition;
- a sensitivity analysis.

## How to run

1. Keep this folder structure:
   ```
   Bond Yield Spread/
   ├── spread.ipynb
   ├── README.md
   └── Data/          <- only the 6 input files listed below
   ```
2. Open `spread.ipynb` in Jupyter or VS Code. It works from this folder or from the repository root.
3. Run **Restart & Run All**. Run it top to bottom; there is only one file to run.

The notebook reads only the local files in `Data/`, using relative paths. It needs no WRDS login, no internet connection and no manual steps. It writes no output files: all tables and figures are shown inside the notebook. Runtime: a few seconds.

## Software

- **Python 3.11 or newer**
- **Packages:** `pandas`, `numpy`, `matplotlib`, `xlrd`
  - `xlrd` is required to read the two Treasury `.xls` files. Newer pandas versions can use `python-calamine` instead.
  - Newey-West regressions are coded in NumPy, so `statsmodels` is not needed.
- **Install:** `pip install pandas numpy matplotlib xlrd`
- **Versions used:** Python 3.11.4, pandas 2.0.3, numpy 1.24.3, matplotlib 3.7.1 (the group's run; the first code cell prints these). Also tested with Python 3.13, pandas 3.0.5, numpy 2.5.3 and matplotlib 3.11.2. `TODO: add the xlrd version (pip show xlrd).`

## Input data (`Data/`)

| File | Source | Series | Used for |
|---|---|---|---|
| `BAA (1).csv` | FRED `BAA` (Moody's) | Seasoned Baa corporate yield (20–30y bonds), monthly avg., % | Corporate leg of every credit spread |
| `GS20.csv` | FRED `GS20` | 20y Treasury, monthly avg. (missing Jan 1987 – Sep 1993) | **Baseline Treasury leg** (maturity-matched); gap months excluded from all calculations |
| `Treasury yields month end off the run.xls` | U.S. Treasury, TNC yield curve (off-the-run par yields), month-end, % | 2, 3, 5, 7, 10, 20, 30y | **10y** = liquidity proxy; 20y, 30y, 5y, 2y = sensitivity |
| `Treasury yields month end on the run.xls` | U.S. Treasury, TNC on-the-run par yields, month-end, % | 2, 5, 10y | **10y** = liquidity proxy; 5y, 2y = sensitivity |
| `VIXCLS.csv` | FRED `VIXCLS` (CBOE) | VIX, daily | Default-risk proxy (Merton model); regressions use Oct 1993 – Sep 2026 |
| `TB3MS (1).csv` | FRED `TB3MS` | 3-month T-bill, monthly avg. | Sensitivity / diagnostic |

The two Treasury `.xls` files are published by the U.S. Department of the Treasury, Office of Economic Policy: "Treasury Coupon Issues" (Treasury Nominal Coupon-Issue yield curve, end-of-month on-the-run and off-the-run par yields), https://home.treasury.gov/data/treasury-coupon-issues-and-corporate-bond-yield-curves/treasury-coupon-issues. `TODO: confirm how the group obtained them (download date, or provided by the instructor).`

These values are hard-coded in the notebook, with citations:
- Slide 59 chart data, read from the Ch. 9 PowerPoint.
- The Baa expected loss rate of 0.124% (slide 55) and the 41% recovery rate (slide 56).
- The 1.5% × 50% upper-bound loss (slide 57).
- The NBER recession dates (nber.org).

## Method summary

- **Credit spread (baseline):** Moody's Baa minus FRED's **20-year Treasury yield (`GS20`)**. This matches maturities, because Baa bonds have 20–30 years to maturity, and both series are H.15 monthly averages.
- **Missing data:** `GS20` is missing from Jan 1987 to Sep 1993 (81 months). These months are **not filled**: every series is blanked in them, so they are excluded from all correlations, regressions, averages and figures. The usable sample is Feb–Dec 1986 plus Oct 1993 – Sep 2026 (407 months); VIX regressions use Oct 1993 – Sep 2026 (396 months).
- **Liquidity proxy:** (off-the-run 10y − on-the-run 10y) × 100, in bp.
- **Frequency:** monthly averages for every series. Month-end Treasury values are averaged over adjacent month-ends, and daily VIX is averaged within each month.
- **Cleaning:**
  - missing values dropped, not filled;
  - duplicates checked;
  - plausibility checks;
  - outliers flagged, not winsorized, because the crisis spikes are the signal;
  - a cleaning log with observation counts.
- **Regressions:** OLS with Newey-West standard errors (12 lags for levels, 3 for changes).
- **Sensitivity:** one assumption changed at a time:
  - sample period;
  - levels vs. changes;
  - Treasury benchmark and maturity;
  - liquidity proxy;
  - frequency;
  - winsorization.
