"""Prism-style SHAP aligned-pairs plots for Fig 6f, 7f, 8f.

Port of Output/SHAP_Data/shap_aligned_pairs_all.py with:
  - cross-platform paths (was Windows-only),
  - Prism toolkit styling (Helvetica, L-spines, render-at-scale),
  - no title (panel letter is added in PowerPoint).

The plot itself is unchanged in structure: for each of the top-5 features by
|mean SHAP|, drugs are split into positive/negative SHAP halves, sorted by
magnitude, and drawn as horizontal lines either side of x=0. Each line is
colored by the drug's ACTUAL class (positive class blue, negative class grey).
Line spacing creates visible white gaps. Drugs with |SHAP| < 1e-6 are excluded
for visual clarity.

Sources:
  - Output/SHAP_Data/shap_arrhythmia_values.csv      (Drug + 14 features)
  - Output/SHAP_Data/shap_heart_damage_values.csv
  - Output/SHAP_Data/shap_concern_binary_values.csv
  - Cleaned_Data/drug_classification.csv             (Drug -> label)

Output: Prism_Style/Fig_{N}f_prism.png for N in {6, 7, 8}.
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

SHAP_DIR = PROJECT_ROOT / "Output" / "SHAP_Data"
CLEANED_DIR = PROJECT_ROOT / "Cleaned_Data"

# Project-canonical SHAP colors (kept identical to the original generator).
COLOR_POS = "#1f77b4"   # positive class
COLOR_NEG = "#888888"   # negative class

CM_PER_IN = 2.54

# Plot HEIGHT matches the d-panel (threshold dot plot) plot height: 4.3 cm.
# Width is proportional / wide enough for 5 features × ~25 line-pairs.
PLOT_W = 3.50
PLOT_H = 4.3 / CM_PER_IN   # 1.693"

MARGIN_L = 1.30   # feature names ("k_elim (Contractility)" is the longest)
MARGIN_R = 0.10
MARGIN_T = 0.05
MARGIN_B = 0.40

FIG_W = PLOT_W + MARGIN_L + MARGIN_R   # ~4.90"
FIG_H = PLOT_H + MARGIN_T + MARGIN_B   # ~2.14"

# Spacings/widths tuned to fit ~50 line-pairs into a 4.3 cm tall plot.
LINE_WIDTH_PT = 0.7
FEATURE_SPACING = 0.9
LINE_SPACING = 0.034
ZERO_THRESHOLD = 1e-6
TOP_K = 5

SCALE = 4

AXES_RECT = (MARGIN_L / FIG_W, MARGIN_B / FIG_H,
             PLOT_W / FIG_W, PLOT_H / FIG_H)

TICK_FONT_PT = 9
AXIS_LABEL_PT = 13
LEGEND_FONT_PT = 8

# Per-figure spec: shap CSV stem, label column, positive/negative legend
# names, plus where the legend should sit inside the plot. Legend location is
# tuned per panel because the empty corner depends on the data distribution.
PANEL_SPECS = {
    6: dict(stem="shap_arrhythmia_values",
            label_col="Arrhythmia",
            label_kind="bool",
            pos_label="Arrhythmogenic",
            neg_label="Not arrhythmogenic",
            legend_loc="lower left"),
    7: dict(stem="shap_heart_damage_values",
            label_col="heart_damage",
            label_kind="bool",
            pos_label="Cardiotoxic",
            neg_label="Not cardiotoxic",
            legend_loc="upper right"),
    8: dict(stem="shap_concern_binary_values",
            label_col="Concern",
            label_kind="most",
            pos_label="Most Concern",
            neg_label="Less/No Concern",
            legend_loc="lower left"),
}


def _label_map(drug_class_df: pd.DataFrame, label_col: str, kind: str) -> dict:
    """drug -> bool (True == positive class)."""
    out = {}
    for _, row in drug_class_df.iterrows():
        v = row[label_col]
        if kind == "bool":
            out[row["Drug"]] = (str(v).lower() == "true") if isinstance(v, str) else bool(v)
        elif kind == "most":
            out[row["Drug"]] = str(v).lower() == "most"
        else:
            raise ValueError(f"unknown label_kind {kind!r}")
    return out


def _pretty_feature(feat: str) -> str:
    """Convert R0_Contractility -> R0 (Contractility), k_elim_O2 -> k_elim (O2)."""
    for suffix in ("_Contractility", "_O2"):
        if feat.endswith(suffix):
            return f"{feat[:-len(suffix)]} ({suffix[1:]})"
    return feat.replace("_", " ")


def load_panel(fig_num: int):
    spec = PANEL_SPECS[fig_num]
    shap_csv = SHAP_DIR / f"{spec['stem']}.csv"
    drug_csv = CLEANED_DIR / "drug_classification.csv"
    shap_df = pd.read_csv(shap_csv)
    drug_class = pd.read_csv(drug_csv)
    label_map = _label_map(drug_class, spec["label_col"], spec["label_kind"])
    n_pos = sum(label_map.values())
    n_neg = len(label_map) - n_pos
    return shap_df, label_map, n_pos, n_neg, spec, shap_csv


def _plot_fn(shap_df, label_map, n_pos, n_neg, spec):
    feature_cols = [c for c in shap_df.columns if c != "Drug"]
    mean_shap = shap_df[feature_cols].mean()
    top_features = mean_shap.abs().nlargest(TOP_K).index.tolist()

    def _fn(fig, ax, scale):
        y_positions = []
        y_labels = []

        for feat_idx, feature in enumerate(reversed(top_features)):
            base_y = feat_idx * FEATURE_SPACING
            y_positions.append(base_y)
            y_labels.append(_pretty_feature(feature))

            values = shap_df[feature].values
            drugs = shap_df["Drug"].values

            positive_data = [(v, d) for v, d in zip(values, drugs)
                             if v >= ZERO_THRESHOLD]
            negative_data = [(abs(v), d) for v, d in zip(values, drugs)
                             if v <= -ZERO_THRESHOLD]

            positive_data.sort(key=lambda x: x[0], reverse=True)
            negative_data.sort(key=lambda x: x[0], reverse=True)

            n_pairs = min(len(positive_data), len(negative_data))
            unpaired_pos = positive_data[n_pairs:]
            unpaired_neg = negative_data[n_pairs:]

            for i in range(n_pairs):
                y = base_y + i * LINE_SPACING
                pos_val, pos_drug = positive_data[i]
                neg_val, neg_drug = negative_data[i]
                pos_color = COLOR_POS if label_map.get(pos_drug, False) else COLOR_NEG
                neg_color = COLOR_POS if label_map.get(neg_drug, False) else COLOR_NEG
                ax.hlines(y, 0, pos_val,
                          colors=pos_color, linewidth=LINE_WIDTH_PT * scale)
                ax.hlines(y, -neg_val, 0,
                          colors=neg_color, linewidth=LINE_WIDTH_PT * scale)

            for i, (pos_val, pos_drug) in enumerate(unpaired_pos):
                y = base_y + (n_pairs + i) * LINE_SPACING
                pos_color = COLOR_POS if label_map.get(pos_drug, False) else COLOR_NEG
                ax.hlines(y, 0, pos_val,
                          colors=pos_color, linewidth=LINE_WIDTH_PT * scale)

            for i, (neg_val, neg_drug) in enumerate(unpaired_neg):
                y = base_y + (n_pairs + len(unpaired_pos) + i) * LINE_SPACING
                neg_color = COLOR_POS if label_map.get(neg_drug, False) else COLOR_NEG
                ax.hlines(y, -neg_val, 0,
                          colors=neg_color, linewidth=LINE_WIDTH_PT * scale)

        # Central x=0 line
        ax.axvline(0, color="black", linewidth=0.8 * scale, zorder=4)

        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels)
        ax.set_xlabel("SHAP value")
        # Y-limits scaled to FEATURE_SPACING so the layout works at any plot
        # height; lower buffer leaves room for the bottom feature's lines.
        ax.set_ylim(-0.15 * FEATURE_SPACING,
                    len(top_features) * FEATURE_SPACING + 0.10 * FEATURE_SPACING)

        apply_prism_style(
            ax,
            scale=scale,
            spine_width_pt=1.2,
            hide_spines=("top", "right"),
            show_xticks=True,
            ytick_length_pt=0,         # feature labels need no ticks
            ytick_width_pt=1.0,
            tick_label_size_pt=TICK_FONT_PT,
            ylabel_size_pt=AXIS_LABEL_PT,
            xlabel_size_pt=AXIS_LABEL_PT,
            ylabel_pad_pt=2,
            xlabel_pad_pt=2,
            clean_y_ticks=False,
            bold=False,
        )
        ax.tick_params(axis="y", length=0, width=0, pad=4 * scale)

        # Legend (frameless). Class counts intentionally omitted — just the
        # positive/negative class name.
        handles = [
            Line2D([0], [0], color=COLOR_POS,
                   linewidth=2.0 * scale,
                   label=spec["pos_label"]),
            Line2D([0], [0], color=COLOR_NEG,
                   linewidth=2.0 * scale,
                   label=spec["neg_label"]),
        ]
        ax.legend(
            handles=handles,
            loc=spec["legend_loc"],
            frameon=False,
            handlelength=1.4,
            handletextpad=0.4,
            labelspacing=0.30,
            borderaxespad=0.4,
            prop=helvetica(LEGEND_FONT_PT * scale),
        )

    return _fn


def main():
    from PIL import Image
    for fig_num in (6, 7, 8):
        try:
            shap_df, label_map, n_pos, n_neg, spec, src = load_panel(fig_num)
        except FileNotFoundError as e:
            print(f"[SKIP] {fig_num}f: {e}")
            continue
        out = HERE / f"Fig_{fig_num}f_prism.png"
        render_at_scale(
            _plot_fn(shap_df, label_map, n_pos, n_neg, spec),
            (FIG_W, FIG_H), out,
            scale=SCALE, dpi=600, transparent=True,
            axes_rect=AXES_RECT,
        )
        im = Image.open(out)
        dpi = im.info.get("dpi", (600, 600))[0]
        # Compute top features for the report line
        feature_cols = [c for c in shap_df.columns if c != "Drug"]
        top = shap_df[feature_cols].mean().abs().nlargest(TOP_K).index.tolist()
        print(f"[{fig_num}f] -> {out.name}")
        print(f"    image  : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
        print(f"    plot   : {PLOT_W:.3f}\" x {PLOT_H:.3f}\"  "
              f"({PLOT_W*CM_PER_IN:.2f} x {PLOT_H*CM_PER_IN:.2f} cm)")
        print(f"    source : {src.name} + drug_classification.csv")
        print(f"    classes: {n_pos} {spec['pos_label']} / "
              f"{n_neg} {spec['neg_label']}")
        print(f"    top {TOP_K}: {top}")


if __name__ == "__main__":
    main()
