"""Generate 2D dose-response plots (O2 + Contractility) with PKPD model overlay for ALL drugs.

Pipeline per well:
  1. Spike removal (5x median step) → interpolate
  2. NaN gap check (max 7 consecutive) → exclude or interpolate
  3. Second spike removal (2.5x, more aggressive)
  4. Final NaN fill
  5. Intensive smoothing: LOWESS x3 (0.55→0.45→0.35) → Gaussian σ=3 → CubicSpline → 1000pt

Averaged plot uses compressed-offset (COMPRESS=0.3).
Model overlay uses PKPD elimination (Eq11) coefficients, baseline-aligned at t=0.

Output: Output/2D_Model_Overlay/{Drug}/
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2]))

import figure_config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import CubicSpline
import statsmodels.api as sm
from collections import defaultdict
import re

BASE = Path(__file__).resolve().parent
STAGE2_DIR = BASE / 'Stage2_Tables'
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / 'Output' / '2D_Model_Overlay'
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

SAVE_DPI = 600
MAX_NAN_GAP = 7

# Drug name → folder name in Stage2_Tables
DRUG_FOLDERS = {
    'Amiodarone': 'Amiodarone',
    'Bortezomib': 'Bortezomib (A09)',
    'Chlorpromazine': 'Chlorpromazine',
    'Cobimetinib': 'Cobimetinib (E03)',
    'Dactinomycin': 'Dactinomycin',
    'Daunorubicin': 'Daunorubicin (F03)',
    'Doxorubicin': 'Doxorubicin (G03)',
    'Epirubicin': 'Epirubicin (B04)',
    'Erlotinib': 'Erlotinib (E09)',
    'Etomoxir': 'Etomoxir',
    'Gemcitibine': 'Gemcitibine',
    'Ibrutinib': 'Ibrutinib (C10)',
    'Ibuprofen': 'Ibuprofen',
    'Isoproterenol': 'Isoproterenol',
    'Mexiletine': 'Mexiletine',
    'Nifedipine': 'Nifedipine',
    'Panobinostat': 'Panobinostat (G07)',
    'Plicamycin': 'Plicamycin',
    'Rosiglitazone': 'Rosiglitazone',
    'Sotalol': 'Sotalol',
    'Sunitinib': 'Sunitinib (H08)',
    'Vandetanib': 'Vandetanib (G11)',
    'Vincristine': 'Vincristine',
    'Vioxx': 'Vioxx',
    'Vorinostat': 'Vorinostat (B06)',
}

# ── Smoothing pipeline ──────────────────────────────────────────────────────

def _parse_conc_columns(columns):
    """Parse concentration columns, stripping pandas duplicate suffixes.

    Distinguishes real decimals (0.5, 0.25) from pandas suffixes (8.1, 4.3).
    Strategy: a column like '8.1' is a duplicate of '8' if '8' also exists.
    A column like '0.5' is real if no '0' column exists.
    Columns with 2+ dots (e.g. '0.5.1') always have the last .N stripped.
    """
    col_strs = [str(c) for c in columns]

    # First pass: identify base column names (no dots or 2+ dots stripped)
    base_names = set()
    for s in col_strs:
        if '.' not in s:
            base_names.add(s)

    results = {}
    for s in col_strs:
        n_dots = s.count('.')
        if n_dots == 0:
            # Pure integer: '8', '4', '2'
            try:
                results[s] = float(s)
            except ValueError:
                pass
        elif n_dots >= 2:
            # Definitely a pandas duplicate: '0.5.1' -> '0.5', '0.125.3' -> '0.125'
            last_dot = s.rfind('.')
            base = s[:last_dot]
            try:
                results[s] = float(base)
            except ValueError:
                pass
        else:
            # Exactly 1 dot: could be real ('0.5') or pandas suffix ('8.1')
            dot_pos = s.index('.')
            integer_part = s[:dot_pos]
            if integer_part in base_names:
                # '8.1' → '8' exists as a column, so this is a duplicate
                try:
                    results[s] = float(integer_part)
                except ValueError:
                    pass
            else:
                # '0.5' → no '0' column, so this is a real concentration
                try:
                    results[s] = float(s)
                except ValueError:
                    pass
    return results


def max_nan_gap(arr):
    max_gap = current = 0
    for v in arr:
        if np.isnan(v):
            current += 1
            max_gap = max(max_gap, current)
        else:
            current = 0
    return max_gap


def interpolate_limited(arr, max_gap):
    if max_nan_gap(arr) > max_gap:
        return None
    valid = np.where(~np.isnan(arr))[0]
    if len(valid) < 2:
        return None
    return np.interp(np.arange(len(arr)), valid, arr[valid])


def remove_spikes(vals, threshold_mult=5.0):
    vals = np.array(vals, dtype=float)
    n = len(vals)
    if n < 3:
        return vals.copy(), 0
    diffs = np.abs(np.diff(vals))
    valid_diffs = diffs[~np.isnan(diffs)]
    if len(valid_diffs) == 0:
        return vals.copy(), 0
    typical_step = np.median(valid_diffs)
    if typical_step < 1e-9:
        typical_step = np.mean(valid_diffs) if np.mean(valid_diffs) > 1e-9 else 1.0
    spike_mask = np.zeros(n, dtype=bool)
    for i in range(1, n - 1):
        if np.isnan(vals[i]) or np.isnan(vals[i-1]) or np.isnan(vals[i+1]):
            continue
        neighbor_avg = (vals[i-1] + vals[i+1]) / 2.0
        dev = abs(vals[i] - neighbor_avg)
        neighbor_diff = abs(vals[i+1] - vals[i-1])
        if dev > threshold_mult * typical_step and dev > 2.0 * max(neighbor_diff, typical_step):
            spike_mask[i] = True
    n_removed = int(spike_mask.sum())
    if n_removed == 0:
        return vals.copy(), 0
    cleaned = vals.copy()
    cleaned[spike_mask] = np.nan
    valid_idx = np.where(~np.isnan(cleaned))[0]
    if len(valid_idx) >= 2:
        cleaned = np.interp(np.arange(n), valid_idx, cleaned[valid_idx])
    return cleaned, n_removed


def intensive_smooth(vals, time):
    c = vals.copy()
    valid = ~np.isnan(c)
    if valid.sum() >= 4:
        lowess = sm.nonparametric.lowess(c[valid], time[valid], frac=0.55)
        c = np.interp(time, lowess[:, 0], lowess[:, 1])
    lowess = sm.nonparametric.lowess(c, time, frac=0.45)
    c = np.interp(time, lowess[:, 0], lowess[:, 1])
    lowess = sm.nonparametric.lowess(c, time, frac=0.35)
    c = np.interp(time, lowess[:, 0], lowess[:, 1])
    c = gaussian_filter1d(c, sigma=3.0)
    cs = CubicSpline(time, c, bc_type=((1, 0.0), (2, 0.0)))
    time_fine = np.linspace(time[0], time[-1], 1000)
    c_fine = cs(time_fine)
    return time_fine, c_fine


def process_well(vals, time):
    cleaned, _ = remove_spikes(vals, threshold_mult=5.0)
    interped = interpolate_limited(cleaned, MAX_NAN_GAP)
    if interped is None:
        return None
    interped, _ = remove_spikes(interped, threshold_mult=2.5)
    valid_idx = np.where(~np.isnan(interped))[0]
    if len(valid_idx) < 4:
        return None
    interped = np.interp(np.arange(len(interped)), valid_idx, interped[valid_idx])
    t_fine, v_fine = intensive_smooth(interped, time)
    return t_fine, v_fine


# ── PKPD model ──────────────────────────────────────────────────────────────

def load_all_pkpd_params():
    """Load PKPD elimination coefficients for all drugs, both response types."""
    coeff_path = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
    df = pd.read_excel(coeff_path, sheet_name='pkpd_elimination', header=1)
    df.columns = df.columns.str.strip()

    params = {}
    for _, row in df.iterrows():
        drug = row['Drug']
        for resp_type, sfx in [('O2', '.1'), ('Contractility', '')]:
            try:
                params[(drug, resp_type)] = {
                    'R0': float(row[f'R0{sfx}']),
                    'Emax': float(row[f'Emax{sfx}']),
                    'kappa': float(row[f'kappa{sfx}']),
                    'n': float(row[f'n{sfx}']),
                    'm': float(row[f'm{sfx}']),
                    'tau': float(row[f'tau{sfx}']),
                    'k_elim': float(row[f'k_elim{sfx}']),
                    'Cmax': float(row[f'Cmax_used{sfx}']),
                }
            except (KeyError, ValueError):
                pass
    return params


def pkpd_elimination(t, dose_ratio, p):
    t = np.maximum(t, 0)
    kappa = max(p['kappa'], 1e-9)
    tau = max(p['tau'], 1e-9)
    k_elim = max(p['k_elim'], 1e-9)
    C_t = dose_ratio * np.exp(-k_elim * t)
    driving = kappa * (C_t ** p['n']) * ((t / tau) ** p['m'])
    return p['R0'] + p['Emax'] * (1 - np.exp(-driving))


# ── Data loading ────────────────────────────────────────────────────────────

def load_data(drug_name, resp_type):
    folder = STAGE2_DIR / DRUG_FOLDERS[drug_name]
    csv_name = 'O2_mean.csv' if resp_type == 'O2' else 'Amp_std.csv'
    csv_path = folder / csv_name
    if not csv_path.exists():
        return None, None

    df = pd.read_csv(csv_path)

    # Convert time column, skipping non-numeric rows (e.g. 'baseline')
    time_raw = pd.to_numeric(df.iloc[:, 0], errors='coerce')
    valid_mask = time_raw.notna()
    df = df[valid_mask].reset_index(drop=True)
    time = time_raw[valid_mask].values.astype(float)

    conc_map = _parse_conc_columns(df.columns[1:])

    wells = []
    for col in df.columns[1:]:
        col_str = str(col)
        if col_str not in conc_map:
            continue
        conc = conc_map[col_str]
        vals = pd.to_numeric(df[col], errors='coerce').values.astype(float)
        wells.append((conc, vals))

    return time, wells


# ── Plotting ────────────────────────────────────────────────────────────────

def plot_averaged_with_model(drug_name, resp_type, time, wells, pkpd_params):
    conc_groups = defaultdict(list)
    for conc, vals in wells:
        result = process_well(vals, time)
        if result is not None:
            conc_groups[conc].append(result)

    if not conc_groups:
        print(f'    No valid wells for {resp_type}')
        return

    concs_sorted = sorted(conc_groups.keys(), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_sorted))

    conc_avg_raw = {c: np.mean([v[0] for _, v in traces])
                    for c, traces in conc_groups.items()}
    global_avg = np.mean(list(conc_avg_raw.values()))

    scale = 100 if resp_type == 'Contractility' else 1
    p = pkpd_params.get((drug_name, resp_type))

    fig, ax = plt.subplots(figsize=(12, 8))

    for i, conc in enumerate(concs_sorted):
        traces = conc_groups[conc]
        t_fine = traces[0][0]
        offset_traces = [v - (v[0] - global_avg) for _, v in traces]
        avg = np.mean(offset_traces, axis=0) * scale
        color = cmap(i / max(len(concs_sorted) - 1, 1))
        ax.plot(t_fine, avg, linewidth=2.5, color=color)

        # Model overlay
        if p is not None:
            dose_ratio = conc / p['Cmax']
            t_model = np.linspace(0, 100, 1000)
            r_model = pkpd_elimination(t_model, dose_ratio, p)
            if resp_type == 'Contractility':
                r_model = r_model * 100
            # Align baseline
            r_model = r_model + (avg[0] - r_model[0])
            ax.plot(t_model, r_model, linewidth=2.5, color=color,
                    linestyle='--', alpha=0.8)

    ylabel = r'$O_2$ (% Air)' if resp_type == 'O2' else 'Contractility (%)'
    ax.set_title(f'{drug_name} — {resp_type}', fontsize=28, fontweight='bold', pad=10)
    ax.set_xlabel('Time from Exposure (h)', fontsize=26, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=26, fontweight='bold')
    ax.set_xlim(time[0], 100)
    ax.tick_params(labelsize=20, width=1.5)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight('bold')
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
        spine.set_linewidth(3.0)

    # 2-column legend (column-major): concentrations descending, Data/Model same row
    n_conc = len(concs_sorted)
    half = (n_conc + 1) // 2  # col1 gets extra if odd

    # Col1 = highest concs (descending), Col2 = lowest concs (descending)
    col1_h, col1_l, col2_h, col2_l = [], [], [], []
    for idx in range(half):
        c = concs_sorted[idx]
        col1_h.append(Line2D([0], [0], color=cmap(idx / max(n_conc - 1, 1)),
                             linewidth=2.5))
        col1_l.append(f'{c} mM')
    for idx in range(half, n_conc):
        c = concs_sorted[idx]
        col2_h.append(Line2D([0], [0], color=cmap(idx / max(n_conc - 1, 1)),
                             linewidth=2.5))
        col2_l.append(f'{c} mM')

    # Pad col2 with blanks so both columns have same length
    while len(col2_h) < len(col1_h):
        col2_h.append(Line2D([0], [0], alpha=0))
        col2_l.append('')

    # Append Data / Model as final entry in each column
    col1_h.append(Line2D([0], [0], color='black', linewidth=2.5, linestyle='-'))
    col1_l.append('— Data')
    col2_h.append(Line2D([0], [0], color='black', linewidth=2.5, linestyle='--'))
    col2_l.append('-- Model')

    # Concatenate col1 then col2 (matplotlib ncol=2 fills column-major)
    all_handles = col1_h + col2_h
    all_labels = col1_l + col2_l

    legend_loc = 'lower left' if resp_type == 'Contractility' else 'upper left'
    ax.legend(all_handles, all_labels, fontsize=14,
              loc=legend_loc, ncol=2,
              borderpad=0.3, labelspacing=0.2, handlelength=1.2,
              columnspacing=0.8, handletextpad=0.4,
              framealpha=0.85, edgecolor='none')

    safe = drug_name.replace(' ', '_')
    out = OUTPUT_ROOT / f'{safe}_{resp_type}_data_vs_model.png'
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f'    Saved: {out.name}  ({len(concs_sorted)} concs)')


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')

    pkpd_params = load_all_pkpd_params()
    print(f'Loaded PKPD params for {len(set(d for d, _ in pkpd_params))} drugs\n')

    skip = {'DMSO', 'Troglitazone', 'Troglitarazine'}
    drugs = sorted([d for d in DRUG_FOLDERS if d not in skip])

    for drug in drugs:
        print(f'=== {drug} ===')
        for resp_type in ['O2', 'Contractility']:
            time, wells = load_data(drug, resp_type)
            if time is None:
                print(f'    {resp_type}: no data')
                continue
            print(f'  {resp_type}: {len(wells)} wells')
            plot_averaged_with_model(drug, resp_type, time, wells, pkpd_params)

    print(f'\nDone. Output in: {OUTPUT_ROOT}')
