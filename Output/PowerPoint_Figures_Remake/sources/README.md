# Remake sources — folder convention

This folder holds the **source files for `Cardiac_RODEO_Remake.pptx`** —
images and paired data XLSX for every panel that's currently in the Remake
presentation.

## Layout

```
sources/
  Fig_1/  ─┐
  Fig_2/   │  symlinks back to Output/PowerPoint_Figures/Fig_N/
  Fig_3/   │  (these figures still use the original Tracked content;
  Fig_4/   │   no Prism re-render yet)
  Fig_5/  ─┘
  Fig_6/   ──┐
  Fig_7/     │  REAL FOLDERS — contain ONLY the Prism re-render PNGs +
  Fig_8/   ──┘  paired _prism_data.xlsx that the Remake PPTX uses
  Fig_S1/ ─┐
  Fig_S2/  │  symlinks (no Prism work yet)
  Fig_S3/  │
  Fig_S4/ ─┘
  FIGURE_CHANGE_LOG.md  → symlink to Output/PowerPoint_Figures/FIGURE_CHANGE_LOG.md
  figure_registry.csv   → symlink to Output/PowerPoint_Figures/figure_registry.csv
```

## Why two layouts

- **Fig_1/2/3/4/5 + S1–S4**: still symlinked to the Tracked tree because the
  Remake PPTX uses the same source content as the Tracked PPTX for those
  figures. No Prism-styled re-renders exist yet.
- **Fig_6/7/8**: real folders containing ONLY the new Prism panels. Each
  panel has a paired `_prism_data.xlsx` describing exactly the data
  rendered. The original Tracked content for these figures (`Fig_6a.png`,
  `Fig_6a_data.xlsx`, the `Axisless/` folder, etc.) stays put in
  `Output/PowerPoint_Figures/Fig_6/` so the Tracked PPTX still works.

## File naming convention (in real folders)

- `Fig_N{letter}_prism.png` — the Prism-styled panel PNG used in the Remake
  PPTX. Native size = box size (no PPT scaling, fonts stay sharp).
- `Fig_N{letter}_prism_data.xlsx` — the data plotted on that panel, with
  sheets like `Plotted`, `Metadata`, and panel-specific extras
  (`Top5_Features` for SHAP, per-model AUC sheets for ROC compare, etc.).
- `Fig_N{letter}_prism_legend.png` — the standalone legend PNG for panels
  whose legend lives outside the plot area (currently f/g on slides 6/7).

## Generators

All scripts in `Prism_Style/` write directly into these folders via
`Prism_Style/_paths.py`. After running any `generate_*.py`, refresh the PPTX
with:

```bash
python3 Prism_Style/apply_layout_to_remake.py
```

## When extending to other figures

When you start Prism work on Fig 1/2/3/4/5 or S1–S4, follow the same pattern:
1. Run a generator that saves to `sources/Fig_N/Fig_N{letter}_prism.png`
2. Break the symlink for that figure: `rm sources/Fig_N`, `mkdir sources/Fig_N`
3. Move the Prism files into the new real folder
4. Update `figure_registry.csv` rows for those panels
5. Run `apply_layout_to_remake.py` to wire them into the PPTX
