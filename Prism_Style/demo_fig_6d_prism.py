"""Prism-style Fig_6d: per-drug probability scatter with decision threshold.

Plot layout:
- Horizontal dot plot. 25 drugs on Y (one per row), predicted probability on X.
- Y inverted so positives sit at the top (matches the existing panel).
- Vertical dashed line at the threshold (e.g. 35%).
- Positives = blue (#6C92ED); Negatives = grey (#8E8E8E).

Sizing:
- Plot axis height = 4.3 cm = 1.693" (user-specified)
- Other margins chosen to fit 25 drug names (5 pt Helvetica) on the left
  and the X-axis label "Probability (%)" below.

Data source: Output/PowerPoint_Figures/Fig_6/Fig_6d_data.xlsx (sheet "Predictions").
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import apply_prism_style, render_at_scale, helvetica

DATA_XLSX = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Fig_6" / "Fig_6d_data.xlsx"
OUT_PATH = HERE / "Fig_6d_prism.png"

COLOR_POS = "#6C92ED"
COLOR_NEG = "#8E8E8E"
THRESHOLD_COLOR = "#000000"   # dashed black per Prism convention

SCALE = 4

# Plot axis dimensions
PLOT_H = 4.3 / 2.54           # 4.3 cm -> 1.693"
PLOT_W = 0.90                 # narrower — was 1.80, halved per request

# Outer image margins
MARGIN_L = 0.62               # drug names (up to ~13 chars at 5pt)
MARGIN_R = 0.18               # room for the "100" X tick label overshoot
MARGIN_T = 0.08
MARGIN_B = 0.45               # X tick labels + "Prob (%)" axis label (no clipping)

FIG_W = PLOT_W + MARGIN_L + MARGIN_R
FIG_H = PLOT_H + MARGIN_T + MARGIN_B
AXES_RECT = (MARGIN_L / FIG_W, MARGIN_B / FIG_H, PLOT_W / FIG_W, PLOT_H / FIG_H)


def load_predictions():
    df = pd.read_excel(DATA_XLSX, sheet_name="Predictions")
    df.columns = [c.strip() for c in df.columns]
    threshold = None
    if "Threshold_Value" in df.columns:
        try:
            threshold = float(df["Threshold_Value"].dropna().iloc[0])
        except Exception:
            threshold = None
    if threshold is None:
        threshold = 35.0
    return df, threshold


def plot_6d(fig, ax, scale: float = 1.0):
    df, threshold = load_predictions()

    # Drug labels (5 pt — small enough to fit 25 rows in 1.693" plot height)
    drug_label_size_pt = 5

    prob_col = "Predicted_Arrhythmia_pct"
    y = np.arange(len(df))
    colors = [COLOR_POS if bool(p) else COLOR_NEG for p in df["is_positive"]]

    # Markers: Prism look — solid fill, thin black edge
    ax.scatter(
        df[prob_col].to_numpy(),
        y,
        c=colors,
        s=32 * scale,           # bigger than before (was 18) — more visible
        edgecolor="black",
        linewidth=0.6 * scale,
        zorder=3,
    )

    # Threshold line
    ax.axvline(
        threshold,
        color=THRESHOLD_COLOR,
        linestyle="--",
        dashes=(4, 3),
        linewidth=1.0 * scale,
        zorder=2,
    )
    # Threshold text just right of the line, near the top
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
        show_xticks=True,     # numeric X axis needs outward ticks
        ytick_length_pt=0,    # no tick marks on Y (just drug names)
        ytick_width_pt=1.2,
        tick_label_size_pt=9,
        ylabel_size_pt=13,
        xlabel_size_pt=9,     # match the tick labels — 13pt looked oversized on this narrow plot
        ylabel_pad_pt=3,
        xlabel_pad_pt=4,
        clean_y_ticks=False,  # Y axis is categorical, not numeric
        bold=False,
    )
    # Override Y-tick labels to the smaller 5-pt size (drug names cluttered otherwise)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(helvetica(drug_label_size_pt * scale))
    # Remove Y tick marks entirely (drug names float right next to spine)
    ax.tick_params(axis="y", length=0, width=0, pad=2 * scale)

    # Legend: Pos (blue) / Neg (grey), frameless, top-right of plot
    from matplotlib.lines import Line2D
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
    leg = ax.legend(
        handles=handles,
        loc="lower right",
        frameon=False,
        handlelength=0.8, handletextpad=0.4,
        labelspacing=0.25,
        prop=helvetica(7 * scale),
    )


def main():
    out = render_at_scale(
        plot_6d, (FIG_W, FIG_H), OUT_PATH,
        scale=SCALE, dpi=600, transparent=True,
        axes_rect=AXES_RECT,
    )
    from PIL import Image
    im = Image.open(out)
    dpi = im.info.get("dpi", (600, 600))[0]
    print(f"[6d] -> {out.name}")
    print(f"    image  : {im.size} px = {im.size[0]/dpi:.3f}\" × {im.size[1]/dpi:.3f}\"")
    print(f"    plot   : {PLOT_W:.3f}\" × {PLOT_H:.3f}\"  "
          f"({PLOT_W*2.54:.2f} × {PLOT_H*2.54:.2f} cm)")
    print(f"    source : {DATA_XLSX.name} -> Predictions sheet")
    df, threshold = load_predictions()
    print(f"    rows   : {len(df)} drugs, threshold = {threshold:.1f}%")


if __name__ == "__main__":
    main()
