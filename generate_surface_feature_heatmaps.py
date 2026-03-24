"""Generate O2 heatmaps for Vioxx, Amiodarone, and Mexiletine.

Uses the same pipeline as Figure 2 heatmaps:
  1. Load sorted O2 CSV
  2. Remove outlier data points (O2 > 80 or < 0 → NaN)
  3. Drop wells with > 50% NaN
  4. Linear interpolation within each well
  5. LOWESS smoothing (w=16) per-well along time
  6. Transpose → plot with blue-white-red colormap

Output: Output/Surface_Feature_Comparison/
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import re
from pathlib import Path
from collections import OrderedDict
from matplotlib.colors import LinearSegmentedColormap
from statsmodels.nonparametric.smoothers_lowess import lowess as lowess_func

# ── Constants ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / 'Cleaned_Data' / 'Surface_Feature_Comparison'
HEATMAP_DIR = PROJECT_ROOT / 'Cleaned_Data' / 'Heatmaps'
SAVE_DPI = 600
LOWESS_W = 16
HEATMAP_BLUE = '#123BFF'
HEATMAP_RED = '#FF2908'

# Drug configs: (folder_name, display_name, known_drop_wells)
DRUGS = [
    ('Vioxx', 'Vioxx', []),
    ('Amiodarone', 'Amiodarone', []),
    ('Mexiletine', 'Mexiletine', []),
]

O2_OUTLIER_UPPER = 80   # O2 readings above this are sensor artifacts
O2_OUTLIER_LOWER = 0    # Negative readings are sensor artifacts
WELL_NAN_THRESHOLD = 0.5  # Drop well if >50% of readings are NaN after outlier removal


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_base_conc(col_name):
    """Strip pandas duplicate suffixes: '10.1' -> 10, '0.625.2' -> 0.625."""
    s = str(col_name)
    m = re.match(r'^(.+?)\.(\d)$', s)
    if m:
        base = m.group(1)
        try:
            return float(base)
        except ValueError:
            pass
    try:
        return float(s)
    except ValueError:
        return None


def _conc_label(col_name):
    val = _get_base_conc(col_name)
    if val is None:
        return str(col_name)
    return str(int(val)) if val == int(val) else str(val)


def _apply_lowess(df):
    """Per-well LOWESS smoothing along time axis."""
    smoothed = df.copy().astype(float)
    for col in smoothed.columns:
        series = smoothed[col]
        valid = series.dropna()
        if len(valid) < 3:
            continue
        frac = min(1.0, max(LOWESS_W, 1) / len(valid))
        fitted = lowess_func(valid.values, np.arange(len(valid)),
                             frac=frac, return_sorted=False)
        target = smoothed.index.get_indexer(valid.index)
        smoothed.iloc[target, smoothed.columns.get_loc(col)] = fitted
    return smoothed


def _remove_outlier_points(df, upper=O2_OUTLIER_UPPER, lower=O2_OUTLIER_LOWER):
    """Replace individual outlier data points with NaN."""
    df = df.copy()
    mask = (df > upper) | (df < lower)
    n_outliers = mask.sum().sum()
    if n_outliers > 0:
        print(f"    Replaced {n_outliers} outlier points (>{upper} or <{lower}) with NaN")
    df[mask] = np.nan
    return df


def _drop_bad_wells(df, threshold=WELL_NAN_THRESHOLD):
    """Drop wells with too many NaN values."""
    nan_frac = df.isna().mean()
    bad = nan_frac[nan_frac > threshold].index.tolist()
    if bad:
        labels = [_conc_label(c) for c in bad]
        print(f"    Dropped {len(bad)} wells (>{threshold*100:.0f}% NaN): {labels}")
        df = df.drop(columns=bad)
    return df


def generate_heatmap(drug_folder, drug_name, drop_wells=None):
    """Generate an O2 heatmap following the Figure 2 pipeline."""
    csv_path = HEATMAP_DIR / drug_folder / 'O2_mean_sorted.csv'
    if not csv_path.exists():
        print(f"  ERROR: {csv_path} not found")
        return

    print(f"\n  Processing {drug_name}...")
    print(f"    Source: {csv_path}")

    # 1. Load
    df_raw = pd.read_csv(csv_path, index_col=0)
    n_wells_orig = len(df_raw.columns)
    n_times = len(df_raw.index)
    print(f"    Loaded: {n_wells_orig} wells × {n_times} time points")

    # 2. Drop known bad wells
    if drop_wells:
        cols_to_drop = [c for c in drop_wells if c in df_raw.columns]
        if cols_to_drop:
            df_raw = df_raw.drop(columns=cols_to_drop)
            print(f"    Dropped {len(cols_to_drop)} known bad wells")

    # 3. Remove outlier data points (sensor artifacts)
    df_clean = _remove_outlier_points(df_raw)

    # 4. Drop wells with excessive NaN
    df_clean = _drop_bad_wells(df_clean)
    n_wells_final = len(df_clean.columns)
    print(f"    Wells remaining: {n_wells_final}/{n_wells_orig}")

    # 5. Linear interpolation within each well
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].interpolate(
            method='linear', limit=10, limit_direction='both')

    # 6. LOWESS smoothing
    df_smooth = _apply_lowess(df_clean)

    # 7. Transpose: rows=wells, cols=time
    data = df_smooth.T
    data = data.clip(upper=100)  # O2 cap

    # 8. Labels
    y_labels = [_conc_label(c) for c in data.index.tolist()]
    x_labels = [str(t) for t in data.columns.tolist()]

    # 9. Plot
    cmap = LinearSegmentedColormap.from_list(
        'cardiac_rodeo', [HEATMAP_BLUE, 'white', HEATMAP_RED])
    cmap.set_bad('white')

    fig, ax = plt.subplots(figsize=(12, 7))
    sns.heatmap(
        data, annot=False, cmap=cmap,
        vmin=0, vmax=100,
        cbar_kws={'shrink': 0.8},
        xticklabels=x_labels, yticklabels=y_labels,
        square=False, linewidths=0, ax=ax
    )

    ax.set_xlabel('Time from Exposure (h)', fontsize=22, fontweight='bold')
    ax.set_ylabel(f'{drug_name} Dose', fontsize=22, fontweight='bold')

    # X ticks — thinned, straight
    n_x = len(x_labels)
    x_step = max(1, n_x // 10)
    ax.set_xticks(range(0, n_x, x_step))
    ax.set_xticklabels([x_labels[i] for i in range(0, n_x, x_step)],
                        rotation=0, ha='center', fontsize=16, fontweight='bold')

    # Y ticks — one per concentration group
    conc_groups = OrderedDict()
    for i, lbl in enumerate(y_labels):
        conc_groups.setdefault(lbl, []).append(i)
    tick_positions = [(indices[0] + indices[-1]) / 2 + 0.5
                      for indices in conc_groups.values()]
    ax.set_yticks(tick_positions)
    ax.set_yticklabels(list(conc_groups.keys()), fontsize=16,
                        rotation=0, fontweight='bold')

    # Thick black borders
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
        spine.set_linewidth(2.0)
    ax.tick_params(width=1.5)

    # Colorbar
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=14, width=1.5)
    cbar.set_label(r'$O_2$ (% Air)', fontsize=16, fontweight='bold')
    cbar.outline.set_linewidth(2.0)
    cbar.set_ticks([t for t in range(0, 101, 20)])

    fig.tight_layout()

    # Save
    drug_dir = OUTPUT_DIR / drug_folder
    drug_dir.mkdir(parents=True, exist_ok=True)

    png_path = drug_dir / f'{drug_name}_O2_Heatmap.png'
    fig.savefig(str(png_path), dpi=SAVE_DPI, bbox_inches='tight',
                pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f"    Saved: {png_path.relative_to(PROJECT_ROOT)}")

    # Save data xlsx for provenance
    xlsx_path = drug_dir / f'{drug_name}_O2_Heatmap_data.xlsx'
    with pd.ExcelWriter(str(xlsx_path), engine='openpyxl') as writer:
        # Smoothed data (what's plotted)
        data.to_excel(writer, sheet_name='Smoothed')
        # Raw data before processing
        df_raw.T.to_excel(writer, sheet_name='Raw')
        # Summary
        summary = pd.DataFrame({
            'Drug': [drug_name],
            'Source': [str(csv_path)],
            'Wells_Original': [n_wells_orig],
            'Wells_Final': [n_wells_final],
            'LOWESS_Window': [LOWESS_W],
            'Outlier_Upper': [O2_OUTLIER_UPPER],
            'Outlier_Lower': [O2_OUTLIER_LOWER],
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)
    print(f"    Saved: {xlsx_path.relative_to(PROJECT_ROOT)}")

    return png_path


def main():
    print("=" * 60)
    print("Surface Feature Comparison — O2 Heatmaps")
    print("=" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for drug_folder, drug_name, drop_wells in DRUGS:
        generate_heatmap(drug_folder, drug_name, drop_wells)

    print(f"\nDone. Output in: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == '__main__':
    main()
