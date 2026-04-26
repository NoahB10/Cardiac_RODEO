"""Target box sizes (inches) and panel content mapping for the Remake PPTX
(`Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`).

Slide map (Remake numbering -> figure):
    slide 7 = Figure 6 (Arrhythmia)   — has named groups Panel_6a..g
    slide 8 = Figure 7 (HeartDamage)  — loose pictures, no groups
    slide 9 = Figure 8 (ConcernBinary)— loose pictures, no groups

Read directly from the tracked PPTX once and pinned here so the Prism
generators can re-render at the exact box dimensions (no PPT-side scaling
distortion of fonts).

NEW slide layout (per user's design on slide 6):
- Row 1: a (ROC), b (CM), c (4-metric bar)            — three 1.70" squares
- Row 2: d (threshold dot), e (SHAP)                   — was 3 panels in old layout
- Row 3: f (perf compare bars), g (ROC compare)        — was f/g/h before
- (h panel REMOVED)

Slide 8 has no f or g (no comparison data for ConcernBinary).

`CONTENT` maps PPTX group name -> Prism PNG basename (the source image to
render into that slot).  The renaming swaps:
    Panel_Ne (was cumulative) <- Fig_Nf_prism.png  (SHAP)
    Panel_Nf (was SHAP slot)  <- Fig_Nh_prism.png  (perf compare bars)
    Panel_Ng (was ROC compare slot, unchanged content)
    Panel_Nh -> REMOVE
"""

from __future__ import annotations

# Plot-bottom alignment (per slide 7's manual layout): tops are CALCULATED
# so each row's plot bases line up. Tops therefore vary across panels in a
# row when margin_b differs (e.g. c-panel sits higher because its margin_b
# is smaller than a/b/c's).
#
# Per-panel margin_b (image-bottom margin = the gap below the plot in the
# generated PNG) — must match each generator's actual margin_b.
MARGIN_B = {
    "a": 0.55,    # ROC curve bottom margin (False Positive Rate label)
    "b": 0.50,    # CM bottom margin (Predicted label)
    "c": 0.44,    # 4-metric bar
    "d": 0.45,    # threshold dot plot
    "e": 0.40,    # SHAP
    "f": 0.55,    # ROC compare — taller, matches a-panel margin
    "g": 0.85,    # perf compare bars (2-line model labels at 9pt)
}

# Per-row layout: plot_bottom (where every panel's plot in the row ends),
# letter_top (where panel letters sit, common across the row), and the
# left position of each panel in the row.
ROW_LAYOUT = {
    "row1": {
        "plot_bottom": 2.27,
        "letter_top": 0.62,
        "lefts": {"a": 0.10, "b": 2.34, "c": 4.46},
    },
    "row2": {
        "plot_bottom": 4.78,
        "letter_top": 2.82,
        "lefts": {"d": 0.10, "e": 1.92},
    },
    "row3": {
        # User moved row 3 lower in their slide-6 layout — plot bottoms at
        # 6.95 (vs 6.58 earlier).
        "plot_bottom": 6.95,
        "letter_top": 5.21,
        "lefts": {"f": 0.10, "g": 3.00},   # f LEFT (~2.57 wide), g RIGHT (wide)
    },
}


# Legends are saved as separate PNGs (Fig_Ng_prism_legend.png and
# Fig_Nh_prism_legend.png). The script places ONE copy of each on its slide
# in the OFF-SLIDE grey area (L=8.0, beyond the 7.09" slide width) — the
# user then drags them into position once. On re-runs the script removes
# any prior pictures (legends included) before re-adding to avoid duplicates.
LEGEND_STASH_X = 8.0      # inches (slide is 7.09" wide; this is in the grey area)
LEGEND_STASH_T_BY_LETTER = {
    "f": 0.50,            # f's legend (ROC compare colors / AUCs)
    "g": 1.30,            # g's legend (Acc/F1/MCC color key)
}


# Per-letter legend filename suffix.  E.g. f panel uses Fig_N + 'g_prism_legend.png'
# because the f slot's CONTENT is the old g-letter Prism PNG (after the swap).
LEGEND_FILE_BY_LETTER = {
    "f": "g_prism_legend.png",   # Fig_Ng_prism_legend.png
    "g": "h_prism_legend.png",   # Fig_Nh_prism_legend.png
}

# Which row each panel belongs to.
PANEL_ROW = {
    "a": "row1", "b": "row1", "c": "row1",
    "d": "row2", "e": "row2",
    "f": "row3", "g": "row3",
}


# Maps PPTX panel group -> source Prism PNG filename in Prism_Style/.
# After the f<->g swap:
#   slot e = SHAP                (Fig_Nf_prism.png)
#   slot f = ROC compare (square) (Fig_Ng_prism.png)
#   slot g = perf compare bars   (Fig_Nh_prism.png)
CONTENT = {
    6: {
        "Panel_6a": "Fig_6a_prism.png",
        "Panel_6b": "Fig_6b_prism.png",
        "Panel_6c": "Fig_6c_prism.png",
        "Panel_6d": "Fig_6d_prism.png",
        "Panel_6e": "Fig_6f_prism.png",   # SHAP
        "Panel_6f": "Fig_6g_prism.png",   # ROC compare (was 6g content)
        "Panel_6g": "Fig_6h_prism.png",   # perf compare bars (was 6h content)
    },
    7: {
        "Panel_7a": "Fig_7a_prism.png",
        "Panel_7b": "Fig_7b_prism.png",
        "Panel_7c": "Fig_7c_prism.png",
        "Panel_7d": "Fig_7d_prism.png",
        "Panel_7e": "Fig_7f_prism.png",
        "Panel_7f": "Fig_7g_prism.png",
        "Panel_7g": "Fig_7h_prism.png",
    },
    8: {
        "Panel_8a": "Fig_8a_prism.png",
        "Panel_8b": "Fig_8b_prism.png",
        "Panel_8c": "Fig_8c_prism.png",
        "Panel_8d": "Fig_8d_prism.png",
        "Panel_8e": "Fig_8f_prism.png",
    },
}


# Group names that should be REMOVED from each slide (the old layout had them
# but the new design doesn't).
REMOVE = {
    6: {"Panel_6h"},
    7: {"Panel_7h"},
    8: {"Panel_8f"},   # old slide 8 had f=SHAP; new design moves SHAP to e
}


# When re-rendering: target image size in inches (matches box exactly).
# Single source of truth used by each generator's overrides.
def target_size(slide: int, panel: str) -> tuple[float, float]:
    """(width_in, height_in) for the given slot, matching the PPTX box."""
    _, _, w, h = BOXES[slide][panel]
    return w, h
