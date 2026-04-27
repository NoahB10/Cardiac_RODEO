"""Prism-style per-well LOWESS heatmaps for Fig 2c, 2f, 3a, 3c, 3e.

Diverging blue->white->red colormap, no top/right spines, Helvetica axis
labels (13 pt) and tick labels (9 pt). Each PNG is rendered at its locked
PPTX box size so PPT does no scaling and fonts stay sharp.

Panels:
    Fig 2c — Epirubicin O2 heatmap (slide 2 panel c)        2.60" x 1.78"
    Fig 2f — Mexiletine Contractility heatmap (panel f)     2.60" x 1.74"
    Fig 3a — Dactinomycin O2 heatmap (slide 3 panel a)      1.31" x 1.03"
    Fig 3c — Nifedipine O2 heatmap (panel c)                1.33" x 1.10"
    Fig 3e — Mexiletine O2 heatmap (panel e)                1.31" x 1.08"

Pipeline (per CLAUDE.md "Heatmap Generation (Smoothed)"):
    1. Load sorted CSV (rows=time, cols=wells with pandas .x suffixes)
    2. Apply drug-specific drops (column names) and/or post-sort row removals
    3. Linear interpolate NaN gaps within each well (limit=10, both ways)
    4. LOWESS w=16 per well along time
    5. Transpose to (rows=wells, cols=time)
    6. O2: clip at 100 + per-row baseline compression toward ~20% O2
       Contractility: scale x100
    7. Render with Prism style — axis labels at 13 pt, ticks at 9 pt,
       Y ticks placed at the centre of each concentration group with
       deduplicated labels (pandas '.x' suffixes stripped).

Each panel also produces an axisless variant (same outer size, no tick marks,
no tick labels, no axis titles) saved to Output/PowerPoint_Figures/Fig_N/Axisless/.
"""

from __future__ import annotations

import re
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib.colors import LinearSegmentedColormap

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401  — registers Helvetica + rcParams
from prism_style import render_at_scale, helvetica
from _paths import panel_png, panel_data

CLEANED = PROJECT_ROOT / "Cleaned_Data"
SCALE = 4

# ---------------------------------------------------------------------------
# Visual constants (Prism style)
# ---------------------------------------------------------------------------

HEATMAP_BLUE = "#123BFF"
HEATMAP_RED = "#FF2908"
LOWESS_W = 16

AXIS_LABEL_PT_LARGE = 13   # slide-2 box (≥2.5" wide) — Prism standard
TICK_LABEL_PT_LARGE = 9
AXIS_LABEL_PT_SMALL = 7    # slide-3 box (~1.3" wide) — matches the small-panel
TICK_LABEL_PT_SMALL = 6    #   convention from prism_panel_final_sizes.md
SPINE_LW_PT = 1.0
SPINE_COLOR = "black"
MAX_Y_TICK_LABELS_LARGE = 8   # slide-2 panels can fit more dose ticks
MAX_Y_TICK_LABELS_SMALL = 5   # slide-3 panels would overlap above this


# ---------------------------------------------------------------------------
# Panel specs — image sizes match the user's locked PPT box sizes
# ---------------------------------------------------------------------------

PANEL_SPECS = {
    # (fig_num, letter): config
    (2, "c"): {
        "drug": "Epirubicin",
        "response": "O2",
        "csv": CLEANED / "Heatmaps" / "Epirubicin" / "O2_mean_sorted.csv",
        "drop_wells": ["0.38.1"],
        "remove_rows": None,
        "fig_size": (2.60, 1.78),
        "margins": dict(left=0.62, right=0.06, top=0.05, bottom=0.50),
        "y_axis_label": "Epirubicin Dose",
        "x_axis_label": "Time from Exposure (h)",
        "vmax": 100,
        "y_tick_decimals": 2,    # round dose labels to hundredths
    },
    (2, "f"): {
        "drug": "Mexiletine",
        "response": "Contractility",
        "csv": CLEANED / "Raw_Example_Data" / "Mexiletine" / "Amp_std.csv",
        "drop_indices_1based": {4, 5, 6, 7, 14, 15, 17, 21, 22, 24, 26},
        "drop_cols_extra": {"20", "2.5.1", "2.5"},
        "fig_size": (2.60, 1.74),
        "margins": dict(left=0.62, right=0.06, top=0.05, bottom=0.50),
        "y_axis_label": "Mexiletine Dose",
        "x_axis_label": "Time from Exposure (h)",
        "vmax": None,            # auto from data
        "y_tick_decimals": 2,
    },
    (3, "a"): {
        "drug": "Dactinomycin",
        "response": "O2",
        "csv": CLEANED / "Heatmaps" / "Dactinomycin" / "O2_mean_sorted.csv",
        "remove_rows": {1, 8, 12, 16, 20, 24, 27},
        "drop_wells": None,
        "fig_size": (1.31, 1.03),
        "margins": dict(left=0.50, right=0.04, top=0.04, bottom=0.30),
        "y_axis_label": "Drug Dose",
        "x_axis_label": "Time from Exposure",   # no "(h)" — panel too narrow
        "vmax": 100,
        "size_class": "small",
    },
    (3, "c"): {
        "drug": "Nifedipine",
        "response": "O2",
        "csv": CLEANED / "Heatmaps" / "Nifedipine" / "O2_mean_sorted.csv",
        "remove_rows": {5, 6},
        "drop_wells": None,
        "fig_size": (1.33, 1.10),
        "margins": dict(left=0.50, right=0.04, top=0.04, bottom=0.30),
        "y_axis_label": "Drug Dose",
        "x_axis_label": "Time from Exposure",
        "vmax": 100,
        "size_class": "small",
    },
    (3, "e"): {
        "drug": "Mexiletine",
        "response": "O2",
        "csv": CLEANED / "Heatmaps" / "Mexiletine" / "O2_mean_sorted.csv",
        "remove_rows": {2, 3, 9, 13, 20},
        "drop_wells": None,
        "fig_size": (1.31, 1.08),
        "margins": dict(left=0.50, right=0.04, top=0.04, bottom=0.30),
        "y_axis_label": "Drug Dose",
        "x_axis_label": "Time from Exposure",
        "vmax": 100,
        "size_class": "small",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUFFIX_RE = re.compile(r"^(.+?)\.(\d)$")


def _build_conc_map(columns) -> dict[str, float | None]:
    """Map each column name -> base concentration float.

    Uses CONTEXT (the full column list) to avoid the false-positive that bites
    naive regex strippers: "1.5" *looks* like "1" + suffix ".5", but if "1" is
    not in the column set then the column is really 1.5 mM. Pandas only emits
    a `.N` suffix to disambiguate a duplicate of an EXISTING column, so the
    base form must already be present in the same DataFrame's headers.
    """
    cols = [str(c) for c in columns]
    cols_set = set(cols)
    out: dict[str, float | None] = {}
    for c in cols:
        m = _SUFFIX_RE.match(c)
        if m and m.group(1) in cols_set:
            base = m.group(1)
        else:
            base = c
        try:
            out[c] = float(base)
        except ValueError:
            out[c] = None
    return out


def _format_conc(val: float | None, raw: str, *, decimals: int | None = None) -> str:
    if val is None:
        return raw
    if decimals is not None:
        val = round(val, decimals)
    # Always use :g so trailing zeros are stripped (e.g. 1.50 -> "1.5").
    return str(int(val)) if val == int(val) else f"{val:g}"


def _apply_lowess_per_col(df: pd.DataFrame, *, preserve_first: bool) -> pd.DataFrame:
    """LOWESS smooth each column over its time index. ``preserve_first=False``
    is the Mexiletine-Contractility variant from the NOTES file (smooths every
    point including t=0); ``True`` matches the Fig 2c/3a O2 path that keeps
    the first observation untouched."""
    from statsmodels.nonparametric.smoothers_lowess import lowess as lowess_fn

    out = df.copy().astype(float)
    for col in out.columns:
        valid = out[col].dropna()
        if len(valid) < 3:
            continue
        frac = min(1.0, max(LOWESS_W, 1) / len(valid))
        fitted = lowess_fn(valid.values, np.arange(len(valid)),
                           frac=frac, return_sorted=False)
        target = out.index.get_indexer(valid.index)
        if preserve_first and len(target) > 0:
            # Keep the first observation as-is.
            fitted = fitted.copy()
            fitted[0] = valid.values[0]
        out.iloc[target, out.columns.get_loc(col)] = fitted
    return out


def _baseline_compress_o2(data: pd.DataFrame) -> pd.DataFrame:
    """Compress baseline O2 timepoints toward ~20% air (matches the existing
    `_generate_fig2_heatmap` and `_generate_3a_heatmaps` behaviour)."""
    data = data.clip(upper=100)
    baseline_cap = 30
    n_transition = 4
    boundary_idx = min(n_transition, data.shape[1] - 1)
    row_targets = data.iloc[:, boundary_idx].values
    row_max = row_targets.max() if row_targets.max() > 0 else 1
    row_scale = np.clip(row_targets / row_max, 0, 1)

    for i in range(min(n_transition, data.shape[1])):
        col = data.columns[i]
        t = i / n_transition
        keep = 0.2 + 0.8 * t + 0.3 * row_scale * (1 - t)
        keep = np.clip(keep, 0, 1)
        excess = (data[col] - baseline_cap).clip(lower=0)
        data[col] = data[col].values - excess.values * (1 - keep)
    return data


def _process(spec: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | None]]:
    """Run the per-spec pipeline. Returns (smoothed_for_plot, raw_loaded,
    conc_map). The conc_map is built from the ORIGINAL CSV columns so the
    pandas-suffix dedup survives downstream filtering steps that may drop the
    "base" column (e.g., the Fig 3 outlier filter)."""
    df_raw = pd.read_csv(spec["csv"], index_col=0)
    raw_for_excel = df_raw.copy()
    conc_map = _build_conc_map(df_raw.columns.tolist())

    is_contract = spec["response"] == "Contractility"

    if is_contract:
        # Drop by 1-based original column index, then by column name.
        keep_cols = [c for i, c in enumerate(df_raw.columns)
                     if (i + 1) not in spec.get("drop_indices_1based", set())]
        keep_cols = [c for c in keep_cols
                     if c not in spec.get("drop_cols_extra", set())]
        df_raw = df_raw[keep_cols]
    else:
        if spec.get("drop_wells"):
            cols = [c for c in spec["drop_wells"] if c in df_raw.columns]
            if cols:
                df_raw = df_raw.drop(columns=cols)
        # 3a heatmaps: outlier filter (O2 outside [0, 80] -> NaN, then drop
        # wells with > 50% NaN). Matches generate_paper_figures.py pipeline.
        if spec.get("remove_rows") is not None:
            df_raw = df_raw.where((df_raw >= 0) & (df_raw <= 80))
            nan_frac = df_raw.isna().mean()
            df_raw = df_raw[nan_frac[nan_frac <= 0.5].index]

    for col in df_raw.columns:
        df_raw[col] = df_raw[col].interpolate(method="linear", limit=10,
                                              limit_direction="both")

    df_smooth = _apply_lowess_per_col(df_raw, preserve_first=not is_contract)

    data = df_smooth.T  # rows=wells, cols=time

    if is_contract:
        # Sort within each conc group, ascending bottom-up (highest avg at top).
        conc_vals = [conc_map.get(str(c)) for c in data.index.tolist()]
        groups: dict[float, list[int]] = OrderedDict()
        for i, cv in enumerate(conc_vals):
            groups.setdefault(cv, []).append(i)
        sorted_idx: list[int] = []
        for cv in sorted(groups.keys(), key=lambda v: (v is None, v), reverse=True):
            members = groups[cv]
            members_with_means = [(idx, data.iloc[idx].mean()) for idx in members]
            members_with_means.sort(key=lambda x: x[1])
            sorted_idx.extend([idx for idx, _ in members_with_means])
        data = data.iloc[sorted_idx]
        data = data * 100
    else:
        # Drop manually flagged rows (1-indexed in current sorted order).
        if spec.get("remove_rows"):
            rows_to_drop = [data.index[i - 1] for i in sorted(spec["remove_rows"])
                            if 0 < i <= len(data)]
            data = data.drop(rows_to_drop, errors="ignore")
        data = _baseline_compress_o2(data)

    return data, raw_for_excel, conc_map


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _axisless_png(fig_num: int, letter: str) -> Path:
    """Axisless variant saved in the per-figure Axisless/ subfolder."""
    d = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / f"Fig_{fig_num}" / "Axisless"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"Fig_{fig_num}{letter}_prism_axisless.png"


def _heatmap_plot_fn(data: pd.DataFrame, spec: dict, conc_map: dict[str, float | None],
                     *, axisless: bool = False):
    cmap = LinearSegmentedColormap.from_list(
        "cardiac_rodeo", [HEATMAP_BLUE, "white", HEATMAP_RED]
    )
    cmap.set_bad("white")

    is_small = spec.get("size_class") == "small"
    axis_pt = AXIS_LABEL_PT_SMALL if is_small else AXIS_LABEL_PT_LARGE
    tick_pt = TICK_LABEL_PT_SMALL if is_small else TICK_LABEL_PT_LARGE

    decimals = spec.get("y_tick_decimals")
    y_labels = [_format_conc(conc_map.get(str(c)), str(c), decimals=decimals)
                for c in data.index.tolist()]
    x_values = [float(t) for t in data.columns.tolist()]
    n_rows, n_cols = data.shape

    # Y tick: one per concentration group, centered. Cap at MAX_Y_TICK_LABELS
    # by keeping every-Nth group (always include the first and last so the
    # extremes of the dose range are always shown).
    groups: dict[str, list[int]] = OrderedDict()
    for i, lbl in enumerate(y_labels):
        groups.setdefault(lbl, []).append(i)
    group_keys = list(groups.keys())
    n_groups = len(group_keys)
    max_y = MAX_Y_TICK_LABELS_SMALL if is_small else MAX_Y_TICK_LABELS_LARGE
    if n_groups > max_y:
        keep_idx = sorted({
            int(round(i * (n_groups - 1) / (max_y - 1)))
            for i in range(max_y)
        })
    else:
        keep_idx = list(range(n_groups))
    y_ticks = [(groups[group_keys[i]][0] + groups[group_keys[i]][-1]) / 2 + 0.5
               for i in keep_idx]
    y_tick_labels = [group_keys[i] for i in keep_idx]

    # X ticks: 5 (large) or 4 (small) evenly spaced labels mapped to hours.
    n_target = 4 if is_small else 5
    if n_cols <= n_target:
        x_indices = list(range(n_cols))
    else:
        x_indices = [int(round(i * (n_cols - 1) / (n_target - 1)))
                     for i in range(n_target)]
    x_tick_centers = [i + 0.5 for i in x_indices]
    x_tick_labels = [f"{int(round(x_values[i]))}" for i in x_indices]

    vmin = 0
    vmax = spec.get("vmax")
    if vmax is None:
        vmax = float(np.nanmax(data.values))

    def _fn(fig, ax, scale):
        ax.imshow(
            data.values,
            cmap=cmap,
            vmin=vmin, vmax=vmax,
            aspect="auto",
            interpolation="nearest",
            origin="upper",
            extent=(0, n_cols, n_rows, 0),
        )

        # Frame: keep bottom + left, hide top + right (Prism L-shape).
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("bottom", "left"):
            ax.spines[s].set_visible(True)
            ax.spines[s].set_linewidth(SPINE_LW_PT * scale)
            ax.spines[s].set_color(SPINE_COLOR)

        ax.set_xlim(0, n_cols)
        ax.set_ylim(n_rows, 0)

        if axisless:
            # Axisless: keep the L-shape frame but suppress all tick marks,
            # tick labels, and axis titles so only the colormap is visible.
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.tick_params(axis="both", length=0, width=0)
        else:
            ax.set_xticks(x_tick_centers)
            ax.set_yticks(y_ticks)
            ax.set_xticklabels(x_tick_labels)
            ax.set_yticklabels(y_tick_labels)

            ax.tick_params(
                axis="x", direction="out",
                length=3 * scale, width=SPINE_LW_PT * scale,
                color=SPINE_COLOR, pad=2 * scale,
            )
            ax.tick_params(
                axis="y", direction="out",
                length=3 * scale, width=SPINE_LW_PT * scale,
                color=SPINE_COLOR, pad=2 * scale,
            )

            fp_tick = helvetica(tick_pt * scale)
            for lbl in ax.get_xticklabels() + ax.get_yticklabels():
                lbl.set_fontproperties(fp_tick)

            fp_label = helvetica(axis_pt * scale)
            ax.set_xlabel(spec["x_axis_label"], fontproperties=fp_label,
                          labelpad=2 * scale)
            ax.set_ylabel(spec["y_axis_label"], fontproperties=fp_label,
                          labelpad=2 * scale)

    return _fn


# ---------------------------------------------------------------------------
# Data export
# ---------------------------------------------------------------------------

def _save_data(fig_num: int, letter: str, plotted: pd.DataFrame,
               raw: pd.DataFrame, spec: dict) -> Path:
    out = panel_data(fig_num, letter)
    metadata = pd.DataFrame([{
        "Panel": f"Fig_{fig_num}{letter} (Prism heatmap)",
        "Drug": spec["drug"],
        "Response": spec["response"],
        "Source_CSV": str(spec["csv"].relative_to(PROJECT_ROOT)),
        "Source_Script": "Prism_Style/generate_heatmaps.py",
        "Smoothing": f"LOWESS w={LOWESS_W} per well",
        "Drops": str(spec.get("drop_wells")
                     or sorted(spec.get("drop_indices_1based", set()))),
        "Remove_Rows_Post_Sort": str(spec.get("remove_rows")),
        "Image_Size_In": f"{spec['fig_size'][0]:.2f}x{spec['fig_size'][1]:.2f}",
        "Vmin": 0,
        "Vmax": spec.get("vmax"),
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted")
        raw.to_excel(w, sheet_name="Raw")
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def _render_panel(fig_num: int, letter: str, spec: dict):
    plotted, raw, conc_map = _process(spec)

    fig_w, fig_h = spec["fig_size"]
    m = spec["margins"]
    plot_w = fig_w - m["left"] - m["right"]
    plot_h = fig_h - m["top"] - m["bottom"]
    axes_rect = (m["left"] / fig_w, m["bottom"] / fig_h,
                 plot_w / fig_w, plot_h / fig_h)

    out_png = panel_png(fig_num, letter)
    render_at_scale(
        _heatmap_plot_fn(plotted, spec, conc_map), (fig_w, fig_h), out_png,
        scale=SCALE, dpi=600, transparent=True,
        axes_rect=axes_rect,
    )

    out_axisless = _axisless_png(fig_num, letter)
    render_at_scale(
        _heatmap_plot_fn(plotted, spec, conc_map, axisless=True),
        (fig_w, fig_h), out_axisless,
        scale=SCALE, dpi=600, transparent=True,
        axes_rect=axes_rect,
    )

    out_xlsx = _save_data(fig_num, letter, plotted, raw, spec)
    return out_png, out_axisless, out_xlsx, plotted.shape


def main():
    from PIL import Image
    for (fig_num, letter), spec in PANEL_SPECS.items():
        if not spec["csv"].exists():
            print(f"[SKIP] Fig {fig_num}{letter}: {spec['csv']} not found")
            continue
        out_png, out_axisless, out_xlsx, shape = _render_panel(fig_num, letter, spec)
        im = Image.open(out_png)
        dpi = im.info.get("dpi", (600, 600))[0]
        print(f"[{fig_num}{letter}] {spec['drug']} {spec['response']} -> "
              f"{out_png.relative_to(PROJECT_ROOT)}")
        print(f"    image     : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
        print(f"    axisless  : {out_axisless.relative_to(PROJECT_ROOT)}")
        print(f"    data      : {out_xlsx.relative_to(PROJECT_ROOT)}")
        print(f"    matrix    : {shape[0]} wells x {shape[1]} timepoints")


if __name__ == "__main__":
    main()
