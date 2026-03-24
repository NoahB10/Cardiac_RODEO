"""
Heart Rate (BPM) Analysis for Epirubicin and Doxorubicin.

Based on the pipeline in heart_rate_analysis_script.py.py, adapted for
Epirubicin (B04) and Doxorubicin (G03).

Step 1: Generate comprehensive BPM table across ALL concentrations, wells,
        and timepoints. This table is used to identify interesting wells
        for focused investigation.

Step 2 (future): Focused analysis of selected wells with harmonic doubling
        detection, waveform plots, and half-power filtering.

Data source: Cleaned_Data/Stage1_Raw_Relaxed/ (extracted from Raw_Tables.zip)

Usage:
    python heart_rate_anthracyclines.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.signal import welch

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

# Path discovery
current_dir = Path.cwd()
if current_dir.name == 'Prediction_Models':
    PROJECT_ROOT = current_dir.parent
elif (current_dir / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir
elif (current_dir.parent / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir.parent
else:
    PROJECT_ROOT = current_dir

RELAXED_DIR = PROJECT_ROOT / "Cleaned_Data" / "Stage1_Raw_Relaxed"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "HeartRate_Analysis" / "Anthracyclines"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# QC Parameters
SKIP_INITIAL_ROWS = 5
SKIP_FINAL_ROWS = 1
DOM_FREQ_BAND = (0.1, 2.5)  # Hz (6-150 BPM)
FILENAME_HOUR_PATTERN = re.compile(r"_(\d+)h_", re.IGNORECASE)

# Drug configurations
DRUG_CONFIG = {
    "epirubicin": {
        "folder": "Epirubicin (B04)",
        "baseline_hour": 0,
        "comparison_hour": 24,
        "cmax_uM": 0.45,
    },
    "doxorubicin": {
        "folder": "Doxorubicin (G03)",
        "baseline_hour": 0,
        "comparison_hour": 24,
        "cmax_uM": 0.13,
    },
}

# All timepoints to collect BPM for
ALL_HOURS = [0, 3, 4, 6, 9, 12, 14, 17, 19, 22, 24, 27, 30, 32, 35, 38,
             40, 43, 45, 48, 51, 53, 56, 59, 61, 64, 66, 69, 72, 74, 77,
             80, 82, 85, 88, 90, 93, 96]


# ---------------------------------------------------------------------------
# Helper functions (from heart_rate_analysis_script.py.py)
# ---------------------------------------------------------------------------
def discover_concentrations(drug_folder: Path) -> List[str]:
    if not drug_folder.exists():
        return []
    concentrations = []
    for item in drug_folder.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if name_lower.endswith('mm') or name_lower.endswith('um'):
                concentrations.append(item.name)
    return sorted(concentrations)


def extract_hour_from_filename(filename: str) -> Optional[int]:
    match = FILENAME_HOUR_PATTERN.search(filename)
    if match:
        return int(match.group(1))
    return None


def get_well_name(filename: str) -> str:
    match = re.match(r"^([A-P]\d{2})", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "UNKNOWN"


def load_relaxed_log(filepath: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(filepath)
        if len(df) > SKIP_INITIAL_ROWS + SKIP_FINAL_ROWS:
            df = df.iloc[SKIP_INITIAL_ROWS:-SKIP_FINAL_ROWS].reset_index(drop=True)
        elif len(df) > SKIP_INITIAL_ROWS:
            df = df.iloc[SKIP_INITIAL_ROWS:].reset_index(drop=True)
        required_cols = ["time_s", "amp1_vpp"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return pd.DataFrame()
        df = df.dropna(subset=["time_s", "amp1_vpp"])
        return df
    except Exception:
        return pd.DataFrame()


def compute_dominant_frequency(time_s: np.ndarray, signal: np.ndarray,
                               freq_band: Tuple[float, float] = (0.5, 2.0)):
    if len(signal) < 4:
        return float("nan"), np.array([]), np.array([])
    signal_detrended = signal - np.nanmean(signal)
    order = np.argsort(time_s)
    time_sorted = time_s[order]
    signal_sorted = signal_detrended[order]
    diffs = np.diff(time_sorted)
    if len(diffs) == 0 or np.allclose(diffs, 0):
        return float("nan"), np.array([]), np.array([])
    dt = np.median(diffs)
    if dt <= 0:
        return float("nan"), np.array([]), np.array([])
    fs = 1.0 / dt
    freqs, power = welch(signal_sorted, fs=fs, nperseg=min(256, len(signal_sorted)))
    band_mask = (freqs >= freq_band[0]) & (freqs <= freq_band[1])
    if not band_mask.any():
        return float("nan"), freqs, power
    band_freqs = freqs[band_mask]
    band_power = power[band_mask]
    dominant_freq = float(band_freqs[np.argmax(band_power)])
    return dominant_freq, freqs, power


def detect_harmonic_doubling(freqs, power, detected_freq, threshold=0.7):
    """Check if detected frequency is a harmonic double."""
    if detected_freq <= 1.0 or len(freqs) == 0:
        return False, detected_freq
    half_freq = detected_freq / 2.0
    # Find power at half frequency
    half_idx = np.argmin(np.abs(freqs - half_freq))
    peak_idx = np.argmin(np.abs(freqs - detected_freq))
    if power[peak_idx] == 0:
        return False, detected_freq
    ratio = power[half_idx] / power[peak_idx]
    if ratio >= threshold:
        return True, half_freq
    return False, detected_freq


def find_files_for_concentration(drug_folder: Path, concentration: str,
                                 target_hour: int, tolerance: int = 1) -> List[Path]:
    conc_dir = drug_folder / concentration
    if not conc_dir.exists():
        return []
    matching_files = []
    for csv_file in conc_dir.glob("*.csv"):
        hour = extract_hour_from_filename(csv_file.name)
        if hour is not None and abs(hour - target_hour) <= tolerance:
            matching_files.append(csv_file)
    return sorted(matching_files)


def select_best_file(files: List[Path]) -> Path:
    def starts_at_zero(filepath: Path) -> bool:
        try:
            df = pd.read_csv(filepath, nrows=1)
            if "time_s" in df.columns:
                return abs(df.iloc[0]["time_s"]) < 0.05
        except Exception:
            pass
        return False
    zero_start_files = [f for f in files if starts_at_zero(f)]
    candidates = zero_start_files if zero_start_files else files
    return max(candidates, key=lambda f: f.stat().st_size)


def bpm_for_hour(files: List[Path]):
    if not files:
        return float("nan"), None, None
    file_sel = select_best_file(files)
    df = load_relaxed_log(file_sel)
    if df.empty:
        return float("nan"), None, file_sel.name
    hour = extract_hour_from_filename(file_sel.name)
    freq_hz, freqs, power = compute_dominant_frequency(
        df["time_s"].values, df["amp1_vpp"].values, freq_band=(0.5, 2.0))
    # Check for harmonic doubling
    if not np.isnan(freq_hz):
        doubled, corrected_freq = detect_harmonic_doubling(freqs, power, freq_hz)
        freq_hz = corrected_freq
    bpm = freq_hz * 60 if not np.isnan(freq_hz) else float("nan")
    return bpm, hour, file_sel.name


def parse_concentration_uM(conc_str: str) -> float:
    s = conc_str.strip().lower()
    if s.endswith("mm"):
        s = s[:-2]
    elif s.endswith("um"):
        s = s[:-2]
    s = s.replace("_", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


# ---------------------------------------------------------------------------
# Step 1: Comprehensive BPM table across all timepoints
# ---------------------------------------------------------------------------
def generate_comprehensive_table():
    """Generate BPM at every available timepoint for all wells/concentrations."""
    print("=" * 80)
    print("HEART RATE ANALYSIS — Epirubicin & Doxorubicin")
    print(f"Data source: {RELAXED_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 80)

    all_results = []

    for drug_name, config in DRUG_CONFIG.items():
        drug_folder = RELAXED_DIR / config["folder"]
        if not drug_folder.exists():
            print(f"\nWARNING: {drug_folder} not found — skipping {drug_name}")
            continue

        concentrations = discover_concentrations(drug_folder)
        cmax = config["cmax_uM"]

        print(f"\n{'='*60}")
        print(f"{drug_name.upper()} — {config['folder']}")
        print(f"  Cmax: {cmax} uM")
        print(f"  Concentrations: {', '.join(concentrations)}")
        print(f"  NOTE: All concentrations exceed Cmax — including all for exploration")
        print(f"{'='*60}")

        for concentration in concentrations:
            conc_uM = parse_concentration_uM(concentration)
            conc_dir = drug_folder / concentration
            if not conc_dir.exists():
                continue

            # Discover all wells in this concentration
            wells = set()
            for csv_file in conc_dir.glob("*.csv"):
                w = get_well_name(csv_file.name)
                if w != "UNKNOWN":
                    wells.add(w)

            print(f"\n  {concentration} ({conc_uM:.3f} uM) — {len(wells)} wells: {sorted(wells)}")

            for well in sorted(wells):
                row = {
                    "drug": drug_name,
                    "concentration": concentration,
                    "conc_uM": conc_uM,
                    "well": well,
                    "cmax_uM": cmax,
                    "exceeds_cmax": conc_uM > cmax,
                }

                # Collect BPM at every timepoint
                bpm_values = {}
                for hour in ALL_HOURS:
                    files = find_files_for_concentration(drug_folder, concentration, hour, tolerance=1)
                    well_files = [f for f in files if get_well_name(f.name) == well]
                    if well_files:
                        bpm, _, fname = bpm_for_hour(well_files)
                        bpm_values[hour] = bpm
                        row[f"{hour}h_bpm"] = round(bpm, 2) if not np.isnan(bpm) else np.nan
                        row[f"{hour}h_file"] = fname
                    else:
                        row[f"{hour}h_bpm"] = np.nan
                        row[f"{hour}h_file"] = None

                # Compute baseline and change
                baseline_bpm = bpm_values.get(0, np.nan)
                if np.isnan(baseline_bpm):
                    baseline_bpm = bpm_values.get(3, np.nan)
                    row["baseline_used"] = "3h"
                else:
                    row["baseline_used"] = "0h"

                comp_hour = config["comparison_hour"]
                comp_bpm = bpm_values.get(comp_hour, np.nan)
                if not np.isnan(baseline_bpm) and not np.isnan(comp_bpm):
                    row["bpm_change"] = round(comp_bpm - baseline_bpm, 2)
                    row["pct_change"] = round((comp_bpm - baseline_bpm) / baseline_bpm * 100, 1) if baseline_bpm > 0 else np.nan
                else:
                    row["bpm_change"] = np.nan
                    row["pct_change"] = np.nan

                all_results.append(row)
                # Print summary for this well
                bpm_0 = bpm_values.get(0, np.nan)
                bpm_24 = bpm_values.get(24, np.nan)
                bpm_48 = bpm_values.get(48, np.nan)
                n_timepoints = sum(1 for h in ALL_HOURS if not np.isnan(bpm_values.get(h, np.nan)))
                print(f"    {well}: {n_timepoints} timepoints | 0h={bpm_0:.1f} | 24h={bpm_24:.1f} | 48h={bpm_48:.1f}" if not np.isnan(bpm_0) else f"    {well}: {n_timepoints} timepoints")

    if not all_results:
        print("\nNo results generated!")
        return None

    df = pd.DataFrame(all_results)

    # Reorder columns: metadata first, then BPM columns in hour order, then files
    meta_cols = ["drug", "concentration", "conc_uM", "well", "cmax_uM",
                 "exceeds_cmax", "baseline_used", "bpm_change", "pct_change"]
    bpm_cols = [f"{h}h_bpm" for h in ALL_HOURS if f"{h}h_bpm" in df.columns]
    file_cols = [f"{h}h_file" for h in ALL_HOURS if f"{h}h_file" in df.columns]
    col_order = meta_cols + bpm_cols + file_cols
    existing = [c for c in col_order if c in df.columns]
    df = df[existing]

    # Save
    csv_path = OUTPUT_DIR / "anthracyclines_comprehensive_bpm_all_wells.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")
    print(f"Total rows: {len(df)}")
    print(f"  Epirubicin: {len(df[df['drug']=='epirubicin'])} rows")
    print(f"  Doxorubicin: {len(df[df['drug']=='doxorubicin'])} rows")

    # Also save a summary with just BPM columns (no file paths) for easy viewing
    summary_cols = meta_cols + bpm_cols
    existing_summary = [c for c in summary_cols if c in df.columns]
    df_summary = df[existing_summary]
    summary_path = OUTPUT_DIR / "anthracyclines_bpm_summary.csv"
    df_summary.to_csv(summary_path, index=False)
    print(f"Saved summary (no file paths): {summary_path}")

    return df


# ---------------------------------------------------------------------------
# Step 1b: BPM vs Time plots per drug
# ---------------------------------------------------------------------------
def plot_bpm_vs_time(df: pd.DataFrame):
    """Generate BPM vs Time plots for each drug, one line per well, colored by concentration."""
    if df is None or df.empty:
        return

    bpm_cols = [c for c in df.columns if c.endswith('_bpm') and c[0].isdigit()]
    hours = [int(c.replace('h_bpm', '')) for c in bpm_cols]

    for drug_name in df['drug'].unique():
        df_drug = df[df['drug'] == drug_name]
        concentrations = sorted(df_drug['conc_uM'].unique())
        n_conc = len(concentrations)
        cmap = plt.get_cmap('plasma', n_conc)
        conc_colors = {c: cmap(i / max(n_conc - 1, 1)) for i, c in enumerate(concentrations)}

        fig, ax = plt.subplots(figsize=(14, 6))

        for _, row in df_drug.iterrows():
            bpms = [row.get(col, np.nan) for col in bpm_cols]
            valid = [(h, b) for h, b in zip(hours, bpms) if not np.isnan(b)]
            if not valid:
                continue
            h_vals, b_vals = zip(*valid)
            color = conc_colors[row['conc_uM']]
            ax.plot(h_vals, b_vals, '-o', color=color, markersize=3, linewidth=1,
                    alpha=0.7, label=f"{row['concentration']} {row['well']}")

        ax.set_xlabel('Time (hours)', fontsize=12)
        ax.set_ylabel('BPM (corrected for harmonic doubling)', fontsize=12)
        ax.set_title(f'{drug_name.capitalize()} — Heart Rate Over Time (All Wells)', fontsize=14)
        ax.set_xlim(0, 96)

        # Create legend with unique concentration entries
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, fontsize=6, ncol=4, loc='upper right',
                  bbox_to_anchor=(1.0, 1.0))

        fig.tight_layout()
        fname = f"{drug_name}_bpm_vs_time_all_wells.png"
        fig.savefig(OUTPUT_DIR / fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved plot: {fname}")

    # Also make a concentration-averaged version
    for drug_name in df['drug'].unique():
        df_drug = df[df['drug'] == drug_name]
        concentrations = sorted(df_drug['conc_uM'].unique())
        n_conc = len(concentrations)
        cmap = plt.get_cmap('plasma', n_conc)

        fig, ax = plt.subplots(figsize=(12, 5))

        for i, conc in enumerate(concentrations):
            df_conc = df_drug[df_drug['conc_uM'] == conc]
            mean_bpms = []
            std_bpms = []
            valid_hours = []
            for h, col in zip(hours, bpm_cols):
                vals = df_conc[col].dropna()
                if len(vals) > 0:
                    mean_bpms.append(vals.mean())
                    std_bpms.append(vals.std() if len(vals) > 1 else 0)
                    valid_hours.append(h)

            if valid_hours:
                color = cmap(i / max(n_conc - 1, 1))
                conc_label = df_conc['concentration'].iloc[0]
                ax.plot(valid_hours, mean_bpms, '-o', color=color, markersize=4,
                        linewidth=1.5, label=f"{conc_label} ({conc:.3f} uM)")
                if any(s > 0 for s in std_bpms):
                    ax.fill_between(valid_hours,
                                    [m - s for m, s in zip(mean_bpms, std_bpms)],
                                    [m + s for m, s in zip(mean_bpms, std_bpms)],
                                    alpha=0.15, color=color)

        ax.set_xlabel('Time (hours)', fontsize=12)
        ax.set_ylabel('Mean BPM (± SD)', fontsize=12)
        ax.set_title(f'{drug_name.capitalize()} — Mean Heart Rate by Concentration', fontsize=14)
        ax.set_xlim(0, 96)
        ax.legend(fontsize=7, loc='best')
        fig.tight_layout()
        fname = f"{drug_name}_bpm_vs_time_averaged.png"
        fig.savefig(OUTPUT_DIR / fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved plot: {fname}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    df = generate_comprehensive_table()
    plot_bpm_vs_time(df)
    print(f"\nDone. All outputs in: {OUTPUT_DIR}")
    print("\nNext step: Review the CSV and BPM-vs-time plots to identify")
    print("interesting wells/timepoints for focused waveform investigation.")
