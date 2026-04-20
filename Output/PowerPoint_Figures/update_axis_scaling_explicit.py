"""Rewrite all Axis_Scaling_Reference.xlsx files with explicit values.

No "auto", no vague "drug names" — every min/max is a real number,
every tick list is spelled out, and heatmap colorbar values are added.
"""
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIGS_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures'

# ============================================================
# SHARED CONSTANTS (actual, explicit values)
# ============================================================

DRUGS_25 = ['Amiodarone', 'Bortezomib', 'Chlorpromazine', 'Cobimetinib',
            'Dactinomycin', 'Daunorubicin', 'Doxorubicin', 'Epirubicin',
            'Erlotinib', 'Etomoxir', 'Gemcitibine', 'Ibrutinib', 'Ibuprofen',
            'Isoproterenol', 'Mexiletine', 'Nifedipine', 'Panobinostat',
            'Plicamycin', 'Rosiglitazone', 'Sotalol', 'Sunitinib',
            'Vandetanib', 'Vincristine', 'Vioxx', 'Vorinostat']

FEATURES_14 = ['R0_Contractility', 'Emax_Contractility', 'kappa_Contractility',
               'n_Contractility', 'm_Contractility', 'tau_Contractility',
               'k_elim_Contractility', 'R0_O2', 'Emax_O2', 'kappa_O2',
               'n_O2', 'm_O2', 'tau_O2', 'k_elim_O2']

EQUATIONS_12 = ['Cumulative Exposure', 'Recovery Model', 'Gaussian-Hill Hybrid',
                'Bivariate Gaussian', 'Gaussian Ridge', 'Adaptive Response',
                'Modified Hill', 'Dual Hill Hormesis', 'Biphasic Response',
                'PKPD Elimination', 'Hormesis Hill', 'Dual Exponential']

# Heatmap colormap: blue -> white -> red, linear
HEATMAP_BLUE = '#123BFF'
HEATMAP_RED = '#FF2908'

# ============================================================
# FIGURE 2
# ============================================================

FIG_2 = [
    {
        'Panel': 'd', 'Filename': 'Fig_2d.png',
        'X_Label': 'SNR Bucket Midpoint', 'Y_Label': 'Measurement Count',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': -1.0, 'X_Max': 10.0, 'Y_Min': 0, 'Y_Max': 376347,
        'X_Ticks': '-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10',
        'Y_Ticks': '0, 50000, 100000, 150000, 200000, 250000, 300000, 350000, 400000',
        'Original_Width_in': 9.89, 'Original_Height_in': 5.89,
        'Axisless_Width_in': 9.14, 'Axisless_Height_in': 5.02,
        'Axisless_Width_px': 5481, 'Axisless_Height_px': 3010, 'DPI': 600,
        'Notes': 'Stacked bar: count per SNR bucket (101 buckets, 0.1 wide). Red threshold line at SNR=0.4.',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'g', 'Filename': 'Fig_2g_Epirubicin_O2.png',
        'X_Label': 'Time from Exposure (h)', 'Y_Label': 'Oxygen (% Air)',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 100, 'Y_Min': 0, 'Y_Max': 75,
        'X_Ticks': '0, 20, 40, 60, 80, 100',
        'Y_Ticks': '0, 10, 20, 30, 40, 50, 60, 70',
        'Original_Width_in': 9.13, 'Original_Height_in': 6.40,
        'Axisless_Width_in': 10.02, 'Axisless_Height_in': 7.02,
        'Axisless_Width_px': 6010, 'Axisless_Height_px': 4210, 'DPI': 600,
        'Notes': 'Epirubicin O2 averaged, 9 concentrations (12/6/3/1.5/0.75/0.38/0.19/0.094 mM + offset-shifted edges)',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'h', 'Filename': 'Fig_2h_Epirubicin_TC50.png',
        'X_Label': 'Epirubicin (mM)', 'Y_Label': 'Viability (%)',
        'X_Scale': 'log10', 'Y_Scale': 'linear',
        'X_Min': 0.05, 'X_Max': 20.0, 'Y_Min': -5, 'Y_Max': 105,
        'X_Ticks': '0.1, 1, 10',
        'Y_Ticks': '0, 20, 40, 60, 80, 100',
        'Original_Width_in': 3.80, 'Original_Height_in': 2.59,
        'Axisless_Width_in': 3.19, 'Axisless_Height_in': 2.10,
        'Axisless_Width_px': 1912, 'Axisless_Height_px': 1262, 'DPI': 600,
        'Notes': 'TC50=0.453 mM at 40h. 4PL sigmoid, wells excluded: {0,2,3,4,10,11,13,15}, 6 mM row dropped.',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'i', 'Filename': 'Fig_2i_Epirubicin_O2_Heatmap.png',
        'X_Label': 'Time from Exposure (h)',
        'Y_Label': 'Epirubicin Dose (mM, grouped by conc)',
        'X_Scale': 'linear', 'Y_Scale': 'categorical (wells sorted within conc)',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': '(row 0 = top conc)', 'Y_Max': '(row N = bottom)',
        'X_Ticks': 'time-point subset (~every 10th label displayed)',
        'Y_Ticks': '12, 6, 3, 1.5, 1, 0.75, 0.38, 0.19, 0.094  (19 wells total after dropping 0.38.1)',
        'Original_Width_in': 13.27, 'Original_Height_in': 6.75,
        'Axisless_Width_in': 10.28, 'Axisless_Height_in': 5.78,
        'Axisless_Width_px': 6170, 'Axisless_Height_px': 3467, 'DPI': 600,
        'Notes': 'LOWESS w=16, sorted wells ascending within conc. Colormap: #123BFF -> white -> #FF2908.',
        'Colorbar_Min': 0, 'Colorbar_White': 50, 'Colorbar_Max': 100,
        'Colorbar_Label': 'Oxygen (% Air) — actual data range 0 to 79.15 (never reaches pure red)',
    },
    {
        'Panel': 'j', 'Filename': 'Fig_2j_Mexiletine_Contractility.png',
        'X_Label': 'Time from Exposure (h)', 'Y_Label': 'Contractility (%)',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 100, 'Y_Min': 2.73, 'Y_Max': 11.12,
        'X_Ticks': '0, 20, 40, 60, 80, 100',
        'Y_Ticks': '3, 4, 5, 6, 7, 8, 9, 10, 11  (matplotlib auto on [2.73, 11.12])',
        'Original_Width_in': 9.89, 'Original_Height_in': 7.82,
        'Axisless_Width_in': 10.02, 'Axisless_Height_in': 7.02,
        'Axisless_Width_px': 6010, 'Axisless_Height_px': 4210, 'DPI': 600,
        'Notes': 'Mexiletine contractility averaged, 7 concs (20/10/5/2.5/1.25/0.625/0.156 mM). Shifted to global-avg start.',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'k', 'Filename': 'Fig_2k_Mexiletine_Waveforms.png',
        'X_Label': 'Time (s)', 'Y_Label': 'Contractility (stacked offsets, arbitrary units)',
        'X_Scale': 'linear', 'Y_Scale': 'linear (stacked with vertical offset per dose)',
        'X_Min': 0, 'X_Max': 7,
        'Y_Min': '-0.5 * spacing', 'Y_Max': '2.8 * spacing (spacing = 1.5 * max_ptp)',
        'X_Ticks': '0, 1, 2, 3, 4, 5, 6, 7',
        'Y_Ticks': 'none (y-axis ticks hidden; traces stacked)',
        'Original_Width_in': 9.89, 'Original_Height_in': 8.00,
        'Axisless_Width_in': 10.02, 'Axisless_Height_in': 8.00,
        'Axisless_Width_px': 6010, 'Axisless_Height_px': 4800, 'DPI': 600,
        'Notes': '3 doses stacked: Low=0.625 mM (plasma #fdb42f), Med=2.5 mM (plasma #cc4778), High=5.0 mM (plasma #9c179e). CubicSpline smoothed.',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'l', 'Filename': 'Fig_2l_Mexiletine_Contractility_Heatmap.png',
        'X_Label': 'Time from Exposure (h)',
        'Y_Label': 'Mexiletine Dose (mM, grouped by conc)',
        'X_Scale': 'linear', 'Y_Scale': 'categorical (wells sorted within conc)',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': '(row 0 = top conc)', 'Y_Max': '(row N = bottom)',
        'X_Ticks': 'time-point subset (~every 10th label displayed)',
        'Y_Ticks': '20, 10, 5, 2.5, 1.25, 0.625, 0.156  (14 wells after exclusions)',
        'Original_Width_in': 13.27, 'Original_Height_in': 6.75,
        'Axisless_Width_in': 10.28, 'Axisless_Height_in': 5.78,
        'Axisless_Width_px': 6170, 'Axisless_Height_px': 3467, 'DPI': 600,
        'Notes': 'LOWESS w=16, sorted ascending. Colormap: #123BFF -> white -> #FF2908. vmax auto = data max.',
        'Colorbar_Min': 0, 'Colorbar_White': 12.28, 'Colorbar_Max': 24.56,
        'Colorbar_Label': 'Contractility (%) — vmin=0, vmax=auto=24.56 (white at midpoint 12.28)',
    },
]

# ============================================================
# FIGURE 3
# ============================================================

FIG_3 = [
    {
        'Panel': 'a (Dactinomycin)', 'Filename': 'Fig_3a_Dactinomycin_O2_Heatmap.png',
        'X_Label': 'Time from Exposure (h)', 'Y_Label': 'Dactinomycin Dose (mM)',
        'X_Scale': 'linear (data 0-96h, axis ticks removed)',
        'Y_Scale': 'categorical (wells sorted within conc)',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': '(row 0 = top conc)', 'Y_Max': '(row N = bottom)',
        'X_Ticks': 'none (ax.set_xticks([]))',
        'Y_Ticks': '1.5, 1, 0.75, 0.375, 0.1875, 0.0938, 0.0469, 0.0234, 0.0117  (30 wells input, 7 rows removed: {1,8,12,16,20,24,27})',
        'Original_Width_in': 8.37, 'Original_Height_in': 8.32,
        'Axisless_Width_in': 8.37, 'Axisless_Height_in': 8.32,
        'Axisless_Width_px': 5019, 'Axisless_Height_px': 4991, 'DPI': 600,
        'Notes': 'figsize=(10,10) input, cropped to 8.37x8.32 in by bbox_inches="tight". LOWESS w=16 per well.',
        'Colorbar_Min': 0, 'Colorbar_White': 50, 'Colorbar_Max': 100,
        'Colorbar_Label': 'O2 (%) — vmin=0, vmax=100 explicit. Actual data range -2.80 to 78.91 (never reaches pure red).',
    },
    {
        'Panel': 'a (Nifedipine)', 'Filename': 'Fig_3a_Nifedipine_O2_Heatmap.png',
        'X_Label': 'Time from Exposure (h)', 'Y_Label': 'Nifedipine Dose (mM)',
        'X_Scale': 'linear (data 0-96h, axis ticks removed)',
        'Y_Scale': 'categorical (wells sorted within conc)',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': '(row 0)', 'Y_Max': '(row N)',
        'X_Ticks': 'none (ax.set_xticks([]))',
        'Y_Ticks': '8, 4, 2, 1, 0.5, 0.25, 0.125, 0.0623, 0  (22 wells input, 2 rows removed: {5,6})',
        'Original_Width_in': 8.37, 'Original_Height_in': 8.32,
        'Axisless_Width_in': 8.37, 'Axisless_Height_in': 8.32,
        'Axisless_Width_px': 5019, 'Axisless_Height_px': 4991, 'DPI': 600,
        'Notes': 'figsize=(10,10) input, cropped. LOWESS w=16 per well.',
        'Colorbar_Min': 0, 'Colorbar_White': 50, 'Colorbar_Max': 100,
        'Colorbar_Label': 'O2 (%) — vmin=0, vmax=100 explicit. Actual data range 1.92 to 61.33.',
    },
    {
        'Panel': 'a (Mexiletine)', 'Filename': 'Fig_3a_Mexiletine_O2_Heatmap.png',
        'X_Label': 'Time from Exposure (h)', 'Y_Label': 'Mexiletine Dose (mM)',
        'X_Scale': 'linear (data 0-96h, axis ticks removed)',
        'Y_Scale': 'categorical (wells sorted within conc)',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': '(row 0)', 'Y_Max': '(row N)',
        'X_Ticks': 'none (ax.set_xticks([]))',
        'Y_Ticks': '20, 10, 5, 2.5, 2, 1.25, 0.625, 0.313, 0.156  (22 wells input, 5 rows removed: {2,3,9,13,20})',
        'Original_Width_in': 8.36, 'Original_Height_in': 8.32,
        'Axisless_Width_in': 8.36, 'Axisless_Height_in': 8.32,
        'Axisless_Width_px': 5017, 'Axisless_Height_px': 4991, 'DPI': 600,
        'Notes': 'figsize=(10,10) input, cropped. LOWESS w=16 per well.',
        'Colorbar_Min': 0, 'Colorbar_White': 50, 'Colorbar_Max': 100,
        'Colorbar_Label': 'O2 (%) — vmin=0, vmax=100 explicit. Actual data range -9.25 to 64.40.',
    },
    {
        'Panel': 'b (Mexiletine surface)', 'Filename': 'Mexiletine_Eq7_biphasic_response.png',
        'X_Label': 'Time (h)', 'Y_Label': 'Dose Ratio (C0/Cmax)',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': 0, 'Y_Max': 2,
        'X_Ticks': '0, 20, 40, 60, 80  (plus auto)',
        'Y_Ticks': '0.0, 0.5, 1.0, 1.5, 2.0',
        'Original_Width_in': 7.81, 'Original_Height_in': 7.74,
        'Axisless_Width_in': 7.81, 'Axisless_Height_in': 7.74,
        'Axisless_Width_px': 4686, 'Axisless_Height_px': 4644, 'DPI': 600,
        'Notes': ('3D surface (equation: biphasic_response). Z-axis = O2 response. '
                  'View angle elev=25, azim=-158. Shares colorbar with Nifedipine/Dactinomycin surfaces.'),
        'Colorbar_Min': 0, 'Colorbar_White': '(midpoint)', 'Colorbar_Max': 100,
        'Colorbar_Label': 'Z-axis (O2 response %) shared across 3 surfaces. Colormap: turbo.',
    },
    {
        'Panel': 'b (Nifedipine surface)', 'Filename': 'Nifedipine_Eq10_modified_hill_simple.png',
        'X_Label': 'Time (h)', 'Y_Label': 'Dose Ratio (C0/Cmax)',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': 0, 'Y_Max': 2,
        'X_Ticks': '0, 20, 40, 60, 80  (plus auto)',
        'Y_Ticks': '0.0, 0.5, 1.0, 1.5, 2.0',
        'Original_Width_in': 7.81, 'Original_Height_in': 7.74,
        'Axisless_Width_in': 7.81, 'Axisless_Height_in': 7.74,
        'Axisless_Width_px': 4686, 'Axisless_Height_px': 4644, 'DPI': 600,
        'Notes': '3D surface (equation: modified_hill_simple). Z-axis = O2 response. View angle elev=25, azim=-158.',
        'Colorbar_Min': 0, 'Colorbar_White': '(midpoint)', 'Colorbar_Max': 100,
        'Colorbar_Label': 'Z-axis (O2 response %) shared. Colormap: turbo.',
    },
    {
        'Panel': 'b (Dactinomycin surface)', 'Filename': 'Dactinomycin_Eq3_gaussian_hill_hybrid.png',
        'X_Label': 'Time (h)', 'Y_Label': 'Dose Ratio (C0/Cmax)',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': 0, 'Y_Max': 2,
        'X_Ticks': '0, 20, 40, 60, 80  (plus auto)',
        'Y_Ticks': '0.0, 0.5, 1.0, 1.5, 2.0',
        'Original_Width_in': 7.81, 'Original_Height_in': 7.74,
        'Axisless_Width_in': 7.81, 'Axisless_Height_in': 7.74,
        'Axisless_Width_px': 4686, 'Axisless_Height_px': 4644, 'DPI': 600,
        'Notes': '3D surface (equation: gaussian_hill_hybrid). Z-axis = O2 response. View angle elev=25, azim=-158.',
        'Colorbar_Min': 0, 'Colorbar_White': '(midpoint)', 'Colorbar_Max': 100,
        'Colorbar_Label': 'Z-axis (O2 response %) shared. Colormap: turbo.',
    },
    {
        'Panel': 'b (shared colorbar)', 'Filename': 'Fig_3b_colorbar.png',
        'X_Label': '(colorbar image)', 'Y_Label': 'Z-axis (O2 response %)',
        'X_Scale': 'n/a', 'Y_Scale': 'linear',
        'X_Min': '', 'X_Max': '', 'Y_Min': 0, 'Y_Max': 100,
        'X_Ticks': 'n/a',
        'Y_Ticks': '0, 20, 40, 60, 80, 100',
        'Original_Width_in': 0.86, 'Original_Height_in': 2.51,
        'Axisless_Width_in': 0.86, 'Axisless_Height_in': 2.51,
        'Axisless_Width_px': 519, 'Axisless_Height_px': 1506, 'DPI': 600,
        'Notes': 'Standalone vertical colorbar shared across the 3 Fig 3b surfaces.',
        'Colorbar_Min': 0, 'Colorbar_White': '(midpoint)', 'Colorbar_Max': 100,
        'Colorbar_Label': 'O2 response (%), turbo cmap',
    },
    {
        'Panel': 'c', 'Filename': 'Fig_3c.png',
        'X_Label': 'R-squared', 'Y_Label': 'Equation',
        'X_Scale': 'linear', 'Y_Scale': 'categorical',
        'X_Min': -0.667, 'X_Max': 0.566,
        'Y_Min': '(row 0 = worst O2)', 'Y_Max': '(row 11 = best O2)',
        'X_Ticks': '-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6',
        'Y_Ticks': ', '.join(EQUATIONS_12) + '  (sorted by O2 R^2 ascending)',
        'Original_Width_in': 11.96, 'Original_Height_in': 5.88,
        'Axisless_Width_in': 11.96, 'Axisless_Height_in': 5.88,
        'Axisless_Width_px': 7175, 'Axisless_Height_px': 3526, 'DPI': 600,
        'Notes': 'Horizontal bar chart of R^2 per equation, 2 bars each (Contractility + O2), rainbow colors by rank. Contractility R^2 range 0.085-0.497, O2 R^2 range -0.667 to 0.566.',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'd (Arrhythmia subplot)', 'Filename': 'Fig_3d.png',
        'X_Label': 'Accuracy', 'Y_Label': 'AUC ROC',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 1, 'Y_Min': 0, 'Y_Max': 1,
        'X_Ticks': '0, 0.25, 0.5, 0.75, 1',
        'Y_Ticks': '0.25, 0.5, 0.75, 1',
        'Original_Width_in': 23.71, 'Original_Height_in': 8.24,
        'Axisless_Width_in': 23.71, 'Axisless_Height_in': 8.24,
        'Axisless_Width_px': 14227, 'Axisless_Height_px': 4945, 'DPI': 600,
        'Notes': ('3-panel scatter (Arrhythmia | Heart Damage | Concern Binary). '
                  f'Points colored by equation ({len(EQUATIONS_12)} equations: {", ".join(EQUATIONS_12)}). '
                  'Actual plotted data: Accuracy 0.360-0.800, AUC 0.210-0.887. Diagonal y=x reference line. '
                  'Best model shown per target (XGBoost or GaussianNB, selected per panel).'),
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'd (alternate - bar form)', 'Filename': 'Fig_3d_alternate.png',
        'X_Label': 'Equation', 'Y_Label': 'AUC ROC',
        'X_Scale': 'categorical', 'Y_Scale': 'linear',
        'X_Min': '', 'X_Max': '', 'Y_Min': 0, 'Y_Max': 1,
        'X_Ticks': ', '.join(EQUATIONS_12),
        'Y_Ticks': '0.0, 0.25, 0.5, 0.75, 1.0',
        'Original_Width_in': 7.32, 'Original_Height_in': 2.37,
        'Axisless_Width_in': 7.32, 'Axisless_Height_in': 2.37,
        'Axisless_Width_px': 4390, 'Axisless_Height_px': 1422, 'DPI': 600,
        'Notes': 'Alternate form (grouped bars, 3 models per equation: XGBoost, SVM_RBF, RandomForest).',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'd (alternate grid)', 'Filename': 'Fig_3d_alternate_grid.png',
        'X_Label': 'Accuracy', 'Y_Label': 'AUC ROC',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 1, 'Y_Min': 0, 'Y_Max': 1,
        'X_Ticks': '0, 0.25, 0.5, 0.75, 1',
        'Y_Ticks': '0, 0.25, 0.5, 0.75, 1',
        'Original_Width_in': 9.10, 'Original_Height_in': 7.40,
        'Axisless_Width_in': 9.10, 'Axisless_Height_in': 7.40,
        'Axisless_Width_px': 5460, 'Axisless_Height_px': 4440, 'DPI': 600,
        'Notes': '3x3 grid: rows=3 targets, cols=3 models (XGBoost/SVM_RBF/RandomForest). 12 equations colored dots per subplot.',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'e (O2)', 'Filename': 'Fig_3e_O2.png',
        'X_Label': 'Time from Exposure (h)', 'Y_Label': 'O2 (fraction of baseline)',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 100, 'Y_Min': 0.816, 'Y_Max': 3.964,
        'X_Ticks': '0, 20, 40, 60, 80, 100',
        'Y_Ticks': '1.0, 1.5, 2.0, 2.5, 3.0, 3.5  (visible ticks; matplotlib auto-range)',
        'Original_Width_in': 10.52, 'Original_Height_in': 7.43,
        'Axisless_Width_in': 10.52, 'Axisless_Height_in': 7.43,
        'Axisless_Width_px': 6312, 'Axisless_Height_px': 4458, 'DPI': 600,
        'Notes': ('Vandetanib O2 overlay. figsize=(12,8), xlim=[0,100], ylim=auto. '
                  'Axis-range Y=[0.816, 3.964]; data Y=[0.959, 3.821]. '
                  '3 concs: 0.5 mM (blue), 0.125 mM (pink), 0.062 mM (yellow). Solid=Data, Dashed=Model. '
                  'Outlier filter: v_norm.min()>0, v_norm.max()<4.5, v_norm.max()>1.5 (drops dead-well + high outlier).'),
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'e (Contractility)', 'Filename': 'Fig_3e_Contractility.png',
        'X_Label': 'Time from Exposure (h)', 'Y_Label': 'Contractility (fraction of baseline)',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 100, 'Y_Min': 0.542, 'Y_Max': 1.024,
        'X_Ticks': '0, 20, 40, 60, 80, 100',
        'Y_Ticks': '0.6, 0.7, 0.8, 0.9, 1.0  (visible ticks; matplotlib auto-range)',
        'Original_Width_in': 10.52, 'Original_Height_in': 7.44,
        'Axisless_Width_in': 10.52, 'Axisless_Height_in': 7.44,
        'Axisless_Width_px': 6311, 'Axisless_Height_px': 4463, 'DPI': 600,
        'Notes': ('Sotalol Contractility overlay. figsize=(12,8), xlim=[0,100], ylim=auto. '
                  'Axis-range Y=[0.542, 1.024]; data Y=[0.564, 1.002]. '
                  '3 concs: 5.0 mM (blue), 2.5 mM (pink), 0.313 mM (yellow). Solid=Data, Dashed=Model. '
                  'Model dashes converge to ~0.83 by t=100h. Outlier filter: caps rise >1.03 at t=95, '
                  '>1.10 at t=50; drops 0.313 mM traces dipping <0.75 at t=40.'),
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
]

# ============================================================
# FIGURE 6 / 7 / 8 (shared structure, different targets)
# ============================================================

def _build_classifier_fig(letter_prefix, target_name, roc_notes, panel_h_models, panel_h_ticks,
                          shap_range, panel_h_y_max=1.20, panel_h_y_min=0.0):
    """Build axis info rows for Fig 6, 7, or 8 (same panel pattern).

    panel_h_models: string of model names (categorical X-ticks for panel h)
    shap_range: (min, max) for panel f X-axis
    """
    rows = [
        {
            'Panel': 'b', 'Filename': f'Fig_{letter_prefix}b.png',
            'X_Label': 'Predicted', 'Y_Label': 'Actual',
            'X_Scale': 'categorical', 'Y_Scale': 'categorical',
            'X_Min': '', 'X_Max': '', 'Y_Min': '', 'Y_Max': '',
            'X_Ticks': 'Neg, Pos', 'Y_Ticks': 'Neg, Pos',
            'Notes': f'{target_name} confusion matrix (counts only), Blues cmap. 2x2 cells: TN/FP/FN/TP.',
        },
        {
            'Panel': 'b (with %)', 'Filename': f'Fig_{letter_prefix}b_with_pct.png',
            'X_Label': 'Predicted', 'Y_Label': 'Actual',
            'X_Scale': 'categorical', 'Y_Scale': 'categorical',
            'X_Min': '', 'X_Max': '', 'Y_Min': '', 'Y_Max': '',
            'X_Ticks': 'Neg, Pos', 'Y_Ticks': 'Neg, Pos',
            'Notes': f'{target_name} confusion matrix with row percentages (e.g. "73 (66.4%)")',
        },
        {
            'Panel': 'c', 'Filename': f'Fig_{letter_prefix}c.png',
            'X_Label': 'Metric', 'Y_Label': 'Score',
            'X_Scale': 'categorical', 'Y_Scale': 'linear',
            'X_Min': '', 'X_Max': '', 'Y_Min': 0.0, 'Y_Max': 1.15,
            'X_Ticks': 'Accuracy, AUC ROC, F1, MCC',
            'Y_Ticks': '0.0, 0.2, 0.4, 0.6, 0.8, 1.0',
            'Notes': f'{target_name} 4-metric bar chart with error bars (mean +/- std across folds)',
        },
        {
            'Panel': 'd', 'Filename': f'Fig_{letter_prefix}d.png',
            'X_Label': 'Prob (%)', 'Y_Label': 'Drug',
            'X_Scale': 'linear', 'Y_Scale': 'categorical (25 drugs, sorted by prob)',
            'X_Min': -5, 'X_Max': 105, 'Y_Min': '(row 0)', 'Y_Max': '(row 24)',
            'X_Ticks': '0, 20, 40, 60, 80, 100',
            'Y_Ticks': ', '.join(DRUGS_25),
            'Notes': f'{target_name} per-drug prob scatter. Green=positive, red=negative. Threshold line at 35%%.',
        },
        {
            'Panel': 'd (with stats)', 'Filename': f'Fig_{letter_prefix}d_with_stats.png',
            'X_Label': 'Prob (%)', 'Y_Label': 'Drug',
            'X_Scale': 'linear', 'Y_Scale': 'categorical (25 drugs)',
            'X_Min': -5, 'X_Max': 105, 'Y_Min': '(row 0)', 'Y_Max': '(row 24)',
            'X_Ticks': '0, 20, 40, 60, 80, 100',
            'Y_Ticks': ', '.join(DRUGS_25),
            'Notes': f'{target_name} threshold plot with mean +/- std bands per class (positive/negative)',
        },
        {
            'Panel': 'e', 'Filename': f'Fig_{letter_prefix}e.png',
            'X_Label': '# Features', 'Y_Label': 'Cumulative Score (%)',
            'X_Scale': 'linear (integer)', 'Y_Scale': 'linear',
            'X_Min': 1, 'X_Max': 14, 'Y_Min': -5.0, 'Y_Max': 105.0,
            'X_Ticks': '1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14',
            'Y_Ticks': '0, 20, 40, 60, 80, 100',
            'Notes': f'{target_name} cumulative feature importance. One line per drug (25 lines). Horizontal threshold line at 35%.',
        },
        {
            'Panel': 'f', 'Filename': f'Fig_{letter_prefix}f.png',
            'X_Label': 'SHAP Value (impact on model output)', 'Y_Label': 'Feature',
            'X_Scale': 'linear', 'Y_Scale': 'categorical (14 features)',
            'X_Min': shap_range[0], 'X_Max': shap_range[1],
            'Y_Min': '(row 0)', 'Y_Max': '(row 13)',
            'X_Ticks': 'matplotlib auto (symmetric around 0)',
            'Y_Ticks': ', '.join(FEATURES_14),
            'Notes': f'{target_name} SHAP aligned pairs. Drugs sorted by |SHAP| descending. Positive extends right, negative extends left.',
        },
        {
            'Panel': 'g', 'Filename': f'Fig_{letter_prefix}g.png',
            'X_Label': 'False Positive Rate', 'Y_Label': 'True Positive Rate',
            'X_Scale': 'linear', 'Y_Scale': 'linear',
            'X_Min': 0, 'X_Max': 1, 'Y_Min': 0.0, 'Y_Max': 1.0,
            'X_Ticks': '0.0, 0.2, 0.4, 0.6, 0.8, 1.0',
            'Y_Ticks': '0.0, 0.2, 0.4, 0.6, 0.8, 1.0',
            'Notes': roc_notes,
        },
        {
            'Panel': 'h', 'Filename': f'Fig_{letter_prefix}h.png',
            'X_Label': 'Model', 'Y_Label': 'Score',
            'X_Scale': 'categorical', 'Y_Scale': 'linear',
            'X_Min': '', 'X_Max': '', 'Y_Min': panel_h_y_min, 'Y_Max': panel_h_y_max,
            'X_Ticks': panel_h_models,
            'Y_Ticks': panel_h_ticks,
            'Notes': f'{target_name} grouped bar: Accuracy, F1, MCC per model with error bars',
        },
    ]
    # Fill shared dimensions + empty colorbar cols
    for r in rows:
        r.setdefault('Original_Width_in', 10.0)
        r.setdefault('Original_Height_in', 6.0)
        r.setdefault('Axisless_Width_in', 10.0)
        r.setdefault('Axisless_Height_in', 6.0)
        r.setdefault('Axisless_Width_px', 6000)
        r.setdefault('Axisless_Height_px', 3600)
        r.setdefault('DPI', 600)
        for c in ('Colorbar_Min', 'Colorbar_White', 'Colorbar_Max', 'Colorbar_Label'):
            r.setdefault(c, '')
    return rows


FIG_6 = _build_classifier_fig(
    '6', 'Arrhythmia',
    roc_notes='Arrhythmia ROC: Organoid (green #2ca02c) vs CNN DIQT (red #d62728) vs CNN 5-fold (purple #9467bd). Confidence bands from bootstrap.',
    panel_h_models='Organoid, CNN (DIQT), CNN (5-fold)',
    panel_h_ticks='0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2',
    shap_range=(-0.206, 0.166),
)

FIG_7 = _build_classifier_fig(
    '7', 'Heart Damage',
    roc_notes='Heart Damage ROC: Organoid (green #2ca02c) vs ADMET-AI DICTrank (blue #1f77b4), SwissADME DICTrank (orange #ff7f0e), ADMET-AI Scaffold (purple #9467bd), SwissADME Scaffold (red #d62728).',
    panel_h_models='ADMET-AI (DICTrank), SwissADME (DICTrank), ADMET-AI (Scaffold), SwissADME (Scaffold), Organoid',
    panel_h_ticks='-0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2',
    shap_range=(-0.180, 0.463),
    panel_h_y_min=-0.3, panel_h_y_max=1.20,
)

FIG_8 = _build_classifier_fig(
    '8', 'Concern (Binary)',
    roc_notes='Concern (Binary) ROC: Organoid (green #2ca02c). Single-model plot.',
    panel_h_models='Organoid',
    panel_h_ticks='0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2',
    shap_range=(-0.648, 0.146),
)
# Fig 8 has no panel g/h (only binary, single model)
FIG_8 = [r for r in FIG_8 if r['Panel'] not in ('g', 'h')]

# ============================================================
# FIGURE 4 / 5 — 5x5 3D SURFACE GRIDS
# ============================================================

def _build_5x5_surface_rows(fig_num, response_name, z_display_cap, z_actual_max, units):
    """Each 5x5 cell is an individual 3D surface plot at 7x7.5 in."""
    return [
        {
            'Panel': 'cell (each of 25, with title)',
            'Filename': f'{response_name}_<Drug>.png  (25 images)',
            'X_Label': 'Time (h)', 'Y_Label': 'Dose Ratio (C0/Cmax)',
            'X_Scale': 'linear', 'Y_Scale': 'linear',
            'X_Min': 0, 'X_Max': 96, 'Y_Min': 0, 'Y_Max': 2,
            'X_Ticks': '0, 20, 40, 60, 80  (shown only on right col)',
            'Y_Ticks': '0.0, 0.5, 1.0, 1.5, 2.0  (shown only on bottom row)',
            'Original_Width_in': 7.0, 'Original_Height_in': 7.5,
            'Axisless_Width_in': 7.0, 'Axisless_Height_in': 7.5,
            'Axisless_Width_px': 4200, 'Axisless_Height_px': 4500, 'DPI': 600,
            'Notes': (f'{response_name} 3D surface per drug (25 total). View angle elev=25, azim=-158. '
                      'Z-axis label shown only on left col; title: drug name (28pt bold).'),
            'Colorbar_Min': 0, 'Colorbar_White': f'{z_display_cap / 2}',
            'Colorbar_Max': z_display_cap,
            'Colorbar_Label': (f'{response_name} ({units}). vmin=0, vmax={z_display_cap} display cap '
                               f'(actual data max ~{z_actual_max}; values above cap shown solid red). '
                               'Colormap: turbo (extended with solid red above cap).'),
        },
        {
            'Panel': 'cell (no title variant)',
            'Filename': f'{response_name}_<Drug>.png  (25 images, _NoTitles folder)',
            'X_Label': 'Time (h)', 'Y_Label': 'Dose Ratio (C0/Cmax)',
            'X_Scale': 'linear', 'Y_Scale': 'linear',
            'X_Min': 0, 'X_Max': 96, 'Y_Min': 0, 'Y_Max': 2,
            'X_Ticks': '0, 20, 40, 60, 80  (right col only)',
            'Y_Ticks': '0.0, 0.5, 1.0, 1.5, 2.0  (bottom row only)',
            'Original_Width_in': 7.0, 'Original_Height_in': 7.5,
            'Axisless_Width_in': 7.0, 'Axisless_Height_in': 7.5,
            'Axisless_Width_px': 4200, 'Axisless_Height_px': 4500, 'DPI': 600,
            'Notes': f'Same as above but with drug title removed (titles go in PowerPoint text boxes).',
            'Colorbar_Min': 0, 'Colorbar_White': f'{z_display_cap / 2}',
            'Colorbar_Max': z_display_cap,
            'Colorbar_Label': f'Same scaling as titled variant. {response_name} ({units}).',
        },
        {
            'Panel': 'colorbar (shared)',
            'Filename': f'{response_name}_colorbar_600dpi.png',
            'X_Label': '(colorbar)', 'Y_Label': f'{response_name} ({units})',
            'X_Scale': 'n/a', 'Y_Scale': 'linear',
            'X_Min': '', 'X_Max': '', 'Y_Min': 0, 'Y_Max': z_display_cap,
            'X_Ticks': 'n/a',
            'Y_Ticks': (f'0, {z_display_cap * 0.25}, {z_display_cap * 0.5}, '
                        f'{z_display_cap * 0.75}, {z_display_cap}'),
            'Original_Width_in': 1.5, 'Original_Height_in': 6.0,
            'Axisless_Width_in': 1.5, 'Axisless_Height_in': 6.0,
            'Axisless_Width_px': 900, 'Axisless_Height_px': 3600, 'DPI': 600,
            'Notes': f'Standalone shared colorbar for the 25-cell grid.',
            'Colorbar_Min': 0, 'Colorbar_White': z_display_cap / 2,
            'Colorbar_Max': z_display_cap,
            'Colorbar_Label': f'{response_name} ({units}). turbo cmap with solid red above cap.',
        },
    ]


FIG_4 = _build_5x5_surface_rows(4, 'O2', z_display_cap=35, z_actual_max=50, units='%')
FIG_5 = _build_5x5_surface_rows(5, 'Contractility', z_display_cap=0.04, z_actual_max=0.069, units='response')


# ============================================================
# SUPPLEMENTARY FIGURES
# ============================================================

FIG_S1 = [
    {
        'Panel': 'a', 'Filename': 'Fig_S1a.png',
        'X_Label': 'Time (h)', 'Y_Label': 'Concentration (mM)',
        'X_Scale': 'linear', 'Y_Scale': 'categorical (concentration)',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': '(row 0 = top conc)', 'Y_Max': '(row N = bottom)',
        'X_Ticks': 'every ~8th timepoint shown',
        'Y_Ticks': '5, 1.25, 0.313, 0.078, 0.0195, 0.00488  (Vandetanib concs, every ~6th row)',
        'Original_Width_in': 10.0, 'Original_Height_in': 8.0,
        'Axisless_Width_in': 10.0, 'Axisless_Height_in': 8.0,
        'Axisless_Width_px': 6000, 'Axisless_Height_px': 4800, 'DPI': 600,
        'Notes': 'Vandetanib O2 Std Dev heatmap, square cells.',
        'Colorbar_Min': 0, 'Colorbar_White': '(data midpoint)', 'Colorbar_Max': '(data max)',
        'Colorbar_Label': 'O2 Std Dev (%) — vmin=raw_min, vmax=raw_max (auto from data). Colormap: #123BFF -> white -> #FF2908',
    },
    {
        'Panel': 'b', 'Filename': 'Fig_S1b.png',
        'X_Label': 'Time (h)', 'Y_Label': 'Concentration (mM)',
        'X_Scale': 'linear', 'Y_Scale': 'categorical (concentration)',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': '(row 0)', 'Y_Max': '(row N)',
        'X_Ticks': 'every ~8th timepoint',
        'Y_Ticks': '5, 1.25, 0.313, 0.078, 0.0195, 0.00488',
        'Original_Width_in': 10.0, 'Original_Height_in': 8.0,
        'Axisless_Width_in': 10.0, 'Axisless_Height_in': 8.0,
        'Axisless_Width_px': 6000, 'Axisless_Height_px': 4800, 'DPI': 600,
        'Notes': 'Vandetanib O2 Dominant Frequency heatmap, square cells.',
        'Colorbar_Min': 0, 'Colorbar_White': '(data midpoint)', 'Colorbar_Max': '(data max)',
        'Colorbar_Label': 'Dominant Frequency (Hz) — auto from data. Colormap: #123BFF -> white -> #FF2908',
    },
    {
        'Panel': 'c', 'Filename': 'Fig_S1c.png',
        'X_Label': 'Time (h)', 'Y_Label': 'Concentration (mM)',
        'X_Scale': 'linear', 'Y_Scale': 'categorical (concentration)',
        'X_Min': 0, 'X_Max': 96, 'Y_Min': '(row 0)', 'Y_Max': '(row N)',
        'X_Ticks': 'every ~8th timepoint',
        'Y_Ticks': '5, 1.25, 0.313, 0.078, 0.0195, 0.00488',
        'Original_Width_in': 10.0, 'Original_Height_in': 8.0,
        'Axisless_Width_in': 10.0, 'Axisless_Height_in': 8.0,
        'Axisless_Width_px': 6000, 'Axisless_Height_px': 4800, 'DPI': 600,
        'Notes': 'Vandetanib Amplitude at Dominant Frequency heatmap, square cells.',
        'Colorbar_Min': 0, 'Colorbar_White': '(data midpoint)', 'Colorbar_Max': '(data max)',
        'Colorbar_Label': 'Amplitude (Vpp) — auto from data. Colormap: #123BFF -> white -> #FF2908',
    },
]

FIG_S3 = [
    {
        'Panel': 'a', 'Filename': 'Fig_S3a.png',
        'X_Label': 'Prediction Accuracy', 'Y_Label': 'AUC ROC',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0, 'X_Max': 1, 'Y_Min': 0, 'Y_Max': 1,
        'X_Ticks': '0.0, 0.2, 0.4, 0.6, 0.8, 1.0',
        'Y_Ticks': '0.0, 0.2, 0.4, 0.6, 0.8, 1.0',
        'Original_Width_in': 14.0, 'Original_Height_in': 5.0,
        'Axisless_Width_in': 14.0, 'Axisless_Height_in': 5.0,
        'Axisless_Width_px': 8400, 'Axisless_Height_px': 3000, 'DPI': 600,
        'Notes': ('3-panel scatter: Arrhythmia, Heart Damage, Concern. '
                  'Models by marker: SVM_RBF (square), XGBoost (triangle), GaussianNB (diamond). '
                  'Equations by color: PKPD Elimination (green), Dual Exponential (blue), '
                  'Modified Hill Hormesis (dusty rose). y=x diagonal reference line.'),
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
]

FIG_S4 = [
    {
        'Panel': 'a', 'Filename': 'Fig_S4a.png',
        'X_Label': 'False Positive Rate', 'Y_Label': 'True Positive Rate',
        'X_Scale': 'linear', 'Y_Scale': 'linear',
        'X_Min': 0.0, 'X_Max': 1.0, 'Y_Min': 0, 'Y_Max': 1,
        'X_Ticks': '0.0, 0.2, 0.4, 0.6, 0.8, 1.0',
        'Y_Ticks': '0.0, 0.2, 0.4, 0.6, 0.8, 1.0',
        'Original_Width_in': 10.0, 'Original_Height_in': 6.0,
        'Axisless_Width_in': 10.0, 'Axisless_Height_in': 6.0,
        'Axisless_Width_px': 6000, 'Axisless_Height_px': 3600, 'DPI': 600,
        'Notes': 'ADMET LOOCV ROC: ADMET-AI (blue #1f77b4) vs SwissADME (orange #ff7f0e). Confidence bands + chance line y=x.',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
    {
        'Panel': 'b', 'Filename': 'Fig_S4b.png',
        'X_Label': 'Model', 'Y_Label': 'AUC ROC',
        'X_Scale': 'categorical', 'Y_Scale': 'linear',
        'X_Min': '', 'X_Max': '', 'Y_Min': 0, 'Y_Max': 1,
        'X_Ticks': 'MoLFormer, Organoid',
        'Y_Ticks': '0.0, 0.2, 0.4, 0.6, 0.8, 1.0',
        'Original_Width_in': 10.0, 'Original_Height_in': 6.0,
        'Axisless_Width_in': 10.0, 'Axisless_Height_in': 6.0,
        'Axisless_Width_px': 6000, 'Axisless_Height_px': 3600, 'DPI': 600,
        'Notes': 'MoLFormer vs Organoid LOOCV grouped bar chart. Dashed horizontal line at 0.5 (chance).',
        'Colorbar_Min': '', 'Colorbar_White': '', 'Colorbar_Max': '', 'Colorbar_Label': '',
    },
]

# ============================================================
# WRITE SHEETS
# ============================================================

COLUMN_ORDER = [
    'Figure', 'Panel', 'Filename',
    'X_Label', 'Y_Label', 'X_Scale', 'Y_Scale',
    'X_Min', 'X_Max', 'Y_Min', 'Y_Max',
    'X_Ticks', 'X_Tick_Step', 'Y_Ticks', 'Y_Tick_Step',
    'Colorbar_Min', 'Colorbar_White', 'Colorbar_Max', 'Colorbar_Label', 'Colorbar_Tick_Step',
    'Original_Width_in', 'Original_Height_in',
    'Axisless_Width_in', 'Axisless_Height_in',
    'Axisless_Width_px', 'Axisless_Height_px', 'DPI',
    'Notes',
]


def _compute_step(ticks_str):
    """Parse a tick string and return the major step size (or '' if non-uniform/categorical).

    Detects log-spaced ticks (e.g. 0.1, 1, 10) and returns "x10 per decade" instead
    of reporting a variable linear step.
    """
    if not ticks_str or not isinstance(ticks_str, str):
        return ''
    s = ticks_str.split('(')[0].strip()
    parts = [p.strip() for p in s.replace(';', ',').split(',') if p.strip()]
    nums = []
    for p in parts:
        try:
            nums.append(float(p))
        except ValueError:
            return ''  # categorical → no numeric step
    if len(nums) < 2:
        return ''
    # Linear step
    steps = [round(nums[i + 1] - nums[i], 6) for i in range(len(nums) - 1)]
    if all(abs(s - steps[0]) < 1e-6 for s in steps):
        step = steps[0]
        return int(step) if step == int(step) else step
    # Log-spaced? ratios all equal and positive inputs
    if all(n > 0 for n in nums):
        ratios = [round(nums[i + 1] / nums[i], 6) for i in range(len(nums) - 1)]
        if all(abs(r - ratios[0]) < 1e-6 for r in ratios):
            r = ratios[0]
            return f'x{int(r) if r == int(r) else r} per decade'
    return f'variable ({min(steps)} to {max(steps)})'


def _colorbar_step(cb_min, cb_max):
    """Compute a reasonable step for colorbars. Assume 5 intervals (6 ticks)."""
    try:
        lo = float(cb_min); hi = float(cb_max)
    except (TypeError, ValueError):
        return ''
    step = (hi - lo) / 5.0
    return int(step) if step == int(step) else round(step, 3)


def _step_for_axis(ticks_str, scale_str):
    """Compute tick step, using the scale type for sensible fallbacks."""
    scale_lc = str(scale_str or '').lower()
    ticks_lc = str(ticks_str or '').lower()
    # No ticks at all
    if 'none' in ticks_lc or ticks_lc.strip() in ('', 'n/a', 'nan'):
        return 'no ticks'
    # Categorical axes: step is not meaningful
    if 'categorical' in scale_lc:
        return 'categorical (non-uniform bins)'
    return _compute_step(ticks_str)


def write_sheet(rows, figure_num, outpath):
    for r in rows:
        r['Figure'] = figure_num
        r.setdefault('X_Tick_Step', _step_for_axis(r.get('X_Ticks', ''), r.get('X_Scale', '')))
        r.setdefault('Y_Tick_Step', _step_for_axis(r.get('Y_Ticks', ''), r.get('Y_Scale', '')))
        r.setdefault('Colorbar_Tick_Step', _colorbar_step(r.get('Colorbar_Min', ''),
                                                          r.get('Colorbar_Max', '')))
        for c in COLUMN_ORDER:
            r.setdefault(c, '')
    df = pd.DataFrame(rows, columns=COLUMN_ORDER)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(outpath, engine='openpyxl') as w:
        df.to_excel(w, sheet_name=f'Fig_{figure_num}_Axis_Info', index=False)
    print(f'  wrote {outpath.relative_to(PROJECT_ROOT)}  ({len(df)} panels)')


def main():
    print('Rewriting Axis_Scaling_Reference.xlsx files with explicit values...')
    for rows, fig in [(FIG_2, '2'), (FIG_3, '3'),
                      (FIG_4, '4'), (FIG_5, '5'),
                      (FIG_6, '6'), (FIG_7, '7'), (FIG_8, '8'),
                      (FIG_S1, 'S1'), (FIG_S3, 'S3'), (FIG_S4, 'S4')]:
        outpath = FIGS_DIR / f'Fig_{fig}' / 'Axisless' / 'Axis_Scaling_Reference.xlsx'
        write_sheet(rows, fig, outpath)
    print('Done.')


if __name__ == '__main__':
    main()
