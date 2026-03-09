Here’s how the picking equation pipeline works, based on run_pipeline.py:

It’s the main entry point for the equation‑fitting workflow. The full pipeline runs 4 steps in order: fit all equations, consolidate coefficients, build the Excel workbook, and generate the LaTeX report + Overleaf zip.
Step 1 (run_fitting): calls fit_all_equations.run_all_fits() to fit all 11 equations to both Contractility and O2 data and returns the fit results.
Step 2 (run_consolidation): calls consolidate.consolidate_all_equations() to gather and combine coefficient CSVs.
Step 3 (run_excel_creation): calls create_excel.create_all_equations_excel() to generate all_equations_coefficients.xlsx.
Step 4 (run_report_generation): calls generate_report.generate_full_report() to build the LaTeX report and an Overleaf‑ready zip.
It validates inputs up front using config.validate_paths() (unless you pass --no-validate). You can run the whole pipeline (default) or individual steps with flags (--fit, --consolidate, --excel, --report). Output paths are printed at the end, including the coefficients directory, Excel file, and report/zip if generated.

Here’s what the fitting is based on and where to change bounds/initial conditions.

What the fitting is based on

Data source: Excel sheets in Heart_Contractility_Averaged.xlsx and O2_Mean_Averaged.xlsx, plus drug_Cmax.csv.
Parsing rules: fit_all_equations.py reads each sheet, treats column 0 as time and other columns as concentrations (parsed from the header), filters to 0 <= time <= 96 and for O2 keeps response < 200, and drops sheets with <25 valid points.
Model equations: functions in equations.py referenced by name via EQUATION_FUNCTIONS.
Optimization: SciPy curve_fit with bounds and multi‑start initial guesses; concentration is normalized by Cmax before fitting.
Where to modify boundary conditions (parameter bounds and data filtering)

Parameter bounds:
Global base bounds by response type: config.py in get_bounds(...).
Equation‑specific bounds: fit_all_equations.py in get_param_bounds(...).
Data “boundary conditions” (filtering rules):
Time window 0–96 and O2 cap <200: fit_all_equations.py in parse_excel_data(...).
Minimum required points (<25 is skipped): fit_all_equations.py in parse_excel_data(...).
Excluded drugs/sheets: config.py in EXCLUDED_DRUGS and SKIP_SHEETS.
Where to modify initial conditions (initial parameter guesses)

Default starting guesses per equation: fit_all_equations.py in get_initial_guess(...).
Special data‑driven initialization for pkpd_elimination: also in get_initial_guess(...).
Multi‑start variations (how guesses are perturbed): fit_all_equations.py in fit_single_drug(...).