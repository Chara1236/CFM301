# Project 5: Comparing Mutual Funds — Are the Fees Justified?

## Funds
| Role | Tickers |
|---|---|
| Active funds evaluated | FCNTX (Fidelity Contrafund), TRBCX (T. Rowe Price Blue Chip Growth), AGTHX (Growth Fund of America A), FMAGX (Fidelity Magellan) |
| Share-class sensitivity | GFACX (Growth Fund of America C) |
| Index-fund benchmark | VFINX (S&P 500), NAESX (small cap), VIVAX (value), VIGRX (growth) |

## Get the data (free sources, no WRDS)

1. Open `pull_data.py` and set `SEC_USER_AGENT = "Your Name your@uwaterloo.ca"` (the SEC requires it).
2. In the VS Code terminal, from the `CFM301` folder:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r "Mutual Funds\requirements.txt"
python "Mutual Funds\pull_data.py"
```

The first run takes roughly 20–40 minutes, mostly for the SEC filings. Each step saves its files and is skipped next time. To run one step only, use for example `python "Mutual Funds\pull_data.py" yahoo`.

| Step | Source | Output in `Data/` | Used for |
|---|---|---|---|
| tickers | SEC `company_tickers_mf.json` | `sec_ticker_map.csv` | Links tickers to SEC fund IDs |
| yahoo | Yahoo Finance (prices, dividends, capital gains) | `returns_monthly.csv`, `check_annual_returns.csv` | Total returns (req. 3, 5, 7, 9) |
| french | Ken French data library | `ff_factors.csv` | CAPM, FF3, Carhart factors, risk-free rate |
| nport | SEC Form N-PORT (2019+) | `nport_monthly.csv`, `nport_class_returns.csv` | Monthly flows; official returns to check Yahoo |
| nsar | SEC Form N-SAR (1994–2018) | `nsar_semiannual.csv`, `nsar_monthly_flows.csv` | Flows before 2019; expense-ratio estimate |
| fees | SEC prospectus risk/return data sets (2011+) | `expense_ratios_sec.csv`, `fee_distribution_all_funds_2025.csv` | Gross vs net alpha; fee distribution |
| panel | All of the above | `panel_monthly.csv` | One file for the analysis |

`Data/raw/` holds cached downloads and isn't needed by the analysis.

## Checks to do after the first run
- **Returns:** compare a few years in `check_annual_returns.csv` with each fund's published calendar-year returns (fund website or annual report).
- **N-SAR:** compare a few `net_assets_k` (thousands of $) and `expense_ratio_est` values with the annual reports. This is the most fragile parser.
- **Fees:** if a fund-year has no expense ratio, add it by hand to `Data/expense_ratios_manual.csv` (columns `ticker,year,exp_ratio`, as a decimal). Manual values take priority.

## Reproducibility
The analysis notebook should read only the CSVs in `Data/`. Submit those CSVs so the instructor doesn't need internet access.
