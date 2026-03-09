"""
Configuration for Prediction Models Pipeline

Contains paths, model parameters, and settings.
"""
from pathlib import Path

# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PREDICTION_MODELS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = PREDICTION_MODELS_DIR.parent

# Input data
EQN_COEFFICIENTS_DIR = PROJECT_ROOT / "EQN_Coefficients"
COEFFICIENTS_FILE = EQN_COEFFICIENTS_DIR / "all_equations_coefficients.xlsx"

# Output directories
OUTPUT_DIR = PROJECT_ROOT / "Output"
MODEL_OUTPUT_DIR = OUTPUT_DIR / "Model_Properties"
METRICS_OUTPUT_DIR = OUTPUT_DIR / "Performance_Metrics"
PLOTS_OUTPUT_DIR = OUTPUT_DIR / "Prediction_Plots"
SHAP_OUTPUT_DIR = OUTPUT_DIR / "SHAP_Data"
LATEX_OUTPUT_DIR = OUTPUT_DIR / "LaTeX_Reports"

# Create output directories
for d in [MODEL_OUTPUT_DIR, METRICS_OUTPUT_DIR, PLOTS_OUTPUT_DIR, SHAP_OUTPUT_DIR, LATEX_OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# =============================================================================
# DATA CONFIGURATION
# =============================================================================

# Sheet name for dual exponential coefficients
EQUATION_SHEET = "dual_exponential"

# Feature columns for Contractility
CONTRACTILITY_PARAMS = ['R0', 'A_benefit', 'A_tox', 'kb', 'kt', 'tau_b', 'tau_t', 'nb', 'nt', 'mb', 'mt']

# Feature columns for O2 (with .1 suffix in Excel)
O2_PARAMS = [f"{p}.1" for p in CONTRACTILITY_PARAMS]

# Target columns
TARGET_COLUMNS = {
    'arrhythmia': 'Arrhythmia',
    'heart_damage': 'Cardiotoxicity',  # Also called heart_damage
    'concern': 'Concern'
}

# Class mappings
BINARY_MAPPING = {'true': 1, 'false': 0, True: 1, False: 0, 1: 1, 0: 0}
CONCERN_MAPPING = {'most': 2, 'less': 1, 'no': 0}
CONCERN_LABELS = ['no', 'less', 'most']

# =============================================================================
# MODEL PARAMETERS
# =============================================================================

# XGBoost for Arrhythmia
XGBOOST_PARAMS = {
    'n_estimators': 100,
    'max_depth': 3,
    'learning_rate': 0.1,
    'random_state': 42,
    'eval_metric': 'logloss'
}

# RBF SVM for Heart Damage
SVM_PARAMS = {
    'kernel': 'rbf',
    'C': 1.0,
    'gamma': 'scale',
    'probability': True,
    'random_state': 42
}

# Random Forest for Concern
RF_PARAMS = {
    'n_estimators': 100,
    'max_depth': 5,
    'min_samples_split': 5,
    'min_samples_leaf': 2,
    'random_state': 42,
    'n_jobs': -1
}

# =============================================================================
# CROSS-VALIDATION
# =============================================================================

CV_METHOD = 'loocv'  # Leave-One-Out Cross-Validation
RANDOM_STATE = 42

# =============================================================================
# SHAP CONFIGURATION
# =============================================================================

SHAP_BACKGROUND_SAMPLES = 10
SHAP_NSAMPLES = 'auto'

# =============================================================================
# PLOTTING
# =============================================================================

FIGURE_DPI = 150
SAVE_TRANSPARENT = True
TOP_N_FEATURES = 10

# =============================================================================
# LATEX REPORT
# =============================================================================

LATEX_TEMPLATE = "prediction_models_report"


def validate_paths():
    """Check that required input files exist."""
    if not COEFFICIENTS_FILE.exists():
        raise FileNotFoundError(f"Coefficients file not found: {COEFFICIENTS_FILE}")
    return True


if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Coefficients file: {COEFFICIENTS_FILE}")
    print(f"File exists: {COEFFICIENTS_FILE.exists()}")
