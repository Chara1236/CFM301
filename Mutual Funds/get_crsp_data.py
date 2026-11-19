"""
CFM 301 Project 5 - pull ALL mutual fund data from WRDS/CRSP in one run.

Run from the CFM301 folder in the VS Code terminal:
    python "Mutual Funds/get_crsp_data.py"

It asks for your WRDS username/password (and Duo) once, then saves to
Mutual Funds/Data/:
    fund_names.csv            ticker -> crsp_fundno / crsp_portno lookup (check it!)
    monthly_returns.csv       mret (total return, after fees), mnav, mtna
    fund_summary.csv          exp_ratio, turn_ratio, fees, TNA, objective code
    ff_factors.csv            mktrf, smb, hml, umd, rf (monthly, decimals)
    fee_distribution_2025.csv expense ratios of all US domestic equity funds
    portfolio_map.csv         all share classes of each fund (crsp_portno)

After this, the analysis code needs no WRDS login (reproducibility rule).
Requirements: pip install wrds pandas
"""
from pathlib import Path
import pandas as pd
import wrds

DATA = Path(__file__).resolve().parent / "Data"
DATA.mkdir(exist_ok=True)

WRDS_USERNAME = None          # put your WRDS username in quotes, or leave None to be asked
START, END = "1993-01-01", "2025-12-31"

FUNDS = ["FCNTX", "TRBCX", "AGTHX", "FMAGX"]      # funds being evaluated
EXTRA = ["GFACX"]                                 # Growth Fund of America C shares (sensitivity)
INDEX = ["VFINX", "NAESX", "VIVAX", "VIGRX"]      # implementable index-fund benchmark
TICKERS = FUNDS + EXTRA + INDEX

db = wrds.Connection(wrds_username=WRDS_USERNAME) if WRDS_USERNAME else wrds.Connection()

# CRSP mutual fund tables live in "crsp" at most schools, "crsp_q_mutualfunds" at others
LIB = "crsp"
try:
    db.raw_sql("select crsp_fundno from crsp.fund_names limit 1")
except Exception:
    LIB = "crsp_q_mutualfunds"
print(f"Using CRSP mutual fund library: {LIB}")


def save(df, name):
    df.to_csv(DATA / name, index=False)
    print(f"saved {name}: {len(df):,} rows")


def in_list(values):
    return ",".join(f"'{v}'" if isinstance(v, str) else str(int(v)) for v in values)


# 1. Ticker -> fund number -----------------------------------------------------
names = db.raw_sql(f"""
    select crsp_fundno, crsp_portno, ticker, fund_name, chgdt, chgenddt,
           first_offer_dt, index_fund_flag, et_flag
    from {LIB}.fund_names
    where ticker in ({in_list(TICKERS)})
    order by ticker, chgdt
""", date_cols=["chgdt", "chgenddt", "first_offer_dt"])
save(names, "fund_names.csv")

# Keep the fund number each ticker had most recently, and show it for checking
latest = names.sort_values("chgdt").groupby("ticker").tail(1)
print("\nCHECK these matches (ticker -> fund):")
print(latest[["ticker", "crsp_fundno", "crsp_portno", "fund_name"]].to_string(index=False))
missing = sorted(set(TICKERS) - set(latest["ticker"]))
if missing:
    print(f"\nWARNING: no CRSP match for {missing}")

fundnos = latest["crsp_fundno"].dropna().astype(int).tolist()
portnos = latest["crsp_portno"].dropna().astype(int).tolist()

# 2. All share classes of the same portfolios (optional aggregation) -----------
pmap = db.raw_sql(f"""
    select crsp_fundno, crsp_portno, begdt, enddt
    from {LIB}.portnomap
    where crsp_portno in ({in_list(portnos)})
""", date_cols=["begdt", "enddt"]) if portnos else pd.DataFrame()
save(pmap, "portfolio_map.csv")

# 3. Monthly returns and TNA --------------------------------------------------
rets = db.raw_sql(f"""
    select crsp_fundno, caldt, mret, mnav, mtna
    from {LIB}.monthly_returns
    where crsp_fundno in ({in_list(fundnos)})
      and caldt between '{START}' and '{END}'
    order by crsp_fundno, caldt
""", date_cols=["caldt"])
save(rets, "monthly_returns.csv")

# 4. Fees, turnover, objective code -------------------------------------------
summ = db.raw_sql(f"""
    select crsp_fundno, caldt, exp_ratio, turn_ratio, mgmt_fee, actual_12b1,
           tna_latest, nav_latest, crsp_obj_cd, fiscal_yearend
    from {LIB}.fund_summary2
    where crsp_fundno in ({in_list(fundnos)})
      and caldt between '{START}' and '{END}'
    order by crsp_fundno, caldt
""", date_cols=["caldt"])
save(summ, "fund_summary.csv")

# 5. Fama-French 3 factors + momentum + risk-free (same table as your Project 2)
ff = db.raw_sql(f"""
    select dateff as date, mktrf, smb, hml, umd, rf
    from ff_all.factors_monthly
    where dateff between '{START}' and '{END}'
    order by dateff
""", date_cols=["date"])
save(ff, "ff_factors.csv")

# 6. Fee distribution: all US domestic equity funds, 2025 ----------------------
fees = db.raw_sql(f"""
    select s.crsp_fundno, s.caldt, s.exp_ratio, s.tna_latest, s.crsp_obj_cd,
           n.index_fund_flag, n.et_flag
    from {LIB}.fund_summary2 s
    left join {LIB}.fund_names n
      on s.crsp_fundno = n.crsp_fundno
     and s.caldt between n.chgdt and coalesce(n.chgenddt, '9999-12-31')
    where s.caldt between '2025-01-01' and '2025-12-31'
      and s.crsp_obj_cd like 'ED%'
""", date_cols=["caldt"])
save(fees, "fee_distribution_2025.csv")

db.close()

# Quick sanity checks ----------------------------------------------------------
print("\n--- checks ---")
print("months of returns per fund:")
print(rets.dropna(subset=["mret"]).groupby("crsp_fundno")["caldt"].agg(["min", "max", "count"]))
print(f"missing mret: {rets['mret'].isna().sum()}, missing mtna: {rets['mtna'].isna().sum()}")
print(f"duplicate fund-months: {rets.duplicated(['crsp_fundno', 'caldt']).sum()}")
print(f"factor months: {len(ff)} ({ff['date'].min().date()} to {ff['date'].max().date()})")
print("\nDone. All files are in", DATA)
