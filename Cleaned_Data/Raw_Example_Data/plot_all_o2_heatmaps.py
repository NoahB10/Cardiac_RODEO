"""Generate O2 heatmaps for ALL drugs using the Figure 2 pipeline.

Pipeline:
  1. Load sorted O2 CSV from Cleaned_Data/Heatmaps/{Drug}/O2_mean_sorted.csv
  2. Remove outlier data points (O2 > 80 or < 0 → NaN)
  3. Drop wells with > 50% NaN
  4. Linear interpolation within each well (limit=10)
  5. LOWESS smoothing (w=16) per-well along time
  6. Transpose → plot with blue-white-red colormap, grouped Y-axis labels

Output: Output/Surface_Feature_Comparison/O2_Heatmaps/
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2]))

import figure_config
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
from pathlib import Path
from collections import OrderedDict
from matplotlib.colors import LinearSegmentedColormap
from statsmodels.nonparametric.smoothers_lowess import lowess as lowess_func

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEATMAP_DIR = PROJECT_ROOT / 'Cleaned_Data' / 'Heatmaps'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / 'Surface_Feature_Comparison' / 'O2_Heatmaps'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SAVE_DPI = 600
LOWESS_W = 16
HEATMAP_BLUE = '#123BFF'
HEATMAP_RED = '#FF2908'

O2_OUTLIER_UPPER = 80
O2_OUTLIER_LOWER = 0
WELL_NAN_THRESHOLD = 0.5

SKIP_FOLDERS = {'Output', 'Daunorubicin (F03)', 'Doxorubicin (G03)',
                'Epirubicin (F03)', 'Vandetanib (G11)'}

FIG3_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures' / 'Fig_3'
FIG3_DIR.mkdir(parents=True, exist_ok=True)

# Rows to remove (1-indexed) per drug
DRUG_SKIP_ROWS = {
    'Dactinomycin': {1, 8, 12, 16, 20, 24, 27},
    'Doxorubicin': {9, 12},
    'Nifedipine': {5, 6},
    'Mexiletine': {2, 3, 9, 13, 20},
}

# Drugs chosen for Fig 3 heatmap options
FIG3_CHOSEN = {'Doxorubicin', 'Nifedipine', 'Dactinomycin', 'Mexiletine'}


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


def _remove_outlier_points(df):
    """Replace individual outlier data points with NaN."""
    df = df.copy()
    mask = (df > O2_OUTLIER_UPPER) | (df < O2_OUTLIER_LOWER)
    n_outliers = mask.sum().sum()
    if n_outliers > 0:
        print(f"    Replaced {n_outliers} outlier points with NaN")
    df[mask] = np.nan
    return df


def _drop_bad_wells(df):
    """Drop wells with too many NaN values."""
    nan_frac = df.isna().mean()
    bad = nan_frac[nan_frac > WELL_NAN_THRESHOLD].index.tolist()
    if bad:
        labels = [_conc_label(c) for c in bad]
        print(f"    Dropped {len(bad)} wells (>{WELL_NAN_THRESHOLD*100:.0f}% NaN): {labels}")
        df = df.drop(columns=bad)
    return df


def generate_heatmap(drug_folder, drug_name):
    """Generate an O2 heatmap following the Figure 2 pipeline."""
    csv_path = HEATMAP_DIR / drug_folder / 'O2_mean_sorted.csv'
    if not csv_path.exists():
        print(f"  SKIP: no O2_mean_sorted.csv")
        return

    print(f"  Processing {drug_name}...")

    # 1. Load
    df_raw = pd.read_csv(csv_path, index_col=0)
    n_wells_orig = len(df_raw.columns)
    print(f"    {n_wells_orig} wells × {len(df_raw.index)} time points")

    # 2. Remove outlier data points
    df_clean = _remove_outlier_points(df_raw)

    # 3. Drop wells with excessive NaN
    df_clean = _drop_bad_wells(df_clean)
    n_wells_final = len(df_clean.columns)

    # 4. Linear interpolation within each well
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].interpolate(
            method='linear', limit=10, limit_direction='both')

    # 5. LOWESS smoothing
    df_smooth = _apply_lowess(df_clean)

    # 6. Transpose: rows=wells, cols=time
    data = df_smooth.T
    data = data.clip(upper=100)

    # 6b. Remove manually flagged rows (1-indexed)
    skip_rows = DRUG_SKIP_ROWS.get(drug_name, set())
    if skip_rows:
        keep = [i for i in range(len(data)) if (i + 1) not in skip_rows]
        data = data.iloc[keep]
        print(f"    Removed rows {sorted(skip_rows)}, {len(data)} wells remain")

    # 7. Labels — concentration groups for Y axis
    y_labels = [_conc_label(c) for c in data.index.tolist()]
    # Row-numbered labels for review (1-indexed)
    y_labels_numbered = [f'{i+1}: {lbl}' for i, lbl in enumerate(y_labels)]
    x_labels = [str(t) for t in data.columns.tolist()]

    # 8. Plot
    cmap = LinearSegmentedColormap.from_list(
        'cardiac_rodeo', [HEATMAP_BLUE, 'white', HEATMAP_RED])
    cmap.set_bad('white')

    n_wells = len(y_labels)
    fig_height = max(5.0, min(8.0, n_wells * 0.22))

    fig, ax = plt.subplots(figsize=(12, fig_height))
    sns.heatmap(
        data, annot=False, cmap=cmap,
        vmin=0, vmax=100,
        cbar_kws={'shrink': 0.8},
        xticklabels=x_labels, yticklabels=y_labels_numbered,
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

    # Y ticks — show every row with number
    ax.set_yticks([i + 0.5 for i in range(n_wells)])
    ax.set_yticklabels(y_labels_numbered, fontsize=10,
                        rotation=0, fontweight='bold')

    # Thick black borders
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
        spine.set_linewidth(2.0)
    ax.tick_params(width=1.5)

    # Colorbar
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=14, width=1.5)
    cbar.set_label('Oxygen (% Air)', fontsize=16, fontweight='bold')
    cbar.outline.set_linewidth(2.0)
    cbar.set_ticks([t for t in range(0, 101, 20)])

    fig.tight_layout()

    safe_name = drug_name.replace(' ', '_')
    out = OUTPUT_DIR / f'{safe_name}_O2_Heatmap.png'
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches='tight',
                pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f"    Saved: {out.name}  ({n_wells_final}/{n_wells_orig} wells)")

    # Save to Fig_3 for chosen drugs
    if drug_name in FIG3_CHOSEN:
        fig3_png = FIG3_DIR / f'Fig_3a_{safe_name}_O2_Heatmap.png'
        fig3_xlsx = FIG3_DIR / f'Fig_3a_{safe_name}_O2_Heatmap_data.xlsx'

        # Numbered review version (for identifying rows to remove)
        fig_num, ax_num = plt.subplots(figsize=(12, fig_height))
        sns.heatmap(
            data, annot=False, cmap=cmap,
            vmin=0, vmax=100,
            cbar_kws={'shrink': 0.8},
            xticklabels=x_labels, yticklabels=y_labels_numbered,
            square=False, linewidths=0, ax=ax_num
        )
        ax_num.set_xlabel('Time from Exposure (h)', fontsize=22, fontweight='bold')
        ax_num.set_ylabel(f'{drug_name} Dose', fontsize=22, fontweight='bold')
        n_x = len(x_labels)
        x_step = max(1, n_x // 10)
        ax_num.set_xticks(range(0, n_x, x_step))
        ax_num.set_xticklabels([x_labels[i] for i in range(0, n_x, x_step)],
                               rotation=0, ha='center', fontsize=16, fontweight='bold')
        ax_num.set_yticks([i + 0.5 for i in range(n_wells)])
        ax_num.set_yticklabels(y_labels_numbered, fontsize=10, rotation=0, fontweight='bold')
        for spine in ax_num.spines.values():
            spine.set_edgecolor('black')
            spine.set_linewidth(2.0)
        ax_num.tick_params(width=1.5)
        cbar_num = ax_num.collections[0].colorbar
        cbar_num.ax.tick_params(labelsize=14, width=1.5)
        cbar_num.set_label('Oxygen (% Air)', fontsize=16, fontweight='bold')
        cbar_num.outline.set_linewidth(2.0)
        fig_num.tight_layout()
        fig3_numbered = FIG3_DIR / f'Fig_3a_{safe_name}_O2_Heatmap_NUMBERED.png'
        fig_num.savefig(str(fig3_numbered), dpi=SAVE_DPI, bbox_inches='tight',
                        pad_inches=0.05, facecolor='white')
        plt.close(fig_num)
        print(f"    Fig3 numbered: {fig3_numbered.name}")

        # Clean version for Fig 3: axis labels but no ticks, no colorbar
        fig2, ax2 = plt.subplots(figsize=(7, 7))
        sns.heatmap(
            data, annot=False, cmap=cmap,
            vmin=0, vmax=100,
            cbar=False,
            xticklabels=False, yticklabels=False,
            square=False, linewidths=0, ax=ax2
        )
        ax2.set_xlabel('Time from Exposure (h)', fontsize=22, fontweight='bold')
        ax2.set_ylabel(f'{drug_name} Dose', fontsize=22, fontweight='bold')
        ax2.set_xticks([])
        ax2.set_yticks([])
        for spine in ax2.spines.values():
            spine.set_visible(False)
        fig2.tight_layout()
        fig2.savefig(str(fig3_png), dpi=SAVE_DPI, bbox_inches='tight',
                     pad_inches=0.02, facecolor='white')
        plt.close(fig2)
        print(f"    Fig3: {fig3_png.name}")

        # Excel data
        with pd.ExcelWriter(str(fig3_xlsx), engine='openpyxl') as writer:
            data.to_excel(writer, sheet_name='Smoothed')
            df_raw.T.to_excel(writer, sheet_name='Raw')
            summary = pd.DataFrame({
                'Drug': [drug_name],
                'Source': [str(csv_path)],
                'Wells_Original': [n_wells_orig],
                'Wells_Final': [len(data)],
                'Rows_Removed': [str(sorted(skip_rows)) if skip_rows else 'None'],
                'LOWESS_Window': [LOWESS_W],
                'Outlier_Upper': [O2_OUTLIER_UPPER],
                'Outlier_Lower': [O2_OUTLIER_LOWER],
                'Pipeline': ['Load sorted CSV → Remove O2>80/<0 → Drop >50% NaN wells → '
                             'Linear interp (limit=10) → LOWESS w=16 per-well → Clip 100'],
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)
        print(f"    Fig3: {fig3_xlsx.name}")


if __name__ == '__main__':
    folders = sorted([d for d in HEATMAP_DIR.iterdir()
                      if d.is_dir() and d.name not in SKIP_FOLDERS])
    print(f'Processing {len(folders)} drugs...\n')
    for folder in folders:
        # Clean display name (remove plate codes like "(G03)")
        display_name = folder.name.split(' (')[0]
        generate_heatmap(folder.name, display_name)
    print(f'\nDone. All heatmaps in: {OUTPUT_DIR}')
