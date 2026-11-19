"""
CFM 301 Project 5 - pull ALL data from free public sources (no WRDS needed).

Run from the CFM301 folder in the VS Code terminal:
    python "Mutual Funds/pull_data.py"            # everything
    python "Mutual Funds/pull_data.py" yahoo sec  # only some steps

Steps (each saves CSVs to Mutual Funds/Data/ and is skipped if its output exists;
delete a file to re-download it):

  tickers  SEC ticker -> CIK / series ID / class ID map
  yahoo    Daily prices + dividends + capital gains -> monthly TOTAL returns,
           built two ways (own reinvestment vs Yahoo Adj Close) as a check
  french   Fama-French 3 factors + momentum + risk-free (Ken French library)
  nport    SEC Form N-PORT, 2019+: quarter-end net assets, monthly sales /
           redemptions (= actual monthly flows), official monthly returns
  nsar     SEC Form N-SAR, 1994-2018: semi-annual net assets, monthly sales /
           redemptions, expenses and average net assets (-> expense ratio)
  fees     SEC prospectus risk/return data sets, 2011+: expense ratio of every
           share class (your funds' history + fee distribution)
  panel    Merge everything into one monthly analysis file + run checks

The SEC asks every script to identify itself. Put your name and email in
SEC_USER_AGENT below (or set the environment variable SEC_USER_AGENT).

Requirements: pip install pandas numpy requests yfinance
"""
from pathlib import Path
import io
import os
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------- settings ---
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "UWaterloo CFM301 student c245zhao@uwaterloo.ca")

HERE = Path(__file__).resolve().parent
DATA = HERE / "Data"
RAW = DATA / "raw"                       # cached downloads (not needed by the analysis)
DATA.mkdir(exist_ok=True)
RAW.mkdir(exist_ok=True)

START, END = "1993-01-01", "2025-12-31"

FUNDS = {   # ticker: short name used in every output file
    "FCNTX": "Contrafund",
    "TRBCX": "BlueChipGrowth",
    "AGTHX": "GrowthFundAmerica_A",
    "FMAGX": "Magellan",
}
EXTRA = {"GFACX": "GrowthFundAmerica_C"}                 # share-class sensitivity
INDEX = {"VFINX": "Vanguard500", "NAESX": "VanguardSmallCap",
         "VIVAX": "VanguardValue", "VIGRX": "VanguardGrowth"}
ALL = {**FUNDS, **EXTRA, **INDEX}

# words that identify each fund inside multi-fund SEC filings
NAME_KEYS = {"FCNTX": "CONTRAFUND", "TRBCX": "BLUE CHIP GROWTH", "AGTHX": "GROWTH FUND OF AMERICA",
             "FMAGX": "MAGELLAN", "GFACX": "GROWTH FUND OF AMERICA",
             "VFINX": "500 INDEX", "NAESX": "SMALL-CAP INDEX", "VIVAX": "VALUE INDEX",
             "VIGRX": "GROWTH INDEX"}

FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
RR_URL = "https://www.sec.gov/files/dera/data/mutual-fund-prospectus-risk/return-summary-data-sets/{q}_rr1.zip"


# ----------------------------------------------------------------- helpers ---
def done(name):
    if (DATA / name).exists():
        print(f"  {name} exists, skipping (delete it to re-download)")
        return True
    return False


def save(df, name):
    df.to_csv(DATA / name, index=False)
    print(f"  saved {name}: {len(df):,} rows")


_last = [0.0]


def sec_get(url, binary=False):
    """GET from sec.gov with the required User-Agent and <=8 requests/second."""
    if not SEC_USER_AGENT:
        sys.exit("Set SEC_USER_AGENT at the top of pull_data.py to 'Your Name your@email' first.")
    wait = 0.13 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    for attempt in range(4):
        r = requests.get(url, headers={"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"},
                         timeout=120)
        _last[0] = time.time()
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.content if binary else r.text
    r.raise_for_status()


def local(tag):
    return tag.rsplit("}", 1)[-1]


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return np.nan


def ticker_map():
    p = DATA / "sec_ticker_map.csv"
    if not p.exists():
        step_tickers()
    return pd.read_csv(p)


def filings(cik, forms):
    """All filings of the given form types for one CIK (pages through history)."""
    j = __import__("json").loads(sec_get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"))
    pages = [j["filings"]["recent"]]
    for f in j["filings"].get("files", []):
        pages.append(__import__("json").loads(sec_get("https://data.sec.gov/submissions/" + f["name"])))
    df = pd.concat([pd.DataFrame(p) for p in pages], ignore_index=True)
    return df[df["form"].isin(forms)].copy()


# ==================================================================== steps ===
def step_tickers():
    """SEC's official mutual-fund ticker file: ticker -> CIK, series, class."""
    if done("sec_ticker_map.csv"):
        return
    j = __import__("json").loads(sec_get("https://www.sec.gov/files/company_tickers_mf.json"))
    df = pd.DataFrame(j["data"], columns=j["fields"])
    df = df[df["symbol"].isin(ALL)].rename(columns={"symbol": "ticker", "seriesId": "series_id",
                                                    "classId": "class_id"})
    df["name"] = df["ticker"].map(ALL)
    missing = set(ALL) - set(df["ticker"])
    if missing:
        print(f"  WARNING: not in SEC ticker file: {sorted(missing)}")
    save(df, "sec_ticker_map.csv")


def step_yahoo():
    """Monthly total returns from Yahoo Finance, built two ways:
       ret_tr  = own calculation: (close + dividend + capital gain) / previous close
       ret_adj = change in Yahoo's 'Adj Close'
       If the two disagree a lot in a month, a distribution is probably missing."""
    if done("returns_monthly.csv"):
        return
    import yfinance as yf
    out = []
    for t, name in ALL.items():
        h = yf.Ticker(t).history(start=START, end="2026-01-01", auto_adjust=False, actions=True)
        if h.empty:
            print(f"  WARNING: no Yahoo data for {t}")
            continue
        h.index = h.index.tz_localize(None)
        h.to_csv(RAW / f"yahoo_daily_{t}.csv")
        dist = h.get("Dividends", 0) + h.get("Capital Gains", 0)
        daily_tr = (h["Close"] + dist) / h["Close"].shift(1) - 1
        m = pd.DataFrame({
            "ret_tr": (1 + daily_tr).resample("ME").prod() - 1,
            "ret_adj": h["Adj Close"].resample("ME").last().pct_change(fill_method=None),
            "nav": h["Close"].resample("ME").last(),
            "distributions": dist.resample("ME").sum(),
            "trading_days": h["Close"].resample("ME").count(),
        })
        m = m.iloc[1:]                       # first month is partial
        m["ticker"], m["name"] = t, name
        out.append(m.rename_axis("date").reset_index())
        print(f"  {t}: {m.index.min():%Y-%m} to {m.index.max():%Y-%m}")
    df = pd.concat(out)
    save(df, "returns_monthly.csv")

    # Check: compound each calendar year; compare with the fund's published
    # annual total returns (fund website / annual report) for a few years.
    yr = (df.assign(year=pd.to_datetime(df["date"]).dt.year)
            .groupby(["ticker", "year"])[["ret_tr", "ret_adj"]]
            .apply(lambda g: (1 + g).prod() - 1).reset_index())
    yr["gap"] = yr["ret_tr"] - yr["ret_adj"]
    save(yr, "check_annual_returns.csv")
    big = yr[yr["gap"].abs() > 0.005]
    if len(big):
        print(f"  NOTE: {len(big)} fund-years where own and Adj-Close returns differ by >0.5%."
              " Compare those years with the fund's published returns (check_annual_returns.csv).")


def read_french(fname):
    raw = RAW / fname
    if not raw.exists():
        r = requests.get(FRENCH + fname, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        raw.write_bytes(r.content)
    with zipfile.ZipFile(raw) as z:
        text = z.read(z.namelist()[0]).decode("latin-1")
    return parse_french(text)


def parse_french(text):
    """Keep only the monthly block (rows starting with YYYYMM); values are % -> decimals."""
    rows, header, started = [], None, False
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if re.fullmatch(r"\d{6}", parts[0] or ""):
            started = True
            rows.append(parts)
        elif started:
            break                            # annual block starts after a blank/label line
        elif len(parts) > 1 and parts[0] == "":
            header = parts[1:]
    df = pd.DataFrame(rows).iloc[:, : len(header) + 1]
    df.columns = ["yyyymm"] + [h.lower().replace("-", "") for h in header]
    df["date"] = pd.to_datetime(df["yyyymm"], format="%Y%m") + pd.offsets.MonthEnd(0)
    vals = df.drop(columns=["yyyymm", "date"]).apply(pd.to_numeric, errors="coerce") / 100
    return pd.concat([df[["date"]], vals], axis=1)


def step_french():
    if done("ff_factors.csv"):
        return
    ff3 = read_french("F-F_Research_Data_Factors_CSV.zip")          # mktrf, smb, hml, rf
    mom = read_french("F-F_Momentum_Factor_CSV.zip")                # mom
    mom.columns = ["date", "umd"]
    df = ff3.merge(mom, on="date", how="left")
    df = df[(df["date"] >= START) & (df["date"] <= END)]
    save(df, "ff_factors.csv")


def parse_nport(xml_text):
    """One NPORT-P filing -> dict with series, period, net assets, monthly flows, class returns."""
    root = ET.fromstring(xml_text.encode() if isinstance(xml_text, str) else xml_text)
    rec = {"returns": [], "flows": {}}
    for el in root.iter():
        n = local(el.tag)
        if n == "seriesId" and "series_id" not in rec:
            rec["series_id"] = (el.text or "").strip()
        elif n == "repPdDate":
            rec["period"] = (el.text or "").strip()
        elif n == "netAssets" and "net_assets" not in rec:
            rec["net_assets"] = num(el.text)
        elif n == "monthlyTotReturn":
            rec["returns"].append({k: el.attrib.get(k) for k in ("classId", "rtn1", "rtn2", "rtn3")})
        elif re.fullmatch(r"mon[123]Flow", n):
            rec["flows"][int(n[3])] = {k: num(el.attrib.get(k)) for k in ("sales", "reinvestment", "redemption")}
    return rec


def step_nport():
    if done("nport_monthly.csv"):
        return
    tm = ticker_map()
    rows, rets = [], []
    for cik, grp in tm[tm["ticker"].isin(list(FUNDS) + list(EXTRA))].groupby("cik"):
        want = dict(zip(grp["series_id"], grp["ticker"]))
        classes = dict(zip(grp["class_id"], grp["ticker"]))
        f = filings(cik, {"NPORT-P"})
        print(f"  CIK {cik}: {len(f)} N-PORT filings to scan for {sorted(set(want.values()))}")
        for _, r in f.iterrows():
            acc = r["accessionNumber"].replace("-", "")
            doc = os.path.basename(r["primaryDocument"])          # drop the xsl viewer folder
            try:
                rec = parse_nport(sec_get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"))
            except Exception as e:
                print(f"    skip {r['accessionNumber']}: {e}")
                continue
            if rec.get("series_id") not in want:
                continue
            end = pd.Timestamp(rec["period"]) + pd.offsets.MonthEnd(0)
            for k in (1, 2, 3):
                month = end - pd.offsets.MonthEnd(3 - k)
                fl = rec["flows"].get(k, {})
                rows.append({"date": month, "series_id": rec["series_id"], "ticker": want[rec["series_id"]],
                             "net_assets": rec["net_assets"] if k == 3 else np.nan,
                             "sales": fl.get("sales"), "reinvestment": fl.get("reinvestment"),
                             "redemption": fl.get("redemption"), "accession": r["accessionNumber"]})
            for c in rec["returns"]:
                for k in (1, 2, 3):
                    rets.append({"date": end - pd.offsets.MonthEnd(3 - k), "class_id": c["classId"],
                                 "ticker": classes.get(c["classId"]), "ret_pct": num(c[f"rtn{k}"])})
    df = pd.DataFrame(rows).sort_values(["ticker", "date", "accession"])
    df = df.drop_duplicates(["ticker", "date"], keep="last")              # amendments: keep latest
    df["net_flow"] = df["sales"].fillna(0) + df["reinvestment"].fillna(0) - df["redemption"].fillna(0)
    save(df, "nport_monthly.csv")
    r = pd.DataFrame(rets).dropna(subset=["ticker"]).drop_duplicates(["class_id", "date"], keep="last")
    save(r, "nport_class_returns.csv")


NSAR_LINE = re.compile(r"^(\d{3})\s+([A-Z])(\d{2})(\d{2})(\d{2})\s+(.*\S)\s*$")


def parse_nsar(text):
    """N-SAR answer lines look like '028 A010100     52341' =
       item 028, row A, column 01, series 01, sub 00, value.
       Amounts are in thousands of dollars."""
    period = re.search(r"CONFORMED PERIOD OF REPORT:\s*(\d{8})", text)
    out = []
    for line in text.splitlines():
        m = NSAR_LINE.match(line)
        if m:
            item, row, col, series, sub, val = m.groups()
            out.append({"item": item, "row": row, "col": col, "series": series, "sub": sub, "value": val})
    return (period.group(1) if period else None), pd.DataFrame(out)


def nsar_series_for(lines, key):
    """Find which N-SAR series number belongs to the fund (item 007 C lists series names)."""
    names = lines[(lines["item"] == "007") & (lines["row"] == "C") & lines["value"].str.contains("[A-Za-z]")]
    hit = names[names["value"].str.upper().str.contains(key)]
    if len(hit):
        return hit["series"].iloc[0]
    return lines["series"].mode().iloc[0] if len(lines) else None    # single-fund filer


def step_nsar():
    if done("nsar_semiannual.csv"):
        return
    tm = ticker_map()
    rows, monthly = [], []
    for _, fund in tm[tm["ticker"].isin(list(FUNDS) + list(EXTRA))].iterrows():
        f = filings(fund["cik"], {"NSAR-A", "NSAR-B", "NSAR-A/A", "NSAR-B/A"})
        print(f"  {fund['ticker']}: {len(f)} N-SAR filings")
        for _, r in f.iterrows():
            acc = r["accessionNumber"]
            url = f"https://www.sec.gov/Archives/edgar/data/{int(fund['cik'])}/{acc.replace('-', '')}/{acc}.txt"
            try:
                period, L = parse_nsar(sec_get(url))
            except Exception as e:
                print(f"    skip {acc}: {e}")
                continue
            if L.empty or period is None:
                continue
            s = nsar_series_for(L, NAME_KEYS[fund["ticker"]])
            S = L[L["series"] == s]
            def get(item, row, col="00"):
                hit = S.loc[(S["item"] == item) & (S["row"] == row) & (S["col"] == col), "value"]
                return num(hit.iloc[0]) if len(hit) else np.nan
            end = pd.Timestamp(period) + pd.offsets.MonthEnd(0)
            rows.append({"date": end, "ticker": fund["ticker"], "form": r["form"], "accession": acc,
                         "nsar_series": s,
                         "net_assets_k": get("074", "T"),            # net assets, $000
                         "avg_net_assets_k": get("074", "V"),        # average net assets, $000
                         "total_expenses_k": get("072", "X")})       # total expenses, $000
            for i, row in enumerate("ABCDEF"):                       # item 28: 6 months of flows
                monthly.append({"date": end - pd.offsets.MonthEnd(5 - i), "ticker": fund["ticker"],
                                "sales_k": get("028", row, "01"), "reinvest_k": get("028", row, "02"),
                                "redemptions_k": get("028", row, "04"), "accession": acc})
    df = pd.DataFrame(rows).sort_values(["ticker", "date", "accession"]).drop_duplicates(
        ["ticker", "date"], keep="last")
    # NSAR-B expenses cover the whole fiscal year; NSAR-A covers six months
    months = np.where(df["form"].str.startswith("NSAR-B"), 12, 6)
    df["expense_ratio_est"] = df["total_expenses_k"] / df["avg_net_assets_k"] * (12 / months)
    save(df, "nsar_semiannual.csv")
    m = pd.DataFrame(monthly).sort_values(["ticker", "date", "accession"]).drop_duplicates(
        ["ticker", "date"], keep="last")
    m["net_flow_k"] = m["sales_k"].fillna(0) + m["reinvest_k"].fillna(0) - m["redemptions_k"].fillna(0)
    save(m, "nsar_monthly_flows.csv")
    print("  CHECK: compare a few net_assets_k and expense_ratio_est values with the funds' annual reports.")


def step_fees():
    """Expense ratios from the SEC risk/return data sets (all funds, 2011+)."""
    if done("expense_ratios_sec.csv"):
        return
    tm = ticker_map()
    my_classes = set(tm["class_id"])
    hist, latest = [], []
    for year in range(2011, 2026):
        for q in range(1, 5):
            tag = f"{year}q{q}"
            raw = RAW / f"{tag}_rr1.zip"
            try:
                if not raw.exists():
                    raw.write_bytes(sec_get(RR_URL.format(q=tag), binary=True))
                with zipfile.ZipFile(raw) as z:
                    numf = [n for n in z.namelist() if n.lower().startswith("num")][0]
                    d = pd.read_csv(z.open(numf), sep="\t", dtype=str, low_memory=False)
            except Exception as e:
                print(f"  {tag}: skipped ({e})")
                continue
            d = d[d["tag"].str.contains("ExpensesOverAssets", na=False)]
            d["value"] = pd.to_numeric(d["value"], errors="coerce")
            d["quarter"] = tag
            hist.append(d[d["class"].isin(my_classes)])
            if year == 2025:
                latest.append(d)
            print(f"  {tag}: {len(d):,} expense-ratio facts")
            raw.unlink()                       # zips are big; keep only what we use
    h = pd.concat(hist)[["quarter", "adsh", "tag", "ddate", "series", "class", "value"]]
    h = h.merge(tm[["class_id", "ticker"]], left_on="class", right_on="class_id", how="left")
    save(h, "expense_ratios_sec.csv")
    if latest:
        l = pd.concat(latest)
        l = l[l["tag"] == "NetExpensesOverAssets"] if (l["tag"] == "NetExpensesOverAssets").any() else l
        save(l[["quarter", "series", "class", "tag", "value"]].drop_duplicates(["class"], keep="last"),
             "fee_distribution_all_funds_2025.csv")


def step_panel():
    """One row per fund-month with everything the regressions need."""
    need = ["returns_monthly.csv", "ff_factors.csv"]
    if any(not (DATA / n).exists() for n in need):
        print("  panel needs returns_monthly.csv and ff_factors.csv first")
        return
    r = pd.read_csv(DATA / "returns_monthly.csv", parse_dates=["date"])
    ff = pd.read_csv(DATA / "ff_factors.csv", parse_dates=["date"])
    p = r.merge(ff, on="date", how="left")
    p["ret"] = p["ret_tr"]
    p["exret"] = p["ret"] - p["rf"]

    # annual expense ratio -> monthly; best available source per year
    exp = []
    if (DATA / "expense_ratios_sec.csv").exists():
        e = pd.read_csv(DATA / "expense_ratios_sec.csv")
        e = e[e["tag"] == "ExpensesOverAssets"] if (e["tag"] == "ExpensesOverAssets").any() else e
        e["year"] = e["quarter"].str[:4].astype(int)
        exp.append(e.groupby(["ticker", "year"])["value"].median().rename("exp_ratio").reset_index()
                     .assign(exp_source="SEC prospectus"))
    if (DATA / "nsar_semiannual.csv").exists():
        n = pd.read_csv(DATA / "nsar_semiannual.csv", parse_dates=["date"])
        n = n[n["form"].str.startswith("NSAR-B")].assign(year=lambda x: x["date"].dt.year)
        exp.append(n.groupby(["ticker", "year"])["expense_ratio_est"].last().rename("exp_ratio")
                     .reset_index().assign(exp_source="N-SAR estimate"))
    manual = DATA / "expense_ratios_manual.csv"        # optional: ticker,year,exp_ratio (decimal)
    if manual.exists():
        exp.insert(0, pd.read_csv(manual).assign(exp_source="manual (annual report)"))
    if exp:
        E = pd.concat(exp).dropna(subset=["exp_ratio"]).drop_duplicates(["ticker", "year"], keep="first")
        E.loc[E["exp_ratio"] > 0.05, "exp_ratio"] /= 100            # percent -> decimal
        p["year"] = p["date"].dt.year
        p = p.merge(E, on=["ticker", "year"], how="left")
        p["exp_ratio"] = p.groupby("ticker")["exp_ratio"].transform(lambda s: s.ffill().bfill())
        p["exp_monthly"] = p["exp_ratio"] / 12
        p["ret_gross"] = p["ret"] + p["exp_monthly"]
        p["exret_gross"] = p["ret_gross"] - p["rf"]

    # flows: N-SAR (1994-2018) and N-PORT (2019+), in dollars
    fl = []
    if (DATA / "nsar_monthly_flows.csv").exists():
        a = pd.read_csv(DATA / "nsar_monthly_flows.csv", parse_dates=["date"])
        fl.append(a.assign(net_flow=a["net_flow_k"] * 1000, flow_source="N-SAR")[["ticker", "date", "net_flow", "flow_source"]])
    if (DATA / "nport_monthly.csv").exists():
        b = pd.read_csv(DATA / "nport_monthly.csv", parse_dates=["date"])
        fl.append(b.assign(flow_source="N-PORT")[["ticker", "date", "net_flow", "flow_source"]])
    if fl:
        F = pd.concat(fl).sort_values("flow_source").drop_duplicates(["ticker", "date"], keep="last")
        p = p.merge(F, on=["ticker", "date"], how="left")
    p["role"] = np.where(p["ticker"].isin(list(FUNDS)), "active", np.where(p["ticker"].isin(list(INDEX)), "index", "extra"))
    save(p.drop(columns=["year"], errors="ignore"), "panel_monthly.csv")
    check(p)


def check(p):
    print("\n--- data checks (report these counts, requirement 4) ---")
    print(f"  duplicate fund-months : {p.duplicated(['ticker', 'date']).sum()}")
    print(f"  months missing return : {p['ret'].isna().sum()}")
    print(f"  months missing factors: {p['mktrf'].isna().sum()}")
    if "exp_ratio" in p:
        print(f"  months missing fee    : {p['exp_ratio'].isna().sum()}")
    ext = p[p["ret"].abs() > 0.25]
    print(f"  |monthly return| > 25%: {len(ext)}" + (f"  {ext[['ticker', 'date', 'ret']].values.tolist()}" if len(ext) else ""))
    print("  coverage by fund:")
    cov = p.dropna(subset=["ret"]).groupby("ticker")["date"].agg(["min", "max", "count"])
    if "net_flow" in p:
        cov["flow_months"] = p.dropna(subset=["net_flow"]).groupby("ticker").size()
    print(cov.to_string())


STEPS = {"tickers": step_tickers, "yahoo": step_yahoo, "french": step_french,
         "nport": step_nport, "nsar": step_nsar, "fees": step_fees, "panel": step_panel}

if __name__ == "__main__":
    chosen = sys.argv[1:] or list(STEPS)
    for name in chosen:
        print(f"\n== {name} ==")
        try:
            STEPS[name]()
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}  (other steps continue; send this message for a fix)")
