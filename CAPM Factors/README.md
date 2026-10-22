# Project 2: Idiosyncratic-volatility LMH factor

This folder contains the analysis of whether an equal-weighted portfolio of low-idiosyncratic-volatility S&P 500 stocks (Q1) outperforms high-volatility stocks (Q5), before and after controlling for market exposure. The current project factor is `LMH = Q1 - Q5`; it is not the downside-beta project described in the older requirements guide.

## Run the analysis

Requirements: Python 3.11 or newer, VS Code, and the Python and Jupyter extensions.

From the repository root, create and activate an environment, then install the notebook dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install pandas numpy matplotlib jupyter ipykernel
```

Open `volatility.ipynb` in VS Code, select `.venv`, and use **Restart Kernel and Run All**. The notebook locates its CSVs relative to the working directory, whether started from this folder or the repository root. Its main analysis uses the supplied files:

- `market_returns_2000_2025.csv`
- `risk_free_rate_2000_2025.csv`
- `sp500_stocks_2000_2025.csv`

The checked environment versions were pandas 3.0.6, NumPy 2.4.6, and Matplotlib 3.11.2. The CSVs are the provided project inputs; their upstream source and delisting-return coverage are not documented in the files.

## What the notebook includes

- Monthly data validation, duplicate and missing-return counts, and outlier diagnostics.
- Rolling 60-month market beta and idiosyncratic volatility; portfolios use characteristics lagged by one month.
- Equal-weighted volatility quintiles and the LMH portfolio, with CAPM alpha and Newey-West/HAC inference.
- Individual-stock MKT and LMH regressions, MKT-only/LMH-only/joint Fama-MacBeth tests, model-fit comparisons, and factor-return collinearity diagnostics.
- Raw-return, winsorized, and crisis-month sensitivity results, plus market-state comparisons.

## Remaining assignment steps

- Confirm with the instructor that idiosyncratic volatility satisfies the requirement for a factor beyond the standard factors. The supplied files do not include SMB, HML, or UMD returns, so a Fama-French/Carhart benchmark is not yet estimated.
- Review and format `project2_report.md` to the course's four-page limit; verify all figures and tables against a clean notebook run.
- Turn `presentation_outline.md` into the group's 5–6 minute slide deck and adapt its peer-review question to the paired group's project.
- Have a group member who did not write the code run the project from a fresh folder and confirm the final report numbers.
