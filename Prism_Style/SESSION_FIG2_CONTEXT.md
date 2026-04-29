# Session Context — Fig 2 Prism Panels (a, b, d, e)

This file captures the state at the end of the Fig 2 Prism re-render sessions
so a new terminal can pick up integration into the Remake PPTX.

---

## What's Done

Four Prism-style panels for **slide 2** of the Remake deck have been rendered
at native size (matching their PPT picture-frame boxes exactly, no scaling):

| Panel | Box (in)    | Source data XLSX                                  | Description                                                            |
|-------|-------------|---------------------------------------------------|------------------------------------------------------------------------|
| 2a    | 2.31 × 1.82 | `Fig_2g_Epirubicin_O2_data.xlsx` → Plotted_Data   | Epirubicin O₂ multi-line, 8 doses, time 0–96 h                         |
| 2b    | 2.33 × 1.82 | `Fig_2h_Epirubicin_TC50_data.xlsx` → TC50         | Epirubicin TC50 sigmoid (Hill 4PL), Viability vs Epirubicin mM, log-x  |
| 2d    | 2.25 × 1.74 | `Fig_2j_Mexiletine_Contractility_data.xlsx` → Plotted_Data | Mexiletine Contractility multi-line, 7 doses, time 0–96 h     |
| 2e    | 2.06 × 1.76 | `Fig_2k_Mexiletine_Waveforms_data.xlsx` → Plotted_Data     | Mexiletine stacked waveforms (Low/Med/High @ 48 h)            |

**Shared style:** Helvetica, L-spines (top/right hidden), axis labels 13 pt,
ticks 9 pt, transparent background, 600 dpi. 4× upscale + LANCZOS downscale
for crisp text. Generator runs at native size — no PPT-side rescaling needed.

**Y-axis convention** (a/b had ticks every 10 per latest user request;
d/e use intervals appropriate to their data range):
- 2a: ylim 0–75, yticks every 10 → `[0, 10, 20, 30, 40, 50, 60, 70]`
- 2b: ylim −5 to 105, yticks every 10 → `[0, 10, 20, ..., 100]`
- 2d: ylim 2–12, yticks every 2 → `[2, 4, 6, 8, 10, 12]`
- 2e: no y-ticks (stacked waveforms with text labels)

**Color palettes:**
- 2a: 8-color sequential (dark blue → yellow), defined as `PALETTE_8` in generator
- 2b: project Pos blue `#6C92ED` for points, black sigmoid, red `#D6332B` TC50 line, grey-dash 50% reference
- 2d: plasma-7 (`PALETTE_PLASMA_7`) — matches the original tracked
  `Fig_2j_Mexiletine_Contractility.png`. Order: high → low conc, dark blue → yellow
- 2e: plasma 3-tone — Low=`#fdb42f` (yellow), Med=`#cc4778` (pink), High=`#9c179e` (purple). Matches `plot_mexiletine_waveforms.py`

---

## File locations (current state)

### Generated outputs — saved to TRACKED Fig_2 folder
```
Output/PowerPoint_Figures/Fig_2/Fig_2a_prism.png       (262 KB, 2.31"×1.82")
Output/PowerPoint_Figures/Fig_2/Fig_2a_prism_data.xlsx
Output/PowerPoint_Figures/Fig_2/Fig_2b_prism.png       (132 KB, 2.33"×1.82")
Output/PowerPoint_Figures/Fig_2/Fig_2b_prism_data.xlsx
Output/PowerPoint_Figures/Fig_2/Fig_2d_prism.png       (2.25"×1.74")
Output/PowerPoint_Figures/Fig_2/Fig_2d_prism_data.xlsx
Output/PowerPoint_Figures/Fig_2/Fig_2e_prism.png       (2.06"×1.76")
Output/PowerPoint_Figures/Fig_2/Fig_2e_prism_data.xlsx
```

### Generator
```
Prism_Style/generate_fig2_panels.py
```
Run with: `python3 Prism_Style/generate_fig2_panels.py`

The `main()` writes directly to `OUT_DIR = Output/PowerPoint_Figures/Fig_2/`.
If you want to re-route to the Remake sources tree, change `OUT_DIR` at the
top of `main()` or use `panel_png(2, "x")` / `panel_data(2, "x")` from
`Prism_Style/_paths.py` (which point at the Remake sources tree).

---

## What's already in the Remake sources tree

```
Output/PowerPoint_Figures_Remake/sources/Fig_2/
├── Fig_2a_prism.png         ← STALE — old (yticks every 20). Replace.
├── Fig_2a_prism_data.xlsx   ← STALE.
├── Fig_2b_prism.png         ← STALE — old (yticks every 25). Replace.
├── Fig_2b_prism_data.xlsx   ← STALE.
├── Fig_2c_prism.png         ← KEEP (Session A heatmap, untouched this session)
├── Fig_2c_prism_data.xlsx   ← KEEP.
├── Fig_2d_prism.png         ← STALE — was empty axis frame (broken). Replace.
├── Fig_2d_prism_data.xlsx   ← STALE.
├── Fig_2e_prism.png         ← STALE — was wrong plot (Contractility multi-line). Replace.
├── Fig_2e_prism_data.xlsx   ← STALE.
├── Fig_2f_prism.png         ← KEEP (Session A heatmap).
└── Fig_2f_prism_data.xlsx   ← KEEP.
```

---

## Remake integration mechanism

The Remake PPTX (`Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`)
has slide-2 picture frames at fixed positions. The user has already placed
those frames; **do NOT move or resize them**. Only the picture bytes get
swapped in-place.

### Position dictionary
`Prism_Style/_layout.py` → `INPLACE_PANELS`:
```python
INPLACE_PANELS = {
    (2, "a"): (0.13, 4.92, "Fig_2a_prism.png"),
    (2, "b"): (2.28, 4.88, "Fig_2b_prism.png"),
    (2, "c"): (4.50, 4.90, "Fig_2c_prism.png"),
    (2, "d"): (0.16, 6.72, "Fig_2d_prism.png"),
    (2, "e"): (2.51, 6.68, "Fig_2e_prism.png"),
    (2, "f"): (4.51, 6.69, "Fig_2f_prism.png"),
    # slide 3 entries also live here…
}
INPLACE_FIG_NUM = {2: 2, 3: 3}
```
Tuple = (left_in, top_in, png_filename).

### Swap script
`Prism_Style/apply_layout_to_remake.py` — `update_inplace_panels()` walks
slide 2/3, finds each picture frame whose (left, top) matches a dict entry
within ±0.05" tolerance, and replaces only the embedded image bytes
(`_swap_picture_source()`). The frame's bbox is preserved exactly. Works for
free-standing pictures AND background pictures inside groups (their L/T sits
at the group origin).

### Source folder the swap reads from
The swap reads PNGs from `panel_dir(fig_num)` =
`Output/PowerPoint_Figures_Remake/sources/Fig_2/`. So the latest PNGs MUST
be present there with the names declared in `INPLACE_PANELS`.

---

## Integration recipe (run this in a new terminal)

```bash
cd "/Users/noahb/Documents/HebrewU Bioengineering/Cardiac_RODEO"

# 1) Stage the 4 fresh panels into the Remake sources tree, replacing
#    the stale a/b/d/e files there. Keep c and f untouched (Session A).
for letter in a b d e; do
    cp "Output/PowerPoint_Figures/Fig_2/Fig_2${letter}_prism.png" \
       "Output/PowerPoint_Figures_Remake/sources/Fig_2/Fig_2${letter}_prism.png"
    cp "Output/PowerPoint_Figures/Fig_2/Fig_2${letter}_prism_data.xlsx" \
       "Output/PowerPoint_Figures_Remake/sources/Fig_2/Fig_2${letter}_prism_data.xlsx"
done

# 2) Verify the 6 panels are all present and recent in the sources tree.
ls -la Output/PowerPoint_Figures_Remake/sources/Fig_2/

# 3) Swap the bytes inside the Remake PPTX (uses python-pptx; needs
#    miniconda env that has it installed).
/Users/noahb/miniconda3/bin/python Prism_Style/apply_layout_to_remake.py
```

The script prints a per-panel report and writes back to
`Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`.

---

## What this session DID NOT touch

- Slide-2 picture frame positions (do NOT move them — they're set manually).
- The `figure_registry.csv` and `FIGURE_CHANGE_LOG.md` updates from the
  earlier session were already committed (`69d0e15 Prism re-render: Fig 2
  line plots and sigmoid`). If you want a follow-up entry for the
  d/e fix + a/b yaxis tweak, add a new dated section to
  `Output/PowerPoint_Figures/FIGURE_CHANGE_LOG.md`.
- Slide 3 panels (Session D's territory) — the `INPLACE_PANELS` dict
  already covers them but no new renders happened this session.

---

## Important gotchas

1. **Python interpreter**: use `/Users/noahb/miniconda3/bin/python`. The
   system `/usr/bin/python3` doesn't have `pptx`, `pandas`, etc.
2. **Frame position match**: if you move a picture frame on slide 2 in
   PowerPoint, its (L, T) may drift outside the ±0.05" tolerance and the
   swap will silently skip it (logged as `[WARN]`). Re-snap or update the
   tuple in `_layout.py`.
3. **The d/e fix corrected a content swap**: previously panel d was an
   empty axis frame (broken) and panel e had the multi-line plot that
   actually belongs in d. Now d=Mexiletine Contractility multi-line and
   e=Mexiletine stacked waveforms — matching the slide layout intent
   (top row Epirubicin: O2 / TC50 / heatmap; bottom row Mexiletine:
   Contractility / waveforms / heatmap).
4. **Mexiletine waveform Plotted_Data** units: the per-trace columns are
   already mV (×1000 from raw amp_vpp_filtered). Don't re-scale.
5. **Plasma palette match**: 2d's `PALETTE_PLASMA_7` was sampled to match
   `plt.get_cmap('plasma', 7)` from `plot_contractility.py`. If you ever
   regenerate the tracked `Fig_2j_Mexiletine_Contractility.png` with a
   different cmap, also update `PALETTE_PLASMA_7` to keep visual identity.

---

## Open follow-ups (if user wants)

- Update `figure_registry.csv` rows for `2,a` `2,b` `2,d_prism` `2,e` to
  reflect the new yticks / new plot content (existing rows still point at
  the prism PNGs in the tracked folder, so paths are correct — just the
  visual differs).
- Add a `## YYYY-MM-DD — Prism Fig 2 fix: d & e content swap, a/b yticks every 10`
  block to `Output/PowerPoint_Figures/FIGURE_CHANGE_LOG.md`.
- Commit message suggestion: `Prism Fig 2: fix d/e content + a/b yticks every 10`.
