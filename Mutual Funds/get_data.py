"""
CFM 301 Project 5 - Canadian mutual funds: are the fees justified?
Data pull + data check.

Run from VS Code (any working directory):
    python "Mutual Funds/get_data.py"

What it does
  1. Downloads the free data automatically into Mutual Funds/Data/:
       - Canadian risk-free rate     (Bank of Canada Valet API, 1-month T-bill)
       - Canadian SMB, HML, UMD, MKT  (AQR "Betting Against Beta" country factors, column CAN)
       - Index ETF prices             (Yahoo Finance: XIC, XCS, XCV, XCG)
       - Fund NAVs as a cross-check   (Yahoo Finance, Morningstar-ID tickers)
  2. Checks the Morningstar Direct exports you put in Data/ by hand
     (returns, fund size, MER, category MERs) and converts them to tidy CSVs.
  3. Prints a report: what exists, what is missing, and format problems
     (missing months, duplicates, extreme returns, wrong units).

Downloads are skipped if the file already exists, so the instructor can
re-run this offline. Delete a file to force a fresh download.

Requirements: pip install pandas numpy requests openpyxl yfinance
"""
from pathlib import Path
import io
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "Data"
DATA.mkdir(exist_ok=True)

START, END = "1998-01-01", "2025-12-31"

# ---------------------------------------------------------------------------
# The four funds (Canadian Equity category, all launched by 1998)
# yahoo: Morningstar-ID ticker on Yahoo Finance. None = look it up by name.
# ---------------------------------------------------------------------------
FUNDS = {
    "MAWER_CDN_EQ_A": {"name": "Mawer Canadian Equity Fund Series A",
                       "yahoo": "0P00007173.TO"},
    "BG_CDN_EQ_D":    {"name": "Beutel Goodman Canadian Equity Fund Class D",
                       "yahoo": "0P000072UC.TO"},
    "RBC_CDN_EQ_A":   {"name": "RBC Canadian Equity Fund Series A",
                       "yahoo": None},
    "FID_CDN_DISC_B": {"name": "Fidelity Canadian Disciplined Equity Fund Series B",
                       "yahoo": None},
}

# Implementable benchmark: cheap Canadian index ETFs (CAD)
ETFS = {
    "XIC.TO": "iShares Core S&P/TSX Capped Composite (market)",
    "XCS.TO": "iShares S&P/TSX SmallCap (size)",
    "XCV.TO": "iShares Canadian Value (value)",
    "XCG.TO": "iShares Canadian Growth (growth)",
}

AQR_URL = ("https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/"
           "Betting-Against-Beta-Equity-Factors-Monthly.xlsx")
BOC_URL = "https://www.bankofcanada.ca/valet/observations/{series}/json?start_date={start}"
UA = {"User-Agent": "Mozilla/5.0 (CFM301 course project)"}

report = []  # (file, status, note)


def log(file, status, note=""):
    report.append((file, status, note))
    print(f"[{status:7}] {file}  {note}")


# ===========================================================================
# 1. Automatic downloads
# ===========================================================================
def get_risk_free():
    out = DATA / "ca_tbill_1m.csv"
    if out.exists():
        return log(out.name, "exists")
    import requests
    for series in ("TB.CDN.30D.MID", "TB.CDN.90D.MID"):
        r = requests.get(BOC_URL.format(series=series, start=START), headers=UA, timeout=60)
        r.raise_for_status()
        obs = r.json()["observations"]
        df = pd.DataFrame({"date": [o["d"] for o in obs],
                           "yield_pct": [o.get(series, {}).get("v") for o in obs]})
        df["date"] = pd.to_datetime(df["date"])
        df["yield_pct"] = pd.to_numeric(df["yield_pct"], errors="coerce")
        df = df.dropna()
        if df["date"].min() <= pd.Timestamp(START) + pd.Timedelta(days=40):
            break
        print(f"  {series} only starts {df['date'].min().date()}, trying 3-month bill")
    # last observation of each month -> monthly rate for the NEXT month's return
    m = df.set_index("date")["yield_pct"].resample("ME").last().to_frame()
    m["rf_monthly"] = m["yield_pct"] / 100 / 12          # annual % -> monthly decimal
    m["series"] = series
    m.reset_index().to_csv(out, index=False)
    log(out.name, "saved", f"{series}, {m.index.min().date()} to {m.index.max().date()}")


def get_aqr_factors():
    out = DATA / "aqr_factors_canada.csv"
    if out.exists():
        return log(out.name, "exists")
    import requests
    raw = DATA / "aqr_bab_factors_monthly.xlsx"
    if not raw.exists():
        r = requests.get(AQR_URL, headers=UA, timeout=120)
        r.raise_for_status()
        raw.write_bytes(r.content)
    frames = {}
    for sheet, col in [("MKT", "mkt_usd"), ("SMB", "smb"), ("HML FF", "hml"), ("UMD", "umd")]:
        x = pd.read_excel(raw, sheet_name=sheet, header=None)
        hdr = x.index[x.iloc[:, 0].astype(str).str.strip().str.upper() == "DATE"][0]
        x.columns = x.iloc[hdr].astype(str).str.strip()
        x = x.iloc[hdr + 1:][["DATE", "CAN"]].dropna()
        x["DATE"] = pd.to_datetime(x["DATE"]) + pd.offsets.MonthEnd(0)
        frames[col] = x.set_index("DATE")["CAN"].astype(float)
    f = pd.DataFrame(frames).rename_axis("date")
    f = f.loc[START:END]
    f.reset_index().to_csv(out, index=False)
    log(out.name, "saved", f"{f.index.min().date()} to {f.index.max().date()} "
                           "(decimals; MKT is USD excess return, use for checks only)")


def yahoo_monthly(tickers):
    import yfinance as yf
    px = yf.download(list(tickers), start=START, end="2026-01-01",
                     auto_adjust=False, progress=False)["Adj Close"]
    if isinstance(px, pd.Series):
        px = px.to_frame(tickers[0])
    px = px.resample("ME").last()
    ret = px.pct_change(fill_method=None)
    long = (ret.stack().rename("ret").reset_index()
              .rename(columns={"Date": "date", "Ticker": "ticker", "level_1": "ticker"}))
    return long


def get_etfs():
    out = DATA / "etf_returns_monthly.csv"
    if out.exists():
        return log(out.name, "exists")
    df = yahoo_monthly(list(ETFS))
    df.to_csv(out, index=False)
    starts = df.dropna().groupby("ticker")["date"].min().dt.date.to_dict()
    log(out.name, "saved", f"first months: {starts}")


def get_fund_navs_yahoo():
    """Cross-check only. Yahoo 'Adj Close' for Canadian funds is not guaranteed
    to reinvest distributions; Morningstar total return is the main source."""
    out = DATA / "yahoo_fund_returns_monthly.csv"
    if out.exists():
        return log(out.name, "exists")
    import yfinance as yf
    tick = {}
    for key, f in FUNDS.items():
        t = f["yahoo"]
        if t is None:
            try:
                hits = [q for q in yf.Search(f["name"], max_results=8).quotes
                        if str(q.get("symbol", "")).endswith(".TO")]
                t = hits[0]["symbol"] if hits else None
                print(f"  {key}: Yahoo search -> {t} "
                      f"({hits[0].get('longname') if hits else 'no match'}) - CHECK THIS")
            except Exception as e:
                print(f"  {key}: Yahoo search failed ({e})")
        if t:
            tick[t] = key
    if not tick:
        return log(out.name, "MISSING", "no Yahoo tickers found")
    df = yahoo_monthly(list(tick))
    df["fund"] = df["ticker"].map(tick)
    df.to_csv(out, index=False)
    log(out.name, "saved", f"tickers used: {tick}")


# ===========================================================================
# 2. Morningstar Direct exports (manual, see README) -> tidy CSVs
# ===========================================================================
MD_FILES = {
    "md_monthly_returns.csv": "Monthly total return, % , CAD (funds + S&P/TSX Capped Composite TR)",
    "md_fund_size.csv":       "Fund size (all series), monthly, CAD",
    "md_expense_ratio.csv":   "Annual report net expense ratio (MER), %, yearly",
    "md_turnover.csv":        "Annual report turnover ratio, %, yearly (optional)",
    "md_category_mer.csv":    "All Canadian Equity funds: name, MER, fund size (one date)",
}


def wide_to_long(path, value_name):
    """Morningstar exports one row per fund and one column per date.
    Turn that into date, fund, value. Already-long files pass through."""
    df = pd.read_csv(path, thousands=",")
    df.columns = [str(c).strip() for c in df.columns]
    if {"date", "fund"}.issubset(df.columns):
        df["date"] = pd.to_datetime(df["date"]) + pd.offsets.MonthEnd(0)
        return df
    name_col = df.columns[0]
    date_cols = {}
    for c in df.columns[1:]:
        # headers look like "Monthly Return 1998-10" or "1998-10" or "Oct 1998"
        token = c.split()[-1] if c.split() else c
        for cand in (c, token, " ".join(c.split()[-2:])):
            d = pd.to_datetime(cand, errors="coerce", format="mixed")
            if pd.notna(d):
                date_cols[c] = d + pd.offsets.MonthEnd(0)
                break
    if not date_cols:
        raise ValueError(f"{path.name}: no date-like columns found; headers are {list(df.columns)[:6]}")
    long = df[[name_col, *date_cols]].melt(id_vars=name_col, var_name="col", value_name=value_name)
    long["date"] = long["col"].map(date_cols)
    long = long.rename(columns={name_col: "fund"}).drop(columns="col")
    long[value_name] = pd.to_numeric(long[value_name], errors="coerce")
    return long[["date", "fund", value_name]].sort_values(["fund", "date"])


def check_md():
    for fname, desc in MD_FILES.items():
        p = DATA / fname
        if not p.exists():
            log(fname, "MISSING", f"export from Morningstar Direct: {desc}")
            continue
        try:
            if fname == "md_category_mer.csv":
                df = pd.read_csv(p, thousands=",")
                log(fname, "ok", f"{len(df)} funds, columns: {list(df.columns)[:5]}")
                continue
            value = {"md_monthly_returns.csv": "ret_pct", "md_fund_size.csv": "tna_cad",
                     "md_expense_ratio.csv": "mer_pct", "md_turnover.csv": "turnover_pct"}[fname]
            long = wide_to_long(p, value)
            tidy = DATA / fname.replace("md_", "tidy_")
            long.to_csv(tidy, index=False)
            log(fname, "ok", f"-> {tidy.name}: {long['fund'].nunique()} series, "
                             f"{long['date'].min().date()} to {long['date'].max().date()}")
        except Exception as e:
            log(fname, "BAD", str(e))


# ===========================================================================
# 3. Format checks on everything in Data/
# ===========================================================================
def check_panel(path, id_col, val_col, kind):
    df = pd.read_csv(path, parse_dates=["date"])
    issues = []
    dups = df.duplicated([id_col, "date"]).sum()
    if dups:
        issues.append(f"{dups} duplicate rows")
    miss = df[val_col].isna().sum()
    if miss:
        issues.append(f"{miss} missing values")
    if kind == "return":
        v = df[val_col].dropna()
        if val_col.endswith("_pct"):
            v = v / 100                      # Morningstar returns are in percent
            if v.abs().median() < 0.002:
                issues.append("values look like DECIMALS but column is percent")
        elif v.abs().median() > 0.2:         # should be decimal
            issues.append("values look like PERCENT; divide by 100")
            v = v / 100
        ext = (v.abs() > 0.30).sum()
        if ext:
            issues.append(f"{ext} monthly returns beyond +/-30% (check outliers)")
    for g, s in df.dropna(subset=[val_col]).groupby(id_col)["date"]:
        months = pd.period_range(s.min(), s.max(), freq="M")
        gaps = len(months) - s.dt.to_period("M").nunique()
        if gaps > 0 and kind != "annual":
            issues.append(f"{g}: {gaps} missing months inside its range")
    log(path.name, "BAD" if issues else "ok", "; ".join(issues) or "no format problems")


def check_all():
    print("\n--- format checks ---")
    checks = [("etf_returns_monthly.csv", "ticker", "ret", "return"),
              ("yahoo_fund_returns_monthly.csv", "ticker", "ret", "return"),
              ("tidy_monthly_returns.csv", "fund", "ret_pct", "return"),
              ("tidy_fund_size.csv", "fund", "tna_cad", "level"),
              ("tidy_expense_ratio.csv", "fund", "mer_pct", "annual")]
    for f, idc, val, kind in checks:
        if (DATA / f).exists():
            check_panel(DATA / f, idc, val, kind)
    rf = DATA / "ca_tbill_1m.csv"
    if rf.exists():
        r = pd.read_csv(rf)
        bad = (r["rf_monthly"] > 0.02).sum() + (r["rf_monthly"] < 0).sum()
        log(rf.name, "BAD" if bad else "ok", f"{bad} implausible monthly rates" if bad else "rates in 0-2%/month")


# ===========================================================================
if __name__ == "__main__":
    for step in (get_risk_free, get_aqr_factors, get_etfs, get_fund_navs_yahoo):
        try:
            step()
        except Exception as e:
            log(step.__name__, "FAILED", f"{type(e).__name__}: {e}")
    print("\n--- Morningstar Direct exports ---")
    check_md()
    check_all()

    pd.DataFrame(report, columns=["file", "status", "note"]).to_csv(DATA / "data_check_report.csv", index=False)
    missing = [f for f, s, _ in report if s in ("MISSING", "FAILED", "BAD")]
    print(f"\n{len(missing)} item(s) need attention." if missing else "\nAll data present and clean.")
    sys.exit(0)
