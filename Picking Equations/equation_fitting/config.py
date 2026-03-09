"""
Configuration for Equation Fitting Pipeline

Contains paths, equation definitions, and fitting parameters.
"""
from pathlib import Path

# =============================================================================
# PATHS
# =============================================================================

# Base paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Cardiac_RODEO
CLEANED_DATA = PROJECT_ROOT / "Cleaned_Data"

# Input data files
CONTRACTILITY_FILE = CLEANED_DATA / "Heart_Contractility_Averaged.xlsx"
O2_FILE = CLEANED_DATA / "O2_Mean_Averaged.xlsx"
CMAX_FILE = CLEANED_DATA / "drug_Cmax.csv"

# Drug classification source
CLASSIFICATION_FILE = PROJECT_ROOT / "EQN_Coefficients" / "all_equations_coefficients.xlsx"

# Output paths - centralized in project Output folder
OUTPUT_DIR = PROJECT_ROOT / "Output" / "Equation_Fitting"
COEFF_DIR = OUTPUT_DIR / "Coefficients"
PLOTS_DIR = OUTPUT_DIR / "Plots"
REPORTS_DIR = PROJECT_ROOT / "Output" / "LaTeX_Reports"
ARCHIVES_DIR = REPORTS_DIR / "Archives"
PDFS_DIR = REPORTS_DIR  # Save PDFs directly in LaTeX_Reports, not a subfolder

# Final Excel output
FINAL_EXCEL = PROJECT_ROOT / "EQN_Coefficients" / "all_equations_coefficients.xlsx"

# =============================================================================
# DRUGS TO EXCLUDE
# =============================================================================

EXCLUDED_DRUGS = ['DMSO', 'Troglitazone', 'Troglitarazine']

SKIP_SHEETS = [
    'all_drugs', 'all_drugs smoothed', 'smoothed all data',
    'smoothed_all_data', 'all data', 'alldata'
]

# =============================================================================
# EQUATION DEFINITIONS
# =============================================================================

# All 12 equation names (order matters for Excel sheets)
EQUATION_NAMES = [
    'dual_exponential',
    'bivariate_gaussian',
    'gaussian_hill_hybrid',
    'modified_hill_hormesis',
    'gaussian_ridge',
    'adaptive_response',
    'biphasic_response',
    'cumulative_exposure',
    'recovery_model',
    'modified_hill_simple',
    'pkpd_elimination',
    'hormesis_v0'
]

# Equation metadata
EQUATIONS = {
    'dual_exponential': {
        'name': 'Dual Exponential (Eq1)',
        'formula': r'R(C,t) = R_0 + A_b(1-e^{-k_b C^{n_b}})(1-e^{-t/\tau_b})^{m_b} - A_t(1-e^{-k_t C^{n_t}})(1-e^{-t/\tau_t})^{m_t}',
        'params': ['R0', 'A_benefit', 'A_tox', 'kb', 'kt', 'tau_b', 'tau_t', 'nb', 'nt', 'mb', 'mt'],
        'n_params': 11
    },
    'bivariate_gaussian': {
        'name': 'Bivariate Gaussian (Eq2)',
        'formula': r'R(C,t) = R_0 + A_1 G_1(C,t) + A_2 G_2(C,t)',
        'params': ['R0', 'A1', 'A2', 'muC1', 'muT1', 'sigC1', 'sigT1', 'rho1', 'muC2', 'muT2', 'sigC2', 'sigT2', 'rho2'],
        'n_params': 13
    },
    'gaussian_hill_hybrid': {
        'name': 'Gaussian-Hill Hybrid (Eq3)',
        'formula': r'R(C,t) = R_0 + E_{max} \exp(-(C-\mu_c)^2/(2\sigma_c^2)) \cdot (t/\tau)^m/(1+(t/\tau)^m) - E_{tox} C^n/(TC_{50}^n+C^n) (1-e^{-t/\tau_{tox}})',
        'params': ['R0', 'Emax', 'mu_c', 'sigma_c', 'tau', 'm', 'E_tox', 'n', 'TC50_norm', 'tau_tox'],
        'n_params': 10
    },
    'modified_hill_hormesis': {
        'name': 'Modified Hill (Hormesis) (Eq4)',
        'formula': r'R(C,t) = R_0 + E_b C^{n_b}/(EC_{50,b}^{n_b}+C^{n_b})(1-e^{-t/\tau_b}) - E_t C^{n_t}/(TC_{50}^{n_t}+C^{n_t})(1-e^{-t/\tau_t})',
        'params': ['R0', 'E_benefit', 'E_tox', 'EC50_b_norm', 'TC50_norm', 'nb', 'nt', 'tau_b', 'tau_t'],
        'n_params': 9
    },
    'gaussian_ridge': {
        'name': 'Gaussian Ridge (Eq5)',
        'formula': r'R(C,t) = R_0 + A \exp(-(C-\mu_c)^2/(2\sigma_c^2))(1-e^{-\kappa(t/\tau)^m}) - B \exp(-(C-\mu_{tox})^2/(2\sigma_{tox}^2))(1-e^{-\lambda t})',
        'params': ['R0', 'A', 'B', 'mu_c', 'sigma_c', 'mu_tox', 'sigma_tox', 'kappa', 'tau', 'm', 'lam'],
        'n_params': 11
    },
    'adaptive_response': {
        'name': 'Adaptive Response (Eq6)',
        'formula': r'R(C,t) = R_0 + E_{max} C^n/(EC_{50}^n+C^n) \cdot e^{-t/\tau_{adapt}} (1-e^{-t/\tau_{onset}})',
        'params': ['R0', 'Emax', 'EC50_norm', 'n', 'tau_onset', 'tau_adapt'],
        'n_params': 6
    },
    'biphasic_response': {
        'name': 'Biphasic Response (Eq7)',
        'formula': r'R(C,t) = R_0 + E_{stim} C^{n_1}/(EC_{50,stim}^{n_1}+C^{n_1})(1-e^{-t/\tau_{stim}}) - E_{inhib} C^{n_2}/(IC_{50}^{n_2}+C^{n_2})(1-e^{-t/\tau_{inhib}})',
        'params': ['R0', 'E_stim', 'E_inhib', 'EC50_stim_norm', 'IC50_norm', 'n1', 'n2', 'tau_stim', 'tau_inhib'],
        'n_params': 9
    },
    'cumulative_exposure': {
        'name': 'Cumulative Exposure (Eq8)',
        'formula': r'R(C_0,t) = R_0 - E_{tox}(1-e^{-\alpha \cdot AUC(t)/TC_{50}}), \quad AUC(t)=C_0(1-e^{-k_{elim}t})/k_{elim}',
        'params': ['R0', 'E_tox', 'alpha', 'TC50_norm', 'k_elim'],
        'n_params': 5
    },
    'recovery_model': {
        'name': 'Recovery Model (Eq9)',
        'formula': r'R(C,t) = R_0 - E_{damage}(1-e^{-k_{damage} C t}) \cdot e^{-k_{recovery} t}',
        'params': ['R0', 'E_damage', 'k_damage', 'k_recovery'],
        'n_params': 4
    },
    'modified_hill_simple': {
        'name': 'Modified Hill (Simple) (Eq10)',
        'formula': r'R(C,t) = R_0 + E_{max}(1-e^{-\kappa C^n (t/\tau)^m})',
        'params': ['R0', 'Emax', 'kappa', 'tau', 'n', 'm'],
        'n_params': 6
    },
    'pkpd_elimination': {
        'name': 'PKPD Elimination (Eq11)',
        'formula': r'R(C_0,t) = R_0 + E_{max}(1-e^{-\kappa (C_0 e^{-k_{elim}t})^n (t/\tau)^m})',
        'params': ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim'],
        'n_params': 7
    },
    'hormesis_v0': {
        'name': 'Hormesis V0 (Legacy) (Eq12)',
        'formula': r'R(C,t) = R_0 + E_b (C/EC_{50,b})^{n_b}/(1+(C/EC_{50,b})^{n_b})(1-e^{-t/\tau_b}) - E_t (C/TC_{50})^{n_t}/(1+(C/TC_{50})^{n_t})(1-e^{-t/\tau_t})',
        'params': ['R0', 'E_benefit', 'E_tox', 'EC50_b_norm', 'TC50_norm', 'nb', 'nt', 'tau_b', 'tau_t'],
        'n_params': 9
    }
}

# =============================================================================
# FITTING BOUNDS
# =============================================================================

def get_bounds(response_type):
    """Get fitting bounds based on response type."""
    if response_type.lower() == 'contractility':
        return {
            'R0': (0, 0.2),
            'Emax': (0, 0.2),
            'A': (0, 0.4),
            'kappa': (1e-6, 100),
            'n': (0.1, 6.0),
            'm': (0.1, 6.0),
            'tau': (0.1, 96.0),
            'k_elim': (1e-6, 1.0),
            'k_on': (1e-6, 10),
            'k_off': (1e-6, 1),
            'sigma': (0.01, 96),
        }
    else:  # O2
        return {
            'R0': (5, 25),
            'Emax': (0, 100),
            'A': (0, 100),
            'kappa': (1e-6, 100),
            'n': (0.1, 6.0),
            'm': (0.1, 6.0),
            'tau': (0.1, 96.0),
            'k_elim': (1e-6, 1.0),
            'k_on': (1e-6, 10),
            'k_off': (1e-6, 1),
            'sigma': (0.01, 96),
        }

# =============================================================================
# VALIDATION
# =============================================================================

def validate_paths():
    """Check that required input files exist."""
    missing = []
    for name, path in [
        ('Contractility data', CONTRACTILITY_FILE),
        ('O2 data', O2_FILE),
        ('Cmax file', CMAX_FILE),
    ]:
        if not path.exists():
            missing.append(f"{name}: {path}")

    if missing:
        print("Missing files:")
        for m in missing:
            print(f"  - {m}")
        return False
    return True

if __name__ == "__main__":
    print("Configuration loaded successfully")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Data files exist: {validate_paths()}")
    print(f"Equations defined: {len(EQUATION_NAMES)}")
