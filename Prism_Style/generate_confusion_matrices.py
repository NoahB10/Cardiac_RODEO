"""Prism-style confusion matrices for Fig 6b, 7b, 8b.

2x2 blue-sequential grid (matplotlib ``Blues`` cmap), big cell counts
(white on dark, black on light), "Neg"/"Pos" tick labels, rotated "Actual"
on the left and "Predicted" below, with a thin outer frame and interior
crosshair separating the cells. No title (panel letter goes on the slide).

Data source: Output/PowerPoint_Figures/Fig_{N}/Fig_{N}b_data.xlsx (sheet "CM").
Output: Prism_Style/Fig_{N}b_prism.png for N in {6, 7, 8}.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import render_at_scale, helvetica
from _paths import panel_png, panel_data

FIG_DIR = PROJECT_ROOT / "Output" / "PowerPoint_Figures"
SCALE = 4

# Plot area locked at 3.6 cm x 3.6 cm (the prior good size), total image ~2.02" x 1.97".
CM_PER_IN = 2.54
PLOT_SIZE = 3.6 / CM_PER_IN   # 1.4173"

MARGIN_L = 0.55   # "Actual" + Neg/Pos y-tick labels
MARGIN_R = 0.05
MARGIN_T = 0.05
MARGIN_B = 0.50   # "Predicted" + Neg/Pos x-tick labels

FIG_W = PLOT_SIZE + MARGIN_L + MARGIN_R   # ~2.02"
FIG_H = PLOT_SIZE + MARGIN_T + MARGIN_B   # ~1.97" (~5.00 cm tall — matches the prior good size)
AXES_RECT = (MARGIN_L / FIG_W, MARGIN_B / FIG_H,
             PLOT_SIZE / FIG_W, PLOT_SIZE / FIG_H)

FRAME_COLOR = "#555555"
FRAME_LW_PT = 0.8

# Font sizes scaled to the 1.70" image (smaller than the c/d panels' 13pt
# because this image is tighter). Cell digits stay prominent.
CELL_FONT_PT = 14   # cell count digits
TICK_FONT_PT = 9    # "Neg" / "Pos"   — matches c/d panels
AXIS_LABEL_PT = 13  # "Actual" / "Predicted"   — matches c/d panels


def load_cm(fig_num: int):
    """Load the 2x2 CM for Fig {N}b (rows=Actual Neg/Pos, cols=Pred Neg/Pos)."""
    xlsx = FIG_DIR / f"Fig_{fig_num}" / f"Fig_{fig_num}b_data.xlsx"
    df = pd.read_excel(xlsx, sheet_name="CM", index_col=0)
    return df.to_numpy(dtype=int), xlsx


def _plot_cm(cm):
    """Return a ``plot_fn(fig, ax, scale)`` closure for this matrix."""
    vmax = int(cm.max())
    text_threshold = vmax * 0.5  # white above, black below

    def _fn(fig, ax, scale):
        ax.imshow(cm, cmap="Blues", vmin=0, vmax=vmax, aspect="equal",
                  interpolation="nearest", zorder=1)

        # Cell counts
        fp_num = helvetica(CELL_FONT_PT * scale)
        for (i, j), v in np.ndenumerate(cm):
            color = "white" if v > text_threshold else "black"
            ax.text(j, i, f"{int(v)}", ha="center", va="center",
                    color=color, fontproperties=fp_num, zorder=3)

        # Tick labels (Neg / Pos)
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Neg", "Pos"])
        ax.set_yticklabels(["Neg", "Pos"])
        fp_tick = helvetica(TICK_FONT_PT * scale)
        for lbl in ax.get_xticklabels() + ax.get_yticklabels():
            lbl.set_fontproperties(fp_tick)
        ax.tick_params(axis="both", length=0, pad=4 * scale)

        # Hide matplotlib spines; we draw a single thin frame + crosshair.
        for s in ax.spines.values():
            s.set_visible(False)

        # Outer frame (data coords: cells are at integer positions, extent ±0.5)
        frame = Rectangle(
            (-0.5, -0.5), 2, 2, fill=False,
            edgecolor=FRAME_COLOR,
            linewidth=FRAME_LW_PT * scale, zorder=4,
        )
        ax.add_patch(frame)

        # Interior crosshair
        ax.axvline(0.5, color=FRAME_COLOR,
                   linewidth=FRAME_LW_PT * scale, zorder=4)
        ax.axhline(0.5, color=FRAME_COLOR,
                   linewidth=FRAME_LW_PT * scale, zorder=4)

        # Axis labels — fixed-inch offsets converted to axes-fraction so they
        # stay a constant physical distance from the grid regardless of
        # PLOT_SIZE. Placed beyond the Neg/Pos tick labels.
        actual_x_in = 0.40        # "Actual" sits this far left of the grid
        predicted_y_in = 0.34     # "Predicted" sits this far below the grid

        ax.text(
            -actual_x_in / PLOT_SIZE, 0.5, "Actual",
            transform=ax.transAxes,
            ha="center", va="center", rotation=90,
            fontproperties=helvetica(AXIS_LABEL_PT * scale),
        )

        ax.text(
            0.5, -predicted_y_in / PLOT_SIZE, "Predicted",
            transform=ax.transAxes,
            ha="center", va="center",
            fontproperties=helvetica(AXIS_LABEL_PT * scale),
        )

        ax.set_xlim(-0.5, 1.5)
        ax.set_ylim(1.5, -0.5)  # flip so row 0 (Actual Neg) is on top

    return _fn


def _save_data(fig_num: int, cm: np.ndarray, src: Path) -> Path:
    out = panel_data(fig_num, "b")
    df_cm = pd.DataFrame(
        cm, index=["Actual_Neg", "Actual_Pos"], columns=["Pred_Neg", "Pred_Pos"]
    )
    metrics = {
        "TN": int(cm[0, 0]), "FP": int(cm[0, 1]),
        "FN": int(cm[1, 0]), "TP": int(cm[1, 1]),
    }
    metrics["Accuracy"] = (metrics["TN"] + metrics["TP"]) / cm.sum()
    metrics["Sensitivity"] = metrics["TP"] / max(1, metrics["TP"] + metrics["FN"])
    metrics["Specificity"] = metrics["TN"] / max(1, metrics["TN"] + metrics["FP"])
    metadata = pd.DataFrame([{
        "Panel": f"Fig_{fig_num}b (Prism)",
        "Description": "Confusion matrix for the Organoid classifier",
        "Source_Script": "Prism_Style/generate_confusion_matrices.py",
        "Source_Data": str(src.relative_to(PROJECT_ROOT)),
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_cm.to_excel(w, sheet_name="Plotted")
        pd.DataFrame([metrics]).to_excel(w, sheet_name="Metrics", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


def main():
    from PIL import Image
    for fig_num in (6, 7, 8):
        cm, src = load_cm(fig_num)
        out = panel_png(fig_num, "b")
        render_at_scale(
            _plot_cm(cm), (FIG_W, FIG_H), out,
            scale=SCALE, dpi=600, transparent=True,
            axes_rect=AXES_RECT,
        )
        data_xlsx = _save_data(fig_num, cm, src)
        im = Image.open(out)
        dpi = im.info.get("dpi", (600, 600))[0]
        print(f"[{fig_num}b] -> {out.relative_to(PROJECT_ROOT)}")
        print(f"    image : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
        print(f"    data  : {data_xlsx.relative_to(PROJECT_ROOT)}")
        print(f"    cm    : [[{cm[0,0]:4d}, {cm[0,1]:4d}], "
              f"[{cm[1,0]:4d}, {cm[1,1]:4d}]]")


if __name__ == "__main__":
    main()
