"""
Extracts Doxorubicin per-well raw data, applies LOWESS w=8 (no outlier removal),
saves raw + final CSVs, and generates comparison images.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from statsmodels.nonparametric.smoothers_lowess import lowess
from pathlib import Path

PROJECT_ROOT = Path("C:/Users/NoahB/Documents/HebrewU Bioengineering/Cardiac_RODEO")
CLEANED_DATA = PROJECT_ROOT / 'Cleaned_Data'
HEATMAP_DIR  = CLEANED_DATA / 'Heatmaps' / 'Doxorubicin (G03)'
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR      = Path(__file__).parent

HEATMAP_BLUE = '#123BFF'
HEATMAP_RED  = '#FF2908'
CMAP = LinearSegmentedColormap.from_list('cardiac_rodeo', [HEATMAP_BLUE, 'white', HEATMAP_RED])
CMAP.set_bad('white')

LOWESS_WINDOW = 8


def apply_lowess_per_column(df, window=LOWESS_WINDOW):
    smoothed = df.copy().astype(float)
    for col in smoothed.columns:
        series = smoothed[col]
        valid = series.dropna()
        if len(valid) < 3:
            continue
        first_idx = valid.index[0]
        first_val = valid.iloc[0]
        to_smooth = valid.iloc[1:]
        if len(to_smooth) < 2:
            continue
        frac = min(1.0, max(window, 1) / len(to_smooth))
        fitted = lowess(to_smooth.values, np.arange(len(to_smooth)),
                        frac=frac, return_sorted=False)
        target = smoothed.index.get_indexer(to_smooth.index)
        smoothed.iloc[target, smoothed.columns.get_loc(col)] = fitted
        smoothed.at[first_idx, col] = first_val
    return smoothed


def clean_concentration_labels(labels):
    """Remove pandas .1 .2 suffixes from duplicate concentration columns."""
    import re
    cleaned = []
    for label in labels:
        s = str(label)
        m = re.match(r'^(\d+\.?\d*?)(?:\.\d+)?$', s)
        if m:
            val = float(m.group(1))
            cleaned.append(str(int(val)) if val == int(val) else str(val))
        else:
            cleaned.append(s)
    return cleaned


def plot_heatmap_comparison(df_raw, df_final, label, out_path):
    vmin = min(np.nanpercentile(df_raw.values, 2), np.nanpercentile(df_final.values, 2))
    vmax = max(np.nanpercentile(df_raw.values, 98), np.nanpercentile(df_final.values, 98))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f'Doxorubicin {label} — LOWESS w={LOWESS_WINDOW} (no outlier removal)',
                 fontsize=10, fontweight='bold')

    titles = ['Raw', f'LOWESS w={LOWESS_WINDOW}']
    datasets = [df_raw.T, df_final.T]

    for ax, data, title in zip(axes, datasets, titles):
        y_labels = clean_concentration_labels(data.index.tolist())
        sns.heatmap(data, annot=False, cmap=CMAP, vmin=vmin, vmax=vmax,
                    cbar=False, xticklabels=False, yticklabels=False,
                    linewidths=0, ax=ax)
        ax.set_title(title, fontsize=8, fontweight='bold')
        n_x = data.shape[1]
        x_step = max(1, n_x // 8)
        ax.set_xticks([i + 0.5 for i in range(0, n_x, x_step)])
        ax.set_xticklabels([str(data.columns[i]) for i in range(0, n_x, x_step)],
                           rotation=45, ha='right', fontsize=5)
        ax.set_xlabel('Time (h)', fontsize=6)
        n_y = data.shape[0]
        y_step = max(1, n_y // 8)
        ax.set_yticks([i + 0.5 for i in range(0, n_y, y_step)])
        ax.set_yticklabels([y_labels[i] for i in range(0, n_y, y_step)], fontsize=5, rotation=0)
        ax.set_ylabel('Conc (mM)', fontsize=6)

    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, fraction=0.015, pad=0.02)
    cbar.ax.tick_params(labelsize=5)
    cbar.set_label(label, fontsize=6)

    plt.tight_layout()
    fig.savefig(str(out_path), dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def make_unique_columns(columns):
    """Make duplicate column names unique by appending .1, .2, etc."""
    seen = {}
    new_cols = []
    for c in columns:
        key = str(c)
        if key in seen:
            seen[key] += 1
            new_cols.append(f"{key}.{seen[key]}")
        else:
            seen[key] = 0
            new_cols.append(key)
    return new_cols


if __name__ == '__main__':
    # --- Load O2 mean (rows=conc, cols=time) -> transpose to (rows=time, cols=conc) ---
    df_o2 = pd.read_excel(
        CLEANED_DATA / 'DrugScreen19.11.25_compiled_O2_mean.xlsx',
        sheet_name='Doxorubicin O2_mean', index_col=0
    ).T
    df_o2.index = pd.to_numeric(df_o2.index, errors='coerce')
    df_o2 = df_o2.astype(float)
    df_o2.columns = make_unique_columns(df_o2.columns)

    # --- Load Contractility (rows=time, cols=conc) ---
    df_amp = pd.read_excel(
        CLEANED_DATA / 'Stage2_Tables_compiled_Amp_std_raw.xlsx',
        sheet_name='Doxorubicin (G03)', index_col=0
    ).astype(float)
    df_amp.index = pd.to_numeric(df_amp.index, errors='coerce')

    # Save raw CSVs
    df_o2.to_csv(HEATMAP_DIR / 'O2_mean.csv')
    df_amp.to_csv(HEATMAP_DIR / 'Amp_std.csv')
    print(f"Saved raw CSVs to {HEATMAP_DIR.name}/")
    print(f"  O2_mean.csv: {df_o2.shape}")
    print(f"  Amp_std.csv: {df_amp.shape}")

    for df_raw, csv_name, label in [
        (df_o2,  'O2_mean.csv',  'O2 Mean'),
        (df_amp, 'Amp_std.csv',  'Contractility'),
    ]:
        print(f"\n--- {label} ---")
        n_nan = int(df_raw.isna().sum().sum())
        print(f"  NaN in raw data: {n_nan}")

        # Interpolate any existing NaN gaps
        df_interp = df_raw.copy()
        for col in df_interp.columns:
            df_interp[col] = df_interp[col].interpolate(
                method='linear', limit=10, limit_direction='both'
            )
        remaining = int(df_interp.isna().sum().sum())
        print(f"  Remaining NaN after interpolation: {remaining}")

        # Apply LOWESS w=8
        df_final = apply_lowess_per_column(df_interp)
        print(f"  LOWESS w={LOWESS_WINDOW} applied")

        # Save final CSV
        out_csv = HEATMAP_DIR / csv_name.replace('.csv', '_final.csv')
        df_final.to_csv(out_csv)
        print(f"  Final CSV: {out_csv.name}")

        # Comparison plot (raw vs LOWESS)
        plot_heatmap_comparison(df_raw, df_final, label,
                                OUT_DIR / f'doxorubicin_{label.replace(" ", "_")}_comparison.png')

    print("\nDone.")
