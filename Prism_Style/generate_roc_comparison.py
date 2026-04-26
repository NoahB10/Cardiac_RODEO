"""Prism-style ROC comparison curves for Fig 6g, 7g.

Fig 6g (Arrhythmia): Organoid vs MoLFormer CNN models — 3 curves.
Fig 7g (HeartDamage): Organoid vs 4 ADMET methods (DICTrank x ADMET-AI/SwissADME,
                      Scaffold x ADMET-AI/SwissADME) — 5 curves.
Fig 8g: does not exist — no comparison panel for ConcernBinary.

Each curve gets a shaded ±1 std confidence band when band data is available:
  - 7g sheets carry TPR_Lower/TPR_Upper natively for every model.
  - 6g sheets are means only; the Organoid band is reconstructed from the
    Fig_6a 10-fold CV data (same source as the a-panel). CNN comparators have
    no per-fold data in the project — they render as plain lines.

Project conventions (from figure_registry / CLAUDE.md):
- Organoid is always green (#2ca02c) AND first in the legend.
- 6g comparators (CNN): DIQT=red (#d62728), 5-fold=purple (#9467bd).
- 7g comparators (ADMET): ADMET-AI DICTrank=blue (#1f77b4),
                          SwissADME DICTrank=orange (#ff7f0e),
                          ADMET-AI Scaffold=purple (#9467bd),
                          SwissADME Scaffold=red (#d62728).

Plot area locked at 3.6 cm x 3.6 cm — matches the a-panel ROC.

Data: Output/PowerPoint_Figures/Fig_{N}/Fig_{N}g_data.xlsx, one sheet per
model. 6g Organoid bands cross-loaded from Fig_6a_data.xlsx ROC_Data sheet.
Output: Prism_Style/Fig_{N}g_prism.png for N in {6, 7}.
"""

from __future__ import annotations

import re
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
from prism_style import apply_prism_style, render_at_scale, helvetica, clean_decimal_formatter
from _roc_bootstrap import (cached_bootstrap, cv_fold_band_from_a_panel,
                             cv_fold_band_for_7g_organoid,
                             roc_from_predictions)
from _legend_export import render_legend_image
import matplotlib.ticker as mticker

FIG_DIR = PROJECT_ROOT / "Output" / "PowerPoint_Figures"

ORGANOID_GREEN = "#2ca02c"
DIAG_COLOR = "#666666"
BAND_ALPHA = 0.20
CM_PER_IN = 2.54
SCALE = 4

# Plot HEIGHT 3.6 cm — same as the a-panel ROC and the b-panel CM. Width
# stays 1.85" so the long axis labels ("True/False Positive Rate" at 13 pt)
# don't get cut off.
PLOT_W = 1.85
PLOT_H = 3.6 / CM_PER_IN   # 1.4173" — aligned with a, b

MARGIN_L = 0.62   # rotated "True Positive Rate" + Y-tick numbers
MARGIN_R = 0.10
MARGIN_T = 0.05
MARGIN_B = 0.55   # "False Positive Rate" + X-tick numbers

FIG_W = PLOT_W + MARGIN_L + MARGIN_R   # ~2.57"
FIG_H = PLOT_H + MARGIN_T + MARGIN_B   # ~2.30"


def _layout():
    rect = (MARGIN_L / FIG_W, MARGIN_B / FIG_H,
            PLOT_W / FIG_W, PLOT_H / FIG_H)
    return FIG_W, FIG_H, rect

TICK_FONT_PT = 9      # uniform across all Prism panels
AXIS_LABEL_PT = 13    # uniform across all Prism panels
LEGEND_FONT_PT = 8    # legend sits outside the plot in its own PNG

# Per-figure: list of (sheet_name, label, color), Organoid first.
PANEL_SPECS: dict[int, list[tuple[str, str, str]]] = {
    6: [
        ("Organoid",  "Organoid",            ORGANOID_GREEN),
        ("CNN_DIQT",  "CNN (DIQT)",          "#d62728"),
        ("CNN_5fold", "CNN (5-fold)",        "#9467bd"),
    ],
    7: [
        ("Organoid",            "Organoid",          ORGANOID_GREEN),
        ("DICTrank_ADMETAI",    "ADMET-AI DICTrank",   "#1f77b4"),
        ("DICTrank_SwissADME",  "SwissADME DICTrank",  "#ff7f0e"),
        ("Scaffold_ADMETAI",    "ADMET-AI Scaffold",   "#9467bd"),
        ("Scaffold_SwissADME",  "SwissADME Scaffold",  "#d62728"),
    ],
}

# Both g-panel legends are exported as separate PNG files so they can be
# placed independently in PowerPoint.


# 6g comparator → (excel sheet name, prob column, label column)
_FIG6G_PRED_SHEETS = {
    "CNN_DIQT":  ("DIQT_Predictions",      "DIQT_prob",   "Arrhythmia_label"),
    "CNN_5fold": ("CNN_5fold_Predictions", "CNN_25_prob", "Arrhythmia_label"),
}


def _comparator_bootstrap(cache_key: str, src: Path, sheet: str,
                           prob_col: str, label_col: str,
                           target_fpr: np.ndarray):
    df = pd.read_excel(src, sheet_name=sheet)
    df.columns = [str(c).strip() for c in df.columns]
    probs = df[prob_col].to_numpy(dtype=float)
    labels = df[label_col].to_numpy(dtype=int)
    stats = cached_bootstrap(cache_key, probs, labels)
    return (np.interp(target_fpr, stats["FPR"], stats["TPR_lower"]),
            np.interp(target_fpr, stats["FPR"], stats["TPR_upper"]))


# 7g DICTrank comparators — predictions stored in dictrank_retrain CSV.
_FIG7G_DICTRANK_FILE = (PROJECT_ROOT / "Output" / "ADMET_Comparison" /
                        "dictrank_retrain_predictions_25.csv")
_FIG7G_LABELS_FILE = (PROJECT_ROOT / "Output" / "ADMET_Comparison" /
                      "cardiac_rodeo_full_ADMET.csv")
_FIG7G_AUC_STD_FILE = (PROJECT_ROOT / "Output" / "ADMET_Comparison" /
                       "all_methods_metrics_with_std.csv")
_FIG7G_DICTRANK_SHEETS = {
    "DICTrank_ADMETAI":   "ADMET_AI_Prob",
    "DICTrank_SwissADME": "SwissADME_Prob",
}
# Scaffold per-drug predictions are NOT persisted to disk by full_analysis.py
# — only the bootstrap MEAN curves are saved. Until that script is patched to
# also dump per-drug probs, we synthesize a band of equivalent width using
# the saved 10-fold CV AUC_Std from all_methods_metrics_with_std.csv.
_FIG7G_SCAFFOLD_SHEETS = {
    "Scaffold_ADMETAI":   ("Scaffold", "ADMET-AI"),
    "Scaffold_SwissADME": ("Scaffold", "SwissADME"),
}


def _load_7g_dictrank():
    labels = pd.read_csv(_FIG7G_LABELS_FILE)
    preds = pd.read_csv(_FIG7G_DICTRANK_FILE)
    merged = preds.merge(labels[["Drug", "heart_damage"]], on="Drug", how="left")
    merged["heart_damage"] = merged["heart_damage"].astype(int)
    return merged


def _bootstrap_band_for_7g_dictrank(sheet_name: str, target_fpr: np.ndarray):
    if sheet_name not in _FIG7G_DICTRANK_SHEETS:
        return None, None
    prob_col = _FIG7G_DICTRANK_SHEETS[sheet_name]
    merged = _load_7g_dictrank().dropna(subset=[prob_col])
    probs = merged[prob_col].to_numpy(dtype=float)
    labels = merged["heart_damage"].to_numpy(dtype=int)
    stats = cached_bootstrap(f"Fig_7g_{sheet_name}", probs, labels)
    return (np.interp(target_fpr, stats["FPR"], stats["TPR_lower"]),
            np.interp(target_fpr, stats["FPR"], stats["TPR_upper"]))


def _scaffold_band_from_auc_std(sheet_name: str, mean_tpr: np.ndarray):
    """Scaffold methods: per-drug predictions aren't on disk; use the saved
    10-fold AUC_Std as a proxy band width. NOT bootstrap — see memory.
    """
    if sheet_name not in _FIG7G_SCAFFOLD_SHEETS:
        return None, None
    method, model = _FIG7G_SCAFFOLD_SHEETS[sheet_name]
    metrics = pd.read_csv(_FIG7G_AUC_STD_FILE)
    metrics.columns = [c.strip() for c in metrics.columns]
    row = metrics[(metrics["Method"] == method) & (metrics["Model"] == model)]
    if row.empty:
        return None, None
    auc_std = float(row["AUC_Std"].iloc[0])
    return (np.clip(mean_tpr - auc_std, 0, 1),
            np.clip(mean_tpr + auc_std, 0, 1))


def _organoid_band_for_g(fig_num: int, target_fpr: np.ndarray):
    """Organoid band for the g panels — uses the SAME 10-fold CV per-fold
    ROC source as the matching a-panel (so 6a/6g and 7a/7g visually agree).
    """
    if fig_num == 6:
        stats = cv_fold_band_from_a_panel(6)
    else:
        stats = cv_fold_band_for_7g_organoid()
    return (np.interp(target_fpr, stats["FPR"], stats["TPR_lower"]),
            np.interp(target_fpr, stats["FPR"], stats["TPR_upper"]))


def load_curves(fig_num: int):
    """Return (curves, src) where curves is a list of dicts in legend order.

    Each dict has: label, color, fpr, tpr, auc, lower (or None), upper (or None).
    Bands come from TPR_Lower/Upper if present in the sheet; for 6g/Organoid
    we cross-load the a-panel 10-fold CV to get a band.
    """
    src = FIG_DIR / f"Fig_{fig_num}" / f"Fig_{fig_num}g_data.xlsx"
    out = []
    for sheet, label, color in PANEL_SPECS[fig_num]:
        df = pd.read_excel(src, sheet_name=sheet)
        df.columns = [str(c).strip() for c in df.columns]
        fpr = df["FPR"].to_numpy(dtype=float)
        tpr = df["TPR"].to_numpy(dtype=float)
        auc = float(df["AUC"].dropna().iloc[0])
        # Recompute bands using bootstrap (n=300, seed=42) on the per-drug
        # predictions, cached to Prism_Style/bands_cache/. Ignore any
        # TPR_Lower/Upper in the source sheet — in 7g those were a
        # binomial-SE shortcut, not bootstrap.
        if sheet == "Organoid":
            lower, upper = _organoid_band_for_g(fig_num, fpr)
        elif fig_num == 6 and sheet in _FIG6G_PRED_SHEETS:
            pred_sheet, prob_col, label_col = _FIG6G_PRED_SHEETS[sheet]
            lower, upper = _comparator_bootstrap(
                f"Fig_6g_{sheet}", src, pred_sheet, prob_col, label_col, fpr)
        elif fig_num == 7 and sheet in _FIG7G_DICTRANK_SHEETS:
            lower, upper = _bootstrap_band_for_7g_dictrank(sheet, fpr)
        elif fig_num == 7 and sheet in _FIG7G_SCAFFOLD_SHEETS:
            # Per-drug predictions for Scaffold methods aren't persisted by
            # full_analysis.py. AUC_Std proxy until that script is patched.
            lower, upper = _scaffold_band_from_auc_std(sheet, tpr)
        else:
            lower = upper = None
        out.append({
            "label": label, "color": color,
            "fpr": fpr, "tpr": tpr, "auc": auc,
            "lower": lower, "upper": upper,
        })
    return out, src


def _build_legend_handles(curves, scale):
    """Same handles the panel would have used internally — exported to the
    standalone legend PNG."""
    handles = []
    for i, c in enumerate(curves):
        lw = 1.4 * scale if i == 0 else 1.1 * scale
        handles.append(
            Line2D([0], [0], color=c["color"], linewidth=lw,
                   label=f"{c['label']} ({c['auc']:.2f})")
        )
    return handles


def _plot_fn(curves):
    def _fn(fig, ax, scale):
        # Diagonal reference (random classifier)
        ax.plot([0, 1], [0, 1],
                color=DIAG_COLOR,
                linestyle="--", dashes=(4, 3),
                linewidth=0.9 * scale, zorder=2)

        # Plot each curve. Organoid (first) gets a thicker line, and any curve
        # with band data gets a shaded ±1 std region.
        for i, c in enumerate(curves):
            lw = 1.4 * scale if i == 0 else 1.1 * scale
            if c["lower"] is not None and c["upper"] is not None:
                ax.fill_between(c["fpr"], c["lower"], c["upper"],
                                color=c["color"], alpha=BAND_ALPHA,
                                linewidth=0,
                                zorder=3 if i == 0 else 2)
            ax.plot(c["fpr"], c["tpr"], color=c["color"],
                    linewidth=lw, zorder=5 if i == 0 else 4)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
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

        # Legend is rendered to a separate PNG (Fig_Ng_prism_legend.png)
        # — see render_legend_image in _legend_export.py.

    return _fn


def main():
    from PIL import Image
    for fig_num in (6, 7):
        try:
            curves, src = load_curves(fig_num)
        except FileNotFoundError as e:
            print(f"[SKIP] {fig_num}g: {e}")
            continue
        fig_w, fig_h, rect = _layout()
        out = HERE / f"Fig_{fig_num}g_prism.png"
        render_at_scale(
            _plot_fn(curves), (fig_w, fig_h), out,
            scale=SCALE, dpi=600, transparent=True,
            axes_rect=rect,
        )
        # Standalone legend PNG.
        legend_out = HERE / f"Fig_{fig_num}g_prism_legend.png"
        render_legend_image(
            _build_legend_handles(curves, scale=SCALE),
            prop=helvetica(LEGEND_FONT_PT * SCALE),
            out_path=legend_out,
            scale=SCALE,
            handlelength=1.4,
            handletextpad=0.4,
            labelspacing=0.35,
            borderpad=0.0,
        )
        im = Image.open(out)
        dpi = im.info.get("dpi", (600, 600))[0]
        leg_im = Image.open(legend_out)
        print(f"[{fig_num}g] -> {out.name}")
        print(f"    image  : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"  (no legend)")
        print(f"    legend : {legend_out.name}  {leg_im.size} px = "
              f"{leg_im.size[0]/dpi:.3f}\" x {leg_im.size[1]/dpi:.3f}\"")
        print(f"    plot   : {PLOT_W:.3f}\" x {PLOT_H:.3f}\"  "
              f"({PLOT_W*CM_PER_IN:.2f} x {PLOT_H*CM_PER_IN:.2f} cm)")
        print(f"    source : {src.name}")
        for c in curves:
            band = "with band" if c["lower"] is not None else "no band"
            print(f"      {c['label']:25s} AUC={c['auc']:.3f}  ({band})")


if __name__ == "__main__":
    main()
