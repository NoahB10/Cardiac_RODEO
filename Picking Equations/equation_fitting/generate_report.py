"""
Generate LaTeX Report from Equation Fitting Results

Creates comprehensive LaTeX document with equations, figures, and statistics.
Also creates a zip file ready for Overleaf upload.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
from datetime import datetime
import zipfile
import shutil
import subprocess
import tempfile
from config import (
    COEFF_DIR, PLOTS_DIR, REPORTS_DIR, PDFS_DIR,
    EQUATION_NAMES, EQUATIONS, PROJECT_ROOT
)

# Ensure output directories exist
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
PDFS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# LATEX EQUATION DEFINITIONS
# =============================================================================

LATEX_EQUATIONS = {
    'polynomial': {
        'latex': r'R(C,t) = R_0 + a_1 C + a_2 t + a_3 C^2 + a_4 t^2 + a_5 Ct + a_6 C^3 + a_7 t^3 + a_8 C^2 t + a_9 Ct^2',
        'description': '10-parameter polynomial surface for flexible response modeling.',
        'subfunctions': None
    },
    'modified_hill': {
        'latex': r'R(C,t) = R_0 + E_{\mathrm{max}} \cdot \left(1 - e^{-\kappa (C/C_{\mathrm{max}})^n (t/\tau)^m}\right)',
        'description': 'Hill-type equation with concentration and time dependence.',
        'subfunctions': None
    },
    'dual_exponential': {
        'latex': r'''R(C,t) = R_0 + A_{\mathrm{benefit}}\left(1-e^{-k_b C^{n_b}}\right)(1-e^{-t/\tau_b})^{m_b}
                 - A_{\mathrm{tox}}\left(1-e^{-k_t C^{n_t}}\right)(1-e^{-t/\tau_t})^{m_t}''',
        'description': 'Separate exponential terms for beneficial and toxic effects.',
        'subfunctions': None
    },
    'bivariate_gaussian': {
        'latex': r'R(C,t) = R_0 + A_1 G_1(C,t) + A_2 G_2(C,t)',
        'description': 'Sum of two bivariate Gaussian surfaces for localized effects.',
        'subfunctions': r'''where $G_i(C,t) = \exp\left(-\frac{1}{2(1-\rho_i^2)}\left[\frac{(C-\mu_{C,i})^2}{\sigma_{C,i}^2} + \frac{(t-\mu_{t,i})^2}{\sigma_{t,i}^2} - \frac{2\rho_i(C-\mu_{C,i})(t-\mu_{t,i})}{\sigma_{C,i}\sigma_{t,i}}\right]\right)$'''
    },
    'gaussian_hill_hybrid': {
        'latex': r'R(C,t) = R_0 + E_{\mathrm{max}} H(C) G(t) - E_{\mathrm{tox}} T(C) f(t)',
        'description': 'Combines Hill concentration dependence with Gaussian time profile.',
        'subfunctions': r'''where:
\begin{itemize}
\item $H(C) = \exp\left(-\frac{(C-\mu_C)^2}{2\sigma_C^2}\right)$ (Gaussian concentration profile)
\item $G(t) = \frac{(t/\tau)^m}{1+(t/\tau)^m}$ (Hill-type time dependence)
\item $T(C) = \frac{C^n}{TC_{50}^n + C^n}$ (toxic Hill function)
\item $f(t) = 1 - e^{-t/\tau_{\mathrm{tox}}}$ (time onset of toxicity)
\end{itemize}'''
    },
    'gaussian_ridge': {
        'latex': r'R(C,t) = R_0 + A \exp\left(-\frac{(C-\mu_C)^2}{2\sigma_C^2} - \frac{(t-\mu_t)^2}{2\sigma_t^2}\right)',
        'description': 'Simple 2D Gaussian ridge centered at optimal concentration-time.',
        'subfunctions': None
    },
    'pkpd_elimination': {
        'latex': r'R(C_0,t) = R_0 + E_{\mathrm{max}}\left(1 - e^{-\kappa (C_0 e^{-k_{\mathrm{elim}} t})^n (t/\tau)^m}\right)',
        'description': 'PK-PD model with first-order drug elimination kinetics.',
        'subfunctions': r'''where $C(t) = C_0 e^{-k_{\mathrm{elim}} t}$ is the drug concentration at time $t$ following first-order elimination.'''
    },
    'adaptive_response': {
        'latex': r'R(C,t) = R_0 + E_{\mathrm{max}} \frac{C^n}{EC_{50}^n + C^n} \cdot e^{-t/\tau_{\mathrm{adapt}}} (1-e^{-t/\tau_{\mathrm{onset}}})',
        'description': 'Models initial effect with adaptive tolerance over time.',
        'subfunctions': None
    },
    'recovery_model': {
        'latex': r'R(C,t) = R_0 - E_{\mathrm{damage}}(1-e^{-k_{\mathrm{damage}} C t}) \cdot e^{-k_{\mathrm{recovery}} t}',
        'description': 'Reversible damage with exponential recovery kinetics.',
        'subfunctions': None
    },
    'cumulative_exposure': {
        'latex': r'R(C_0,t) = R_0 - E_{\mathrm{tox}}\left(1-e^{-\alpha \cdot \mathrm{AUC}(t)/TC_{50}}\right)',
        'description': 'AUC-dependent toxicity based on cumulative drug exposure.',
        'subfunctions': r'''where $\mathrm{AUC}(t) = \frac{C_0}{k_{\mathrm{elim}}}(1-e^{-k_{\mathrm{elim}} t})$ is the area under the concentration-time curve.'''
    },
    'biphasic_response': {
        'latex': r'R(C,t) = R_0 + E_{\mathrm{stim}} H_1(C) f_1(t) - E_{\mathrm{inhib}} H_2(C) f_2(t)',
        'description': 'Biphasic model with low-dose stimulation and high-dose inhibition.',
        'subfunctions': r'''where:
\begin{itemize}
\item $H_1(C) = \frac{C^{n_1}}{EC_{50,\mathrm{stim}}^{n_1} + C^{n_1}}$ (stimulation Hill function)
\item $H_2(C) = \frac{C^{n_2}}{IC_{50}^{n_2} + C^{n_2}}$ (inhibition Hill function)
\item $f_1(t) = 1 - e^{-t/\tau_{\mathrm{stim}}}$ (stimulation time onset)
\item $f_2(t) = 1 - e^{-t/\tau_{\mathrm{inhib}}}$ (inhibition time onset)
\end{itemize}'''
    },
    'modified_hill_hormesis': {
        'latex': r'R(C,t) = R_0 + E_{\mathrm{benefit}} H_b(C) f_b(t) - E_{\mathrm{tox}} H_t(C) f_t(t)',
        'description': 'Modified Hill equation with hormesis (low-dose benefit, high-dose toxicity).',
        'subfunctions': r'''where:
\begin{itemize}
\item $H_b(C) = \frac{C^{n_b}}{EC_{50,b}^{n_b} + C^{n_b}}$ (benefit Hill function)
\item $H_t(C) = \frac{C^{n_t}}{TC_{50}^{n_t} + C^{n_t}}$ (toxicity Hill function)
\item $f_b(t) = 1 - e^{-t/\tau_b}$, $f_t(t) = 1 - e^{-t/\tau_t}$ (time onset functions)
\end{itemize}'''
    },
    'modified_hill_simple': {
        'latex': r'R(C,t) = R_0 + E_{\mathrm{max}}\left(1 - e^{-\kappa C^n (t/\tau)^m}\right)',
        'description': 'Simplified Hill model with combined concentration-time effect.',
        'subfunctions': None
    },
    'hormesis_v0': {
        'latex': r'R(C,t) = R_0 + E_{\mathrm{benefit}} H_b(C) f_b(t) - E_{\mathrm{tox}} H_t(C) f_t(t)',
        'description': 'Legacy hormesis model (similar to modified Hill hormesis).',
        'subfunctions': r'''where:
\begin{itemize}
\item $H_b(C) = \frac{(C/EC_{50,b})^{n_b}}{1 + (C/EC_{50,b})^{n_b}}$ (benefit Hill function)
\item $H_t(C) = \frac{(C/TC_{50})^{n_t}}{1 + (C/TC_{50})^{n_t}}$ (toxicity Hill function)
\item $f_b(t) = 1 - e^{-t/\tau_b}$, $f_t(t) = 1 - e^{-t/\tau_t}$ (time onset functions)
\end{itemize}'''
    }
}

# =============================================================================
# PARAMETER NAME FORMATTING FOR LATEX
# =============================================================================

def format_param_for_latex(param):
    """
    Format a parameter name for proper LaTeX rendering.
    Handles subscripts, Greek letters, and multi-character subscripts.
    """
    # Greek letter mappings
    greek_map = {
        'kappa': r'\kappa',
        'tau': r'\tau',
        'sigma': r'\sigma',
        'sig': r'\sigma',
        'mu': r'\mu',
        'lambda': r'\lambda',
        'alpha': r'\alpha',
        'rho': r'\rho',
    }

    # Check if entire param is a Greek letter
    param_lower = param.lower()
    if param_lower in greek_map:
        return greek_map[param_lower]

    # Remove "_norm" suffix if present (TC50_norm → TC50)
    if param.endswith('_norm'):
        param = param[:-5]

    # Handle parameters with underscores (subscripts)
    if '_' in param:
        parts = param.split('_', 1)
        base = parts[0]
        subscript = parts[1]

        # Check if base is a Greek letter
        base_lower = base.lower()
        if base_lower in greek_map:
            base = greek_map[base_lower]

        # Multi-character subscripts need braces with \mathrm for text
        if len(subscript) > 1:
            # Check if subscript contains comma (like "C,1")
            if ',' in subscript:
                return f'{base}_{{{subscript}}}'
            else:
                return f'{base}_{{\\mathrm{{{subscript}}}}}'
        else:
            return f'{base}_{subscript}'

    # Handle Greek letter prefixes with single letter + number (muC1, sigT2, rho1, etc.)
    import re
    # Pattern: Greek prefix + uppercase/lowercase letter + optional number
    match = re.match(r'^(mu|sig|sigma|rho|tau|kappa|alpha)(C|T|c|t)(\d*)$', param)
    if match:
        greek_part = match.group(1)
        letter = match.group(2)
        number = match.group(3)

        # Map Greek prefix
        greek_latex = greek_map.get(greek_part.lower(), greek_part)

        # Build subscript
        if number:
            subscript = f'{letter},{number}'
        else:
            subscript = letter

        return f'{greek_latex}_{{{subscript}}}'

    # Handle single Greek letter followed by number (rho1, rho2, etc.)
    match = re.match(r'^(mu|sig|sigma|rho|tau|kappa|alpha)(\d+)$', param)
    if match:
        greek_part = match.group(1)
        number = match.group(2)
        greek_latex = greek_map.get(greek_part.lower(), greek_part)
        return f'{greek_latex}_{number}'

    # Handle common parameter patterns without underscores
    param_mappings = {
        'R0': r'R_0',
        'Emax': r'E_{\mathrm{max}}',
        'E_max': r'E_{\mathrm{max}}',
        'E_tox': r'E_{\mathrm{tox}}',
        'Etox': r'E_{\mathrm{tox}}',
        'A_benefit': r'A_{\mathrm{benefit}}',
        'A_tox': r'A_{\mathrm{tox}}',
        'E_benefit': r'E_{\mathrm{benefit}}',
        'E_damage': r'E_{\mathrm{damage}}',
        'E_stim': r'E_{\mathrm{stim}}',
        'E_inhib': r'E_{\mathrm{inhib}}',
        'k_elim': r'k_{\mathrm{elim}}',
        'k_damage': r'k_{\mathrm{damage}}',
        'k_recovery': r'k_{\mathrm{recovery}}',
        'k_on': r'k_{\mathrm{on}}',
        'k_off': r'k_{\mathrm{off}}',
        'k_adapt': r'k_{\mathrm{adapt}}',
        'tau_b': r'\tau_b',
        'tau_t': r'\tau_t',
        'tau_onset': r'\tau_{\mathrm{onset}}',
        'tau_adapt': r'\tau_{\mathrm{adapt}}',
        'tau_stim': r'\tau_{\mathrm{stim}}',
        'tau_inhib': r'\tau_{\mathrm{inhib}}',
        'tau_tox': r'\tau_{\mathrm{tox}}',
        'TC50': r'TC_{50}',
        'EC50': r'EC_{50}',
        'EC50_b': r'EC_{50,b}',
        'EC50_stim': r'EC_{50,\mathrm{stim}}',
        'IC50': r'IC_{50}',
        'sigma_c': r'\sigma_C',
        'sigma_t': r'\sigma_t',
        'sigma_C': r'\sigma_C',
        'mu_c': r'\mu_C',
        'mu_t': r'\mu_t',
        'mu_C': r'\mu_C',
        'mu_tox': r'\mu_{\mathrm{tox}}',
        'sigma_tox': r'\sigma_{\mathrm{tox}}',
        'nb': r'n_b',
        'nt': r'n_t',
        'mb': r'm_b',
        'mt': r'm_t',
        'kb': r'k_b',
        'kt': r'k_t',
        'n1': r'n_1',
        'n2': r'n_2',
        'lam': r'\lambda',
        'A1': r'A_1',
        'A2': r'A_2',
    }

    if param in param_mappings:
        return param_mappings[param]

    # Default: return as-is (for simple single-letter params like n, m, A, etc.)
    return param

# =============================================================================
# RESULTS LOADING
# =============================================================================

def load_fitting_results():
    """
    Load R2 values from coefficient CSVs.

    Returns DataFrames with R2 values for each equation and drug.
    """
    contractility_results = []
    o2_results = []

    for eq_name in EQUATION_NAMES:
        c_file = COEFF_DIR / f"{eq_name}_coefficients_contractility.csv"
        o_file = COEFF_DIR / f"{eq_name}_coefficients_o2.csv"

        if c_file.exists():
            df_c = pd.read_csv(c_file)
            if 'R2' in df_c.columns:
                for _, row in df_c.iterrows():
                    contractility_results.append({
                        'Drug': row['Drug'],
                        'Equation': eq_name,
                        'R2': row['R2']
                    })

        if o_file.exists():
            df_o = pd.read_csv(o_file)
            if 'R2' in df_o.columns:
                for _, row in df_o.iterrows():
                    o2_results.append({
                        'Drug': row['Drug'],
                        'Equation': eq_name,
                        'R2': row['R2']
                    })

    return pd.DataFrame(contractility_results), pd.DataFrame(o2_results)


def compute_summary_statistics(df):
    """Compute mean and std R2 for each equation."""
    if df.empty:
        return pd.DataFrame()

    summary = df.groupby('Equation')['R2'].agg(['mean', 'std', 'count']).reset_index()
    summary.columns = ['Equation', 'Mean_R2', 'Std_R2', 'N_drugs']
    return summary

# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_r2_comparison_scatter(df_o):
    """Create plot of mean O2 R2 values by equation."""
    summary_o = df_o.groupby('Equation')['R2'].mean()

    fig, ax = plt.subplots(figsize=(10, 8))
    o2_colors = [
        '#E6194B', '#3CB44B', '#FFE119', '#4363D8',
        '#F58231', '#911EB4', '#46F0F0', '#F032E6',
        '#BCF60C', '#FABEBE', '#008080', '#E6BEFF',
    ]

    labels = []
    values = []
    color_list = []

    sorted_entries = []
    for eq_name in EQUATION_NAMES:
        o_val = summary_o.get(eq_name, np.nan)
        if np.isfinite(o_val):
            sorted_entries.append((eq_name, o_val))

    sorted_entries.sort(key=lambda x: x[1], reverse=True)

    for i, (eq_name, o_val) in enumerate(sorted_entries):
        eq_info = EQUATIONS.get(eq_name, {})
        labels.append(eq_info.get('name', eq_name))
        values.append(o_val)
        color_list.append(o2_colors[i % len(o2_colors)])

    y_pos = np.arange(len(labels))
    ax.barh(y_pos, values, color=color_list, edgecolor='black', linewidth=1.0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel('Mean R2 (O2)', fontsize=12, fontweight='bold')
    ax.set_title('O2 Mean R2 by Equation', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-0.3, 0.7)

    plt.tight_layout()
    fig_path = PLOTS_DIR / 'r2_comparison_scatter.pdf'
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()

    return fig_path


def create_r2_heatmap(df_c, df_o):
    """Create heatmap of R2 values by equation and response type."""
    summary_c = df_c.groupby('Equation')['R2'].mean()
    summary_o = df_o.groupby('Equation')['R2'].mean()

    data = []
    labels = []

    for eq_name in EQUATION_NAMES:
        eq_info = EQUATIONS.get(eq_name, {})
        label = eq_info.get('name', eq_name)
        c_val = summary_c.get(eq_name, np.nan)
        o_val = summary_o.get(eq_name, np.nan)
        data.append([c_val, o_val])
        labels.append(label)

    data_arr = np.array(data)

    fig, ax = plt.subplots(figsize=(6, 10))
    im = ax.imshow(data_arr, cmap='RdYlGn', aspect='auto', vmin=-0.3, vmax=0.6)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Contractility', 'O2'], fontsize=11)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)

    # Add values
    for i in range(len(labels)):
        for j in range(2):
            val = data_arr[i, j]
            if np.isfinite(val):
                color = 'white' if val < 0.1 else 'black'
                ax.text(j, i, f'{val:.3f}', ha='center', va='center', color=color, fontsize=9)

    ax.set_title('Mean R² by Equation', fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=ax, label='Mean R²')

    plt.tight_layout()
    fig_path = PLOTS_DIR / 'r2_heatmap.pdf'
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()

    return fig_path


def create_r2_comparison_excel(df_c, df_o):
    """
    Create Excel file with R2 comparison data for all equations.

    This creates an Excel file alongside the R2 plots that can be used
    to recreate the visualizations.
    """
    # Mapping equation names to display names
    eq_display = {eq: info.get('name', eq) for eq, info in EQUATIONS.items()}

    # Collect R2 statistics for each equation
    r2_data = []

    for eq_name in EQUATION_NAMES:
        row = {
            'Equation': eq_name,
            'Equation_Display': eq_display.get(eq_name, eq_name)
        }

        # Contractility statistics
        c_data = df_c[df_c['Equation'] == eq_name]['R2']
        if len(c_data) > 0:
            row['Mean_R2_Contractility'] = c_data.mean()
            row['Std_R2_Contractility'] = c_data.std()
            row['Min_R2_Contractility'] = c_data.min()
            row['Max_R2_Contractility'] = c_data.max()
            row['N_Drugs_Contractility'] = len(c_data)

        # O2 statistics
        o_data = df_o[df_o['Equation'] == eq_name]['R2']
        if len(o_data) > 0:
            row['Mean_R2_O2'] = o_data.mean()
            row['Std_R2_O2'] = o_data.std()
            row['Min_R2_O2'] = o_data.min()
            row['Max_R2_O2'] = o_data.max()
            row['N_Drugs_O2'] = len(o_data)

        r2_data.append(row)

    # Create DataFrame and sort by Mean R2 O2 (descending)
    df_r2 = pd.DataFrame(r2_data)
    if 'Mean_R2_O2' in df_r2.columns:
        df_r2 = df_r2.sort_values('Mean_R2_O2', ascending=False)

    # Save to Excel in Plots folder (same location as plots)
    excel_path = PLOTS_DIR / 'r2_comparison_by_equation.xlsx'
    df_r2.to_excel(excel_path, index=False)

    return excel_path


def create_r2_distributions(df_c, df_o):
    """Create distribution plots for R2 values."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Contractility
    for eq_name in EQUATION_NAMES:
        eq_data = df_c[df_c['Equation'] == eq_name]['R2'].dropna()
        if len(eq_data) > 2:
            eq_info = EQUATIONS.get(eq_name, {})
            label = eq_info.get('name', eq_name)
            try:
                sns.kdeplot(eq_data, ax=axes[0], label=label, alpha=0.7)
            except:
                pass

    axes[0].set_xlabel('R²', fontsize=12)
    axes[0].set_ylabel('Density', fontsize=12)
    axes[0].set_title('Contractility R² Distribution', fontsize=13, fontweight='bold')
    axes[0].legend(fontsize=7, loc='upper left')
    axes[0].set_xlim(-0.5, 1.0)

    # O2
    for eq_name in EQUATION_NAMES:
        eq_data = df_o[df_o['Equation'] == eq_name]['R2'].dropna()
        if len(eq_data) > 2:
            eq_info = EQUATIONS.get(eq_name, {})
            label = eq_info.get('name', eq_name)
            try:
                sns.kdeplot(eq_data, ax=axes[1], label=label, alpha=0.7)
            except:
                pass

    axes[1].set_xlabel('R²', fontsize=12)
    axes[1].set_ylabel('Density', fontsize=12)
    axes[1].set_title('O2 R² Distribution', fontsize=13, fontweight='bold')
    axes[1].legend(fontsize=7, loc='upper left')
    axes[1].set_xlim(-0.5, 1.0)

    plt.tight_layout()
    fig_path = PLOTS_DIR / 'r2_distributions.pdf'
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()

    return fig_path

# =============================================================================
# LATEX REPORT GENERATION
# =============================================================================

def generate_latex_document(summary_c, summary_o):
    """Generate complete LaTeX document."""
    timestamp = datetime.now().strftime('%B %d, %Y')

    # Combine and sort summaries
    combined = []
    for eq_name in EQUATION_NAMES:
        eq_info = EQUATIONS.get(eq_name, {})
        c_row = summary_c[summary_c['Equation'] == eq_name]
        o_row = summary_o[summary_o['Equation'] == eq_name]

        c_mean = c_row['Mean_R2'].values[0] if len(c_row) > 0 else np.nan
        c_std = c_row['Std_R2'].values[0] if len(c_row) > 0 else np.nan
        o_mean = o_row['Mean_R2'].values[0] if len(o_row) > 0 else np.nan
        o_std = o_row['Std_R2'].values[0] if len(o_row) > 0 else np.nan

        combined.append({
            'eq_name': eq_name,
            'display_name': eq_info.get('name', eq_name),
            'c_mean': c_mean, 'c_std': c_std,
            'o_mean': o_mean, 'o_std': o_std,
            'avg': np.nanmean([c_mean, o_mean])
        })

    combined.sort(key=lambda x: x['avg'] if np.isfinite(x['avg']) else -999, reverse=True)

    o2_ranked = [eq for eq in combined if np.isfinite(eq['o_mean'])]
    o2_ranked.sort(key=lambda x: x['o_mean'], reverse=True)

    n_drugs = int(summary_c['N_drugs'].max()) if len(summary_c) > 0 else 0

    latex = r'''\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{float}

\geometry{margin=1in}
\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue}

\title{Equation Selection Analysis\\for Cardiac Drug Response Modeling}
\author{Cardiac RODEO Project}
\date{''' + timestamp + r'''}

\begin{document}

\maketitle

\begin{abstract}
This report presents a comprehensive analysis of ''' + str(len(EQUATION_NAMES)) + r''' candidate equations
for modeling cardiac drug response data. Each equation was fit to both Contractility and O$_2$ consumption
measurements across ''' + str(n_drugs) + r''' drugs. The equations are evaluated based
on their coefficient of determination ($R^2$), and parameter interpretability.
\end{abstract}

\tableofcontents
\newpage

% =============================================================================
\section{Executive Summary}
% =============================================================================

\subsection{Top Performing Equations}

\begin{table}[H]
\centering
\caption{Top 5 Equations by Mean $R^2$}
\begin{tabular}{llcc}
\toprule
\textbf{Rank} & \textbf{Equation} & \textbf{Contractility} & \textbf{O$_2$} \\
\midrule
'''

    for i, eq in enumerate(combined[:5]):
        name_escaped = eq['display_name'].replace('_', r'\_')
        c_str = f"{eq['c_mean']:.4f}" if np.isfinite(eq['c_mean']) else "N/A"
        o_str = f"{eq['o_mean']:.4f}" if np.isfinite(eq['o_mean']) else "N/A"
        latex += f"{i+1} & {name_escaped} & {c_str} & {o_str} \\\\\n"

    latex += r'''\bottomrule
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{Top 3 Equations by O$_2$ Mean $R^2$}
\begin{tabular}{llcc}
\toprule
\textbf{Rank} & \textbf{Equation} & \textbf{O$_2$ Mean} & \textbf{O$_2$ Std} \\
\midrule
'''

    for i, eq in enumerate(o2_ranked[:3]):
        name_escaped = eq['display_name'].replace('_', r'\_')
        o_mean = f"{eq['o_mean']:.4f}" if np.isfinite(eq['o_mean']) else "N/A"
        o_std = f"{eq['o_std']:.4f}" if np.isfinite(eq['o_std']) else "N/A"
        latex += f"{i+1} & {name_escaped} & {o_mean} & {o_std} \\\\\n"

    latex += r'''\bottomrule
\end{tabular}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=0.7\textwidth]{figures/r2_comparison_scatter.pdf}
\caption{Mean $R^2$ values for O$_2$ by equation.}
\label{fig:scatter}
\end{figure}

\newpage

% =============================================================================
\section{Candidate Equations}
% =============================================================================

'''

    for eq_name in EQUATION_NAMES:
        eq_info = EQUATIONS.get(eq_name, {})
        latex_eq = LATEX_EQUATIONS.get(eq_name, {})

        display_name = eq_info.get('name', eq_name).replace('_', r'\_')
        latex += f"\n\\subsection{{{display_name}}}\n\n"

        desc = latex_eq.get('description', 'No description available.')
        latex += f"\\textbf{{Description:}} {desc}\n\n"

        formula = latex_eq.get('latex', 'Not available')
        latex += f"\\textbf{{Mathematical Form:}}\n\\begin{{equation}}\n{formula}\n\\end{{equation}}\n\n"

        # Add subfunctions if present (for composite equations like H(C)G(t))
        subfunctions = latex_eq.get('subfunctions')
        if subfunctions:
            latex += f"{subfunctions}\n\n"

        # Format parameters with proper LaTeX subscripts and Greek letters
        params = eq_info.get('params', [])
        params_formatted = [f"${format_param_for_latex(p)}$" for p in params]
        params_str = ', '.join(params_formatted)
        latex += f"\\textbf{{Parameters:}} {params_str}\n\n"

    latex += r'''
\newpage

% =============================================================================
\section{Complete Results}
% =============================================================================

\begin{figure}[H]
\centering
\includegraphics[width=0.5\textwidth]{figures/r2_heatmap.pdf}
\caption{Heatmap of mean $R^2$ values. Green = good fit, Red = poor fit.}
\label{fig:heatmap}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{figures/r2_distributions.pdf}
\caption{Distribution of $R^2$ values across drugs.}
\label{fig:distributions}
\end{figure}

\subsection{Full Statistics Table}

\begin{longtable}{lcccc}
\caption{Complete $R^2$ Results by Equation} \\
\toprule
\textbf{Equation} & \textbf{Cont. Mean} & \textbf{Cont. Std} & \textbf{O$_2$ Mean} & \textbf{O$_2$ Std} \\
\midrule
\endfirsthead
\toprule
\textbf{Equation} & \textbf{Cont. Mean} & \textbf{Cont. Std} & \textbf{O$_2$ Mean} & \textbf{O$_2$ Std} \\
\midrule
\endhead
\bottomrule
\endlastfoot
'''

    for eq in combined:
        name_escaped = eq['display_name'].replace('_', r'\_')
        c_mean = f"{eq['c_mean']:.4f}" if np.isfinite(eq['c_mean']) else "N/A"
        c_std = f"{eq['c_std']:.4f}" if np.isfinite(eq['c_std']) else "N/A"
        o_mean = f"{eq['o_mean']:.4f}" if np.isfinite(eq['o_mean']) else "N/A"
        o_std = f"{eq['o_std']:.4f}" if np.isfinite(eq['o_std']) else "N/A"
        latex += f"{name_escaped} & {c_mean} & {c_std} & {o_mean} & {o_std} \\\\\n"

    latex += r'''
\end{longtable}

\newpage

% =============================================================================
\section{Conclusions}
% =============================================================================

Based on the analysis of ''' + str(len(EQUATION_NAMES)) + r''' equations:

\begin{enumerate}
'''

    if combined:
        best = combined[0]
        name_escaped = best['display_name'].replace('_', r'\_')
        c_str = f"{best['c_mean']:.4f}" if np.isfinite(best['c_mean']) else "N/A"
        o_str = f"{best['o_mean']:.4f}" if np.isfinite(best['o_mean']) else "N/A"
        latex += f"    \\item The \\textbf{{{name_escaped}}} equation achieved the highest overall performance "
        latex += f"with mean $R^2$ values of {c_str} (Contractility) and {o_str} (O$_2$).\n"

    latex += r'''    \item Equations with separate benefit and toxicity components generally performed well.
    \item The PK-PD elimination model provides interpretable pharmacokinetic parameters.
\end{enumerate}

\subsection{Recommendations}

For cardiotoxicity prediction, we recommend:
\begin{itemize}
'''

    for eq in combined[:3]:
        if np.isfinite(eq['avg']):
            name_escaped = eq['display_name'].replace('_', r'\_')
            latex += f"    \\item \\textbf{{{name_escaped}}}: Mean $R^2$ = {eq['avg']:.4f}\n"

    latex += r'''
\end{itemize}

\end{document}
'''

    # Write file
    report_path = REPORTS_DIR / 'equation_analysis_report.tex'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(latex)

    return report_path


def compile_latex_to_pdf(tex_path):
    """Compile LaTeX to PDF and save in the PDFs folder."""
    pdf_dir = PDFS_DIR

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            work_tex = tmp_path / tex_path.name
            shutil.copy(tex_path, work_tex)

            figures_dir = tmp_path / "figures"
            figures_dir.mkdir(parents=True, exist_ok=True)
            for fig_file in PLOTS_DIR.glob("*.pdf"):
                shutil.copy(fig_file, figures_dir / fig_file.name)

            cmd = [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={pdf_dir}",
                work_tex.name
            ]
            result = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True)
            if result.returncode != 0:
                print("  WARNING: pdflatex failed; PDF not generated.")
                if result.stderr:
                    last_line = result.stderr.strip().splitlines()[-1]
                    print(f"  pdflatex: {last_line}")
                return None

            pdf_path = pdf_dir / work_tex.with_suffix(".pdf").name
            if not pdf_path.exists():
                print("  WARNING: pdflatex completed but PDF not found.")
                return None

            return pdf_path
    except FileNotFoundError:
        print("  WARNING: pdflatex not found; skipping PDF generation.")
        return None
    except Exception as exc:
        print(f"  WARNING: PDF generation failed: {exc}")
        return None


def create_overleaf_zip():
    """Create zip file ready for Overleaf upload."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f'equation_analysis_{timestamp}.zip'
    zip_path = REPORTS_DIR / zip_name

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add LaTeX file
        tex_file = REPORTS_DIR / 'equation_analysis_report.tex'
        if tex_file.exists():
            zf.write(tex_file, 'main.tex')

        # Add figures
        for fig_file in PLOTS_DIR.glob('*.pdf'):
            zf.write(fig_file, f'figures/{fig_file.name}')

        # Add CSVs as reference
        for csv_file in COEFF_DIR.glob('*.csv'):
            zf.write(csv_file, f'data/{csv_file.name}')

    # Also create a "latest" copy
    latest_path = REPORTS_DIR / 'overleaf_latest.zip'
    shutil.copy(zip_path, latest_path)

    return zip_path, latest_path


def generate_full_report():
    """Run complete report generation pipeline."""
    print("\n" + "="*80)
    print("GENERATING LATEX REPORT")
    print("="*80 + "\n")

    # Load results
    print("Loading fitting results...")
    df_c, df_o = load_fitting_results()
    print(f"  Contractility: {len(df_c)} results")
    print(f"  O2: {len(df_o)} results")

    if df_c.empty and df_o.empty:
        print("  ERROR: No fitting results found. Run fit_all_equations.py first.")
        return None, None

    # Compute summaries
    summary_c = compute_summary_statistics(df_c)
    summary_o = compute_summary_statistics(df_o)

    # Create figures
    print("\nGenerating figures...")
    if not df_o.empty:
        fig1 = create_r2_comparison_scatter(df_o)
        print(f"  Created: {fig1.name}")
    else:
        print("  WARNING: No O2 results for O2-only plot")

    if not df_c.empty and not df_o.empty:
        fig2 = create_r2_heatmap(df_c, df_o)
        print(f"  Created: {fig2.name}")

        fig3 = create_r2_distributions(df_c, df_o)
        print(f"  Created: {fig3.name}")

        # Create Excel file with R2 comparison data (for graph recreation)
        excel_path = create_r2_comparison_excel(df_c, df_o)
        print(f"  Created: {excel_path.name}")
    else:
        print("  WARNING: Insufficient data for heatmap/distributions")

    # Generate LaTeX
    print("\nGenerating LaTeX document...")
    tex_path = generate_latex_document(summary_c, summary_o)
    print(f"  Created: {tex_path.name}")

    # Compile PDF
    print("\nCompiling PDF...")
    pdf_path = compile_latex_to_pdf(tex_path)
    if pdf_path:
        print(f"  Created: {pdf_path.name}")
    else:
        print("  PDF not created")

    # Create zip
    print("\nCreating Overleaf zip...")
    zip_path, latest_path = create_overleaf_zip()
    print(f"  Created: {zip_path.name}")
    print(f"  Latest: {latest_path.name}")

    print("\n" + "="*80)
    print("REPORT GENERATION COMPLETE")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  LaTeX: {tex_path}")
    if pdf_path:
        print(f"  PDF: {pdf_path}")
    print(f"  Zip: {zip_path}")
    print(f"\nTo compile locally: pdflatex {tex_path}")
    print(f"To upload to Overleaf: Use {latest_path}")

    return tex_path, zip_path


if __name__ == "__main__":
    generate_full_report()
