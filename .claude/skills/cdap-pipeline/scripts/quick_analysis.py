"""Quick analysis utilities for CDAP pipeline results.

This module provides convenience functions for common analysis tasks
when working with CDAP log file data.

Usage:
    from scripts.quick_analysis import quick_summary, plot_well_timeseries

    # Get summary statistics
    stats = quick_summary(result, drug="Amiodarone")

    # Plot time series
    plot_well_timeseries(result, drug="Amiodarone", well="A01", concentration=0.01)
"""
from __future__ import annotations

from typing import Optional, Dict, List
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def quick_summary(result, drug: str = None) -> pd.DataFrame:
    """Generate quick summary statistics from Stage 1 result.

    Args:
        result: Stage1Result object
        drug: Specific drug to analyze (None = all drugs)

    Returns:
        DataFrame with summary statistics per well/segment
    """
    stats_list = []

    for d, plate, conc, well_id, seg_key, segment in result.iter_segments():
        if drug and d != drug:
            continue

        df = segment.data

        stats = {
            "drug": d,
            "plate": plate,
            "concentration_mM": conc,
            "well_id": well_id,
            "segment": seg_key,
            "n_rows": len(df),
            "completeness": segment.completeness,
            "o2_mean": df["oxygen_pct_air"].mean(),
            "o2_std": df["oxygen_pct_air"].std(),
            "o2_min": df["oxygen_pct_air"].min(),
            "o2_max": df["oxygen_pct_air"].max(),
            "snr_mean": df["snr"].mean(),
            "snr_min": df["snr"].min(),
            "snr_max": df["snr"].max()
        }

        stats_list.append(stats)

    return pd.DataFrame(stats_list)


def plot_well_timeseries(
    result,
    drug: str,
    well_id: str,
    concentration: float,
    plate: str = None,
    save_path: Optional[Path] = None
):
    """Plot oxygen time series for a specific well.

    Args:
        result: Stage1Result object
        drug: Drug name
        well_id: Well identifier (e.g., "A01")
        concentration: Concentration in mM
        plate: Plate name (if None, uses first available)
        save_path: Path to save figure (if None, displays)
    """
    drug_result = result.drugs.get(drug)
    if not drug_result:
        print(f"Drug {drug} not found")
        return

    if plate is None:
        plate = list(drug_result.plates.keys())[0]

    plate_result = drug_result.plates.get(plate)
    if not plate_result:
        print(f"Plate {plate} not found")
        return

    conc_result = plate_result.concentrations.get(concentration)
    if not conc_result:
        print(f"Concentration {concentration} not found")
        return

    well_result = conc_result.wells.get(well_id)
    if not well_result:
        print(f"Well {well_id} not found")
        return

    # Combine all segments
    all_times = []
    all_o2 = []
    all_snr = []

    for seg_key in sorted(well_result.segments.keys()):
        segment = well_result.segments[seg_key]
        df = segment.data

        all_times.extend(df["abs_time"].values)
        all_o2.extend(df["oxygen_pct_air"].values)
        all_snr.extend(df["snr"].values)

    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # O2 plot
    ax1.plot(all_times, all_o2, linewidth=0.5, color='blue')
    ax1.set_ylabel("O2 (% air)", fontsize=12)
    ax1.set_title(f"{drug} {concentration}mM - Well {well_id}", fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # SNR plot
    ax2.plot(all_times, all_snr, linewidth=0.5, color='red')
    ax2.axhline(2.0, color='black', linestyle='--', linewidth=1, label='SNR threshold')
    ax2.set_ylabel("SNR", fontsize=12)
    ax2.set_xlabel("Time", fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Saved to {save_path}")
    else:
        plt.show()


def compare_concentrations(
    result,
    drug: str,
    metric: str = "o2_mean",
    plate: str = None,
    save_path: Optional[Path] = None
):
    """Compare metric across concentrations for a drug.

    Args:
        result: Stage1Result object
        drug: Drug name
        metric: Metric to compare ("o2_mean", "o2_std", etc.)
        plate: Plate name (if None, uses first available)
        save_path: Path to save figure
    """
    drug_result = result.drugs.get(drug)
    if not drug_result:
        print(f"Drug {drug} not found")
        return

    if plate is None:
        plate = list(drug_result.plates.keys())[0]

    plate_result = drug_result.plates.get(plate)
    if not plate_result:
        print(f"Plate {plate} not found")
        return

    # Calculate metric for each concentration
    conc_values = {}

    for conc_val, conc_result in plate_result.concentrations.items():
        all_values = []

        for well_id, well in conc_result.wells.items():
            for seg_key, segment in well.segments.items():
                df = segment.data

                if metric == "o2_mean":
                    all_values.append(df["oxygen_pct_air"].mean())
                elif metric == "o2_std":
                    all_values.append(df["oxygen_pct_air"].std())
                elif metric == "snr_mean":
                    all_values.append(df["snr"].mean())

        if all_values:
            conc_values[conc_val] = all_values

    # Plot
    concentrations = sorted(conc_values.keys())
    means = [np.mean(conc_values[c]) for c in concentrations]
    stds = [np.std(conc_values[c]) for c in concentrations]

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.errorbar(concentrations, means, yerr=stds, marker='o',
                linewidth=2, markersize=8, capsize=5)
    ax.set_xscale('log')
    ax.set_xlabel("Concentration (mM)", fontsize=12)
    ax.set_ylabel(metric.replace("_", " ").title(), fontsize=12)
    ax.set_title(f"{drug} - {metric.replace('_', ' ').title()}", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Saved to {save_path}")
    else:
        plt.show()


def export_summary_csv(result, output_path: Path, drug: str = None):
    """Export summary statistics to CSV.

    Args:
        result: Stage1Result object
        output_path: Path to save CSV file
        drug: Specific drug (None = all drugs)
    """
    summary_df = quick_summary(result, drug=drug)
    summary_df.to_csv(output_path, index=False)
    print(f"Exported summary to {output_path}")


def check_data_quality(result, drug: str = None) -> Dict[str, any]:
    """Check data quality metrics.

    Args:
        result: Stage1Result object
        drug: Specific drug (None = all drugs)

    Returns:
        Dictionary with quality metrics
    """
    total_segments = 0
    low_completeness = 0
    low_snr_fraction_high = 0

    for d, plate, conc, well_id, seg_key, segment in result.iter_segments():
        if drug and d != drug:
            continue

        total_segments += 1

        if segment.completeness < 0.6:
            low_completeness += 1

        df = segment.data
        low_snr_pct = (df["snr"] < 2.0).sum() / len(df)

        if low_snr_pct > 0.2:
            low_snr_fraction_high += 1

    return {
        "total_segments": total_segments,
        "low_completeness_count": low_completeness,
        "low_completeness_pct": low_completeness / total_segments * 100 if total_segments > 0 else 0,
        "high_low_snr_count": low_snr_fraction_high,
        "high_low_snr_pct": low_snr_fraction_high / total_segments * 100 if total_segments > 0 else 0
    }


if __name__ == "__main__":
    # Example usage
    from cdap import Stage1Config, run_stage1

    config = Stage1Config()
    result = run_stage1(config, single_drug="Amiodarone")

    # Get summary
    summary = quick_summary(result, drug="Amiodarone")
    print(summary.head())

    # Check quality
    quality = check_data_quality(result, drug="Amiodarone")
    print("\nQuality metrics:")
    for key, value in quality.items():
        print(f"  {key}: {value}")

    # Plot example
    plot_well_timeseries(result, drug="Amiodarone", well_id="A01", concentration=0.01)
