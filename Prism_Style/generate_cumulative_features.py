"""Prism-style cumulative-feature trajectories for Fig 6e, 7e, 8e.

For each drug, plots its predicted probability (%) as features are added
one at a time (1..14). Pos / Neg colored to match the d-panel dot plots.
A dashed horizontal threshold line marks the decision boundary.

Data source: Output/PowerPoint_Figures/Fig_{N}/Fig_{N}e_data.xlsx
    sheet "Cumulative_Data"  (rows = cumulative feature sets, cols = drugs)
    sheet "Source_Metadata"  (Threshold value)
Pos/Neg labels come from the matching d-panel data (Fig_{N}d_data.xlsx,
sheet "Predictions", column "is_positive").

Output: Prism_Style/Fig_{N}e_prism.png for N in {6, 7, 8}.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import apply_prism_style, render_at_scale, helvetica

FIG_DIR = PROJECT_ROOT / "Output" / "PowerPoint_Figures"

COLOR_POS = "#6C92ED"
COLOR_NEG = "#8E8E8E"
THRESHOLD_COLOR = "#000000"
SCALE = 4

# Plot area: 6.0 cm wide x 4.3 cm tall.  Plot HEIGHT matches the d-panel
# (threshold dot plot at 4.3 cm) so the two sit at the same row height.
# Plot WIDTH is wider to fit the 14 x-tick labels comfortably at 9 pt.
CM_PER_IN = 2.54
PLOT_W = 6.0 / CM_PER_IN   # 2.362"
PLOT_H = 4.3 / CM_PER_IN   # 1.6929"

MARGIN_L = 0.55   # "Cumulative Score (%)" + Y-tick labels
MARGIN_R = 0.10   # legend overshoot room
MARGIN_T = 0.05
MARGIN_B = 0.50   # "# Features" + X-tick labels

FIG_W = PLOT_W + MARGIN_L + MARGIN_R   # ~3.01"
FIG_H = PLOT_H + MARGIN_T + MARGIN_B   # ~1.97"
AXES_RECT = (MARGIN_L / FIG_W, MARGIN_B / FIG_H,
             PLOT_W / FIG_W, PLOT_H / FIG_H)

# Font sizes consistent with a/b/c/d panels.
TICK_FONT_PT = 9
AXIS_LABEL_PT = 13
LEGEND_FONT_PT = 9


def load_e_data(fig_num: int):
    e_xlsx = FIG_DIR / f"Fig_{fig_num}" / f"Fig_{fig_num}e_data.xlsx"
    cum = pd.read_excel(e_xlsx, sheet_name="Cumulative_Data")
    cum.columns = [c.strip() if isinstance(c, str) else c for c in cum.columns]

    meta = pd.read_excel(e_xlsx, sheet_name="Source_Metadata")
    threshold = float(meta["Threshold"].iloc[0])

    d_xlsx = FIG_DIR / f"Fig_{fig_num}" / f"Fig_{fig_num}d_data.xlsx"
    d_df = pd.read_excel(d_xlsx, sheet_name="Predictions")
    d_df.columns = [c.strip() for c in d_df.columns]
    pos_map = dict(zip(d_df["Drug"].astype(str), d_df["is_positive"].astype(bool)))

    return cum, threshold, pos_map, e_xlsx


def _plot_fn(cum, threshold, pos_map):
    drug_cols = [c for c in cum.columns if c != "Cumulative_Coefficients"]
    n_features = len(cum)
    x = np.arange(1, n_features + 1)

    def _fn(fig, ax, scale):
        # Draw negatives first so positives render on top
        order = sorted(drug_cols, key=lambda d: bool(pos_map.get(d, False)))
        for drug in order:
            y = cum[drug].to_numpy(dtype=float)
            is_pos = bool(pos_map.get(drug, False))
            color = COLOR_POS if is_pos else COLOR_NEG
            ax.plot(
                x, y,
                color=color,
                linewidth=0.6 * scale,
                alpha=0.75,
                marker="o",
                markersize=2.0 * scale,
                markeredgewidth=0,
                zorder=3 if is_pos else 2,
            )

        ax.axhline(
            threshold,
            color=THRESHOLD_COLOR,
            linestyle="--",
            dashes=(4, 3),
            linewidth=1.0 * scale,
            zorder=4,
        )

        ax.set_xlim(0.5, n_features + 0.5)
        ax.set_xticks(x)
        ax.set_xticklabels([str(int(v)) for v in x])
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xlabel("# Features")
        ax.set_ylabel("Score (%)")

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
            clean_y_ticks=False,
            bold=False,
        )

        handles = [
            Line2D([0], [0], color=COLOR_POS, marker="o",
                   markersize=3.0 * scale,
                   markeredgewidth=0,
                   linewidth=1.0 * scale, label="Pos"),
            Line2D([0], [0], color=COLOR_NEG, marker="o",
                   markersize=3.0 * scale,
                   markeredgewidth=0,
                   linewidth=1.0 * scale, label="Neg"),
            Line2D([0], [0], color=THRESHOLD_COLOR,
                   linestyle="--", dashes=(4, 3),
                   linewidth=1.0 * scale, label="Thresh"),
        ]
        ax.legend(
            handles=handles,
            loc="center right",
            frameon=False,
            handlelength=1.2, handletextpad=0.4,
            labelspacing=0.30,
            prop=helvetica(LEGEND_FONT_PT * scale),
        )

    return _fn


def main():
    from PIL import Image
    for fig_num in (6, 7, 8):
        try:
            cum, threshold, pos_map, src = load_e_data(fig_num)
        except FileNotFoundError as e:
            print(f"[SKIP] {fig_num}e: {e}")
            continue
        out = HERE / f"Fig_{fig_num}e_prism.png"
        render_at_scale(
            _plot_fn(cum, threshold, pos_map),
            (FIG_W, FIG_H), out,
            scale=SCALE, dpi=600, transparent=True,
            axes_rect=AXES_RECT,
        )
        im = Image.open(out)
        dpi = im.info.get("dpi", (600, 600))[0]
        n_pos = sum(1 for v in pos_map.values() if v)
        n_neg = len(pos_map) - n_pos
        print(f"[{fig_num}e] -> {out.name}")
        print(f"    image  : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
        print(f"    plot   : {PLOT_W:.3f}\" x {PLOT_H:.3f}\"  "
              f"({PLOT_W*2.54:.2f} x {PLOT_H*2.54:.2f} cm)")
        print(f"    source : {src.name} -> Cumulative_Data ({len(cum)} rows, "
              f"{len(cum.columns)-1} drugs)")
        print(f"    labels : {n_pos} Pos / {n_neg} Neg, "
              f"threshold = {threshold:.1f}%")


if __name__ == "__main__":
    main()
