"""Export processed data for all Fig 2 panels.
Each Excel contains the PROCESSED data that directly plots to the graph.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import CubicSpline
from statsmodels.nonparametric.smoothers_lowess import lowess as lowess_func
import statsmodels.api as sm
from collections import defaultdict, OrderedDict

FIG2 = Path('Output/PowerPoint_Figures/Fig_2')

def apply_lowess_full(df_in, window=16):
    smoothed = df_in.copy().astype(float)
    for col in smoothed.columns:
        series = smoothed[col]
        valid = series.dropna()
        if len(valid) < 3:
            continue
        frac = min(1.0, max(window, 1) / len(valid))
        fitted = lowess_func(valid.values, np.arange(len(valid)), frac=frac, return_sorted=False)
        target = smoothed.index.get_indexer(valid.index)
        smoothed.iloc[target, smoothed.columns.get_loc(col)] = fitted
    return smoothed

def intensive_smooth(vals, time):
    c = vals.copy()
    valid = ~np.isnan(c)
    if valid.sum() >= 4:
        lo = sm.nonparametric.lowess(c[valid], time[valid], frac=0.55)
        c = np.interp(time, lo[:, 0], lo[:, 1])
    lo = sm.nonparametric.lowess(c, time, frac=0.45)
    c = np.interp(time, lo[:, 0], lo[:, 1])
    lo = sm.nonparametric.lowess(c, time, frac=0.35)
    c = np.interp(time, lo[:, 0], lo[:, 1])
    c = gaussian_filter1d(c, sigma=3.0)
    cs = CubicSpline(time, c, bc_type=((1, 0.0), (2, 0.0)))
    tf = np.linspace(time[0], time[-1], 1000)
    return tf, cs(tf)

def remove_spikes(vals, threshold_mult=5.0):
    vals = np.array(vals, dtype=float)
    n = len(vals)
    if n < 3:
        return vals.copy()
    diffs = np.abs(np.diff(vals))
    vd = diffs[~np.isnan(diffs)]
    if len(vd) == 0:
        return vals.copy()
    ts = np.median(vd)
    if ts < 1e-9:
        ts = np.mean(vd) if np.mean(vd) > 1e-9 else 1.0
    mask = np.zeros(n, dtype=bool)
    for i in range(1, n - 1):
        if np.isnan(vals[i]) or np.isnan(vals[i-1]) or np.isnan(vals[i+1]):
            continue
        na = (vals[i-1] + vals[i+1]) / 2
        dev = abs(vals[i] - na)
        nd = abs(vals[i+1] - vals[i-1])
        if dev > threshold_mult * ts and dev > 2 * max(nd, ts):
            mask[i] = True
    if not mask.any():
        return vals.copy()
    c = vals.copy()
    c[mask] = np.nan
    vi = np.where(~np.isnan(c))[0]
    if len(vi) >= 2:
        c = np.interp(np.arange(n), vi, c[vi])
    return c

def max_nan_gap(arr):
    mx = cur = 0
    for v in arr:
        if np.isnan(v):
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0
    return mx

KNOWN_EPI = {12, 6, 3, 1.5, 0.75, 0.38, 0.19, 0.094}
KNOWN_MEX = {20, 10, 5, 2.5, 1.25, 0.625, 0.313, 0.156}
MAX_GAP = 7

def get_conc(s, known):
    s = str(s)
    parts = s.split('.')
    for n in range(len(parts), 0, -1):
        try:
            v = float('.'.join(parts[:n]))
            if v in known:
                return v
        except ValueError:
            pass
    return float(s)

def process_dose_response(csv_path, skip_wells, known_concs, apply_shift=False):
    """Process a dose-response CSV into averaged smoothed traces per concentration."""
    csv = pd.read_csv(csv_path)
    time = csv.iloc[:, 0].values.astype(float)

    conc_groups = defaultdict(list)
    for i, col in enumerate(csv.columns[1:]):
        if i in skip_wells:
            continue
        conc = get_conc(col, known_concs)
        vals = csv[col].values.astype(float)
        cleaned = remove_spikes(vals, 5.0)
        if max_nan_gap(cleaned) > MAX_GAP:
            continue
        vi = np.where(~np.isnan(cleaned))[0]
        if len(vi) < 2:
            continue
        cleaned = np.interp(np.arange(len(cleaned)), vi, cleaned[vi])
        cleaned = remove_spikes(cleaned, 2.5)
        vi = np.where(~np.isnan(cleaned))[0]
        if len(vi) < 4:
            continue
        cleaned = np.interp(np.arange(len(cleaned)), vi, cleaned[vi])
        tf, vf = intensive_smooth(cleaned, time)
        conc_groups[conc].append((tf, vf))

    avg_traces = {}
    for conc in sorted(conc_groups.keys(), reverse=True):
        traces = conc_groups[conc]
        avg_traces[conc] = np.mean([v for _, v in traces], axis=0)

    if apply_shift:
        starts = {c: avg_traces[c][0] for c in avg_traces}
        ss = sorted(starts.items(), key=lambda x: x[1])
        MARGIN = 1.5
        if ss[-1][1] > ss[-2][1] + MARGIN:
            shift = ss[-1][1] - (ss[-2][1] + MARGIN)
            avg_traces[ss[-1][0]] -= shift
        if ss[0][1] < ss[1][1] - MARGIN:
            shift = (ss[1][1] - MARGIN) - ss[0][1]
            avg_traces[ss[0][0]] += shift

    tf = list(conc_groups.values())[0][0][0]
    df = pd.DataFrame({'Time_h': tf})
    for conc in sorted(avg_traces.keys(), reverse=True):
        n_wells = len(conc_groups[conc])
        df[f'{conc}_mM_(n={n_wells})'] = avg_traces[conc]
    return df


# === Panel g: Epirubicin O2 averaged ===
print('Panel g: Epirubicin O2 averaged dose-response...')
df_g = process_dose_response(
    'Cleaned_Data/Raw_Example_Data/Epirubicin/O2_mean.csv',
    skip_wells={1}, known_concs=KNOWN_EPI, apply_shift=True)
with pd.ExcelWriter(FIG2 / 'Fig_2g_Epirubicin_O2_data.xlsx', engine='openpyxl') as w:
    df_g.to_excel(w, sheet_name='Processed_Averaged', index=False)
print(f'  {df_g.shape[1]-1} concentrations, {len(df_g)} points')

# === Panel i: Epirubicin O2 heatmap ===
print('Panel i: Epirubicin O2 heatmap...')
df_i = pd.read_csv('Cleaned_Data/Heatmaps/Epirubicin/O2_mean_sorted.csv', index_col=0)
DROP_I = ['0.38.1', '12.0', '3.0', '0.19', '1.5.1', '0.75.1', '0.75.3']
df_i = df_i.drop(columns=[c for c in DROP_I if c in df_i.columns])
for col in df_i.columns:
    df_i[col] = df_i[col].interpolate(method='linear', limit=10, limit_direction='both')
df_i_smooth = apply_lowess_full(df_i)
data_i = df_i_smooth.T.clip(upper=100)
with pd.ExcelWriter(FIG2 / 'Fig_2i_Epirubicin_O2_Heatmap_data.xlsx', engine='openpyxl') as w:
    data_i.to_excel(w, sheet_name='Heatmap_Processed', index=True)
print(f'  {data_i.shape[0]} wells x {data_i.shape[1]} timepoints')

# === Panel j: Mexiletine Contractility 2D ===
print('Panel j: Mexiletine Contractility 2D dose-response...')
df_j = process_dose_response(
    'Cleaned_Data/Raw_Example_Data/Mexiletine/Amp_std.csv',
    skip_wells=set(), known_concs=KNOWN_MEX, apply_shift=False)
with pd.ExcelWriter(FIG2 / 'Fig_2j_Mexiletine_Contractility_data.xlsx', engine='openpyxl') as w:
    df_j.to_excel(w, sheet_name='Processed_Averaged', index=False)
print(f'  {df_j.shape[1]-1} concentrations, {len(df_j)} points')

# === Panel l: Mexiletine Contractility heatmap ===
print('Panel l: Mexiletine Contractility heatmap...')
df_l = pd.read_csv('Cleaned_Data/Raw_Example_Data/Mexiletine/Amp_std.csv', index_col=0)
REMOVE_ORIG = {4, 5, 6, 7, 14, 15, 17, 21, 22, 24, 26}
REMOVE_EXTRA = {'20', '2.5.1', '2.5'}
keep = [col for i, col in enumerate(df_l.columns) if (i + 1) not in REMOVE_ORIG]
keep = [col for col in keep if col not in REMOVE_EXTRA]
df_l = df_l[keep]
for col in df_l.columns:
    df_l[col] = df_l[col].interpolate(method='linear', limit=10, limit_direction='both')
df_l_smooth = apply_lowess_full(df_l)
data_l = df_l_smooth.T * 100
concs_l = [get_conc(c, KNOWN_MEX) for c in data_l.index]
groups_l = OrderedDict()
for i, (wn, conc) in enumerate(zip(data_l.index, concs_l)):
    groups_l.setdefault(conc, []).append((i, wn, data_l.iloc[i].mean()))
new_order = []
for conc in groups_l:
    new_order.extend([idx for idx, _, _ in sorted(groups_l[conc], key=lambda x: x[2], reverse=True)])
data_l = data_l.iloc[new_order]
with pd.ExcelWriter(FIG2 / 'Fig_2l_Mexiletine_Contractility_data.xlsx', engine='openpyxl') as w:
    data_l.to_excel(w, sheet_name='Heatmap_Processed', index=True)
print(f'  {data_l.shape[0]} wells x {data_l.shape[1]} timepoints')

print('\nDone. All data files contain processed/plotted data.')
