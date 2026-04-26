"""Prism-style 3D surface plots for Fig 3 panels b and f.

Panel b: Dactinomycin O2, equation 3 (gaussian_hill_hybrid).
Panel f: Mexiletine O2, equation 7 (biphasic_response).

Each surface is rendered at the slide-3 PPT box size (1.19" x 1.18") so
fonts stay crisp when the picture lands in PowerPoint with no further
scaling. Coefficients come from
`EQN_Coefficients/all_equations_coefficients.xlsx` (.1 suffix = O2 column
group; see CLAUDE.md "Data Source of Truth").

View, color, and label conventions follow CLAUDE.md "3D Surface Plots":
  - view_init(elev=25, azim=-158)
  - X axis = Time (h), Y axis = Dose Ratio (C0/Cmax), Z axis = response
  - text2D() for axis labels (3D set_*label is unreliable under tight bbox)
  - turbo colormap

Output:
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3b_prism.png
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3b_prism_data.xlsx
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3f_prism.png
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3f_prism_data.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers projection)

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401  (registers Helvetica)
from prism_style import helvetica
from _paths import panel_png, panel_data

COEFF_XLSX = PROJECT_ROOT / "EQN_Coefficients" / "all_equations_coefficients.xlsx"

# Native render size (inches) — PPT slide-3 panel boxes for b and f are
# uniform 1.192 x 1.181. Render at exactly that so fonts don't reflow.
PANEL_W = 1.19
PANEL_H = 1.18

# Render-at-scale: draw 4× then LANCZOS-downsample so tick lines and label
# edges stay crisp. Same trick as the rest of Prism_Style/.
SCALE = 4
DPI = 600

# Surface grid resolution.
N_GRID = 60

# 3D view (locked per CLAUDE.md).
VIEW_ELEV = 25
VIEW_AZIM = -158

# Axis label sizes are in FINAL points (post-downscale).  Keep them small
# enough to fit in a 1.19" wide image but readable.
LABEL_PT = 7
TICK_PT = 5  # ticks are off by default — kept here for reference

# Per-panel spec: drug, equation function, sheet name, response type.
PANELS = {
    "b": dict(
        drug="Dactinomycin",
        sheet="gaussian_hill_hybrid",
        equation_label="Eq3 (gaussian_hill_hybrid)",
        response="O2",
    ),
    "f": dict(
        drug="Mexiletine",
        sheet="biphasic_response",
        equation_label="Eq7 (biphasic_response)",
        response="O2",
    ),
}


def _gaussian_hill_hybrid(C_norm, t, R0, Emax, mu_c, sigma_c, tau, m,
                          E_tox, n, TC50_norm, tau_tox):
    """R = R0 + Emax*Gauss(C)*Hill(t) - E_tox*Hill(C)*(1-exp(-t/tau_tox))."""
    t = np.maximum(t, 1e-9)
    tau = max(tau, 1e-9)
    tau_tox = max(tau_tox, 1e-9)
    sigma_c = max(sigma_c, 1e-6)
    TC50_norm = max(TC50_norm, 1e-9)

    gauss_conc = np.exp(-0.5 * ((C_norm - mu_c) / sigma_c) ** 2)
    hill_time = (t / tau) ** m / (1 + (t / tau) ** m)
    benefit = Emax * gauss_conc * hill_time

    toxic_conc = (C_norm ** n) / (TC50_norm ** n + C_norm ** n)
    toxic_time = 1 - np.exp(-t / tau_tox)
    toxic = E_tox * toxic_conc * toxic_time

    return R0 + benefit - toxic


def _biphasic_response(C_norm, t, R0, E_stim, E_inhib, EC50_stim_norm,
                       IC50_norm, n1, n2, tau_stim, tau_inhib):
    """R = R0 + E_stim*Hill1(C)*(1-exp(-t/tau_stim))
            + E_inhib*Hill2(C)*(1-exp(-t/tau_inhib))."""
    t = np.maximum(t, 1e-9)
    EC50_stim_norm = max(EC50_stim_norm, 1e-9)
    IC50_norm = max(IC50_norm, 1e-9)
    tau_stim = max(tau_stim, 1e-9)
    tau_inhib = max(tau_inhib, 1e-9)

    stim_conc = (C_norm ** n1) / (EC50_stim_norm ** n1 + C_norm ** n1)
    stim_time = 1 - np.exp(-t / tau_stim)
    stimulation = E_stim * stim_conc * stim_time

    inhib_conc = (C_norm ** n2) / (IC50_norm ** n2 + C_norm ** n2)
    inhib_time = 1 - np.exp(-t / tau_inhib)
    inhibition = E_inhib * inhib_conc * inhib_time

    return R0 + stimulation - inhibition


# Per-equation: (column list in Excel, function).
EQUATION_COLS = {
    "gaussian_hill_hybrid": (
        ["R0", "Emax", "mu_c", "sigma_c", "tau", "m",
         "E_tox", "n", "TC50_norm", "tau_tox"],
        _gaussian_hill_hybrid,
    ),
    "biphasic_response": (
        ["R0", "E_stim", "E_inhib", "EC50_stim_norm", "IC50_norm",
         "n1", "n2", "tau_stim", "tau_inhib"],
        _biphasic_response,
    ),
}


def load_coefficients(sheet: str, drug: str, response: str) -> dict:
    """Returns {param: float} for the requested drug/response from a sheet.

    Excel uses duplicate-column convention: bare names = Contractility,
    `.1`-suffixed names = O2. We load with header=1 and strip whitespace
    per CLAUDE.md.
    """
    df = pd.read_excel(COEFF_XLSX, sheet_name=sheet, header=1)
    df.columns = df.columns.str.strip()
    row = df[df["Drug"] == drug]
    if row.empty:
        raise KeyError(f"drug {drug!r} not found in sheet {sheet!r}")
    row = row.iloc[0]

    cols, _ = EQUATION_COLS[sheet]
    suffix = ".1" if response == "O2" else ""
    out = {c: float(row[f"{c}{suffix}"]) for c in cols}
    out["Cmax"] = float(row[f"Cmax_used{suffix}"])
    out["R2"] = float(row[f"R2{suffix}"])
    out["N_points"] = int(row[f"N_points{suffix}"])
    return out


def compute_surface(sheet: str, params: dict):
    """Return (T, Dr, Response) numpy meshes over (time, dose_ratio).

    Time 0–96 h, Dose Ratio 0–2 (×Cmax), per project convention.
    """
    cols, fn = EQUATION_COLS[sheet]
    args = [params[c] for c in cols]

    time = np.linspace(0, 96, N_GRID)
    dose_ratio = np.linspace(0, 2, N_GRID)
    T, Dr = np.meshgrid(time, dose_ratio)
    Response = fn(Dr, T, *args)
    return T, Dr, Response


def _draw(letter: str, spec: dict, out_path: Path):
    """Render the surface PNG at PANEL_W x PANEL_H inches, native."""
    params = load_coefficients(spec["sheet"], spec["drug"], spec["response"])
    T, Dr, Response = compute_surface(spec["sheet"], params)

    big_w = PANEL_W * SCALE
    big_h = PANEL_H * SCALE

    fig = plt.figure(figsize=(big_w, big_h), dpi=DPI)
    # Tight axes box: leave a small margin so the wireframe back walls and
    # axis labels both fit.  Anchor the 3D axes manually because mpl's 3D
    # auto-layout adds unpredictable padding.
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.96], projection="3d")

    # Color normalization on Response itself (some equations have negatives;
    # turbo handles either).
    vmin = float(np.nanmin(Response))
    vmax = float(np.nanmax(Response))

    ax.plot_surface(
        T, Dr, Response,
        cmap="turbo",
        vmin=vmin, vmax=vmax,
        linewidth=0,
        antialiased=True,
        edgecolor="none",
    )

    ax.view_init(elev=VIEW_ELEV, azim=VIEW_AZIM)

    # Strip every default tick + label — we use text2D below for clean labels.
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_ticks([])
        # Hide the default axis label too (we draw via text2D).
        axis.label.set_visible(False)
    # Spines / pane edges: keep the wireframe-grid look subtle.
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor((1, 1, 1, 0))
        axis.pane.set_edgecolor("black")
        axis.pane.set_linewidth(0.5 * SCALE)
    # Hide the axis lines (the bold corner edges) — wireframe panes already
    # convey the axes orientation.
    ax.xaxis.line.set_color((0, 0, 0, 0))
    ax.yaxis.line.set_color((0, 0, 0, 0))
    ax.zaxis.line.set_color((0, 0, 0, 0))

    # text2D labels (CLAUDE.md: 3D set_*label is unreliable under bbox).
    z_label = r"$O_2$ (%)" if spec["response"] == "O2" else "Contractility"
    ax.text2D(
        0.02, 0.50, z_label,
        transform=ax.transAxes,
        rotation=90, ha="left", va="center",
        fontproperties=helvetica(LABEL_PT * SCALE, bold=False),
    )
    ax.text2D(
        0.30, 0.04, "Dose Ratio",
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontproperties=helvetica(LABEL_PT * SCALE, bold=False),
    )
    ax.text2D(
        0.78, 0.06, "Time (h)",
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontproperties=helvetica(LABEL_PT * SCALE, bold=False),
    )

    # Save at the upscaled size, no bbox crop, transparent.
    tmp = NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    full_bbox = Bbox.from_bounds(0, 0, big_w, big_h)
    fig.savefig(tmp.name, dpi=DPI, transparent=True,
                bbox_inches=full_bbox, pad_inches=0)
    plt.close(fig)

    # Downscale to the target physical pixel count so PIL stamps the
    # correct DPI metadata (matches PANEL_W x PANEL_H at DPI).
    from PIL import Image
    target_px = (int(round(PANEL_W * DPI)), int(round(PANEL_H * DPI)))
    im = Image.open(tmp.name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.resize(target_px, Image.LANCZOS).save(out_path, dpi=(DPI, DPI))
    os.remove(tmp.name)
    return params, T, Dr, Response


def _save_data(letter: str, spec: dict, params: dict,
               T, Dr, Response, out_path: Path):
    """Write a Plotted/Coefficients/Metadata workbook for the panel."""
    plotted = pd.DataFrame({
        "Time_h": T.ravel(),
        "Dose_Ratio": Dr.ravel(),
        "Response": Response.ravel(),
    })

    coef_row = {"Drug": spec["drug"],
                "Equation": spec["equation_label"],
                "Response_Type": spec["response"]}
    coef_row.update(params)
    coefficients = pd.DataFrame([coef_row])

    metadata = pd.DataFrame([{
        "Panel": f"Fig_3{letter} (Prism)",
        "Description": (f"3D surface of {spec['drug']} "
                        f"{spec['response']} response over Time x Dose Ratio "
                        f"({spec['equation_label']})"),
        "Source_Script": "Prism_Style/generate_fig3_surfaces.py",
        "Source_Coefficients": str(COEFF_XLSX.relative_to(PROJECT_ROOT)),
        "Source_Sheet": spec["sheet"],
        "View_Elev": VIEW_ELEV,
        "View_Azim": VIEW_AZIM,
        "Time_h_min": 0, "Time_h_max": 96,
        "Dose_Ratio_min": 0, "Dose_Ratio_max": 2,
        "Grid_N": N_GRID,
        "Color_Map": "turbo",
    }])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        coefficients.to_excel(w, sheet_name="Coefficients", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)


def main():
    from PIL import Image
    for letter, spec in PANELS.items():
        png_out = panel_png(3, letter)
        data_out = panel_data(3, letter)
        params, T, Dr, Response = _draw(letter, spec, png_out)
        _save_data(letter, spec, params, T, Dr, Response, data_out)
        im = Image.open(png_out)
        dpi = im.info.get("dpi", (DPI, DPI))[0]
        print(f"[3{letter}] {spec['drug']} {spec['response']} "
              f"({spec['equation_label']})")
        print(f"    image  : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
        print(f"    data   : {data_out.relative_to(PROJECT_ROOT)}")
        print(f"    R²={params['R2']:.3f}  Cmax={params['Cmax']:.4f}")


if __name__ == "__main__":
    main()
