"""Prism-style per-drug probability dot plots for Fig 6d, 7d, 8d.

Same visual spec as ``demo_fig_6d_prism.py`` — this module just generalizes
the probability column name so the three figures (Arrhythmia / Heart Damage /
High Concern) all render from one driver.

Data source: Output/PowerPoint_Figures/Fig_{N}/Fig_{N}d_data.xlsx (sheet "Predictions").
Output: Prism_Style/Fig_{N}d_prism.png for N in {6, 7, 8}.
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

# Plot area 0.90" x 4.3 cm (1.69") — the prior good size. Total ~1.70" x 2.22".
PLOT_H = 4.3 / 2.54   # 4.3 cm -> 1.693"
PLOT_W = 0.90

MARGIN_L = 0.62
MARGIN_R = 0.18
MARGIN_T = 0.08
MARGIN_B = 0.45

FIG_W = PLOT_W + MARGIN_L + MARGIN_R
FIG_H = PLOT_H + MARGIN_T + MARGIN_B
AXES_RECT = (MARGIN_L / FIG_W, MARGIN_B / FIG_H,
             PLOT_W / FIG_W, PLOT_H / FIG_H)

PANEL_SPECS = {
    6: "Predicted_Arrhythmia_pct",
    7: "Predicted_Heart_Damage_pct",
    8: "Predicted_High_Concern_pct",
}


def load_predictions(fig_num: int, prob_col: str):
    xlsx = FIG_DIR / f"Fig_{fig_num}" / f"Fig_{fig_num}d_data.xlsx"
    df = pd.read_excel(xlsx, sheet_name="Predictions")
    df.columns = [c.strip() for c in df.columns]
    if prob_col not in df.columns:
        raise KeyError(
            f"Expected column '{prob_col}' in {xlsx.name}; got {list(df.columns)}"
        )
    threshold = None
    if "Threshold_Value" in df.columns:
        try:
            threshold = float(df["Threshold_Value"].dropna().iloc[0])
        except Exception:
            threshold = None
    if threshold is None:
        threshold = 35.0
    return df, threshold, xlsx


def _plot_fn(df, threshold, prob_col):
    drug_label_size_pt = 5

    def _fn(fig, ax, scale):
        y = np.arange(len(df))
        colors = [COLOR_POS if bool(p) else COLOR_NEG for p in df["is_positive"]]

        ax.scatter(
            df[prob_col].to_numpy(), y,
            c=colors,
            s=32 * scale,
            edgecolor="black",
            linewidth=0.6 * scale,
            zorder=3,
        )

        ax.axvline(
            threshold,
            color=THRESHOLD_COLOR,
            linestyle="--",
            dashes=(4, 3),
            linewidth=1.0 * scale,
            zorder=2,
        )
        ax.text(
            threshold + 1.5, 0.2,
            f"{threshold:.0f}%",
            color=THRESHOLD_COLOR,
            fontproperties=helvetica(7 * scale),
            ha="left", va="top",
            zorder=4,
        )

        ax.set_yticks(y)
        ax.set_yticklabels(df["Drug"].tolist())
        ax.set_xlim(-2, 102)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.invert_yaxis()
        ax.set_xlabel("Prob (%)")
        ax.set_ylabel("")

        apply_prism_style(
            ax,
            scale=scale,
            spine_width_pt=1.2,
            hide_spines=("top", "right"),
            show_xticks=True,
            ytick_length_pt=0,
            ytick_width_pt=1.2,
            tick_label_size_pt=9,
            ylabel_size_pt=13,
            xlabel_size_pt=13,    # uniform with all other Prism panels
            ylabel_pad_pt=3,
            xlabel_pad_pt=4,
            clean_y_ticks=False,
            bold=False,
        )
        for lbl in ax.get_yticklabels():
            lbl.set_fontproperties(helvetica(drug_label_size_pt * scale))
        ax.tick_params(axis="y", length=0, width=0, pad=2 * scale)

        handles = [
            Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=COLOR_POS, markeredgecolor="black",
                   markeredgewidth=0.6 * scale,
                   markersize=5 * scale, label="Pos"),
            Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=COLOR_NEG, markeredgecolor="black",
                   markeredgewidth=0.6 * scale,
                   markersize=5 * scale, label="Neg"),
        ]
        ax.legend(
            handles=handles,
            loc="lower right",
            frameon=False,
            handlelength=0.8, handletextpad=0.4,
            labelspacing=0.25,
            prop=helvetica(7 * scale),
        )

    return _fn


def main():
    from PIL import Image
    for fig_num, prob_col in PANEL_SPECS.items():
        try:
            df, threshold, src = load_predictions(fig_num, prob_col)
        except FileNotFoundError as e:
            print(f"[SKIP] {fig_num}d: {e}")
            continue
        except KeyError as e:
            print(f"[SKIP] {fig_num}d: {e}")
            continue
        out = HERE / f"Fig_{fig_num}d_prism.png"
        render_at_scale(
            _plot_fn(df, threshold, prob_col), (FIG_W, FIG_H), out,
            scale=SCALE, dpi=600, transparent=True,
            axes_rect=AXES_RECT,
        )
        im = Image.open(out)
        dpi = im.info.get("dpi", (600, 600))[0]
        n_pos = int(df["is_positive"].sum())
        print(f"[{fig_num}d] -> {out.name}")
        print(f"    image  : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
        print(f"    plot   : {PLOT_W:.3f}\" x {PLOT_H:.3f}\"  "
              f"({PLOT_W*2.54:.2f} x {PLOT_H*2.54:.2f} cm)")
        print(f"    source : {src.name} -> Predictions ({prob_col})")
        print(f"    rows   : {len(df)} drugs  ({n_pos} pos, "
              f"{len(df)-n_pos} neg), threshold = {threshold:.1f}%")


if __name__ == "__main__":
    main()
