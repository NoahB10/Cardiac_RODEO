"""
3D Raw Data Visualization with Concentration-wise Averages for Organoid Drug Screens

Functions:
- load_grid_csv(file_path): Load a time x concentration grid (e.g., O2_mean.csv) to tidy format.
- compute_concentration_averages(df): Average across duplicate concentration columns at each time.
- plot_3d_raw_with_averages(drug_name, response_name, df_raw, df_avg, save_dir): Produce 3D scatter of raw points and overlay averaged points/lines.
- process_drug_folder(drug_folder): Generate plots for O2_mean and Amp_std in a given drug folder.
- main(): Iterate drug folders and generate all plots.

Parameters:
- Input CSVs must have time values in the index (first column) and numeric concentration headers (may contain duplicates).
- Outputs are saved under model_visualizations_raw/[Drug]_[Response]_[raw3d].png

Notes:
- Concentrations are used as-is (raw units), no normalization by Cmax here.
- Averages are computed by grouping duplicate concentration columns and averaging across them per time.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 (needed for 3D projection)
from pathlib import Path


def load_grid_csv(file_path: str) -> pd.DataFrame:
    """
    Load a grid CSV where rows are time points and columns are concentrations.

    Returns a tidy DataFrame with columns: ['time', 'concentration', 'response']
    - time: float (hours)
    - concentration: float (raw units as in header)
    - response: float
    """
    df = pd.read_csv(file_path, index_col=0)

    # Filter numeric time indices only
    numeric_index = []
    for idx in df.index:
        try:
            numeric_index.append(float(idx))
        except Exception:
            pass
    df = df.loc[df.index.astype(str).isin(map(str, numeric_index))]

    # Cast index to float time
    df.index = df.index.astype(float)

    # Keep only numeric concentration columns
    numeric_cols = []
    for col in df.columns:
        try:
            _ = float(col)
            numeric_cols.append(col)
        except Exception:
            continue
    df = df[numeric_cols]

    # Build tidy dataframe (long format)
    tidy_rows = []
    for col in df.columns:
        conc_val = float(col)
        series = df[col]
        for t, val in series.items():
            if pd.notna(val):
                tidy_rows.append((float(t), float(conc_val), float(val)))
    tidy = pd.DataFrame(tidy_rows, columns=["time", "concentration", "response"])
    return tidy


essential_cols = ["time", "concentration", "response"]

def compute_concentration_averages(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Given tidy data with possibly duplicate concentrations (replicates),
    compute the average response per (time, concentration).
    Returns tidy DataFrame with the same columns.
    """
    if not set(essential_cols).issubset(df_raw.columns):
        raise ValueError("df_raw must contain columns: time, concentration, response")
    grouped = df_raw.groupby(["time", "concentration"], as_index=False)["response"].mean()
    return grouped


def plot_3d_raw_with_averages(drug_name: str, response_name: str,
                               df_raw: pd.DataFrame, df_avg: pd.DataFrame,
                               save_dir: str) -> None:
    """
    Create a 3D scatter of raw data and overlay averaged values at each
    (time, concentration). Also connect averaged values across time for
    each concentration to highlight the trend.
    """
    if df_raw.empty or df_avg.empty:
        return

    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{drug_name}_{response_name}_raw3d.png")

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Raw points (semi-transparent)
    ax.scatter(df_raw["time"].values,
               df_raw["concentration"].values,
               df_raw["response"].values,
               c='tab:red', alpha=0.35, s=12, label='Raw points')

    # Averaged points (bigger, colored)
    ax.scatter(df_avg["time"].values,
               df_avg["concentration"].values,
               df_avg["response"].values,
               c='tab:blue', alpha=0.9, s=20, label='Averaged per concentration')

    # Connect averaged values across time for each concentration
    for conc_val, df_c in df_avg.groupby("concentration"):
        df_c_sorted = df_c.sort_values("time")
        ax.plot(df_c_sorted["time"].values,
                df_c_sorted["concentration"].values,
                df_c_sorted["response"].values,
                color='tab:blue', alpha=0.6, linewidth=1.0)

    ax.set_title(f"{drug_name} - {response_name}: Raw 3D with Concentration-wise Averages", pad=16)
    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Concentration (raw units)")
    ax.set_zlabel(f"{response_name} response")

    # Make the plot easier to read
    ax.grid(True, alpha=0.2)
    ax.view_init(elev=22, azim=40)
    ax.legend(loc='upper left')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def process_drug_folder(drug_folder: str) -> None:
    """
    Generate raw 3D plots with averaged values for both O2_mean and Amp_std
    in the provided drug folder.
    """
    drug_name = Path(drug_folder).name
    out_dir = os.path.join("model_visualizations_raw")
    os.makedirs(out_dir, exist_ok=True)

    for response_name in ["O2_mean", "Amp_std"]:
        csv_path = os.path.join(drug_folder, f"{response_name}.csv")
        if not os.path.exists(csv_path):
            continue
        try:
            df_raw = load_grid_csv(csv_path)
            if df_raw.empty:
                continue
            df_avg = compute_concentration_averages(df_raw)
            plot_3d_raw_with_averages(drug_name, response_name, df_raw, df_avg, out_dir)
        except Exception as e:
            print(f"Failed for {drug_name} {response_name}: {e}")


def main() -> None:
    """
    Iterate over immediate subfolders (one per drug) and create plots.
    """
    base_dir = "."
    for entry in os.listdir(base_dir):
        full = os.path.join(base_dir, entry)
        if os.path.isdir(full) and entry not in ["__pycache__", "model_visualizations", "model_visualizations_improved"]:
            process_drug_folder(full)
    print("Raw 3D plots saved to model_visualizations_raw/")


if __name__ == "__main__":
    main()






