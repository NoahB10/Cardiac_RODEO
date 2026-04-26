"""Prism-style ROC curves for Fig 6a, 7a, 8a.

Bootstrap mean ± 1 std band from the Organoid OOF per-drug predictions
(`Output/Prediction_Scatter_Data/{task}_predictions.csv`). Same methodology
as `ADMET_Comparison/Scripts/full_analysis.py:bootstrap_roc_stats` —
n_iter=300, seed=42 — and identical to the band methodology used by the g
panels, so every Prism ROC plot speaks the same statistical language.

Result is cached to `Prism_Style/bands_cache/Fig_{N}a_Organoid.csv` so runs
are deterministic; the cache invalidates if the underlying predictions
change (digested into the metadata line at the top of each cached CSV).

Plot area: 3.6 cm x 3.6 cm — matches the b-panel CM plot area.

Output: Prism_Style/Fig_{N}a_prism.png for N in {6, 7, 8}.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
import pandas as pd
from prism_style import apply_prism_style, render_at_scale, helvetica, clean_decimal_formatter
from _roc_bootstrap import cv_fold_band_from_a_panel
from _paths import panel_png, panel_data
import matplotlib.ticker as mticker

# Project convention: Organoid is always this green.
ORGANOID_GREEN = "#2ca02c"
BAND_ALPHA = 0.20
DIAG_COLOR = "#666666"

SCALE = 4
CM_PER_IN = 2.54

# Plot area locked at 3.6 cm x 3.6 cm. Total image ~2.14" x 2.02".
PLOT_W = 3.6 / CM_PER_IN
PLOT_H = 3.6 / CM_PER_IN

MARGIN_L = 0.62
MARGIN_R = 0.10
MARGIN_T = 0.05
MARGIN_B = 0.55

FIG_W = PLOT_W + MARGIN_L + MARGIN_R
FIG_H = PLOT_H + MARGIN_T + MARGIN_B
AXES_RECT = (MARGIN_L / FIG_W, MARGIN_B / FIG_H,
             PLOT_W / FIG_W, PLOT_H / FIG_H)

# Project-standard font sizes.
TICK_FONT_PT = 9
AXIS_LABEL_PT = 13
ANNOTATION_PT = 9


def load_roc_data(fig_num: int):
    """CV-fold-cached ROC for Fig {N}a Organoid (10-fold mean ± std).

    Returns (grid, mean_tpr, std_tpr, mean_auc, std_auc, n_folds, src).
    """
    stats = cv_fold_band_from_a_panel(fig_num)
    src = HERE / "bands_cache" / f"Fig_{fig_num}a_Organoid.csv"
    return (stats["FPR"],
            stats["TPR_mean"],
            stats["TPR_upper"] - stats["TPR_mean"],
            stats["AUC_mean"],
            stats["AUC_std"],
            10,
            src)


def _plot_fn(grid, mean_tpr, std_tpr, mean_auc, std_auc):
    def _fn(fig, ax, scale):
        # Diagonal reference (random classifier)
        ax.plot([0, 1], [0, 1],
                color=DIAG_COLOR,
                linestyle="--", dashes=(4, 3),
                linewidth=0.9 * scale, zorder=2)

        # Confidence band
        upper = np.clip(mean_tpr + std_tpr, 0, 1)
        lower = np.clip(mean_tpr - std_tpr, 0, 1)
        ax.fill_between(grid, lower, upper,
                        color=ORGANOID_GREEN, alpha=BAND_ALPHA,
                        linewidth=0, zorder=3)

        # Mean ROC curve
        ax.plot(grid, mean_tpr,
                color=ORGANOID_GREEN,
                linewidth=1.3 * scale,
                zorder=4,
                label=f"Organoid")

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        # 0.00->0, 1.00->1 on both axes per project tick-label convention.
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(clean_decimal_formatter))
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")

        apply_prism_style(
            ax,
            scale=scale,
            spine_width_pt=1.2,
            hide_spines=("top", "right"),
            show_xticks=True,
            ytick_length_pt=4.0,
            ytick_width_pt=1.0,
            tick_label_size_pt=TICK_FONT_PT,
            ylabel_size_pt=AXIS_LABEL_PT,
            xlabel_size_pt=AXIS_LABEL_PT,
            ylabel_pad_pt=2,
            xlabel_pad_pt=2,
            clean_y_ticks=True,
            bold=False,
        )

        # Mean AUC annotation, bottom-right inside the plot
        ax.text(
            0.96, 0.06,
            f"AUC = {mean_auc:.2f} ± {std_auc:.2f}",
            transform=ax.transAxes,
            ha="right", va="bottom",
            fontproperties=helvetica(ANNOTATION_PT * scale),
            zorder=5,
        )

    return _fn


def _save_data(fig_num: int, grid, mean_tpr, std_tpr, mean_auc, std_auc):
    """Write the data plotted on Fig_Na to Fig_Na_prism_data.xlsx."""
    out = panel_data(fig_num, "a")
    plotted = pd.DataFrame({
        "FPR": grid,
        "TPR_mean": mean_tpr,
        "TPR_std": std_tpr,
        "TPR_lower": (mean_tpr - std_tpr).clip(0, 1),
        "TPR_upper": (mean_tpr + std_tpr).clip(0, 1),
    })
    summary = pd.DataFrame([{
        "Metric": "AUC",
        "Mean": mean_auc,
        "Std": std_auc,
        "Source": "10-fold CV across folds in Fig_Na_data.xlsx[ROC_Data]",
    }])
    metadata = pd.DataFrame([{
        "Panel": f"Fig_{fig_num}a (Prism)",
        "Description": "Mean ROC curve across 10-fold CV with ±1 std band",
        "Method": "10-fold CV mean across folds (deterministic)",
        "Source_Script": "Prism_Style/generate_roc_curves.py",
        "Source_Data": f"Output/PowerPoint_Figures/Fig_{fig_num}/Fig_{fig_num}a_data.xlsx",
        "Cache_File": f"Prism_Style/bands_cache/Fig_{fig_num}a_Organoid.csv",
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        summary.to_excel(w, sheet_name="Summary", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


def main():
    from PIL import Image
    for fig_num in (6, 7, 8):
        try:
            grid, mean_tpr, std_tpr, mean_auc, std_auc, n_pred, src = \
                load_roc_data(fig_num)
        except FileNotFoundError as e:
            print(f"[SKIP] {fig_num}a: {e}")
            continue
        out = panel_png(fig_num, "a")
        render_at_scale(
            _plot_fn(grid, mean_tpr, std_tpr, mean_auc, std_auc),
            (FIG_W, FIG_H), out,
            scale=SCALE, dpi=600, transparent=True,
            axes_rect=AXES_RECT,
        )
        data_xlsx = _save_data(fig_num, grid, mean_tpr, std_tpr, mean_auc, std_auc)
        im = Image.open(out)
        dpi = im.info.get("dpi", (600, 600))[0]
        print(f"[{fig_num}a] -> {out.relative_to(PROJECT_ROOT)}")
        print(f"    image  : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
        print(f"    data   : {data_xlsx.relative_to(PROJECT_ROOT)}")
        print(f"    AUC    : {mean_auc:.3f} ± {std_auc:.3f}")


if __name__ == "__main__":
    main()
