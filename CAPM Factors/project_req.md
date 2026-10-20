
3

Automatic Zoom
CFM 301: Financial Data Analytics
Course Projects — Instructions
Over the term you will complete a series of hands-on projects that build your ability to source, clean,
and analyze financial data, and to turn that analysis into an investment decision. Each project builds on
the tools covered in the corresponding module. Beyond the objective stated for each project, the choice
of data sample, asset universe, and implementation details is left to you — document and justify your
choices.
Purpose of the Projects
The main objective of each project is to assess how well your group has grasped the class material and
how correctly you apply it. Each project lists the techniques from class you are expected to apply (e.g.,
constructing returns correctly, cleaning the data, testing how sensitive your results are to your
assumptions), and grading follows that list. If a technique does not apply to your setting, explain why in
the report; a technique skipped without explanation is treated as missing.
Economic Question, Motivation & Audience
Crucially, every project needs to have a specific economic goal or research question. It is everyone's job
in the group to come up with and refine this question.
Formulating a clear, well-motivated economic question is what sets CFM apart from more technical
programs such as FARM (Mathematics/Financial Analysis and Risk Management). While technical rigor is
essential, CFM projects must bridge quantitative techniques with real-world financial decision-making
and economic insight.
Intended audience: State who your analysis is for and who would be interested in funding it (e.g., a
government agency, the general public, mutual fund or pension fund managers). Your audience should
shape how you frame the question, which assumptions are reasonable, and how you word your
conclusion.
Example: In a recent discussion on capital allocation
(https://www.youtube.com/watch?v=KCt9a9AnNfk), Mark Carney mentioned that global capital is
under-weighted in the Canadian market relative to its benchmark. Is that claim empirically true? A
project could conduct a quantitative portfolio optimization exercise specifically designed to test this
hypothesis—evaluating whether an under-allocation to Canadian assets is justified by risk-return trade-
offs or represents an unexploited market inefficiency. Possible audiences: federal policymakers or
Canadian pension fund managers.
Reproducibility
The instructor must be able to run your code on the files you submit and get the numbers in your report.
Reproducibility is a separate item in every project rubric. Before you submit:
• Submit the data files your code needs, but include only the data you actually use (e.g., the assets,
variables, and sample period in your analysis), not the whole dataset you downloaded. Your code
should run on these files without a WRDS login, an internet connection, or any manual step (no
copy-pasting between files, no editing in Excel).
• Use relative file paths (e.g., data/crsp_monthly.csv), never paths on your own computer (e.g.,
C:\Users\...\Desktop).
• Include a short README listing the language and version, required packages (with versions), and
which files to run in what order.
• Make sure your code reproduces every table and figure in the report from a clean start (for
notebooks, use "Restart & Run All").
• Have a group member who did not write the code run your submission from a new folder, start to
finish.
If your results cannot be reproduced from your submission, the reproducibility points are lost, and
results that cannot be verified may not receive credit in other rubric categories.
Groups, Submissions & In-Class Presentations
These are group projects. You will work in groups of 3–5 students; there are 11 groups in total. Group
membership stays the same for all projects.
Submission: Upload your report, code, data files, and README to the project's LEARN Dropbox folder no
later than 2 days before the presentation date. Upload your presentation slides to the separate LEARN
Dropbox folder for slides no later than 1 hour before the presentation session begins.
Presentation: Your group will deliver a 5–6 minute in-class presentation of your own project: your
economic question and audience, your data and methodology, your results, and your economic
conclusion. Across the 6 projects over the term, every student in the group must present in class at least
once.
Attendance and individual questions: After your presentation, the instructor will ask every member of
your group at least one question. All group members must therefore attend their group's presentation
session. A member who is absent cannot be asked a question and will receive a lower presentation
grade for that project.
Peer review: For each project, your group is paired with a different group. Read your paired group's
report after the report deadline, and during their presentation ask at least one substantive question or
make one substantive comment on their methodology, assumptions, or conclusions.
Each project is worth 15 points total: 12 points for your own project (analysis, report, and code) and 3
points for your in-class presentation and peer review — see the grading rubric for each project below.
Project 2: Finding and Testing a Factor
Objective
Propose at least one factor — beyond the market, size (SMB), value (HML), and momentum (UMD)
factors covered in class — that you believe helps explain the cross-section of asset returns, and provide
empirical evidence for it. Your factor can be a macro factor (e.g., inflation, growth, volatility) or a
dynamic/style factor (e.g., quality, illiquidity, low volatility, credit risk) constructed as a long-short
portfolio.
This project is primarily a test of whether your group can correctly apply the tools covered in class:
constructing returns, cleaning financial data, building a factor, running and interpreting factor
regressions, testing how sensitive your results are to your assumptions, and interpreting your results in
light of the rational vs. behavioral theories and the notions of market efficiency covered in class. Each of
these is listed below and graded.
Requirements
1. Propose one or two candidate factors and give an economic rationale for why exposure to it
should earn a risk premium (i.e., how it defines "bad times," per the multifactor framework
covered in class). Identify your intended audience (e.g., quantitative fund managers deciding
whether to tilt toward the factor, or pension funds evaluating factor-based products).
2. Construct or source a time series for your factor and a set of test assets (e.g., individual stocks or
portfolios sorted on a characteristic related to your factor) using CRSP and/or Compustat.
3. Construct returns correctly. Returns for your test assets and for each leg of a long-short factor
must be total returns that include dividends and are adjusted for stock splits and other
distributions, as covered in class. For example, CRSP's RET includes dividends while RETX does
not, and CRSP's raw price (PRC) is not adjusted for splits (use CFACPR if you compute returns
from prices). If you use Compustat, apply the adjustment factor and include dividends. State
which variable or formula you used and the return frequency.
4. Clean the data using the methods covered in class. At a minimum, address missing values,
duplicate observations, and outliers. Winsorize returns and firm characteristics used to sort
stocks (state the cut-offs, e.g., 1st/99th percentile) or explain why winsorizing is not appropriate
for your sample. Report how many observations each step affects.
5. Test your factor with OLS: regress test-asset returns on your factor (and the market factor as a
control), and report the estimated loadings, t-statistics, and R².
6. Compare the explanatory power of your factor to a standard benchmark model (e.g., CAPM, or a
Fama-French style multifactor model) and state whether your factor adds explanatory power.
7. Test how sensitive your results are to your assumptions. Re-run your main tests under at least
two alternative assumptions, such as:
– a different sample period or sub-periods (e.g., excluding a crisis period, or before vs. after
the factor became widely known),
– a different way of forming the factor (e.g., terciles vs. quintiles, equal- vs. value-weighted
legs),
– a different benchmark model, or
– a different winsorization cut-off.
Report whether your factor's premium, significance, and added explanatory power hold up. A
compact table is sufficient.
8. Discuss whether the evidence for your factor is better described as rational (risk-based) or
behavioral, referencing the theories covered in class. Support your argument with evidence —
for example, how your factor performs during bad times such as recessions or market
downturns.
9. Implications for market efficiency. Using the notions of market efficiency covered in class,
discuss what your results imply for the efficient market hypothesis:
– Which form of efficiency (weak, semi-strong, or strong) does your factor speak to, given
the information used to construct it?
– If your factor earns a premium, is it consistent with an efficient market (compensation for
bearing risk in bad times), or does it point to an inefficiency?
– If it points to an inefficiency, why has it not been traded away (e.g., costly information or
trading, barriers to the entry of capital), and is it consistent with a "near-efficient" market
in the sense of Grossman and Stiglitz (1980)?
Explain what your conclusion means for your intended audience (e.g., can they earn the
premium after costs, and should they?).
Deliverables
• Uploaded to the LEARN Dropbox 2 days before the presentation date:
– Code (script or notebook) that reproduces your results end-to-end, plus a README (see
Reproducibility above).
– The raw data files you actually used, trimmed to just what's needed to run your code (not
the full downloaded dataset), so your submission runs end-to-end without extra downloads.
– A report (max. 4 pages) containing:
◦ Factor definition, construction, economic rationale, and intended audience.
◦ Data description: source, universe, sample period, return construction (dividends,
splits), and cleaning steps (including winsorization).
◦ Regression table(s) with coefficients, t-statistics, and R².
◦ Sensitivity analysis: how your results change under at least two alternative
assumptions.
◦ Interpretation: does the factor earn a premium, does it add power beyond the
benchmark model, is the evidence more rational or behavioral, what does it imply for
market efficiency, and what does this mean for your intended audience?
• Uploaded to the LEARN Dropbox for slides 1 hour before the presentation session: your
presentation slides.
• In class: a 5–6 minute presentation of your own project, with every group member present to
answer the instructor's questions, and at least one prepared question or comment during your
paired group's presentation.
Grading Rubric (15 pts)
Criterion Points
Factor clearly defined with a sound economic rationale and intended audience 2
Data sourcing, factor construction, return construction (dividends, splits), and
cleaning (incl. winsorization) correctly done and documented
2
Regressions correctly specified and reported (coefficients, t-stats, R²) 2
Comparison to a benchmark model included and correctly interpreted 1
Sensitivity analysis: at least two alternative assumptions tested and their effect on
the conclusion discussed
2
Interpretation well argued and supported by evidence: rational vs. behavioral
explanation, implications for market efficiency, and relevance to the intended
audience
2
Reproducibility: submitted code and data reproduce the reported results without
modification
1
In-class presentation: 5–6 min, clearly explaining your question, methodology,
and results; each member present and answering the instructor's questions
(graded individually; absent members receive a lower grade)
2
Peer review: substantive question or comment on the paired group's project
during their presentation
1
Note: For all projects, keep your data pull, cleaning steps, and analysis reproducible from the raw source
data. Cite any external packages or data sources you use. Every student must present at least once
across the 6 project presentation sessions during the term.