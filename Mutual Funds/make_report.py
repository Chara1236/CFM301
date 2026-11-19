"""Build report.docx from the tables and figures that mutualfunds.ipynb writes to output/.
Run after the notebook:  python make_report.py   (from the Mutual Funds folder)"""
from pathlib import Path
import ast
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
ACTIVE = ["FCNTX", "TRBCX", "AGTHX", "FMAGX"]
SHORT = {"FCNTX": "Contrafund (FCNTX)", "TRBCX": "Blue Chip Growth (TRBCX)",
         "AGTHX": "Growth Fund of America A (AGTHX)", "FMAGX": "Magellan (FMAGX)"}

# ------------------------------------------------------------------ numbers ---
t1 = pd.read_csv(OUT / "table1_factor_regressions.csv").set_index(["fund", "model"])
t2 = pd.read_csv(OUT / "table2_fees_gross_net_index.csv", index_col=0)
t3 = pd.read_csv(OUT / "table3a_persistence_halves.csv", header=[0, 1], index_col=0)
flows = pd.read_csv(OUT / "table3b_flows.csv", index_col=0)
sens = pd.read_csv(OUT / "table4_sensitivity.csv", index_col=0)
bench = pd.read_csv(OUT / "table_index_benchmark.csv").set_index(["fund", "returns"])
feep = pd.read_csv(OUT / "table_fee_distribution.csv", index_col=0)
fto = pd.read_csv(OUT / "table_fee_turnover_regression.csv").set_index(["returns", "spec"])
fg = pd.read_csv(OUT / "table_fee_groups.csv", index_col=0)
size = pd.read_csv(OUT / "table_fund_size.csv", index_col=0)
clean = pd.read_csv(OUT / "table0_cleaning.csv", index_col=0)
nport = pd.read_csv(OUT / "check_nport.csv", index_col=0)
gaps = pd.read_csv(OUT / "tna_rollforward_gaps.csv")
S = pd.read_csv(OUT / "summary_numbers.csv", index_col=0).iloc[:, 0]
num = lambda k: float(S[k])
idx_fee = ast.literal_eval(S["index_fee_avg_%"])

a = lambda f, m="Carhart": t1.loc[(f, m), "alpha"]
fl1 = flows.loc["past12"]
trend = fto.loc[("gross", "fund FE + trend")]
agthx_gap = gaps[(gaps["ticker"] == "AGTHX")].sort_values("months").iloc[-1]
fee_lo, fee_hi = t2["fee_saving"].min(), t2["fee_saving"].max()
roll_pct = sens.loc[["FCNTX", "TRBCX", "AGTHX"]].iloc[:, 6].str.split("%").str[0].astype(int)
roll_lo, roll_hi = roll_pct.min(), roll_pct.max()
load3 = (1 - (1 - 0.0575) ** (1 / 3)) * 100

# ------------------------------------------------------------------ helpers ---
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Inches(0.6))
sec.top_margin = sec.bottom_margin = Inches(0.5)
base = doc.styles["Normal"]
base.font.name = "Calibri"
base.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
base.font.size = Pt(9.5)
base.paragraph_format.space_after = Pt(3)
base.paragraph_format.line_spacing = 1.0
NAVY = RGBColor(0x1F, 0x4E, 0x79)


def heading(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold, r.font.size, r.font.color.rgb = True, Pt(10.5), NAVY
    return p


def para(*parts, size=None, after=None, align=None):
    """parts: str or (str, 'b'|'i') tuples."""
    p = doc.add_paragraph()
    for part in parts:
        text, fmt = (part, "") if isinstance(part, str) else part
        r = p.add_run(text)
        r.bold, r.italic = "b" in fmt, "i" in fmt
        if size:
            r.font.size = Pt(size)
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if align:
        p.alignment = align
    return p


def caption(text):
    p = para((text, "b"), size=8.5, after=1)
    p.paragraph_format.keep_with_next = True
    return p


def note(text):
    return para((text, "i"), size=7.5, after=4)


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hex_fill)
    tcPr.append(sh)


def table(rows, widths, header_rows=1, size=8, bold_first_col=True):
    tb = doc.add_table(rows=len(rows), cols=len(widths))
    tb.alignment = WD_TABLE_ALIGNMENT.CENTER
    tb.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tb.cell(i, j)
            c.width = Inches(widths[j])
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val))
            r.font.size = Pt(size)
            r.bold = i < header_rows or (j == 0 and bold_first_col)
            if i < header_rows:
                shade(c, "DCE6F0")
    return tb


def merge_header(tb, row, c0, c1):
    m = tb.cell(row, c0).merge(tb.cell(row, c1))
    for p in m.paragraphs[1:]:
        p._element.getparent().remove(p._element)


f2 = lambda x: f"{x:+.2f}"


def ordinal(x):
    n = int(round(x))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
at = lambda x, t: f"{x:+.2f} ({t:.1f})"

# ------------------------------------------------------------------- report ---
title = para(("Are the Fees of America’s Largest Growth Funds Justified? Evidence from Four Active Large-Cap Growth Funds, 1993–2025", "b"), size=13, after=1)
para(("CFM 301 Project 5 · Group [#] · [names]", "i"), size=8.5, after=4)

heading("1. Economic question and audience")
para("Four of the largest actively managed US equity funds — Fidelity Contrafund, T. Rowe Price Blue Chip Growth, "
     "American Funds Growth Fund of America and Fidelity Magellan — together manage over $600 billion and charge "
     "0.6–0.8% a year, roughly four times a growth index fund. ",
     ("Question: do these funds earn a gross-of-fee alpha large enough to leave their investors a non-negative net-of-fee "
      "alpha, measured against factor models and against a portfolio of low-cost index funds an investor could actually buy?", "b"),
     " Our audience is ", ("retail investors and the financial advisors who choose funds for them", "b"),
     ": they pay the fee, they choose between these funds and index funds, and they cannot short factors, so the "
     "index-fund benchmark is the alternative that matters most to them. The work would interest (and could be funded by) "
     "investor-advocacy groups and robo-advisors that recommend low-cost portfolios, and securities regulators (SEC, OSC) "
     "reviewing fee disclosure.")

heading("2. Data, return construction and cleaning")
para(("Funds and sample. ", "b"),
     f"Four active large-cap growth funds (same Morningstar category, so comparable) and four Vanguard index funds used "
     f"as the implementable benchmark (500 Index VFINX, Small-Cap NAESX, Value VIVAX, Growth VIGRX). Monthly data "
     f"{S['sample']}; the common sample starts at TRBCX’s inception. ",
     ("Sources (all free; no WRDS access). ", "b"),
     "Daily NAV, dividends and capital gains from Yahoo Finance; Fama-French 3 factors, momentum and the risk-free rate from "
     "Ken French’s library; expense ratios, turnover, monthly sales/redemptions, TNA and per-share distributions from SEC "
     "filings (prospectus risk/return data sets 2011+, Form N-SAR 1993–2018, Form N-PORT 2019+).")
para(("Returns. ", "b"),
     "We use total returns with all distributions reinvested: r(t) = (NAV(t) + dividends + capital gains)/NAV(t−1) − 1, "
     "compounded daily to months, and excess returns over the 1-month T-bill in every regression. ",
     ("Share class: ", "b"),
     "one class per fund, the retail class an individual investor buys (FCNTX, FMAGX and TRBCX are no-load; AGTHX is "
     "Class A, which carries a front-end load of up to 5.75% that is not in its returns or expense ratio — treated as a "
     "sensitivity). Fund-level aggregation across classes is not possible from free data, and the retail class is the "
     "relevant one for our audience. ",
     ("Fees: ", "b"),
     "the expense ratio of each fiscal year (prospectus figure, net of waivers, 2010+; N-SAR expenses ÷ average net "
     "assets before), converted to monthly as fee/12; gross return = net return + fee/12. Turnover from the same filings.")
cl = clean["affected"]
para(("Cleaning (fund-months affected). ", "b"),
     f"{int(clean['rows after'].iloc[0]):,} fund-months → {int(clean['rows after'].iloc[1]):,} after aligning to the common "
     f"sample ({cl.iloc[1]}); duplicates: {cl.iloc[2]}; missing returns or factors: {cl.iloc[3]}. ",
     ("Distributions: ", "b"),
     f"we checked Yahoo’s distributions against the per-share distributions reported to the SEC (N-SAR item 73) and the "
     f"price move on each ex-date and corrected {cl.iloc[4]} (AGTHX’s 1993–95 distributions were recorded at half; a "
     f"spurious FCNTX payment in June 2002 added +5.5% to one month). After correction our returns match the funds’ "
     f"official N-PORT returns (2019+) to a median of {nport['median_abs_diff'].median():.3f} and a maximum of "
     f"{nport['max_abs_diff'].max():.2f} percentage points. ",
     ("Missing fees, turnover and flows: ", "b"),
     f"{clean.loc[clean.index.str.startswith('5a'), 'affected'].iloc[0]} active fund-months have no fee filing for that "
     f"year (2016, 2023, AGTHX 2006–09) and {clean.loc[clean.index.str.startswith('5b'), 'affected'].iloc[0].split(' ')[0]} "
     f"no turnover; both are interpolated between adjacent years or carried from the nearest year. "
     f"{clean.loc[clean.index.str.startswith('6.'), 'affected'].iloc[0].split(' ')[0]} fund-months have no reported "
     f"sales/redemptions (mainly Apr 2018–Jun 2019, between the last N-SAR and first N-PORT filing; see §5). ",
     ("Outliers: ", "b"),
     f"{clean.loc[clean.index.str.startswith('7.'), 'affected'].iloc[0]} months with |return| > 25% and "
     f"{clean.loc[clean.index.str.startswith('7b'), 'affected'].iloc[0]} Carhart residuals beyond 4 s.d. (flagged, kept). We do ",
     ("not winsorize", "b"),
     " the baseline: these are diversified portfolios, so extreme months (Oct 2008, Mar 2020) are real market moves, and "
     "clipping them would distort beta and alpha. A 1%/99% winsorization is a sensitivity check (§6).")

heading("3. Factor-model alphas (net of fees)")
caption("Table 1. Net-of-fee alphas, 1993-07 to 2025-12 (390 months). α and tracking error (TE = s.d. of the regression residual, "
        "Ch. 10 sl. 17–18) in %/yr (monthly × 12, × √12, sl. 29); t-statistics (Newey-West, 6 lags) in parentheses; IR = α/TE.")
hdr1 = ["Fund"] + [m for m in ["CAPM", "", "", "", "Fama-French 3", "", "", "", "Carhart 4", "", "", ""]]
hdr2 = [""] + ["α (t)", "TE", "IR", "R²"] * 3
rows = [hdr1, hdr2]
for f in ACTIVE:
    r = [f]
    for m in ["CAPM", "FF3", "Carhart"]:
        x = t1.loc[(f, m)]
        r += [at(x["alpha"], x["t"]), f"{x['TE']:.2f}", f"{x['IR']:.2f}", f"{x['R2']:.2f}"]
    rows.append(r)
tb = table(rows, [0.7] + [0.85, 0.42, 0.42, 0.42] * 3, header_rows=2)
for c0 in (1, 5, 9):
    merge_header(tb, 0, c0, c0 + 3)
note("Carhart loadings (net): market 0.92–1.06; SMB −0.15 to +0.11; HML −0.09 to −0.25 (growth tilt); UMD +0.17 for FCNTX, ≈0 for the others.")
para(("How alpha changes as factors are added. ", "b"),
     f"All four funds load negatively on HML (they hold growth stocks), and value beat growth on average over the sample "
     f"(HML premium {num('hml_premium_%'):+.1f}%/yr). The FF3 benchmark therefore expects a growth fund to earn ",
     ("less", "i"), " than the CAPM does, so adding SMB and HML ", ("raises", "b"),
     f" every fund’s alpha (e.g. AGTHX {a('AGTHX','CAPM'):+.2f} → {a('AGTHX','FF3'):+.2f}%, TRBCX "
     f"{a('TRBCX','CAPM'):+.2f} → {a('TRBCX','FF3'):+.2f}%) and cuts tracking error: these managers beat the market "
     f"despite a style that lagged. Adding momentum (premium {num('umd_premium_%'):+.1f}%/yr) matters only for "
     f"Contrafund: its UMD loading of 0.17 means part of its FF3 alpha ({a('FCNTX','FF3'):+.2f}%) was momentum "
     f"exposure, and its Carhart alpha falls to {a('FCNTX'):+.2f}% — as in the Berkshire example (Ch. 10, sl. 26–40) and "
     f"Carhart (1997) (Ch. 16, sl. 23), where momentum explains much of the apparent skill of winning funds. Magellan’s alpha is negative under every model.")

heading("4. Fees: gross vs net alpha, implementable benchmark, and fee level")
caption("Table 2. Carhart gross and net alpha, alpha against the constrained index-fund benchmark, and fees (all %/yr; t in parentheses).")
rows = [["Fund", "Avg fee", "2025 fee", "Gross α", "Net α", "Index-bench. α", "Benchmark weights S&P / Small / Value / Growth (%)",
         "Bench. fee", "Verdict (Carhart)"]]
for f in ACTIVE:
    x, b = t2.loc[f], bench.loc[(f, "net")]
    w = " / ".join(f"{b[c]*100:.0f}" for c in ["w_VFINX", "w_NAESX", "w_VIVAX", "w_VIGRX"])
    v = "Justified" if x["verdict"] == "Justified" else "Not justified"
    rows.append([f, f"{x['fee_avg']:.2f}", f"{x['fee_2025']:.2f}", at(x["gross_alpha"], x["t_gross"]),
                 at(x["net_alpha"], x["t_net"]), at(x["index_alpha"], x["t_index"]), w, f"{x['bench_fee']:.2f}", v])
table(rows, [0.6, 0.5, 0.5, 0.85, 0.85, 0.9, 1.45, 0.5, 0.95])
note("Gross return = reported return + that year’s expense ratio/12 (Wermers 2000; Fama-French 2010; Ch. 16, sl. 20–21). Index benchmark "
     "(Ch. 10, sl. 31–34): weights ≥ 0 summing to 1 on VFINX, NAESX, VIVAX, VIGRX plus an intercept (net returns of the index funds, so the benchmark is fully implementable). "
     "Benchmark fee = weighted average expense ratio of the index funds over the sample.")
para(("Gross vs net. ", "b"),
     f"Three funds show a positive gross alpha of {t2.loc[['FCNTX','TRBCX','AGTHX'],'gross_alpha'].min():.1f}–"
     f"{t2.loc[['FCNTX','TRBCX','AGTHX'],'gross_alpha'].max():.1f}%/yr (t ≈ 2.3–2.8): evidence of stock-picking skill. "
     f"Fees of {t2.loc[['FCNTX','TRBCX','AGTHX'],'fee_avg'].min():.1f}–{t2.loc[['FCNTX','TRBCX','AGTHX'],'fee_avg'].max():.1f}% "
     f"consume about a third of it, leaving net alphas of +1.3 to +1.7% that are positive but only marginally significant "
     f"(t = 1.4–1.9). Magellan has no gross alpha to share ({t2.loc['FMAGX','gross_alpha']:+.2f}%), so any fee is unjustified. ",
     ("Implementable benchmark. ", "b"),
     f"The constrained regression puts 53–86% of each fund in the Vanguard Growth Index; a mix of index funds costing "
     f"{t2['bench_fee'].min():.2f}–{t2['bench_fee'].max():.2f}%/yr reproduces 83–94% of each fund’s variance. Against "
     f"this benchmark, net alphas shrink to {t2.loc['TRBCX','index_alpha']:+.2f}% (TRBCX), "
     f"{t2.loc['AGTHX','index_alpha']:+.2f}% (AGTHX) and {t2.loc['FCNTX','index_alpha']:+.2f}% (FCNTX), none "
     f"significant (t ≤ {t2['t_index'].max():.1f}). The same exposures cost {fee_lo:.2f}–{fee_hi:.2f}%/yr less through index funds, so "
     f"most of what investors pay for is growth exposure they could buy cheaply. ",
     ("Fee level and turnover. ", "b"),
     f"The 2025 fees (0.59–0.74%) sit at the {ordinal(feep.loc[ACTIVE,'percentile_all_US_fund_classes'].min())}–"
     f"{ordinal(feep.loc[ACTIVE,'percentile_all_US_fund_classes'].max())} percentile of all US fund share classes (SEC data; median {num('fee_dist_median_%'):.2f}%) and below the ICI average equity-fund fee "
     f"of 1.09% (Ch. 15, sl. 36), but well above the 0.40% asset-weighted average and the index funds’ 0.14–0.17% (3rd–4th "
     f"percentile; Fig. 2a). ", ("Across funds, ", "i"),
     f"the higher-fee pair ({fg.loc['higher-fee pair','funds']}, {fg.loc['higher-fee pair','avg fee']:.2f}%) earned "
     f"{fg.loc['higher-fee pair','avg gross alpha']:.2f}% gross alpha vs {fg.loc['lower-fee pair','avg gross alpha']:.2f}% "
     f"for the lower-fee pair ({fg.loc['lower-fee pair','avg fee']:.2f}%), more than covering the extra fee — but only "
     f"because of Magellan; the cheapest fund (AGTHX) earned as much as the dearest. ", ("Within funds ", "i"),
     f"(Carhart 1997; Ch. 16, sl. 22) we regress each fund-year’s abnormal return on its fee and "
     f"turnover (113 fund-years with observed data). Higher-fee years did ", ("not", "b"),
     f" deliver less gross performance — the fee coefficient is positive but insignificant once we control for a time "
     f"trend (fees and alphas both fell over 1993–2025; t = {trend['t_fee']:.1f}) — but turnover hurts: each 100 points of "
     f"turnover costs {abs(trend['b_turnover'])*100:.1f}%/yr of gross alpha (t = {trend['t_turnover']:.1f}), consistent "
     f"with trading costs. With four funds, neither comparison is a strong test of whether higher fees buy more skill.")

doc.add_picture(str(OUT / "fig2_fees_flows.png"), width=Inches(7.1))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
note("Figure 2. (a) 2025 expense ratios of all US mutual fund share classes (SEC), with our funds, VFINX and the ICI equity average. "
     "(b) Average monthly flow (% of TNA) by quintile of the fund’s past 12-month return relative to the S&P 500 index fund.")

heading("5. Persistence, flows and Berk and Green (2004)")
caption("Table 3. Carhart alpha (%/yr, t) in each half of the sample, and fund size (TNA, $bn).")
rows = [["Fund", "Gross α 1993–2009", "Net α 1993–2009", "Gross α 2009–2025", "Net α 2009–2025", "TNA start", "TNA peak", "TNA 2025"]]
for f in ACTIVE:
    h = t3.loc[f]
    rows.append([f, at(h[("first half", "gross_alpha")], h[("first half", "t_gross")]), at(h[("first half", "net_alpha")], h[("first half", "t_net")]),
                 at(h[("second half", "gross_alpha")], h[("second half", "t_gross")]), at(h[("second half", "net_alpha")], h[("second half", "t_net")]),
                 f"{size.loc[f,'first_tna_bn']:.2f}" if size.loc[f, "first_tna_bn"] < 1 else f"{size.loc[f,'first_tna_bn']:.1f}", f"{size.loc[f,'peak_tna_bn']:.0f}", f"{size.loc[f,'last_tna_bn']:.0f}"])
table(rows, [0.6, 1.05, 1.05, 1.05, 1.05, 0.65, 0.65, 0.65])
note("Halves: 1993-07 to 2009-09 and 2009-10 to 2025-12 (195 months each).")
para(("Persistence (Ch. 16, sl. 23). ", "b"),
     f"The ranking of gross alphas barely survives from the first half to the second (Spearman ρ = "
     f"{num('persistence_spearman_halves'):.2f}, n = 4). Within funds, a fund’s gross alpha over one 36-month block "
     f"predicts only {num('persistence_block_slope'):.2f} of its next block’s (t = {num('persistence_block_t'):.1f}, "
     f"36 pairs): little persistence, as in Carhart (1997). Magellan is persistently bad; AGTHX and TRBCX lost most of "
     f"their alpha in the second half. ",
     ("Flows. ", "b"),
     f"TNA is reported only semi-annually (N-SAR) or quarterly (N-PORT), so we build monthly TNA by rolling "
     f"TNA(t−1)(1+r(t)) + reported net sales forward from each reported value and spreading any gap to the next reported "
     f"value evenly (median gap {num('tna_rollforward_median_gap_pct'):.1f}%; {agthx_gap['gap_pct']:+.0f}% over AGTHX’s "
     f"{int(agthx_gap['months'])}-month gap when its assets exceeded the N-SAR field). The gap is the formula below "
     f"applied to two reported TNAs minus SEC-reported net sales, so it also validates the flow data. Flows are then "
     f"flow(t) = TNA(t) − TNA(t−1)(1+r(t)) (Ch. 16, sl. 26). Regressing monthly flow (% of TNA, winsorized 1/99, fund fixed effects, "
     f"Newey-West) on the past 12-month return gives a slope of {fl1.iloc[0]:.2f} (t = {fl1.iloc[1]:.1f}): a fund 10 "
     f"points ahead attracts about {fl1.iloc[0]*0.1*12:.1f}% of assets in extra inflows per year, and the worst past "
     f"performers suffer clear outflows (Fig. 2b). ",
     ("Berk and Green (Ch. 16, sl. 32–33). ", "b"),
     f"The data fit their story well. Gross alphas are positive for three funds (skill exists), investors chase "
     f"performance, and the funds grew enormously — AGTHX from ${size.loc['AGTHX','first_tna_bn']:.0f}bn to "
     f"${size.loc['AGTHX','last_tna_bn']:.0f}bn, TRBCX to ${size.loc['TRBCX','peak_tna_bn']:.0f}bn. As they grew, alpha "
     f"fell: across 36-month blocks, gross alpha declines by {abs(num('berk_green_slope')):.2f}%/yr per log-unit of TNA "
     f"(t = {num('berk_green_t'):.1f}, fund fixed effects), and in 2009–2025 net alpha is about zero or negative for "
     f"every fund except Contrafund (Fig. 1). Magellan is the classic case: after peaking near "
     f"${size.loc['FMAGX','peak_tna_bn']:.0f}bn around 2000, poor performance drove assets down to "
     f"${size.loc['FMAGX','last_tna_bn']:.0f}bn.")

doc.add_picture(str(OUT / "fig1_rolling_alpha_tna.png"), width=Inches(7.0))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
note("Figure 1. Rolling 36-month Carhart alpha, gross (grey) and net (blue), %/yr, with fund TNA ($bn, shaded).")

heading("6. Sensitivity of the verdict")
caption("Table 4. Net alpha (%/yr) under alternative assumptions; ✓ = fee justified (gross α > 0 and net α ≥ 0), ✗ = not justified.")
cols = list(sens.columns)
nice = {"Baseline Carhart": "Baseline Carhart", "FF3": "FF3 model", "Index-fund benchmark": "Index-fund benchmark",
        "Carhart, first half": "1st half 1993–2009", "Carhart, second half": "2nd half 2009–2025",
        "Winsorized 1/99": "Winsorized 1%/99%", "Rolling 36m: % windows net α≥0 (median α)": "Rolling 36m: % windows net α≥0 (median)",
        "AGTHX with 5.75% load (10y)": "AGTHX incl. 5.75% load (10-yr hold)"}
rows = [["Fund"] + [nice[c] for c in cols]] + [[f] + list(sens.loc[f]) for f in ACTIVE]
table(rows, [0.6, 0.78, 0.7, 0.85, 0.82, 0.82, 0.8, 1.0, 0.93], size=7.5)
para(f"Two assumptions change verdicts. ", ("Sub-periods: ", "b"),
     f"TRBCX’s and AGTHX’s fees were justified in 1993–2009 but not in 2009–2025, when their gross alpha "
     f"({t3.loc[['TRBCX','AGTHX'],('second half','gross_alpha')].min():.2f}–"
     f"{t3.loc[['TRBCX','AGTHX'],('second half','gross_alpha')].max():.2f}%) fell below their fee. ", ("Rolling windows: ", "b"),
     f"net alpha is non-negative in only {roll_lo}–{roll_hi}% of 36-month windows for the three good funds — a three-year track record is close to a coin flip. The other checks leave the "
     f"verdict unchanged: the FF3 model and winsorizing (which raises alphas by trimming crash months) keep three funds "
     f"justified; the index-fund benchmark keeps the signs but makes every net alpha insignificant; and AGTHX’s load, "
     f"spread over a 10-year holding, costs {num('agthx_load_drag_%'):.2f}%/yr but leaves its full-sample net alpha "
     f"positive (over a 3-year holding the load costs {load3:.1f}%/yr and net alpha turns slightly negative). Magellan is unjustified under every assumption.")

heading("7. Conclusions and fee design")
para(("Contrafund — justified (most robust). ", "b"),
     "Positive gross and net alpha in every specification and both halves, despite growing to $176bn; part of its CAPM "
     "alpha is momentum, and its net alpha vs index funds is not significant. ",
     ("Blue Chip Growth and Growth Fund of America — justified over 1993–2025, not since 2009. ", "b"),
     "Both earned real gross alpha early, attracted large inflows and are now close to expensive growth index funds. ",
     ("Magellan — not justified. ", "b"), "Negative gross alpha in every test. ",
     ("For retail investors and advisors: ", "b"),
     "even the best of these funds delivered net alphas that are statistically indistinguishable from zero against a "
     "0.2% index-fund mix, past performance barely persists, and the funds that did well grew until their edge "
     "disappeared. Paying 0.6–0.8% for a large growth fund is hard to justify ex ante; a growth or total-market index "
     "fund is the default, and an active fund needs a fee structure that only pays for alpha.")
para(("Fee design. ", "b"),
     "A flat fee on assets pays the manager for beta and growth exposure that costs 0.2% elsewhere, and rises "
     "automatically as flows chase past returns — exactly the Berk–Green mechanism that hands the rents to the manager. "
     "An index-relative bonus is no better: a growth fund benchmarked to the S&P 500 (as Fidelity’s performance "
     "adjustment is) earns it whenever growth beats the market, with no skill (Ch. 15, sl. 23–28). We recommend that "
     "advisors favour, and that funds offer, ", ("a low base fee near the cost of the index replication (≈0.2–0.25%) plus a "
     "symmetric 40-Act fulcrum fee (Ch. 16, sl. 11; Ch. 15, sl. 15–16) measured against a factor or style benchmark", "b"),
     " (Ch. 15, sl. 27) — here, the constrained index-fund mix of Table 2 — so the manager is paid only for alpha against exposures the "
     "investor could buy cheaply, and refunds part of the fee when alpha is negative. Absent such a fee, buy the index fund.")
para(("Caveats. ", "b"),
     "Survivorship and selection (Ch. 16, sl. 17–19): we chose four famous funds that still exist, so the sample is biased "
     "toward winners (funds that failed were merged away); Magellan shows even famous funds can fail. Incubation (Ch. 16, "
     "sl. 29–30): TRBCX’s first months follow its launch, when small new funds often look unusually good. Benchmark choice: factors are not costless "
     "portfolios, which is why we also use index funds; the index benchmark ignores taxes and trading costs. Sample "
     "period: 1993–2025 favoured large growth stocks, which flatters CAPM alphas. Data: free sources rather than CRSP — "
     "returns were checked against SEC filings, but fees before 2010 are estimates from N-SAR (fund-level, all share "
     "classes), and with four funds cross-sectional tests have little power.")
para(("Sources: ", "b"), "Yahoo Finance (via yfinance); Kenneth R. French Data Library; SEC EDGAR (Forms N-SAR, N-PORT, "
     "prospectus risk/return summary data sets); ICI averages as cited in lecture. Software: Python 3.11 with pandas, NumPy, "
     "SciPy, statsmodels, Matplotlib, yfinance and python-docx. Code: pull_data.py, mutualfunds.ipynb, make_report.py.",
     size=8)

doc.save(HERE / "report.docx")
print("saved", HERE / "report.docx")
