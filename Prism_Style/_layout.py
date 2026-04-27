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


# Per-letter legend filename suffix.  PNG basename = slot letter directly.
LEGEND_FILE_BY_LETTER = {
    "f": "f_prism_legend.png",   # Fig_Nf_prism_legend.png  (ROC compare)
    "g": "g_prism_legend.png",   # Fig_Ng_prism_legend.png  (Acc/F1/MCC key)
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
# NEW Remake-folder convention:
# - Generators save PNGs straight to Output/PowerPoint_Figures_Remake/sources/Fig_N/
# - PNG basenames now use the SLOT letter (a/b/c/d/e/f/g), not the historical
#   panel letter — so Fig_Ne_prism.png IS the SHAP image, etc.
CONTENT = {
    6: {
        "Panel_6a": "Fig_6a_prism.png",
        "Panel_6b": "Fig_6b_prism.png",
        "Panel_6c": "Fig_6c_prism.png",
        "Panel_6d": "Fig_6d_prism.png",
        "Panel_6e": "Fig_6e_prism.png",   # SHAP
        "Panel_6f": "Fig_6f_prism.png",   # ROC compare
        "Panel_6g": "Fig_6g_prism.png",   # perf compare bars
    },
    7: {
        "Panel_7a": "Fig_7a_prism.png",
        "Panel_7b": "Fig_7b_prism.png",
        "Panel_7c": "Fig_7c_prism.png",
        "Panel_7d": "Fig_7d_prism.png",
        "Panel_7e": "Fig_7e_prism.png",
        "Panel_7f": "Fig_7f_prism.png",
        "Panel_7g": "Fig_7g_prism.png",
    },
    8: {
        "Panel_8a": "Fig_8a_prism.png",
        "Panel_8b": "Fig_8b_prism.png",
        "Panel_8c": "Fig_8c_prism.png",
        "Panel_8d": "Fig_8d_prism.png",
        "Panel_8e": "Fig_8e_prism.png",
    },
}


# Group names that should be REMOVED from each slide (the old layout had them
# but the new design doesn't).
REMOVE = {
    6: {"Panel_6h"},
    7: {"Panel_7h"},
    8: {"Panel_8f"},   # old slide 8 had f=SHAP; new design moves SHAP to e
}


# In-place panel swaps on slides 2 and 3 — picture frames stay where the
# user placed them (position-match by stored (left_in, top_in) tuple, ±0.05"
# tolerance). We only swap the image bytes. Works for free-standing pictures
# AND for the BACKGROUND picture inside a manually-built group (the picture
# whose L/T sits at the group origin).
#
# Slide 2 (Figure 2):
#   a, b: line / sigmoid (Session B) — backgrounds inside Group 94 / Group 65
#   d:    empty Contractility axis frame (Session B) — Group 101 background
#   e:    Mexiletine multi-line (Session B) — Group 18 background
#   c, f: heatmaps (Session A) — free-standing pictures
#
# Slide 3 (Figure 3): top row alternates heatmap + surface plot (a/c/e = heatmaps).
INPLACE_PANELS = {
    # (slide_index_1based, panel_letter): (left_in, top_in, png_filename)
    (2, "a"): (0.13, 4.92, "Fig_2a_prism.png"),
    (2, "b"): (2.28, 4.88, "Fig_2b_prism.png"),
    (2, "c"): (4.50, 4.90, "Fig_2c_prism.png"),
    (2, "d"): (0.16, 6.72, "Fig_2d_prism.png"),
    (2, "e"): (2.51, 6.68, "Fig_2e_prism.png"),
    (2, "f"): (4.51, 6.69, "Fig_2f_prism.png"),
    (3, "a"): (0.04, 0.93, "Fig_3a_prism.png"),
    (3, "c"): (2.34, 0.94, "Fig_3c_prism.png"),
    (3, "e"): (4.65, 0.94, "Fig_3e_prism.png"),
    # Row 1 surfaces (paired with the heatmaps above):
    (3, "b"): (1.25, 0.79, "Fig_3b_prism.png"),   # Dactinomycin O2 (Eq3)
    (3, "d"): (3.56, 0.79, "Fig_3d_prism.png"),   # Nifedipine   O2 (Eq10)
    (3, "f"): (5.85, 0.79, "Fig_3f_prism.png"),   # Mexiletine   O2 (Eq7)
    # NOTE: b/d/f are now rendered at 3.77 x 3.82" (much larger than the
    # original 1.19 x 1.18" boxes). They are listed in RESIZE_TO_NATIVE
    # below so the swap also grows each PPTX box to match the new PNG.
    # Row 3 multi-line dose responses (background of Group 42 / Group 41):
    (3, "j"): (0.10, 3.88, "Fig_3j_prism.png"),   # Vandetanib O2
    (3, "k"): (2.74, 3.87, "Fig_3k_prism.png"),   # Sotalol Contractility
    # Panels g (R² bar) and i (LOOCV scatter) are intentionally NOT in this
    # map — Session D rendered them at sizes larger than their PPT boxes
    # under descriptive names (Fig_3_R2_bar_prism.png /
    # Fig_3_LOOCV_scatter_prism.png) and noted manual placement.
}

# fig_num for each in-place slide (slide 2 -> Figure 2 file dir, slide 3 ->
# Figure 3 file dir).
INPLACE_FIG_NUM = {2: 2, 3: 3}

# Inplace panels that should ALSO have their PPTX picture box resized to
# match the rendered PNG's native dimensions (top-left position is kept).
# Useful when re-rendering at a new size — without this the swap-only path
# would shrink the new image into the old box.
RESIZE_TO_NATIVE = {
    (3, "b"), (3, "d"), (3, "f"),
    (3, "j"), (3, "k"),
}

# Backward-compat aliases (older imports may still use the heatmap names).
HEATMAP_PANELS = INPLACE_PANELS
HEATMAP_FIG_NUM = INPLACE_FIG_NUM


# When re-rendering: target image size in inches (matches box exactly).
# Single source of truth used by each generator's overrides.
def target_size(slide: int, panel: str) -> tuple[float, float]:
    """(width_in, height_in) for the given slot, matching the PPTX box."""
    _, _, w, h = BOXES[slide][panel]
    return w, h
