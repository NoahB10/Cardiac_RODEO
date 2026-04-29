"""Prism-style LOOCV Accuracy vs AUC scatter strip for Fig 3 panel i.

Three side-by-side sub-panels — one per target (Arrhythmia, heart_damage,
Concern_Binary). Each sub-panel plots 12 colored dots (one per PK-PD
equation) with x=Accuracy and y=AUC ROC, both 0..1, plus a gray dashed
reference diagonal. Visual style follows
`generate_paper_figures.py:1591+`: rainbow palette, big circle markers,
bold titles.

Sized to fit Group 70 on slide 3 (3.88" × 1.49").

Output:
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3i_prism.png
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3i_prism_data.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.transforms import Bbox

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import apply_prism_style, helvetica, clean_decimal_formatter
from _paths import panel_png, panel_data

SRC = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Fig_3" / "Fig_3d_data.xlsx"

TARGETS = [
    ("Arrhythmia",     "Arrhythmia"),
    ("heart_damage",   "Heart Damage"),
    ("Concern_Binary", "Concern"),
]

# Spectral palette in the same order as generate_paper_figures.py:1597.
# Equation names are the snake_case identifiers in Fig_3d_data.xlsx.
EQ_COLORS = [
    ("dual_exponential",       "#d62728"),
    ("hormesis_v0",            "#e6550d"),
    ("pkpd_elimination",       "#ff7f0e"),
    ("biphasic_response",      "#ffc107"),
    ("modified_hill_hormesis", "#8bc34a"),
    ("modified_hill_simple",   "#2ca02c"),
    ("adaptive_response",      "#00897b"),
    ("gaussian_ridge",         "#17becf"),
    ("bivariate_gaussian",     "#1f77b4"),
    ("gaussian_hill_hybrid",   "#5c6bc0"),
    ("recovery_model",         "#9467bd"),
    ("cumulative_exposure",    "#e377c2"),
]

# Sized to Group 70 on slide 3: 3.88" × 1.49". SUB_PLOT pinned to 1.00"
# so the data axis matches Fig 3g's plot height (same row = same plot
# area height).
FIG_W = 3.88
FIG_H = 1.49
SUB_PLOT = 1.00   # MUST match PLOT_H in generate_r2_bar.py
MARGIN_L = 0.45   # Y label "AUC ROC" rotated + tick labels at 7 pt
MARGIN_R = 0.10
MARGIN_T = 0.18   # title at 9 pt bold
MARGIN_B = FIG_H - MARGIN_T - SUB_PLOT  # 0.31" (X label + ticks)
GAP = (FIG_W - 3 * SUB_PLOT - MARGIN_L - MARGIN_R) / 2  # 0.165"

DPI = 600
SCALE = 4
TICK_FONT_PT = 7
AXIS_LABEL_PT = 9
TITLE_FONT_PT = 9

DOT_SIZE = 22         # marker s param at final-image scale (s = pt²)
DIAG_COLOR = "#9d9d9d"


def load() -> pd.DataFrame:
    df = pd.read_excel(SRC, sheet_name="LOOCV_Strip_Data")
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    return df


def _draw(df: pd.DataFrame, out_path: Path):
    fig = plt.figure(figsize=(FIG_W * SCALE, FIG_H * SCALE), dpi=DPI)

    color_map = dict(EQ_COLORS)
    eq_order = [eq for eq, _ in EQ_COLORS]

    plot_h = FIG_H - MARGIN_T - MARGIN_B

    for i, (target_key, title) in enumerate(TARGETS):
        sub_left_in = MARGIN_L + i * (SUB_PLOT + GAP)
        rect = (sub_left_in / FIG_W, MARGIN_B / FIG_H,
                SUB_PLOT / FIG_W, plot_h / FIG_H)
        ax = fig.add_axes(list(rect))

        sub = df[df["Target"] == target_key]
        ax.plot([0, 1], [0, 1], color=DIAG_COLOR, linestyle="--",
                dashes=(4, 3), linewidth=0.7 * SCALE, zorder=2)

        # Plot in canonical equation order so colors match generate_paper_figures.
        for eq_name in eq_order:
            row = sub[sub["Equation"] == eq_name]
            if row.empty:
                continue
            ax.scatter(
                row["Accuracy"].values[0], row["AUC"].values[0],
                s=DOT_SIZE * SCALE * SCALE,
                c=[color_map[eq_name]],
                edgecolor="black", linewidth=0.4 * SCALE,
                zorder=4,
            )

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(clean_decimal_formatter))

        ax.set_xlabel("Accuracy")
        if i == 0:
            ax.set_ylabel("AUC ROC")
        else:
            ax.set_yticklabels([])

        ax.text(
            0.5, 1.04, title,
            transform=ax.transAxes,
            ha="center", va="bottom",
            fontproperties=helvetica(TITLE_FONT_PT * SCALE, bold=True),
        )

        apply_prism_style(
            ax,
            scale=SCALE,
            spine_width_pt=1.0,
            hide_spines=("top", "right"),
            show_xticks=True,
            ytick_length_pt=3.0,
            ytick_width_pt=0.8,
            tick_label_size_pt=TICK_FONT_PT,
            ylabel_size_pt=AXIS_LABEL_PT,
            xlabel_size_pt=AXIS_LABEL_PT,
            ylabel_pad_pt=2,
            xlabel_pad_pt=2,
            clean_y_ticks=True,
            bold=False,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    full_bbox = Bbox.from_bounds(0, 0, FIG_W * SCALE, FIG_H * SCALE)
    fig.savefig(str(out_path), dpi=DPI, transparent=True,
                bbox_inches=full_bbox, pad_inches=0)
    plt.close(fig)

    from PIL import Image
    target_px = (int(round(FIG_W * DPI)), int(round(FIG_H * DPI)))
    im = Image.open(out_path)
    im.resize(target_px, Image.LANCZOS).save(out_path, dpi=(DPI, DPI))


def _save_data(df: pd.DataFrame):
    out = panel_data(3, "i")
    metadata = pd.DataFrame([{
        "Panel": "Fig_3i (Prism)",
        "Description": "LOOCV Accuracy vs AUC ROC for 12 PK-PD equations across 3 targets",
        "Source_Script": "Prism_Style/generate_loocv_scatter.py",
        "Source_Data": str(SRC.relative_to(PROJECT_ROOT)),
        "Targets": ", ".join(t for t, _ in TARGETS),
        "Color_Map": "rainbow_spectral",
    }])
    plotted = df[["Equation", "Target", "Model", "Accuracy", "AUC",
                  "N_samples", "N_features"]].copy()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        for target_key, title in TARGETS:
            sub = df[df["Target"] == target_key][
                ["Equation", "Model", "Accuracy", "AUC"]
            ]
            sub.to_excel(w, sheet_name=title[:31], index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


def main():
    from PIL import Image
    df = load()
    out = panel_png(3, "i")
    _draw(df, out)
    data_xlsx = _save_data(df)
    im = Image.open(out)
    dpi = im.info.get("dpi", (DPI, DPI))[0]
    print(f"[3i LOOCV] -> {out.relative_to(PROJECT_ROOT)}")
    print(f"    image  : {im.size} px = "
          f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
    print(f"    data   : {data_xlsx.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
