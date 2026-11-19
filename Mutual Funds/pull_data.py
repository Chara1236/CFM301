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

The SEC asks every script to identify itself. Set the environment variable
before running (PowerShell):  $env:SEC_USER_AGENT = "Your Name your@email"

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
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "")      # set in the terminal, never in this file

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
EXTRA = {}                                                # (GFACX share class dropped from the study)
INDEX = {"VFINX": "Vanguard500", "NAESX": "VanguardSmallCap",
         "VIVAX": "VanguardValue", "VIGRX": "VanguardGrowth"}
ALL = {**FUNDS, **EXTRA, **INDEX}

# words that identify each fund inside multi-fund SEC filings
NAME_KEYS = {"FCNTX": "CONTRAFUND", "TRBCX": "BLUE CHIP GROWTH", "AGTHX": "GROWTH FUND OF AMERICA",
             "FMAGX": "MAGELLAN",
             "VFINX": "500 INDEX", "NAESX": "SMALL-CAP INDEX", "VIVAX": "VALUE INDEX",
             "VIGRX": "GROWTH INDEX"}

FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
# SEC posts 2011-2023 as one file per year (e.g. 2019_rr1.zip) and later data per quarter (2025q1_rr1.zip)
RR_BASE = "https://www.sec.gov/files/dera/data/mutual-fund-prospectus-risk/return-summary-data-sets/"
NSAR_CAP = 99_999_999        # N-SAR amount field is full at $100B ($000); the true value is unknown


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
        sys.exit('Set the SEC user agent first, e.g. in PowerShell: $env:SEC_USER_AGENT = "Your Name your@email"')
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
    tm = pd.read_csv(p)
    return tm[tm["ticker"].isin(ALL)]


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
    # Yahoo misses or misstates a few distributions; corrections checked against SEC N-SAR item 73
    # (distributions per share) and the ex-date price move. Amount in Yahoo's price units.
    corr_p = DATA / "distribution_corrections.csv"
    corr = pd.read_csv(corr_p, parse_dates=["date"]) if corr_p.exists() else pd.DataFrame(columns=["ticker", "date", "amount"])
    out = []
    for t, name in ALL.items():
        cache = RAW / f"yahoo_daily_{t}.csv"
        if cache.exists():                                    # reuse the saved download
            h = pd.read_csv(cache, index_col=0)
            h.index = pd.to_datetime(h.index, utc=True).tz_localize(None).normalize()
        else:
            import yfinance as yf
            h = yf.Ticker(t).history(start=START, end="2026-01-01", auto_adjust=False, actions=True)
            if h.empty:
                print(f"  WARNING: no Yahoo data for {t}")
                continue
            h.index = h.index.tz_localize(None)
            h.to_csv(cache)
        dist = h.get("Dividends", 0) + h.get("Capital Gains", 0)
        for _, c in corr[corr["ticker"] == t].iterrows():
            dist.loc[c["date"]] += c["amount"]
            print(f"  {t} {c['date']:%Y-%m-%d}: distribution corrected by {c['amount']:+}")
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
    # reinvested distributions are left out on purpose: they are not new investor money
    df["net_flow"] = df["sales"] - df["redemption"]
    save(df, "nport_monthly.csv")
    r = pd.DataFrame(rets).dropna(subset=["ticker"]).drop_duplicates(["class_id", "date"], keep="last")
    save(r, "nport_class_returns.csv")


# series is two digits, or "AA" = answer applies to all series (common in 1990s filings)
NSAR_LINE = re.compile(r"^(\d{3})\s+([A-Z])(\d{2})([0-9A]{2})(\d{2})\s+(.*\S)\s*$")


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
            AA = L[L["series"] == "AA"]                             # answers shared by all series
            def get(item, row, col="00"):
                hit = S.loc[(S["item"] == item) & (S["row"] == row) & (S["col"] == col), "value"]
                if hit.empty:
                    hit = AA.loc[(AA["item"] == item) & (AA["row"] == row) & (AA["col"] == col), "value"]
                v = num(hit.iloc[0]) if len(hit) else np.nan
                return np.nan if v >= NSAR_CAP else v               # capped field = unknown
            # (for funds over $100B the asset fields can also overflow to 0 or negative; see fee_table)
            end = pd.Timestamp(period) + pd.offsets.MonthEnd(0)
            rows.append({"date": end, "ticker": fund["ticker"], "form": r["form"], "accession": acc,
                         "nsar_series": s,
                         "net_assets_k": get("074", "T"),            # item 74T: net assets, $000
                         "avg_net_assets_k": get("075", "B"),        # item 75B: avg net assets (non-MMF), $000
                         "total_expenses_k": get("072", "X"),        # item 72X: total expenses, $000
                         "reimbursed_k": get("072", "Y"),            # item 72Y: expense reimbursements, $000
                         "turnover_pct": get("071", "D"),            # item 71D: portfolio turnover rate, %
                         "div_ps": get("073", "A", "01"),            # item 73A1: dividends per share, $
                         "capgain_ps": get("073", "B")})             # item 73B: capital gains per share, $
            for i, row in enumerate("ABCDEF"):                       # item 28: 6 months of flows
                monthly.append({"date": end - pd.offsets.MonthEnd(5 - i), "ticker": fund["ticker"],
                                "sales_k": get("028", row, "01"), "reinvest_k": get("028", row, "02"),
                                "redemptions_k": get("028", row, "04"), "accession": acc})
    df = pd.DataFrame(rows).sort_values(["ticker", "date", "accession"]).drop_duplicates(
        ["ticker", "date"], keep="last")
    # funds over $100B overflow the 8-digit asset fields: they show 0, a negative number, or wrap
    # around (e.g. $119B reported as $19B). Drop those: <= 0, or < 40% of the last good value.
    for c in ("net_assets_k", "avg_net_assets_k"):
        df.loc[df[c] <= 0, c] = np.nan
        for t, g in df.groupby("ticker"):
            last = np.nan
            for i, v in g[c].items():
                if pd.notna(v) and pd.notna(last) and v < 0.4 * last:
                    df.loc[i, c] = np.nan
                elif pd.notna(v):
                    last = v
    # NSAR-B expenses cover the whole fiscal year; NSAR-A covers six months
    months = np.where(df["form"].str.startswith("NSAR-B"), 12, 6)
    net_exp = df["total_expenses_k"] - df["reimbursed_k"].fillna(0)     # what shareholders actually paid
    df["expense_ratio_est"] = net_exp / df["avg_net_assets_k"] * (12 / months)
    save(df, "nsar_semiannual.csv")
    m = pd.DataFrame(monthly).sort_values(["ticker", "date", "accession"]).drop_duplicates(
        ["ticker", "date"], keep="last")
    m["net_flow_k"] = m["sales_k"] - m["redemptions_k"]               # reinvestment left out on purpose
    save(m, "nsar_monthly_flows.csv")
    print("  CHECK: compare a few net_assets_k and expense_ratio_est values with the funds' annual reports.")


FEE_TAGS = ["NetExpensesOverAssets", "ExpensesOverAssets"]      # net (after waivers) preferred


def rr_num_tables(zf):
    """Yield every num.tsv inside a risk/return zip (annual zips may hold quarterly zips or folders)."""
    for n in zf.namelist():
        low = n.lower()
        if low.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(zf.read(n))) as inner:
                yield from rr_num_tables(inner)
        elif low.rsplit("/", 1)[-1].startswith("num") and low.endswith((".tsv", ".txt")):
            yield pd.read_csv(zf.open(n), sep="\t", dtype=str, low_memory=False, on_bad_lines="skip")


def rr_period(label, tm, log):
    """Download one risk/return file, keep expense-ratio and turnover facts. Cached in raw/ as small
       CSVs. Returns (fees for my funds, all-fund fees, turnover for my funds) or None if the file is
       not on the SEC site."""
    mine_p, all_p = RAW / f"rr_{label}_mine.csv", RAW / f"rr_{label}_allfees.csv"
    turn_p = RAW / f"rr_{label}_turnover.csv"
    if mine_p.exists() and turn_p.exists():
        log.append({"period": label, "status": "cached"})
        return pd.read_csv(mine_p, dtype={"ddate": str}), pd.read_csv(all_p), pd.read_csv(turn_p)
    raw = RAW / f"{label}_rr1.zip"
    try:
        if not raw.exists():
            raw.write_bytes(sec_get(RR_BASE + f"{label}_rr1.zip", binary=True))
        with zipfile.ZipFile(raw) as z:
            d = pd.concat(list(rr_num_tables(z)), ignore_index=True)
    except Exception as e:
        log.append({"period": label, "status": "failed", "error": f"{type(e).__name__}: {e}"[:200]})
        raw.unlink(missing_ok=True)
        return None
    raw.unlink()                                      # zips are big; keep only what we use
    for c in ("series", "class", "ddate", "adsh"):
        if c not in d:
            d[c] = np.nan
    # turnover is a property of the portfolio (series), so it is matched on series, not class
    tv = d[d["tag"].str.contains("Turnover", case=False, na=False) & d["series"].isin(tm["series_id"])].copy()
    tv["value"] = pd.to_numeric(tv["value"], errors="coerce")
    tv["period"] = label
    tv = tv.merge(tm[["series_id", "ticker"]], left_on="series", right_on="series_id")
    tv = tv[["period", "adsh", "tag", "ddate", "series", "value", "ticker"]]
    tv.to_csv(turn_p, index=False)
    d = d[d["tag"].isin(FEE_TAGS)].copy()
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    d["period"] = label

    # match on share class only: a fact without a class can belong to any class of the series
    # (e.g. Vanguard 500 Admiral at 0.05% vs Investor VFINX at 0.14%)
    d["ticker"] = d["class"].map(dict(zip(tm["class_id"], tm["ticker"])))
    d["level"] = "class"
    mine = d[d["ticker"].notna()][["period", "adsh", "tag", "ddate", "series", "class", "value", "ticker", "level"]]
    allf = d[["period", "series", "class", "tag", "value"]]
    mine.to_csv(mine_p, index=False)
    allf.to_csv(all_p, index=False)
    log.append({"period": label, "status": "ok", "fee_facts_all_funds": len(d), "fee_facts_my_funds": len(mine),
                "my_tickers": " ".join(sorted(mine["ticker"].unique())), "turnover_facts_my_funds": len(tv)})
    return mine, allf, tv


def step_fees():
    """Expense ratios from the SEC risk/return data sets (all funds, 2011+).
       Writes fees_download_log.csv so failed or empty periods are visible."""
    if done("expense_ratios_sec.csv"):
        return
    tm = ticker_map()
    hist, latest, turn, log = [], [], [], []
    # through 2026: prospectuses filed in 2026 report fiscal-2025 fees (see fee_table)
    for year in range(2011, 2027):
        got = rr_period(str(year), tm, log) if year <= 2024 else None
        if got is None:                                  # no yearly file -> try the four quarters
            got = [g for q in range(1, 5) if (g := rr_period(f"{year}q{q}", tm, log)) is not None]
        else:
            got = [got]
        for mine, allf, tv in got:
            hist.append(mine)
            turn.append(tv)
            if year == 2025:
                latest.append(allf)
        print(f"  {year}: {sum(len(g[0]) for g in got)} fee and {sum(len(g[2]) for g in got)} turnover "
              f"facts for my funds from {len(got)} file(s)")
    lg = pd.DataFrame(log)
    lg.to_csv(DATA / "fees_download_log.csv", index=False)
    print(f"  saved fees_download_log.csv: {(lg['status'] == 'failed').sum()} failed downloads "
          "(a failed yearly file is normal when SEC posts that year by quarter)")
    h = pd.concat(hist, ignore_index=True)
    h["ddate"] = h["ddate"].astype(str).str[:8]
    save(h, "expense_ratios_sec.csv")
    save(pd.concat(turn, ignore_index=True), "turnover_sec.csv")
    if latest:
        l = pd.concat(latest).dropna(subset=["class", "value"])
        l["pref"] = l["tag"].map({t: i for i, t in enumerate(FEE_TAGS)})     # net if reported, else gross
        l = l.sort_values(["class", "pref", "period"]).drop_duplicates(["class"], keep="first")
        save(l[["class", "value"]], "fee_distribution_all_funds_2025.csv")      # one fee per share class


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

    # annual expense ratio -> monthly; one fee per fund-year (manual > SEC prospectus > N-SAR)
    years = p.assign(year=p["date"].dt.year).groupby("ticker")["year"].agg(["min", "max"])
    fees = fee_table(years)
    save(fees, "expense_ratio_by_year.csv")
    p["year"] = p["date"].dt.year
    p = p.merge(fees, on=["ticker", "year"], how="left")
    p["exp_monthly"] = p["exp_ratio"] / 12
    p["ret_gross"] = p["ret"] + p["exp_monthly"]
    p["exret_gross"] = p["ret_gross"] - p["rf"]
    turnover = turnover_table(years)
    save(turnover, "turnover_by_year.csv")
    p = p.merge(turnover, on=["ticker", "year"], how="left")

    # flows: N-SAR (1994-2018) and N-PORT (2019+), in dollars; sales - redemptions,
    # reinvested distributions left out on purpose (not new investor money)
    fl = []
    if (DATA / "nsar_monthly_flows.csv").exists():
        a = pd.read_csv(DATA / "nsar_monthly_flows.csv", parse_dates=["date"])
        a["net_flow"] = (a["sales_k"] - a["redemptions_k"]) * 1000
        fl.append(a.assign(flow_source="N-SAR")[["ticker", "date", "net_flow", "flow_source"]])
    if (DATA / "nport_monthly.csv").exists():
        b = nport_by_ticker()
        b["net_flow"] = b["sales"] - b["redemption"]
        fl.append(b.assign(flow_source="N-PORT")[["ticker", "date", "net_flow", "flow_source"]])
    if fl:
        F = pd.concat(fl).dropna(subset=["net_flow"]).sort_values("flow_source")
        F = F.drop_duplicates(["ticker", "date"], keep="last")          # N-PORT wins if both
        p = p.merge(F, on=["ticker", "date"], how="left")
    p = p.merge(tna_table(), on=["ticker", "date"], how="left")
    p["role"] = np.where(p["ticker"].isin(list(FUNDS)), "active", np.where(p["ticker"].isin(list(INDEX)), "index", "extra"))
    save(p.drop(columns=["year"], errors="ignore"), "panel_monthly.csv")
    check(p, fees)
    print("\n  turnover coverage (years by source):")
    print(fee_coverage(turnover.rename(columns={"turnover": "exp_ratio", "turnover_source": "exp_source"})).to_string())


def fee_table(years):
    """One expense ratio per fund-year (decimal) with its source.
       Known years come from (in priority order) Data/expense_ratios_manual.csv, SEC prospectus data
       (net of waivers when reported) and the N-SAR estimate (fund level, so not used for GFACX).
       Gaps between known years are interpolated ('filled'); years before the first / after the
       last known year repeat the nearest known value ('carried')."""
    known = []
    manual = DATA / "expense_ratios_manual.csv"        # optional: ticker,year,exp_ratio (decimal)
    if manual.exists():
        m = pd.read_csv(manual)
        m.loc[m["exp_ratio"] > 0.05, "exp_ratio"] /= 100           # typed as percent -> decimal
        known.append(m.assign(exp_source="manual (annual report)"))
    if (DATA / "expense_ratios_sec.csv").exists():
        e = pd.read_csv(DATA / "expense_ratios_sec.csv", dtype={"ddate": str})
        if "period" not in e:                                       # file from the old version
            e["period"] = e["quarter"]
        if "level" in e:
            e = e[e["level"] == "class"]
        # the prospectus fee table reports the PREVIOUS fiscal year's actual expenses, so a fee filed in
        # year t is assigned to t-1 (the same fiscal-year basis as the N-SAR estimate). ddate is not
        # used because it is a fiscal year-end in some filings and a prospectus date in others.
        e["year"] = e["period"].astype(str).str[:4].astype(int) - 1
        e["pref"] = e["tag"].map({t: i for i, t in enumerate(FEE_TAGS)})
        e = e[e["pref"] == e.groupby(["ticker", "year"])["pref"].transform("min")]
        known.append(e.groupby(["ticker", "year"])["value"].median().rename("exp_ratio").reset_index()
                       .assign(exp_source="SEC prospectus"))
    if (DATA / "nsar_semiannual.csv").exists():
        n = pd.read_csv(DATA / "nsar_semiannual.csv", parse_dates=["date"])
        n = n[(n["ticker"] != "GFACX") & n["form"].str.startswith("NSAR-B")].assign(year=lambda x: x["date"].dt.year)
        n = n[n["avg_net_assets_k"] > 0]       # 0 / negative = field overflowed (fund > $100B)
        known.append(n.groupby(["ticker", "year"])["expense_ratio_est"].last().rename("exp_ratio")
                       .reset_index().assign(exp_source="N-SAR estimate"))
    return fill_years(known, years, "exp_ratio", "exp_source")


def fill_years(known, years, col, src):
    """Stack known (ticker, year, col, src) tables (first one wins), then give every fund one row per
       year: gaps between known years are interpolated ('filled'), years before the first / after the
       last known year repeat the nearest known value ('carried')."""
    K = (pd.concat(known).dropna(subset=[col]).drop_duplicates(["ticker", "year"], keep="first")
         if known else pd.DataFrame(columns=["ticker", "year", col, src]))
    out = []
    for t, (y0, y1) in years.iterrows():
        g = pd.DataFrame({"ticker": t, "year": range(y0, y1 + 1)}).merge(K, on=["ticker", "year"], how="left")
        known_rows = g[col].notna()
        g[col] = g[col].interpolate(limit_area="inside")
        g.loc[~known_rows & g[col].notna(), src] = "filled"
        g[col] = g[col].ffill().bfill()
        g.loc[g[src].isna() & g[col].notna(), src] = "carried"
        out.append(g)
    return pd.concat(out, ignore_index=True)[["ticker", "year", col, src]]


def turnover_table(years):
    """One portfolio turnover rate per fund-year (decimal, 0.30 = 30%) with its source.
       Known years: Data/turnover_manual.csv (ticker,year,turnover), SEC prospectus (filed in year t ->
       fiscal year t-1, as for fees) and N-SAR item 71D (annual reports, NSAR-B). Turnover is a
       portfolio figure, so AGTHX and GFACX share it."""
    known = []
    manual = DATA / "turnover_manual.csv"
    if manual.exists():
        m = pd.read_csv(manual)
        m.loc[m["turnover"] > 5, "turnover"] /= 100                 # typed as percent -> decimal
        known.append(m.assign(turnover_source="manual (annual report)"))
    if (DATA / "turnover_sec.csv").exists():
        s = pd.read_csv(DATA / "turnover_sec.csv")
        s["year"] = s["period"].astype(str).str[:4].astype(int) - 1
        s.loc[s["value"] > 5, "value"] /= 100                        # percent -> decimal if needed
        known.append(s.groupby(["ticker", "year"])["value"].median().rename("turnover").reset_index()
                       .assign(turnover_source="SEC prospectus"))
    if (DATA / "nsar_semiannual.csv").exists():
        n = pd.read_csv(DATA / "nsar_semiannual.csv", parse_dates=["date"])
        if "turnover_pct" in n:
            n = n[n["form"].str.startswith("NSAR-B")].assign(year=lambda x: x["date"].dt.year,
                                                             turnover=lambda x: x["turnover_pct"] / 100)
            known.append(n.groupby(["ticker", "year"])["turnover"].last().reset_index()
                           .assign(turnover_source="N-SAR"))
    return fill_years(known, years, "turnover", "turnover_source")


def nport_by_ticker():
    """N-PORT is filed per series; give the rows to every ticker in that series
       (AGTHX and GFACX share one series, so both get the same fund-level flows and TNA)."""
    b = pd.read_csv(DATA / "nport_monthly.csv", parse_dates=["date"]).drop(columns="ticker")
    tm = ticker_map()
    tm = tm[tm["ticker"].isin(list(FUNDS) + list(EXTRA))]
    return b.merge(tm[["series_id", "ticker"]], on="series_id")


def tna_table():
    """Total net assets in dollars at the dates they are reported: N-SAR (semi-annual, to 2018)
       and N-PORT (quarter ends, 2019+). Fund (series) level, so AGTHX and GFACX share one TNA."""
    parts = []
    if (DATA / "nsar_semiannual.csv").exists():
        n = pd.read_csv(DATA / "nsar_semiannual.csv", parse_dates=["date"])
        n = n[(n["net_assets_k"] > 0) & (n["net_assets_k"] < NSAR_CAP)]    # 0 / negative = overflow
        parts.append(n.assign(tna=n["net_assets_k"] * 1000, tna_source="N-SAR")[["ticker", "date", "tna", "tna_source"]])
    if (DATA / "nport_monthly.csv").exists():
        b = nport_by_ticker().rename(columns={"net_assets": "tna"})
        parts.append(b.assign(tna_source="N-PORT")[["ticker", "date", "tna", "tna_source"]])
    if not parts:
        return pd.DataFrame(columns=["ticker", "date", "tna", "tna_source"])
    T = pd.concat(parts).dropna(subset=["tna"]).sort_values("tna_source")
    return T.drop_duplicates(["ticker", "date"], keep="last")


def fee_coverage(fees):
    """Years per source for each fund, and the runs of years that are NOT directly observed."""
    cov = (fees.pivot_table(index="ticker", columns="exp_source", values="year", aggfunc="count", fill_value=0)
               .reindex(sorted(fees["ticker"].unique()), fill_value=0))
    gaps = {}
    for t, g in fees.groupby("ticker"):
        miss = g.loc[g["exp_source"].isin(["filled", "carried"]) | g["exp_ratio"].isna(), "year"].tolist()
        runs, start = [], None
        for i, y in enumerate(miss):
            start = y if start is None else start
            if i == len(miss) - 1 or miss[i + 1] != y + 1:
                runs.append(f"{start}" if start == y else f"{start}-{y}")
                start = None
        gaps[t] = ", ".join(runs) or "-"
    cov["not_observed"] = pd.Series(gaps)
    return cov


def check(p, fees=None):
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
    if "tna" in p:
        cov["tna_obs"] = p.dropna(subset=["tna"]).groupby("ticker").size()
    print(cov.fillna(0).to_string())
    if fees is not None:
        print("\n  fee coverage (years by source; 'not_observed' = filled or carried, fill these by hand):")
        with pd.option_context("display.width", 200, "display.max_colwidth", 80):
            print(fee_coverage(fees).to_string())
        odd = fees[fees["exp_source"].isin(["SEC prospectus", "N-SAR estimate", "manual (annual report)"])
                   & ((fees["exp_ratio"] < 0.0005) | (fees["exp_ratio"] > 0.015))]
        if len(odd):
            print("\n  fees outside 0.05%-1.5% (check against the annual report):")
            print(odd.to_string(index=False))


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
