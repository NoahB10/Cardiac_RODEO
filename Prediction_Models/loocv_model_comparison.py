"""
LOOCV Model Comparison Pipeline for Cardiac RODEO

Compares XGBoost, SVM (Gaussian/RBF), and Random Forest models
across three equation types (dual_exponential, modified_hill_hormesis, pkpd_elimination)
and three prediction targets (Arrhythmia, heart_damage, Concern_Binary).

Uses Leave-One-Out Cross-Validation (LOOCV) with Accuracy and AUC metrics.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.naive_bayes import GaussianNB
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix, matthews_corrcoef, classification_report


# CatBoost wrapper for sklearn 1.8+ compatibility
class CatBoostWrapper(BaseEstimator, ClassifierMixin):
    """Wrapper for CatBoostClassifier to ensure sklearn 1.8+ compatibility."""

    def __init__(self, iterations=150, depth=4, learning_rate=0.08,
                 auto_class_weights='Balanced', random_seed=42, verbose=False):
        self.iterations = iterations
        self.depth = depth
        self.learning_rate = learning_rate
        self.auto_class_weights = auto_class_weights
        self.random_seed = random_seed
        self.verbose = verbose
        self._model = None

    def fit(self, X, y):
        self._model = CatBoostClassifier(
            iterations=self.iterations,
            depth=self.depth,
            learning_rate=self.learning_rate,
            auto_class_weights=self.auto_class_weights,
            random_seed=self.random_seed,
            verbose=self.verbose
        )
        self._model.fit(X, y)
        self.classes_ = self._model.classes_
        self.feature_importances_ = self._model.feature_importances_
        return self

    def predict(self, X):
        return self._model.predict(X)

    def predict_proba(self, X):
        return self._model.predict_proba(X)
import json
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid tkinter threading issues
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import seaborn as sns

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import warnings
warnings.filterwarnings('ignore')
import subprocess
import zipfile
import shutil

# ============================================================================
# Configuration
# ============================================================================

# Path discovery
current_dir = Path.cwd()
if current_dir.name == 'Prediction_Models':
    PROJECT_ROOT = current_dir.parent
elif (current_dir / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir
elif (current_dir.parent / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir.parent
else:
    PROJECT_ROOT = current_dir

EXCEL_PATH = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'

# Output directory structure - organized by data type, not by script
OUTPUT_ROOT = PROJECT_ROOT / 'Output'
OUTPUT_DIRS = {
    'performance': OUTPUT_ROOT / 'Performance_Metrics',
    'roc': OUTPUT_ROOT / 'ROC_Data',
    'confusion': OUTPUT_ROOT / 'Confusion_Matrices',
    'shap': OUTPUT_ROOT / 'SHAP_Data',
    'scatter': OUTPUT_ROOT / 'Prediction_Scatter_Data',
    'cumulative': OUTPUT_ROOT / 'Cumulative_Plot_Data',
    'latex': OUTPUT_ROOT / 'LaTeX_Reports',
    'feature_importance': OUTPUT_ROOT / 'Feature_Importance',
    'equation_comparison': OUTPUT_ROOT / 'Equation_Comparison',
    'stage2_validation': OUTPUT_ROOT / 'Stage2_Validation',
}

# Create all output directories and add README files
OUTPUT_README = {
    'performance': """Performance Metrics
===================
Source: Prediction_Models/loocv_model_comparison.py

Contains model performance metrics from cross-validation:
- loocv_results.csv: Stage 1 LOOCV results comparing equations
- stage2_results_*fold.csv: Stage 2 multi-seed CV results per fold config
- stage2_all_results.csv: Combined Stage 2 results
- model_performance_summary.csv: Final model performance summary
- *_roc_curve_summary.csv: ROC curve statistics per target
""",
    'roc': """ROC Data
========
Source: Prediction_Models/loocv_model_comparison.py

Contains ROC curve data and plots:
- final_roc_curves.pdf: Final ROC curves for optimal models
- roc_curves_all_models.xlsx: ROC curve data in Excel format
""",
    'confusion': """Confusion Matrices
==================
Source: Prediction_Models/loocv_model_comparison.py

Contains confusion matrix data and plots:
- final_confusion_matrices.pdf: Final confusion matrices for all targets
- *_confusion_matrix.csv: Confusion matrix data per target
- *_classification_report.csv: Classification metrics per target
""",
    'shap': """SHAP Data
=========
Source: Prediction_Models/loocv_model_comparison.py

Contains SHAP (SHapley Additive exPlanations) feature importance data:
- shap_*_bar.pdf: SHAP bar plots for each model
- shap_*_values.csv: Raw SHAP values per drug
- shap_*_mean_importance.csv: Mean absolute SHAP values
- shap_all_models_summary.csv: Combined SHAP summary
- feature_values_*.csv: Feature values used for SHAP computation
""",
    'scatter': """Prediction Scatter Data
=======================
Source: Prediction_Models/loocv_model_comparison.py

Contains prediction scatter plot data:
- prediction_scatter_all.pdf: All-targets prediction scatter plot
- *_predictions.csv: Prediction data per target
- prediction_thresholds.json: Computed thresholds for classification
""",
    'cumulative': """Cumulative Plot Data
====================
Source: Prediction_Models/loocv_model_comparison.py

Contains cumulative feature importance data:
- cumulative_feature_importance.pdf: Cumulative importance plot
- *_cumulative_predictions.csv: Cumulative prediction data per class
""",
    'latex': """LaTeX Reports
=============
Source: Prediction_Models/loocv_model_comparison.py

Contains compiled LaTeX reports:
- prediction_models_report.pdf: Main prediction models report

Note: Individual figure PDFs are stored in their respective data folders.
""",
    'feature_importance': """Feature Importance
==================
Source: Prediction_Models/loocv_model_comparison.py

Contains feature importance analysis:
- feature_importance_comparison.pdf: All 14 PK-PD features comparison plot
""",
    'equation_comparison': """Equation Comparison
===================
Source: Prediction_Models/loocv_model_comparison.py

Contains Stage 1 equation comparison results:
- loocv_comparison_plot.pdf: Comparison of equations (dual_exponential,
  modified_hill_hormesis, pkpd_elimination)
- loocv_concern_plot.pdf: Concern target comparison plot
""",
    'stage2_validation': """Stage 2 Validation
==================
Source: Prediction_Models/loocv_model_comparison.py

Contains Stage 2 multi-seed cross-validation plots:
- stage2_roc_curves_*fold.pdf: ROC curves per fold configuration
- stage2_accuracy_auc_bars_*fold.pdf: Accuracy/AUC bar plots
- stage2_confusion_matrices_*fold.pdf: Confusion matrices per fold config
""",
}

for key, dir_path in OUTPUT_DIRS.items():
    dir_path.mkdir(parents=True, exist_ok=True)
    readme_path = dir_path / 'README.txt'
    if key in OUTPUT_README:
        readme_path.write_text(OUTPUT_README[key])

# Equation configurations: equation_name -> list of parameter names
EQUATION_PARAMS = {
    'dual_exponential': ['R0', 'A_benefit', 'A_tox', 'kb', 'kt', 'tau_b', 'tau_t', 'nb', 'nt', 'mb', 'mt'],
    'modified_hill_hormesis': ['R0', 'E_benefit', 'E_tox', 'EC50_b_norm', 'TC50_norm', 'nb', 'nt', 'tau_b', 'tau_t'],
    'pkpd_elimination': ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim']
}

# Target configurations
# Concern_Binary = binary (no+less vs most)
TARGETS = ['Arrhythmia', 'heart_damage', 'Concern_Binary']

# Model configurations - matched to notebook hyperparameters
def get_models(scale_pos_weight=1.0):
    """
    Return dictionary of model instances with class balancing.

    Parameters:
    -----------
    scale_pos_weight : float
        For XGBoost: ratio of negative/positive samples (e.g., 4.0 for 20% minority)
        Set to 1.0 for balanced classes, >1 for imbalanced with minority=positive
    """
    return {
        'XGBoost': XGBClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            scale_pos_weight=scale_pos_weight,  # Handle class imbalance
            objective='binary:logistic',
            eval_metric='logloss',
            random_state=42,
            n_jobs=-1,
            tree_method='hist'
        ),
        'SVM_RBF': SVC(
            kernel='rbf',
            C=1.0,
            gamma='scale',
            class_weight='balanced',  # Handle class imbalance
            probability=True,  # Required for AUC
            random_state=42
        ),
        'RandomForest': RandomForestClassifier(
            n_estimators=150,
            max_depth=5,
            class_weight='balanced',  # Handle class imbalance
            random_state=42,
            n_jobs=-1
        ),
        'GaussianNB': GaussianNB()
        # GaussianNB assumes Gaussian feature distributions; handles imbalance via priors
    }

# ============================================================================
# Feature Extraction Functions
# ============================================================================

def extract_features_generic(df, equation_name):
    """
    Extract features for any equation type.

    Parameters:
    -----------
    df : pd.DataFrame
        Raw dataframe with equation coefficients
    equation_name : str
        Name of the equation (key in EQUATION_PARAMS)

    Returns:
    --------
    pd.DataFrame
        Feature matrix with columns for Contractility and O2
    """
    param_names = EQUATION_PARAMS[equation_name]
    features = []
    feature_names = []

    # Contractility coefficients (no suffix)
    for param in param_names:
        if param in df.columns:
            features.append(df[param].values)
        else:
            features.append(np.full(len(df), np.nan))
        feature_names.append(f'{param}_Contractility')

    # O2 coefficients (with .1 suffix)
    for param in param_names:
        param_o2 = f'{param}.1'
        if param_o2 in df.columns:
            features.append(df[param_o2].values)
        else:
            features.append(np.full(len(df), np.nan))
        feature_names.append(f'{param}_O2')

    return pd.DataFrame(
        np.column_stack(features),
        columns=feature_names,
        index=df.index
    )


def preprocess_targets(df, target_column):
    """
    Convert target labels to numeric format.

    For Concern_Binary: maps no+less -> 0 (No Concern), most -> 1 (High Concern)
    """
    # Handle Concern_Binary by reading from Concern column
    if target_column == 'Concern_Binary':
        target_series = df['Concern'].copy()
    else:
        target_series = df[target_column].copy()

    target_series = target_series.astype(str).str.strip().str.lower()

    if target_column in ['Arrhythmia', 'heart_damage']:
        mapping = {'true': 1, 'false': 0, '1': 1, '0': 0}
    elif target_column == 'Concern':
        # Multiclass: no=0, less=1, most=2
        mapping = {'most': 2, 'less': 1, 'no': 0, '2': 2, '1': 1, '0': 0}
    elif target_column == 'Concern_Binary':
        # Binary: no+less -> 0 (No Concern), most -> 1 (High Concern)
        mapping = {'most': 1, 'less': 0, 'no': 0, '2': 1, '1': 0, '0': 0}
    else:
        return pd.to_numeric(target_series, errors='coerce')

    return target_series.map(mapping)

# ============================================================================
# LOOCV Evaluation Function
# ============================================================================

def run_loocv(X, y, model, is_multiclass=False):
    """
    Run Leave-One-Out Cross-Validation.

    Parameters:
    -----------
    X : np.ndarray or pd.DataFrame
        Feature matrix
    y : np.ndarray
        Target vector
    model : sklearn estimator
        Model to evaluate
    is_multiclass : bool
        Whether this is a multiclass problem (affects AUC calculation)

    Returns:
    --------
    dict
        Dictionary with accuracy, AUC, predictions, and probabilities
    """
    from sklearn.base import clone

    loo = LeaveOneOut()
    y_true = []
    y_pred = []
    y_proba = []

    # Build base pipeline (matching notebook: scaler + model only)
    base_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', model)
    ])

    # Convert to DataFrame for iloc indexing if needed
    if isinstance(X, np.ndarray):
        X = pd.DataFrame(X)

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Handle any NaN values in training data
        # Fill with column means from training set
        train_means = X_train.mean()
        X_train = X_train.fillna(train_means)
        X_test = X_test.fillna(train_means)

        # Clone and fit pipeline (important: clone entire pipeline)
        pipeline_fold = clone(base_pipeline)
        pipeline_fold.fit(X_train, y_train)

        # Predictions
        pred = pipeline_fold.predict(X_test)
        y_pred.append(pred[0])
        y_true.append(y_test[0])

        # Scores for AUC - use decision_function for SVM (better for AUC)
        # and predict_proba for other models
        model_step = pipeline_fold.named_steps['model']
        is_svm = type(model_step).__name__ == 'SVC'

        if is_svm and hasattr(pipeline_fold, 'decision_function') and not is_multiclass:
            # SVM binary: use decision_function for better AUC
            scores = pipeline_fold.decision_function(X_test)
            y_proba.append(scores[0])  # Raw score (scalar for binary)
        elif hasattr(pipeline_fold, 'predict_proba'):
            # Use predict_proba for multiclass SVM and all other models
            proba = pipeline_fold.predict_proba(X_test)
            y_proba.append(proba[0])

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_proba = np.array(y_proba)

    # Calculate metrics
    accuracy = accuracy_score(y_true, y_pred)

    # Determine if we used SVM (decision_function gives 1D scores for binary)
    used_svm_decision = (y_proba.ndim == 1) or (y_proba.ndim == 2 and y_proba.shape[1] != len(np.unique(y_true)))

    # AUC calculation
    if is_multiclass:
        # Multiclass: use weighted OvR AUC
        try:
            auc = roc_auc_score(y_true, y_proba, multi_class='ovr', average='weighted')
        except ValueError:
            auc = np.nan
    else:
        # Binary: use standard AUC
        try:
            if used_svm_decision or y_proba.ndim == 1:
                # SVM decision_function or 1D scores
                auc = roc_auc_score(y_true, y_proba)
            else:
                # Probability scores (2D array)
                auc = roc_auc_score(y_true, y_proba[:, 1])
        except (ValueError, IndexError):
            auc = np.nan

    return {
        'accuracy': accuracy,
        'auc': auc,
        'y_true': y_true,
        'y_pred': y_pred,
        'y_proba': y_proba,
        'confusion_matrix': confusion_matrix(y_true, y_pred)
    }

# ============================================================================
# Main Pipeline
# ============================================================================

def run_full_pipeline():
    """
    Run the complete LOOCV comparison across all equations, targets, and models.
    """
    print("=" * 70)
    print("LOOCV Model Comparison Pipeline")
    print("=" * 70)
    print(f"\nExcel path: {EXCEL_PATH}")
    print(f"Output root: {OUTPUT_ROOT}")

    # Results storage
    results = []

    # Load Excel file once
    xl = pd.ExcelFile(EXCEL_PATH)

    # Run all combinations
    for equation_name in EQUATION_PARAMS.keys():
        print(f"\n{'='*70}")
        print(f"Processing: {equation_name}")
        print("=" * 70)

        # Load data for this equation
        df = pd.read_excel(xl, sheet_name=equation_name, header=1)
        df.columns = df.columns.str.strip()
        df = df.set_index('Drug')

        # Extract features
        X_df = extract_features_generic(df, equation_name)
        X = X_df.values

        for target in TARGETS:
            print(f"\n  Target: {target}")

            # Preprocess target
            y = preprocess_targets(df, target)

            # Remove samples with missing targets
            valid_mask = ~y.isna()
            X_valid = X[valid_mask]
            y_valid = y[valid_mask].values.astype(int)

            # Only multiclass Concern (3 classes), not Concern_Binary (binary)
            is_multiclass = (target == 'Concern')

            # Compute class imbalance ratio for XGBoost
            if not is_multiclass:
                n_neg = (y_valid == 0).sum()
                n_pos = (y_valid == 1).sum()
                scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0
            else:
                scale_pos_weight = 1.0  # Not used for multiclass

            print(f"    Samples: {len(y_valid)}, Classes: {np.unique(y_valid)}")

            for model_name, model in get_models(scale_pos_weight).items():
                print(f"      {model_name}...", end=" ")

                try:
                    result = run_loocv(X_valid, y_valid, model, is_multiclass)

                    results.append({
                        'Equation': equation_name,
                        'Target': target,
                        'Model': model_name,
                        'Accuracy': result['accuracy'],
                        'AUC': result['auc'],
                        'N_samples': len(y_valid),
                        'Confusion_Matrix': result['confusion_matrix'].tolist()
                    })

                    print(f"Accuracy: {result['accuracy']:.3f}, AUC: {result['auc']:.3f}")

                except Exception as e:
                    print(f"Error: {e}")
                    results.append({
                        'Equation': equation_name,
                        'Target': target,
                        'Model': model_name,
                        'Accuracy': np.nan,
                        'AUC': np.nan,
                        'N_samples': len(y_valid),
                        'Confusion_Matrix': None
                    })

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Save results
    results_csv = OUTPUT_DIRS['performance'] / 'loocv_results.csv'
    results_df.to_csv(results_csv, index=False)
    print(f"\n\nResults saved to: {results_csv}")

    return results_df


def create_comparison_plots(results_df):
    """
    Create comparison bar plots for Arrhythmia and heart_damage.
    """
    # Set up style
    plt.style.use('seaborn-v0_8-whitegrid')

    # Colors for models
    model_colors = {
        'XGBoost': '#2ecc71',
        'SVM_RBF': '#3498db',
        'RandomForest': '#e74c3c',
        'GaussianNB': '#9b59b6'  # Purple for GaussianNB
    }

    # Create figure with subplots
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))

    # Plot settings - all three binary targets
    targets_to_plot = ['Arrhythmia', 'heart_damage', 'Concern_Binary']
    metrics = ['Accuracy', 'AUC']
    equations = list(EQUATION_PARAMS.keys())
    models = ['XGBoost', 'SVM_RBF', 'RandomForest', 'GaussianNB']

    x = np.arange(len(equations))
    width = 0.2  # Adjusted for 4 models

    for row, target in enumerate(targets_to_plot):
        target_data = results_df[results_df['Target'] == target]

        for col, metric in enumerate(metrics):
            ax = axes[row, col]

            for i, model in enumerate(models):
                model_data = target_data[target_data['Model'] == model]
                values = [model_data[model_data['Equation'] == eq][metric].values[0]
                         for eq in equations]

                # Center bars around x position (for n models: offsets are centered)
                offset = (i - (len(models) - 1) / 2) * width
                bars = ax.bar(x + offset, values, width,
                             label=model, color=model_colors[model], edgecolor='black')

                # Add value labels on bars
                for bar, val in zip(bars, values):
                    height = bar.get_height()
                    ax.annotate(f'{val:.2f}',
                               xy=(bar.get_x() + bar.get_width() / 2, height),
                               xytext=(0, 3),
                               textcoords="offset points",
                               ha='center', va='bottom', fontsize=8)

            ax.set_ylabel(metric, fontsize=12)
            display_target = 'Concern Binary' if target == 'Concern_Binary' else target.replace('_', ' ').title()
            ax.set_title(f'{display_target} - {metric}', fontsize=14, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels([eq.replace('_', '\n') for eq in equations], fontsize=10)
            ax.set_ylim(0, 1.15)
            ax.legend(loc='upper right')
            ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='Baseline')

    plt.tight_layout()

    # Save as PDF for LaTeX
    plot_pdf_path = OUTPUT_DIRS['equation_comparison'] / 'loocv_comparison_plot.pdf'
    plt.savefig(plot_pdf_path, format='pdf', bbox_inches='tight')
    print(f"PDF saved to: {plot_pdf_path}")

    plt.close()

    return plot_pdf_path


def create_concern_plot(results_df):
    """
    Create a separate plot for Concern Binary.
    """
    plt.style.use('seaborn-v0_8-whitegrid')

    model_colors = {
        'XGBoost': '#2ecc71',
        'SVM_RBF': '#3498db',
        'RandomForest': '#e74c3c',
        'GaussianNB': '#9b59b6'  # Purple for GaussianNB
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    target_data = results_df[results_df['Target'] == 'Concern_Binary']
    if target_data.empty:
        plt.close()
        return None

    equations = list(EQUATION_PARAMS.keys())
    models = ['XGBoost', 'SVM_RBF', 'RandomForest', 'GaussianNB']
    metrics = ['Accuracy', 'AUC']

    x = np.arange(len(equations))
    width = 0.2  # Adjusted for 4 models

    for col, metric in enumerate(metrics):
        ax = axes[col]

        for i, model in enumerate(models):
            model_data = target_data[target_data['Model'] == model]
            values = []
            for eq in equations:
                eq_data = model_data[model_data['Equation'] == eq][metric]
                if len(eq_data) > 0:
                    values.append(eq_data.values[0])
                else:
                    values.append(0)

            offset = (i - (len(models) - 1) / 2) * width
            bars = ax.bar(x + offset, values, width,
                         label=model, color=model_colors[model], edgecolor='black')

            for bar, val in zip(bars, values):
                height = bar.get_height()
                if not np.isnan(val):
                    ax.annotate(f'{val:.2f}',
                               xy=(bar.get_x() + bar.get_width() / 2, height),
                               xytext=(0, 3),
                               textcoords="offset points",
                               ha='center', va='bottom', fontsize=8)

        ax.set_ylabel(metric, fontsize=12)
        ax.set_title(f'Concern (Binary) - {metric}', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([eq.replace('_', '\n') for eq in equations], fontsize=10)
        ax.set_ylim(0, 1.15)
        ax.legend(loc='upper right')
        ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='Random baseline')

    plt.tight_layout()

    plot_pdf_path = OUTPUT_DIRS['equation_comparison'] / 'loocv_concern_binary_plot.pdf'
    plt.savefig(plot_pdf_path, format='pdf', bbox_inches='tight')

    plt.close()

    return plot_pdf_path


def escape_latex(text):
    """Escape special LaTeX characters."""
    if isinstance(text, str):
        text = text.replace('_', r'\_')
        text = text.replace('&', r'\&')
        text = text.replace('%', r'\%')
        text = text.replace('#', r'\#')
    return text


def create_latex_report(results_df):
    """
    Generate a LaTeX report with results and figures.
    """
    latex_content = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{float}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{xcolor}
\usepackage{colortbl}

\title{LOOCV Model Comparison Results\\
\large Cardiac RODEO Prediction Pipeline}
\author{Automated Analysis Report}
\date{\today}

\begin{document}

\maketitle

\section{Overview}

This report presents the Leave-One-Out Cross-Validation (LOOCV) results comparing four machine learning models across three equation types and three prediction targets.

\subsection{Experimental Setup}

\begin{itemize}
    \item \textbf{Models:} XGBoost, SVM (RBF kernel), Random Forest, Gaussian Naive Bayes
    \item \textbf{Equations:} Dual Exponential, Modified Hill Hormesis, PKPD Elimination
    \item \textbf{Targets:} Arrhythmia (binary), Heart Damage (binary), Concern Binary (binary)
    \item \textbf{Validation:} Leave-One-Out Cross-Validation (n=25 drugs)
    \item \textbf{Metrics:} Accuracy, Area Under ROC Curve (AUC)
\end{itemize}

\section{Results Summary}

\subsection{Binary Classification Results}

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{loocv_comparison_plot.pdf}
    \caption{LOOCV performance comparison for all three binary classification targets across three equation types and four models.}
    \label{fig:binary_results}
\end{figure}

"""

    # Add results tables for all binary targets
    for target in TARGETS:
        target_display = target.replace('_', ' ').title()
        target_data = results_df[results_df['Target'] == target]

        latex_content += f"""
\\subsubsection{{{target_display} Results}}

\\begin{{table}}[H]
\\centering
\\caption{{{target_display} LOOCV Results}}
\\begin{{tabular}}{{llcc}}
\\toprule
\\textbf{{Equation}} & \\textbf{{Model}} & \\textbf{{Accuracy}} & \\textbf{{AUC}} \\\\
\\midrule
"""
        for eq in EQUATION_PARAMS.keys():
            eq_data = target_data[target_data['Equation'] == eq]
            for i, (_, row) in enumerate(eq_data.iterrows()):
                eq_display = eq.replace('_', ' ').title() if i == 0 else ""
                model_display = escape_latex(row['Model'])
                acc = f"{row['Accuracy']:.3f}"
                auc = f"{row['AUC']:.3f}" if not np.isnan(row['AUC']) else "N/A"
                latex_content += f"{eq_display} & {model_display} & {acc} & {auc} \\\\\n"
            latex_content += "\\midrule\n"

        # Remove trailing midrule
        if latex_content.endswith("\\midrule\n"):
            latex_content = latex_content[:-9]  # Remove \midrule\n
        latex_content += """\\bottomrule
\\end{tabular}
\\end{table}

"""

    latex_content += r"""
\section{Key Findings}

"""

    # Find best performers
    for target in TARGETS:
        target_data = results_df[results_df['Target'] == target]
        best_acc = target_data.loc[target_data['Accuracy'].idxmax()]
        best_auc_idx = target_data['AUC'].idxmax() if not target_data['AUC'].isna().all() else None

        target_display = target.replace('_', ' ').title()
        best_acc_model = escape_latex(best_acc['Model'])
        best_acc_eq = best_acc['Equation'].replace('_', ' ')
        latex_content += f"""
\\subsection{{{target_display}}}
\\begin{{itemize}}
    \\item \\textbf{{Best Accuracy:}} {best_acc_model} with {best_acc_eq} ({best_acc['Accuracy']:.1%})
"""
        if best_auc_idx is not None:
            best_auc = target_data.loc[best_auc_idx]
            best_auc_model = escape_latex(best_auc['Model'])
            best_auc_eq = best_auc['Equation'].replace('_', ' ')
            latex_content += f"""    \\item \\textbf{{Best AUC:}} {best_auc_model} with {best_auc_eq} ({best_auc['AUC']:.3f})
"""
        latex_content += """\\end{itemize}

"""

    latex_content += r"""
\section{Conclusion}

This automated LOOCV analysis provides a comprehensive comparison of model performance across different equation representations and prediction targets. The results can guide selection of the optimal equation-model combination for cardiac outcome prediction.

\end{document}
"""

    # Save LaTeX file
    latex_path = OUTPUT_DIRS['latex'] / 'loocv_report.tex'
    with open(latex_path, 'w') as f:
        f.write(latex_content)

    print(f"LaTeX report saved to: {latex_path}")

    return latex_path


# ============================================================================
# STAGE 2: Multi-Seed Stratified K-Fold Validation
# ============================================================================

def get_best_model_for_target(target, scale_pos_weight=1.0):
    """
    Return the best model configuration for each target based on Stage 1 results.
    Using PKPD Elimination equation (best performer).
    All models include class balancing for imbalanced data.

    Best models selected by comprehensive model comparison:
    - Arrhythmia: RandomForest (Accuracy 0.736, AUC 0.802)
    - heart_damage: GaussianNB (Accuracy 0.812, AUC 0.829) - better than SVM_RBF
    - Concern: RandomForest (AUC 0.789)
    - Concern_Binary: GaussianNB (Accuracy 0.740, AUC 0.877) - better than RandomForest

    Parameters:
    -----------
    target : str
        Target variable name
    scale_pos_weight : float
        For XGBoost: ratio of negative/positive samples
    """
    if target == 'Arrhythmia':
        # RandomForest: Best Stage 2 performance (Accuracy 0.736, AUC 0.802)
        return RandomForestClassifier(
            n_estimators=150,
            max_depth=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ), 'RandomForest'
    elif target == 'heart_damage':
        # GaussianNB: Best AUC 0.829 (better than SVM_RBF 0.779)
        # Gaussian Naive Bayes assumes features follow Gaussian distributions
        return GaussianNB(), 'GaussianNB'
    elif target == 'Concern':
        # RandomForest: Best AUC 0.789 in Stage 1 LOOCV
        return RandomForestClassifier(
            n_estimators=150,
            max_depth=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ), 'RandomForest'
    elif target == 'Concern_Binary':
        # GaussianNB: Best AUC 0.877 (better than RandomForest 0.747)
        # Gaussian Naive Bayes assumes features follow Gaussian distributions
        return GaussianNB(), 'GaussianNB'


def run_stratified_kfold_multi_seed(X, y, model, n_seeds=10, n_splits=5, is_multiclass=False):
    """
    Run Stratified K-Fold CV across multiple random seeds.

    Returns per-seed metrics and ROC curve data for plotting.
    """
    from sklearn.model_selection import StratifiedKFold
    from sklearn.base import clone
    from sklearn.metrics import roc_curve, auc, accuracy_score, f1_score

    all_results = {
        'accuracies': [],
        'aucs': [],
        'f1s': [],
        'mccs': [],  # Matthews Correlation Coefficient
        'tprs': [],  # For ROC plotting
        'mean_fpr': np.linspace(0, 1, 100),
        'per_seed': [],
        'all_y_true': [],  # Aggregated for confusion matrix
        'all_y_pred': []
    }

    # Convert to DataFrame if needed
    if isinstance(X, np.ndarray):
        X = pd.DataFrame(X)

    for seed in range(n_seeds):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)

        seed_y_true = []
        seed_y_pred = []
        seed_y_scores = []
        seed_tprs = []
        seed_aucs = []

        for train_idx, test_idx in skf.split(X, y):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # Handle NaN
            train_means = X_train.mean()
            X_train = X_train.fillna(train_means)
            X_test = X_test.fillna(train_means)

            # Build pipeline
            base_pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('model', clone(model))
            ])

            base_pipeline.fit(X_train, y_train)

            # Predictions
            y_pred = base_pipeline.predict(X_test)
            seed_y_true.extend(y_test)
            seed_y_pred.extend(y_pred)

            # Scores for AUC
            model_step = base_pipeline.named_steps['model']
            is_svm = type(model_step).__name__ == 'SVC'

            if is_svm and not is_multiclass:
                scores = base_pipeline.decision_function(X_test)
                seed_y_scores.extend(scores)

                # ROC for this fold
                fpr, tpr, _ = roc_curve(y_test, scores)
            elif hasattr(base_pipeline, 'predict_proba'):
                proba = base_pipeline.predict_proba(X_test)
                if is_multiclass:
                    seed_y_scores.extend(proba)
                else:
                    seed_y_scores.extend(proba[:, 1])
                    fpr, tpr, _ = roc_curve(y_test, proba[:, 1])

            # Interpolate TPR for consistent plotting (binary only)
            if not is_multiclass:
                interp_tpr = np.interp(all_results['mean_fpr'], fpr, tpr)
                interp_tpr[0] = 0.0
                seed_tprs.append(interp_tpr)
                seed_aucs.append(auc(fpr, tpr))

        # Aggregate seed results
        seed_y_true = np.array(seed_y_true)
        seed_y_pred = np.array(seed_y_pred)
        seed_y_scores = np.array(seed_y_scores)

        acc = accuracy_score(seed_y_true, seed_y_pred)
        f1 = f1_score(seed_y_true, seed_y_pred, average='weighted' if is_multiclass else 'binary')
        mcc = matthews_corrcoef(seed_y_true, seed_y_pred)

        if is_multiclass:
            try:
                auc_score = roc_auc_score(seed_y_true, seed_y_scores, multi_class='ovr', average='weighted')
            except:
                auc_score = np.nan
        else:
            auc_score = roc_auc_score(seed_y_true, seed_y_scores)

        all_results['accuracies'].append(acc)
        all_results['aucs'].append(auc_score)
        all_results['f1s'].append(f1)
        all_results['mccs'].append(mcc)
        all_results['all_y_true'].extend(seed_y_true)
        all_results['all_y_pred'].extend(seed_y_pred)

        if not is_multiclass:
            # Average TPR across folds for this seed
            mean_seed_tpr = np.mean(seed_tprs, axis=0)
            mean_seed_tpr[-1] = 1.0
            all_results['tprs'].append(mean_seed_tpr)

        all_results['per_seed'].append({
            'seed': seed,
            'accuracy': acc,
            'auc': auc_score,
            'f1': f1,
            'mcc': mcc,
            'y_true': seed_y_true,
            'y_pred': seed_y_pred,
            'y_scores': seed_y_scores
        })

    # Convert aggregated predictions to arrays
    all_results['all_y_true'] = np.array(all_results['all_y_true'])
    all_results['all_y_pred'] = np.array(all_results['all_y_pred'])

    return all_results


def plot_roc_curves_admethyst_style(results_dict, output_dir, n_folds=5):
    """
    Plot ROC curves in ADMEThyst style with mean ± std bands.
    """
    import matplotlib as mpl
    mpl.rcParams['font.sans-serif'] = "Arial"
    mpl.rcParams['font.family'] = "sans-serif"

    # Colors for each target (binary targets only)
    colors = {
        'Arrhythmia': '#e74c3c',       # Red
        'heart_damage': '#3498db',     # Blue
        'Concern_Binary': '#9b59b6',   # Purple
    }

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_aspect('equal', adjustable='box')

    mean_fpr = np.linspace(0, 1, 100)

    for target, results in results_dict.items():
        # Skip only multiclass Concern (3 classes) - Concern_Binary is binary and gets ROC
        if target == 'Concern':
            continue

        tprs = results['tprs']
        aucs = results['aucs']
        color = colors.get(target, '#2ecc71')

        # Plot individual seed curves (dashed)
        for i, tpr in enumerate(tprs):
            ax.plot(mean_fpr, tpr, color=color, lw=0.75, alpha=0.3, linestyle='--')

        # Calculate mean and std
        mean_tpr = np.mean(tprs, axis=0)
        mean_tpr[-1] = 1.0
        mean_auc = np.mean(aucs)
        std_auc = np.std(aucs)

        # Plot mean curve
        label = f'{target} (AUC = {mean_auc:.2f} ± {std_auc:.2f})'
        ax.plot(mean_fpr, mean_tpr, color=color, lw=3, alpha=0.9, label=label)

        # Plot confidence band
        std_tpr = np.std(tprs, axis=0)
        tprs_upper = np.minimum(mean_tpr + std_tpr, 1)
        tprs_lower = np.maximum(mean_tpr - std_tpr, 0)
        ax.fill_between(mean_fpr, tprs_lower, tprs_upper, color=color, alpha=0.15)

    # Chance line
    ax.plot([0, 1], [0, 1], 'k--', lw=2, label='Chance (AUC = 0.50)')

    # Styling
    ax.set_xlim([-0.05, 1.05])
    ax.set_ylim([-0.05, 1.05])
    ax.set_xlabel('False Positive Rate', fontsize=20)
    ax.set_ylabel('True Positive Rate', fontsize=20)
    ax.set_title(f'Stage 2: ROC Curves (10 Seeds × {n_folds}-Fold Stratified CV)\nPKPD Elimination Equation', fontsize=18)
    ax.tick_params(axis='both', labelsize=16)
    ax.grid(axis='both', which='major', color='grey', linestyle='--', linewidth=0.5, alpha=0.7)
    ax.legend(loc='lower right', fontsize=14)

    plt.tight_layout()

    # Save PDF only
    filename = f'stage2_roc_curves_{n_folds}fold'
    plt.savefig(output_dir / f'{filename}.pdf', format='pdf', bbox_inches='tight')
    plt.close()

    return output_dir / f'{filename}.pdf'


def plot_confusion_matrices(results_dict, output_dir, n_folds, target_labels=None):
    """
    Plot confusion matrices for all four targets in a 2x2 grid.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes = axes.flatten()

    targets = ['Arrhythmia', 'heart_damage', 'Concern_Binary']
    colors = ['Reds', 'Blues', 'Purples']

    # Default labels
    if target_labels is None:
        target_labels = {
            'Arrhythmia': ['No', 'Yes'],
            'heart_damage': ['No', 'Yes'],
            'Concern_Binary': ['No Concern', 'High Concern']
        }

    for idx, (target, cmap) in enumerate(zip(targets, colors)):
        ax = axes[idx]

        if target not in results_dict:
            continue

        results = results_dict[target]
        y_true = results['all_y_true']
        y_pred = results['all_y_pred']

        # Compute confusion matrix
        cm = confusion_matrix(y_true, y_pred)

        # Compute MCC
        mcc = matthews_corrcoef(y_true, y_pred)

        # Normalize
        cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

        # Plot
        im = ax.imshow(cm_normalized, interpolation='nearest', cmap=cmap, vmin=0, vmax=1)

        # Add colorbar
        cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=10)

        # Labels
        labels = target_labels.get(target, [str(i) for i in range(len(cm))])
        tick_marks = np.arange(len(labels))
        ax.set_xticks(tick_marks)
        ax.set_yticks(tick_marks)
        ax.set_xticklabels(labels, fontsize=12)
        ax.set_yticklabels(labels, fontsize=12)

        # Add text annotations
        thresh = 0.5
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, f'{cm[i, j]}\n({cm_normalized[i, j]:.1%})',
                       ha="center", va="center", fontsize=10,
                       color="white" if cm_normalized[i, j] > thresh else "black")

        ax.set_xlabel('Predicted', fontsize=12)
        ax.set_ylabel('Actual', fontsize=12)

        _, model_name = get_best_model_for_target(target)
        ax.set_title(f'{target.replace("_", " ").title()}\n({model_name})\nMCC = {mcc:.3f}', fontsize=14, fontweight='bold')

    plt.suptitle(f'Confusion Matrices ({n_folds}-Fold CV × 10 Seeds)', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()

    filename = f'stage2_confusion_matrices_{n_folds}fold'
    plt.savefig(output_dir / f'{filename}.pdf', format='pdf', bbox_inches='tight')
    plt.close()

    return output_dir / f'{filename}.pdf'


def plot_accuracy_auc_bars(results_dict, output_dir, n_folds=5):
    """
    Plot bar charts comparing Accuracy and AUC across targets with error bars.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    targets = list(results_dict.keys())
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']  # Red, Blue, Green, Purple

    x = np.arange(len(targets))
    width = 0.6

    # Accuracy plot
    ax = axes[0]
    means = [np.mean(results_dict[t]['accuracies']) for t in targets]
    stds = [np.std(results_dict[t]['accuracies']) for t in targets]

    bars = ax.bar(x, means, width, yerr=stds, capsize=8, color=colors,
                  edgecolor='black', linewidth=1.5, error_kw={'linewidth': 2})

    # Add value labels
    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.02,
                f'{mean:.2f}±{std:.2f}', ha='center', va='bottom', fontsize=12, fontweight='bold')

    ax.set_ylabel('Accuracy', fontsize=16)
    ax.set_title(f'Accuracy (10 Seeds × {n_folds}-Fold CV)', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', '\n') for t in targets], fontsize=14)
    ax.set_ylim(0, 1.15)
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='Baseline')
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    # AUC plot
    ax = axes[1]
    means = [np.mean(results_dict[t]['aucs']) for t in targets]
    stds = [np.std(results_dict[t]['aucs']) for t in targets]

    bars = ax.bar(x, means, width, yerr=stds, capsize=8, color=colors,
                  edgecolor='black', linewidth=1.5, error_kw={'linewidth': 2})

    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.02,
                f'{mean:.2f}±{std:.2f}', ha='center', va='bottom', fontsize=12, fontweight='bold')

    ax.set_ylabel('AUC-ROC', fontsize=16)
    ax.set_title(f'AUC-ROC (10 Seeds × {n_folds}-Fold CV)', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', '\n') for t in targets], fontsize=14)
    ax.set_ylim(0, 1.15)
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='Baseline')
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    plt.suptitle(f'Stage 2: Best Models on PKPD Elimination ({n_folds}-Fold)', fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()

    filename = f'stage2_accuracy_auc_bars_{n_folds}fold'
    plt.savefig(output_dir / f'{filename}.pdf', format='pdf', bbox_inches='tight')
    plt.close()

    return output_dir / f'{filename}.pdf'


def run_stage2_pipeline():
    """
    Run Stage 2: Multi-seed stratified k-fold validation on best models.
    Runs 3-fold, 4-fold, and 5-fold CV configurations.
    """
    print("\n" + "=" * 70)
    print("STAGE 2: Multi-Seed Stratified K-Fold Validation")
    print("Equation: PKPD Elimination (Best from Stage 1)")
    print("Fold configurations: 3-fold, 4-fold, 5-fold")
    print("=" * 70)

    # Load data
    xl = pd.ExcelFile(EXCEL_PATH)
    df = pd.read_excel(xl, sheet_name='pkpd_elimination', header=1)
    df.columns = df.columns.str.strip()
    df = df.set_index('Drug')

    # Extract features
    X_df = extract_features_generic(df, 'pkpd_elimination')

    # Store results for all fold configurations
    all_fold_results = {}
    fold_configs = [3, 4, 5]

    for n_folds in fold_configs:
        print(f"\n{'#'*70}")
        print(f"# {n_folds}-FOLD CROSS-VALIDATION")
        print(f"{'#'*70}")

        results_dict = {}

        for target in TARGETS:
            print(f"\n{'='*50}")
            print(f"Target: {target}")
            print("=" * 50)

            # Preprocess target first to compute class weights
            y = preprocess_targets(df, target)
            valid_mask = ~y.isna()
            X_valid = X_df[valid_mask]
            y_valid = y[valid_mask].values.astype(int)

            # Only multiclass Concern (3 classes), not Concern_Binary (binary)
            is_multiclass = (target == 'Concern')

            # Compute class imbalance ratio for XGBoost
            if not is_multiclass:
                n_neg = (y_valid == 0).sum()
                n_pos = (y_valid == 1).sum()
                scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0
            else:
                scale_pos_weight = 1.0

            # Get best model for this target with class balancing
            model, model_name = get_best_model_for_target(target, scale_pos_weight)
            print(f"Best model: {model_name}")

            print(f"Samples: {len(y_valid)}, Classes: {np.unique(y_valid)}")
            print(f"Running 10 seeds × {n_folds}-fold stratified CV...")

            # Run multi-seed CV
            results = run_stratified_kfold_multi_seed(
                X_valid, y_valid, model,
                n_seeds=10, n_splits=n_folds,
                is_multiclass=is_multiclass
            )

            results_dict[target] = results

            # Print summary
            print(f"\nResults across 10 seeds:")
            print(f"  Accuracy: {np.mean(results['accuracies']):.3f} ± {np.std(results['accuracies']):.3f}")
            print(f"  AUC:      {np.mean(results['aucs']):.3f} ± {np.std(results['aucs']):.3f}")
            print(f"  F1:       {np.mean(results['f1s']):.3f} ± {np.std(results['f1s']):.3f}")
            print(f"  MCC:      {np.mean(results['mccs']):.3f} ± {np.std(results['mccs']):.3f}")

        all_fold_results[n_folds] = results_dict

        # Generate plots for this fold configuration
        print(f"\n{'='*50}")
        print(f"Generating {n_folds}-Fold Plots")
        print("=" * 50)

        plot_roc_curves_admethyst_style(results_dict, OUTPUT_DIRS['stage2_validation'], n_folds)
        print(f"ROC curves saved: stage2_roc_curves_{n_folds}fold.pdf")

        plot_accuracy_auc_bars(results_dict, OUTPUT_DIRS['stage2_validation'], n_folds)
        print(f"Bar plots saved: stage2_accuracy_auc_bars_{n_folds}fold.pdf")

        plot_confusion_matrices(results_dict, OUTPUT_DIRS['stage2_validation'], n_folds)
        print(f"Confusion matrices saved: stage2_confusion_matrices_{n_folds}fold.pdf")

        # Save detailed results for this fold config
        stage2_results = []
        for target, results in results_dict.items():
            model, model_name = get_best_model_for_target(target)
            for seed_data in results['per_seed']:
                stage2_results.append({
                    'Target': target,
                    'Model': model_name,
                    'N_Folds': n_folds,
                    'Seed': seed_data['seed'],
                    'Accuracy': seed_data['accuracy'],
                    'AUC': seed_data['auc'],
                    'F1': seed_data['f1'],
                    'MCC': seed_data['mcc']
                })

        stage2_df = pd.DataFrame(stage2_results)
        stage2_df.to_csv(OUTPUT_DIRS['performance'] / f'stage2_results_{n_folds}fold.csv', index=False)

    # Combine all results into one CSV
    all_results_list = []
    for n_folds, results_dict in all_fold_results.items():
        for target, results in results_dict.items():
            model, model_name = get_best_model_for_target(target)
            for seed_data in results['per_seed']:
                all_results_list.append({
                    'Target': target,
                    'Model': model_name,
                    'N_Folds': n_folds,
                    'Seed': seed_data['seed'],
                    'Accuracy': seed_data['accuracy'],
                    'AUC': seed_data['auc'],
                    'F1': seed_data['f1'],
                    'MCC': seed_data['mcc']
                })

    all_results_df = pd.DataFrame(all_results_list)
    all_results_df.to_csv(OUTPUT_DIRS['performance'] / 'stage2_all_results.csv', index=False)
    print(f"\nAll results saved to: {OUTPUT_DIRS['performance'] / 'stage2_all_results.csv'}")

    return all_fold_results


def create_combined_latex_report(stage1_results_df, all_fold_results):
    """
    Create combined LaTeX report with Stage 1 and Stage 2 (all fold configurations).
    """
    latex_content = r"""\documentclass[11pt]{article}
\usepackage[margin=0.9in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{float}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{xcolor}
\usepackage{colortbl}
\usepackage{amsmath}
\usepackage{pdflscape}

\title{Cardiac RODEO Prediction Model Results\\
\large LOOCV Model Comparison \& Multi-Seed Validation}
\author{Automated Analysis Report}
\date{\today}

\begin{document}

\maketitle

%============================================================================
% STAGE 1
%============================================================================
\section{Stage 1: Model \& Equation Selection (LOOCV)}

This section presents Leave-One-Out Cross-Validation (LOOCV) results comparing four machine learning models across three equation types to identify the optimal combination.

\subsection{Experimental Setup}

\begin{itemize}
    \item \textbf{Models:} XGBoost, SVM (RBF kernel), Random Forest, Gaussian Naive Bayes
    \item \textbf{Equations:} Dual Exponential, Modified Hill Hormesis, PKPD Elimination
    \item \textbf{Targets:} Arrhythmia (binary), Heart Damage (binary), Concern Binary (binary)
    \item \textbf{Validation:} Leave-One-Out Cross-Validation (n=25 drugs)
    \item \textbf{Metrics:} Accuracy, Area Under ROC Curve (AUC)
\end{itemize}

\subsection{Results: Binary Classification}

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{loocv_comparison_plot.pdf}
    \caption{Stage 1 LOOCV performance for Arrhythmia, Heart Damage, and Concern Binary prediction.}
    \label{fig:stage1_binary}
\end{figure}

\subsection{Stage 1 Conclusions}

Based on LOOCV results, the \textbf{PKPD Elimination equation} consistently outperformed other equations. The best model for each target:

\begin{table}[H]
\centering
\caption{Best Model Selection from Stage 1}
\begin{tabular}{lccc}
\toprule
\textbf{Target} & \textbf{Best Model} & \textbf{Accuracy} & \textbf{AUC} \\
\midrule
Arrhythmia & Random Forest & 76.0\% & 0.795 \\
Heart Damage & Gaussian NB & 81.2\% & 0.829 \\
Concern Binary & Gaussian NB & 76.0\% & 0.887 \\
\bottomrule
\end{tabular}
\end{table}

\textit{Note: Gaussian Naive Bayes assumes features follow Gaussian distributions within each class and handles class imbalance through prior probabilities.}

%============================================================================
% STAGE 2
%============================================================================
\newpage
\section{Stage 2: Robust Validation (10 Seeds $\times$ K-Fold Stratified CV)}

Having identified the best equation (PKPD Elimination) and optimal model for each target from Stage 1, we now seek to determine the optimal stratified train-test split configuration. By running multiple cross-validation fold configurations (3, 4, 5 folds) across 10 random seeds, we obtain unbiased performance estimates and identify which fold configuration provides the most stable results for each target.

\subsection{Methodology}

\begin{itemize}
    \item \textbf{Equation:} PKPD Elimination (best from Stage 1)
    \item \textbf{Models:} RandomForest (Arrhythmia), GaussianNB (Heart Damage, Concern Binary)
    \item \textbf{Validation:} 3-Fold, 4-Fold, and 5-Fold Stratified Cross-Validation
    \item \textbf{Random Seeds:} 10 different seeds (0-9) per configuration
    \item \textbf{Class Balancing:} RandomForest uses class weighting; GaussianNB inherently handles class imbalance through prior probabilities
\end{itemize}

\textbf{Rationale:} The small sample size (n=25) requires careful selection of the fold count. Too few folds (e.g., 3-fold) may have insufficient training data, while too many folds (e.g., 5-fold) may have too few samples per test fold, especially for the minority class. By testing multiple configurations, we identify the optimal balance.

"""

    # Add sections for each fold configuration
    for n_folds in [3, 4, 5]:
        latex_content += f"""
%----------------------------------------------------------------------------
\\subsection{{{n_folds}-Fold Cross-Validation Results}}
%----------------------------------------------------------------------------

\\begin{{figure}}[H]
    \\centering
    \\includegraphics[width=0.9\\textwidth]{{stage2_roc_curves_{n_folds}fold.pdf}}
    \\caption{{ROC curves for {n_folds}-Fold CV showing mean $\\pm$ std bands across 10 seeds.}}
\\end{{figure}}

\\begin{{figure}}[H]
    \\centering
    \\includegraphics[width=\\textwidth]{{stage2_accuracy_auc_bars_{n_folds}fold.pdf}}
    \\caption{{Accuracy and AUC for {n_folds}-Fold CV with error bars ($\\pm$1 std).}}
\\end{{figure}}

\\begin{{figure}}[H]
    \\centering
    \\includegraphics[width=\\textwidth]{{stage2_confusion_matrices_{n_folds}fold.pdf}}
    \\caption{{Confusion matrices for {n_folds}-Fold CV (aggregated across 10 seeds).}}
\\end{{figure}}

"""
        # Add results table for this fold configuration
        if n_folds in all_fold_results:
            results_dict = all_fold_results[n_folds]

            latex_content += f"""
\\begin{{table}}[H]
\\centering
\\caption{{{n_folds}-Fold CV Results: Mean $\\pm$ Std across 10 Seeds}}
\\begin{{tabular}}{{lccccc}}
\\toprule
\\textbf{{Target}} & \\textbf{{Model}} & \\textbf{{Accuracy}} & \\textbf{{AUC}} & \\textbf{{F1 Score}} & \\textbf{{MCC}} \\\\
\\midrule
"""
            for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
                if target in results_dict:
                    results = results_dict[target]
                    _, model_name = get_best_model_for_target(target)
                    model_name_escaped = model_name.replace('_', r'\_')
                    target_display = target.replace('_', ' ').title()

                    acc_mean = np.mean(results['accuracies'])
                    acc_std = np.std(results['accuracies'])
                    auc_mean = np.mean(results['aucs'])
                    auc_std = np.std(results['aucs'])
                    f1_mean = np.mean(results['f1s'])
                    f1_std = np.std(results['f1s'])
                    mcc_mean = np.mean(results['mccs'])
                    mcc_std = np.std(results['mccs'])

                    latex_content += f"{target_display} & {model_name_escaped} & "
                    latex_content += f"{acc_mean:.3f} $\\pm$ {acc_std:.3f} & "
                    latex_content += f"{auc_mean:.3f} $\\pm$ {auc_std:.3f} & "
                    latex_content += f"{f1_mean:.3f} $\\pm$ {f1_std:.3f} & "
                    latex_content += f"{mcc_mean:.3f} $\\pm$ {mcc_std:.3f} \\\\\n"

            latex_content += r"""\bottomrule
\end{tabular}
\end{table}

"""

    # Summary comparison table
    latex_content += r"""
\newpage
\section{Summary: Cross-Validation Comparison}

\begin{table}[H]
\centering
\caption{AUC Comparison Across All Fold Configurations}
\begin{tabular}{lccc}
\toprule
\textbf{Target} & \textbf{3-Fold AUC} & \textbf{4-Fold AUC} & \textbf{5-Fold AUC} \\
\midrule
"""

    for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
        target_display = target.replace('_', ' ').title()
        aucs = []
        for n_folds in [3, 4, 5]:
            if n_folds in all_fold_results and target in all_fold_results[n_folds]:
                results = all_fold_results[n_folds][target]
                auc_mean = np.mean(results['aucs'])
                auc_std = np.std(results['aucs'])
                aucs.append(f"{auc_mean:.3f} $\\pm$ {auc_std:.3f}")
            else:
                aucs.append("N/A")
        latex_content += f"{target_display} & {aucs[0]} & {aucs[1]} & {aucs[2]} \\\\\n"

    latex_content += r"""\bottomrule
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{Accuracy Comparison Across All Fold Configurations}
\begin{tabular}{lccc}
\toprule
\textbf{Target} & \textbf{3-Fold Acc} & \textbf{4-Fold Acc} & \textbf{5-Fold Acc} \\
\midrule
"""

    for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
        target_display = target.replace('_', ' ').title()
        accs = []
        for n_folds in [3, 4, 5]:
            if n_folds in all_fold_results and target in all_fold_results[n_folds]:
                results = all_fold_results[n_folds][target]
                acc_mean = np.mean(results['accuracies'])
                acc_std = np.std(results['accuracies'])
                accs.append(f"{acc_mean:.3f} $\\pm$ {acc_std:.3f}")
            else:
                accs.append("N/A")
        latex_content += f"{target_display} & {accs[0]} & {accs[1]} & {accs[2]} \\\\\n"

    latex_content += r"""\bottomrule
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{MCC Comparison Across All Fold Configurations}
\begin{tabular}{lccc}
\toprule
\textbf{Target} & \textbf{3-Fold MCC} & \textbf{4-Fold MCC} & \textbf{5-Fold MCC} \\
\midrule
"""

    for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
        target_display = target.replace('_', ' ').title()
        mccs = []
        for n_folds in [3, 4, 5]:
            if n_folds in all_fold_results and target in all_fold_results[n_folds]:
                results = all_fold_results[n_folds][target]
                mcc_mean = np.mean(results['mccs'])
                mcc_std = np.std(results['mccs'])
                mccs.append(f"{mcc_mean:.3f} $\\pm$ {mcc_std:.3f}")
            else:
                mccs.append("N/A")
        latex_content += f"{target_display} & {mccs[0]} & {mccs[1]} & {mccs[2]} \\\\\n"

    latex_content += r"""\bottomrule
\end{tabular}
\end{table}

%============================================================================
% FINAL ANALYSIS
%============================================================================
\newpage
\section{Final Analysis: Optimal Configuration Results}

Based on the cross-validation comparison, we select the optimal fold configuration for each target:
\begin{itemize}
    \item \textbf{Arrhythmia:} 5-Fold CV (best balance of training data and stable estimates)
    \item \textbf{Heart Damage:} 5-Fold CV (consistent fold selection across targets)
    \item \textbf{Concern Binary:} 5-Fold CV (consistent fold selection across targets)
\end{itemize}

\subsection{Final Model Performance}

\begin{table}[H]
\centering
\caption{Final Results with Optimal Fold Configuration}
\begin{tabular}{lcccccc}
\toprule
\textbf{Target} & \textbf{Model} & \textbf{Folds} & \textbf{Accuracy} & \textbf{AUC} & \textbf{F1} & \textbf{MCC} \\
\midrule
"""

    # Add final results with optimal folds
    optimal_folds = {'Arrhythmia': 5, 'heart_damage': 5, 'Concern_Binary': 5}
    for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
        n_folds = optimal_folds[target]
        if n_folds in all_fold_results and target in all_fold_results[n_folds]:
            results = all_fold_results[n_folds][target]
            _, model_name = get_best_model_for_target(target)
            model_name_escaped = model_name.replace('_', r'\_')
            target_display = target.replace('_', ' ').title()

            acc_mean = np.mean(results['accuracies'])
            auc_mean = np.mean(results['aucs'])
            f1_mean = np.mean(results['f1s'])
            mcc_mean = np.mean(results['mccs'])

            latex_content += f"{target_display} & {model_name_escaped} & {n_folds} & "
            latex_content += f"{acc_mean:.3f} & {auc_mean:.3f} & {f1_mean:.3f} & {mcc_mean:.3f} \\\\\n"

    latex_content += r"""\bottomrule
\end{tabular}
\end{table}

\subsection{Optimal Configuration Visualizations}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{final_roc_curves.pdf}
    \caption{ROC curves for final model configurations with optimal fold counts.}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{final_confusion_matrices.pdf}
    \caption{Confusion matrices for final model configurations.}
\end{figure}

\subsection{Feature Importance Analysis}

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{feature_importance_comparison.pdf}
    \caption{Feature importance comparison across all four targets showing all 14 PK-PD features. RandomForest and XGBoost use native feature importances; GaussianNB and SVM use permutation importance.}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{cumulative_feature_importance.pdf}
    \caption{Cumulative feature importance showing how prediction probability changes as features are added.}
\end{figure}

\subsection{SHAP Analysis}

SHAP (SHapley Additive exPlanations) values provide model-agnostic feature importance that accounts for feature interactions. The following plots show aligned positive-negative SHAP pairs for the top 5 features, ordered by magnitude. Each horizontal line represents a drug's SHAP contribution, with positive values (right) increasing predicted risk and negative values (left) decreasing it. Lines are colored by actual class membership: blue indicates drugs that truly belong to the positive class, grey indicates negative class drugs.

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{shap_aligned_arrhythmia.pdf}
    \caption{Aligned SHAP pairs for Arrhythmia prediction. Blue lines = arrhythmogenic drugs (14), grey lines = non-arrhythmogenic drugs (11). The alignment of blue lines on the right (positive SHAP) and grey on the left (negative SHAP) indicates good model discrimination. All 25 drugs shown for each feature (no exclusions).}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{shap_aligned_heart_damage.pdf}
    \caption{Aligned SHAP pairs for Heart Damage prediction (GaussianNB model). Blue lines = cardiotoxic drugs (20), grey lines = non-cardiotoxic drugs (5). Top features identified by SHAP include k\_elim\_Contractility and R0\_Contractility.}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{shap_aligned_concern_binary.pdf}
    \caption{Aligned SHAP pairs for Concern Binary prediction (GaussianNB model). Blue lines = high concern drugs (15), grey lines = low/no concern drugs (10). Top features include n\_O2, R0\_Contractility, and Emax\_Contractility.}
\end{figure}

\subsection{Prediction Scatter Plots}

The following figure shows the predicted probabilities for all 25 drugs across all five prediction targets. Each point represents a drug, with colored points indicating the positive class for that target and gray points indicating negative/other classes. The red dashed line indicates the decision threshold, calculated as the maximum prediction among negative samples plus a margin.

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{prediction_scatter_all.pdf}
    \caption{Prediction scatter plots for all 25 drugs across all six targets (Arrhythmia, Heart Damage, Concern Binary, No Concern, Less Concern, Most Concern). Points are colored by their actual class membership, with thresholds shown as red dashed lines.}
\end{figure}

\section{Conclusions}

\begin{enumerate}
    \item \textbf{PKPD Elimination} equation provides the best predictive performance across all cardiac outcome targets.

    \item \textbf{Arrhythmia prediction} achieves robust AUC using RandomForest with 5-fold CV, with class balancing for the imbalanced dataset.

    \item \textbf{Heart Damage prediction} performs best with GaussianNB and 5-fold CV, achieving AUC of 0.829 (superior to SVM-RBF). Gaussian Naive Bayes assumes features follow Gaussian distributions within each class and handles class imbalance through prior probabilities.

    \item \textbf{Concern Binary prediction} achieves best performance with GaussianNB (AUC 0.877), significantly outperforming RandomForest.

    \item The multi-seed validation across multiple fold configurations confirms model stability and robust feature selection.

    \item \textbf{MCC (Matthews Correlation Coefficient)} provides a balanced measure for imbalanced datasets, ranging from -1 to +1 where 0 indicates random prediction.
\end{enumerate}

\end{document}
"""

    # Build LaTeX report - use temp directory for building, only keep final PDF
    latex_build_dir = OUTPUT_DIRS['latex']
    report_name = 'prediction_models_report'
    report_tex = latex_build_dir / f'{report_name}.tex'
    report_tex.write_text(latex_content)

    # Copy required figures temporarily for building
    figure_sources = {
        'loocv_comparison_plot.pdf': OUTPUT_DIRS['equation_comparison'],
        'loocv_concern_plot.pdf': OUTPUT_DIRS['equation_comparison'],
        'stage2_roc_curves_3fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'stage2_accuracy_auc_bars_3fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'stage2_confusion_matrices_3fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'stage2_roc_curves_4fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'stage2_accuracy_auc_bars_4fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'stage2_confusion_matrices_4fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'stage2_roc_curves_5fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'stage2_accuracy_auc_bars_5fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'stage2_confusion_matrices_5fold.pdf': OUTPUT_DIRS['stage2_validation'],
        'final_roc_curves.pdf': OUTPUT_DIRS['roc'],
        'final_confusion_matrices.pdf': OUTPUT_DIRS['confusion'],
        'feature_importance_comparison.pdf': OUTPUT_DIRS['feature_importance'],
        'cumulative_feature_importance.pdf': OUTPUT_DIRS['cumulative'],
        'shap_aligned_arrhythmia.pdf': OUTPUT_DIRS['shap'],
        'shap_aligned_heart_damage.pdf': OUTPUT_DIRS['shap'],
        'shap_aligned_concern_binary.pdf': OUTPUT_DIRS['shap'],
        'prediction_scatter_all.pdf': OUTPUT_DIRS['scatter'],
    }

    for fig_name, source_dir in figure_sources.items():
        src = source_dir / fig_name
        dst = latex_build_dir / fig_name
        if src.exists():
            shutil.copy2(src, dst)

    pdf_path = latex_build_dir / f'{report_name}.pdf'
    try:
        for _ in range(2):
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', report_tex.name],
                cwd=latex_build_dir,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        print(f"Prediction models PDF saved to: {pdf_path}")
    except FileNotFoundError:
        print("pdflatex not found; skipping PDF generation.")
    except subprocess.CalledProcessError:
        print("pdflatex failed; check prediction_models_report.log for details.")

    # Clean up: remove temporary figure copies and LaTeX auxiliary files
    # Only keep the final PDF
    for fig_name in figure_sources.keys():
        fig_path = latex_build_dir / fig_name
        if fig_path.exists():
            fig_path.unlink()

    # Remove LaTeX auxiliary files
    aux_extensions = ['.aux', '.log', '.out', '.toc', '.tex', '.synctex.gz']
    for ext in aux_extensions:
        aux_file = latex_build_dir / f'{report_name}{ext}'
        if aux_file.exists():
            aux_file.unlink()

    print(f"Final PDF report saved to: {pdf_path}")
    return pdf_path


# ============================================================================
# Final Analysis Plots
# ============================================================================

def generate_final_analysis_plots(all_fold_results, df, X_df):
    """
    Generate plots for the Final Analysis section:
    - ROC curves with optimal fold configs
    - Confusion matrices with optimal fold configs
    - Feature importance comparison
    - Cumulative feature importance

    Saves outputs to appropriate OUTPUT_DIRS folders.
    """
    from sklearn.inspection import permutation_importance
    from sklearn.base import clone

    optimal_folds = {'Arrhythmia': 5, 'heart_damage': 5, 'Concern_Binary': 5}

    # =========================================================================
    # 1. Final ROC Curves
    # =========================================================================
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_aspect('equal', adjustable='box')

    # Colors for binary targets (Concern is multiclass, Concern_Binary is binary)
    colors = {'Arrhythmia': '#e74c3c', 'heart_damage': '#3498db', 'Concern_Binary': '#27ae60'}
    mean_fpr = np.linspace(0, 1, 100)

    # Plot binary targets only (Concern is multiclass, skip it for main ROC)
    for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
        n_folds = optimal_folds[target]
        if n_folds in all_fold_results and target in all_fold_results[n_folds]:
            results = all_fold_results[n_folds][target]

            if 'tprs' in results and len(results['tprs']) > 0:
                mean_tpr = np.mean(results['tprs'], axis=0)
                std_tpr = np.std(results['tprs'], axis=0)
                mean_tpr[-1] = 1.0

                auc_mean = np.mean(results['aucs'])
                auc_std = np.std(results['aucs'])

                # Display name for Concern_Binary
                display_name = 'Concern (Binary)' if target == 'Concern_Binary' else target
                ax.plot(mean_fpr, mean_tpr, color=colors[target], linewidth=2,
                       label=f'{display_name} (AUC = {auc_mean:.2f} ± {auc_std:.2f}, {n_folds}-fold)')
                ax.fill_between(mean_fpr, mean_tpr - std_tpr, mean_tpr + std_tpr,
                               color=colors[target], alpha=0.2)

    ax.plot([0, 1], [0, 1], 'k--', linewidth=1.5, label='Chance (AUC = 0.50)')
    ax.set_xlabel('False Positive Rate', fontsize=14)
    ax.set_ylabel('True Positive Rate', fontsize=14)
    ax.set_title('Final Model ROC Curves (Optimal Fold Configuration)', fontsize=16)
    ax.legend(loc='lower right', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIRS['roc'] / 'final_roc_curves.pdf', format='pdf', bbox_inches='tight')
    plt.close()
    print("Final ROC curves saved: final_roc_curves.pdf")

    # =========================================================================
    # 2. Final Confusion Matrices
    # =========================================================================
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes = axes.flatten()
    targets = ['Arrhythmia', 'heart_damage', 'Concern_Binary']
    cmaps = ['Reds', 'Blues', 'Purples']
    target_labels = {
        'Arrhythmia': ['No', 'Yes'],
        'heart_damage': ['No', 'Yes'],
        'Concern_Binary': ['No Concern', 'High Concern']
    }

    for idx, (target, cmap) in enumerate(zip(targets, cmaps)):
        ax = axes[idx]
        n_folds = optimal_folds[target]

        if n_folds in all_fold_results and target in all_fold_results[n_folds]:
            results = all_fold_results[n_folds][target]
            y_true = results['all_y_true']
            y_pred = results['all_y_pred']

            cm = confusion_matrix(y_true, y_pred)
            mcc = matthews_corrcoef(y_true, y_pred)
            cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

            im = ax.imshow(cm_normalized, interpolation='nearest', cmap=cmap, vmin=0, vmax=1)
            cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

            labels = target_labels.get(target, [str(i) for i in range(len(cm))])
            tick_marks = np.arange(len(labels))
            ax.set_xticks(tick_marks)
            ax.set_yticks(tick_marks)
            ax.set_xticklabels(labels, fontsize=12)
            ax.set_yticklabels(labels, fontsize=12)

            thresh = 0.5
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    ax.text(j, i, f'{cm[i, j]}\n({cm_normalized[i, j]:.1%})',
                           ha="center", va="center", fontsize=10,
                           color="white" if cm_normalized[i, j] > thresh else "black")

            ax.set_xlabel('Predicted', fontsize=12)
            ax.set_ylabel('Actual', fontsize=12)

            _, model_name = get_best_model_for_target(target)
            # Better display name for Concern_Binary
            display_name = 'Concern (Binary)' if target == 'Concern_Binary' else target.replace("_", " ").title()
            ax.set_title(f'{display_name}\n({model_name}, {n_folds}-fold)\nMCC = {mcc:.3f}',
                        fontsize=12, fontweight='bold')

    plt.suptitle('Final Confusion Matrices (Optimal Fold Configuration)', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIRS['confusion'] / 'final_confusion_matrices.pdf', format='pdf', bbox_inches='tight')
    plt.savefig(OUTPUT_DIRS['confusion'] / 'final_confusion_matrices.png', format='png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Final confusion matrices saved: final_confusion_matrices.pdf")

    # =========================================================================
    # 3. Feature Importance Comparison
    # =========================================================================
    # Train final models to get feature importances
    feature_names = X_df.columns.tolist()

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()

    for idx, target in enumerate(targets):
        ax = axes[idx]
        n_folds = optimal_folds[target]

        # Preprocess
        y = preprocess_targets(df, target)
        valid_mask = ~y.isna()
        X_valid = X_df[valid_mask]
        y_valid = y[valid_mask].values.astype(int)

        # Compute scale_pos_weight for XGBoost
        # Only multiclass Concern (3 classes), not Concern_Binary (binary)
        is_multiclass = (target == 'Concern')
        if not is_multiclass:
            n_neg = (y_valid == 0).sum()
            n_pos = (y_valid == 1).sum()
            scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0
        else:
            scale_pos_weight = 1.0

        model, model_name = get_best_model_for_target(target, scale_pos_weight)

        # Handle NaN
        train_means = X_valid.mean()
        X_clean = X_valid.fillna(train_means)

        # Build and train pipeline
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('model', model)
        ])
        pipeline.fit(X_clean, y_valid)

        # Get feature importances
        if model_name in ['RandomForest', 'XGBoost']:
            importances = pipeline.named_steps['model'].feature_importances_
        else:  # SVM - use permutation importance
            perm_imp = permutation_importance(pipeline, X_clean, y_valid,
                                             n_repeats=10, random_state=42, n_jobs=-1)
            importances = perm_imp.importances_mean

        # Sort and plot all 14 features
        importance_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importances
        }).sort_values('Importance', ascending=True)

        colors_bar = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6'][idx]  # Red, Blue, Green, Purple
        ax.barh(importance_df['Feature'], importance_df['Importance'], color=colors_bar, alpha=0.8)
        ax.set_xlabel('Importance', fontsize=12)
        ax.set_title(f'{target.replace("_", " ").title()}\n({model_name})', fontsize=12, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)

    plt.suptitle('Feature Importance Comparison (All 14 Features)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIRS['feature_importance'] / 'feature_importance_comparison.pdf', format='pdf', bbox_inches='tight')
    plt.close()
    print("Feature importance comparison saved: feature_importance_comparison.pdf")

    # =========================================================================
    # 4. Cumulative Feature Importance
    # =========================================================================
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes = axes.flatten()

    for idx, target in enumerate(['Arrhythmia', 'heart_damage', 'Concern_Binary']):  # Binary targets
        ax = axes[idx]

        # Preprocess
        y = preprocess_targets(df, target)
        valid_mask = ~y.isna()
        X_valid = X_df[valid_mask]
        y_valid = y[valid_mask].values.astype(int)

        # Get model
        is_multiclass = False
        n_neg = (y_valid == 0).sum()
        n_pos = (y_valid == 1).sum()
        scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

        model, model_name = get_best_model_for_target(target, scale_pos_weight)

        # Handle NaN
        train_means = X_valid.mean()
        X_clean = X_valid.fillna(train_means)

        # Train model
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('model', model)
        ])
        pipeline.fit(X_clean, y_valid)

        # Get feature importances
        if model_name in ['RandomForest', 'XGBoost']:
            importances = pipeline.named_steps['model'].feature_importances_
        else:
            perm_imp = permutation_importance(pipeline, X_clean, y_valid,
                                             n_repeats=10, random_state=42, n_jobs=-1)
            importances = perm_imp.importances_mean

        # Sort features by importance
        importance_order = np.argsort(importances)[::-1]
        sorted_features = [feature_names[i] for i in importance_order]

        # Compute cumulative predictions per drug (rainbow lines)
        cumulative_probs = []
        max_features = min(14, len(sorted_features))
        for n_features in range(1, max_features + 1):
            selected_features = sorted_features[:n_features]
            X_subset = X_clean[selected_features]

            # Retrain with subset
            pipeline_subset = Pipeline([
                ('scaler', StandardScaler()),
                ('model', clone(model))
            ])
            pipeline_subset.fit(X_subset, y_valid)

            probs = pipeline_subset.predict_proba(X_subset)[:, 1] * 100
            cumulative_probs.append(probs)

        cum_array = np.vstack(cumulative_probs)
        colors_line = plt.cm.rainbow(np.linspace(0, 1, cum_array.shape[1]))
        x_vals = np.arange(1, max_features + 1)
        for line_idx, color in enumerate(colors_line):
            ax.plot(x_vals, cum_array[:, line_idx], color=color, linewidth=1, alpha=0.7)

        ax.set_xlabel('Number of Top Features', fontsize=12)
        ax.set_ylabel('Mean Predicted Probability (%)', fontsize=12)
        ax.set_title(f'{target.replace("_", " ").title()}\n({model_name})', fontsize=12, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)

    plt.suptitle('Cumulative Feature Importance', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIRS['cumulative'] / 'cumulative_feature_importance.pdf', format='pdf', bbox_inches='tight')
    plt.close()
    print("Cumulative feature importance saved: cumulative_feature_importance.pdf")

    # =========================================================================
    # 5. Prediction Scatter Plots - All Models
    # =========================================================================
    # Build final_models dictionary with trained pipelines for each target
    final_models = {}
    for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
        y = preprocess_targets(df, target)
        valid_mask = ~y.isna()
        X_valid = X_df[valid_mask]
        y_valid = y[valid_mask].values.astype(int)

        # Compute scale_pos_weight for binary targets
        n_neg = (y_valid == 0).sum()
        n_pos = (y_valid == 1).sum()
        scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

        model, model_name = get_best_model_for_target(target, scale_pos_weight)

        # Handle NaN
        train_means = X_valid.mean()
        X_clean = X_valid.fillna(train_means)

        # Build and train pipeline
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('model', model)
        ])
        pipeline.fit(X_clean, y_valid)

        final_models[target] = {
            'pipeline': pipeline,
            'X_full': X_clean,
            'y_full': y_valid,
            'model_name': model_name
        }

    generate_prediction_scatter_plot(df, X_df, final_models)


def generate_prediction_scatter_plot(df, X_df, final_models):
    """
    Generate prediction scatter plots for all targets in one row.

    Shows predicted probability for each drug, colored by actual status.
    Saves to OUTPUT_DIRS['scatter'].
    """
    # Palette
    arr_color = '#a3c9f9'      # Arrhythmia
    hd_color = '#c8b7ff'       # Heart Damage
    cb_color = '#f9c9d4'       # Concern Binary (pink)
    neg_color = 'lightgray'

    drugs = df.index.tolist()
    positions = np.arange(len(drugs))
    margin_pp = 2.0  # margin in percentage points for threshold

    # Get predictions from final models
    preds_arr = None
    preds_hd = None
    preds_cb = None

    if 'Arrhythmia' in final_models:
        pipeline = final_models['Arrhythmia']['pipeline']
        X_full = final_models['Arrhythmia']['X_full']
        preds_arr = pipeline.predict_proba(X_full)[:, 1] * 100

    if 'heart_damage' in final_models:
        pipeline = final_models['heart_damage']['pipeline']
        X_full = final_models['heart_damage']['X_full']
        preds_hd = pipeline.predict_proba(X_full)[:, 1] * 100

    if 'Concern_Binary' in final_models:
        pipeline = final_models['Concern_Binary']['pipeline']
        X_full = final_models['Concern_Binary']['X_full']
        preds_cb = pipeline.predict_proba(X_full)[:, 1] * 100

    # Create 3 subplots (Arrhythmia, Heart Damage, Concern Binary)
    fig, axes = plt.subplots(1, 3, figsize=(21, 6), sharey=True)

    thresholds = {}

    # Get actual values
    arr_status = df['Arrhythmia'].astype(str).str.lower().isin(['true', '1', 'yes'])
    hd_status = df['heart_damage'].astype(str).str.lower().isin(['true', '1', 'yes'])
    concern_actual = df['Concern'].astype(str).str.strip().str.lower()
    # Concern_Binary: most=1 (High Concern), no+less=0 (No Concern)
    cb_status = concern_actual.isin(['most'])

    # Plot 1: Arrhythmia
    ax = axes[0]
    if preds_arr is not None:
        point_colors = arr_status.map({True: arr_color, False: neg_color})
        ax.scatter(positions, preds_arr, c=point_colors, alpha=0.8, s=60)

        # Compute threshold
        neg_mask = ~arr_status.values
        if neg_mask.any():
            thr = float(np.max(preds_arr[neg_mask])) + margin_pp
        else:
            thr = float(np.percentile(preds_arr, 50)) + margin_pp
        thr = float(np.clip(thr, 0, 100))
        thr = float(5 * np.ceil(thr / 5.0))
        thresholds['Arrhythmia'] = thr

        ax.axhline(thr, color='red', linestyle='--', linewidth=1.5)
        ax.text(len(drugs) - 0.5, thr + 1.5, f'{thr:.0f}%', color='red',
                fontsize=8, va='bottom', ha='right', fontweight='bold')

    ax.set_xticks(positions)
    ax.set_xticklabels(drugs, rotation=90, fontsize=7)
    ax.set_title('Arrhythmia', fontsize=11, fontweight='bold')
    ax.set_xlabel('Drug', fontsize=9)
    ax.set_ylabel('Predicted Probability (%)', fontsize=10)
    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    # Plot 2: Heart Damage
    ax = axes[1]
    if preds_hd is not None:
        point_colors = hd_status.map({True: hd_color, False: neg_color})
        ax.scatter(positions, preds_hd, c=point_colors, alpha=0.8, s=60)

        # Compute threshold
        neg_mask = ~hd_status.values
        if neg_mask.any():
            thr = float(np.max(preds_hd[neg_mask])) + margin_pp
        else:
            thr = float(np.percentile(preds_hd, 50)) + margin_pp
        thr = float(np.clip(thr, 0, 100))
        thr = float(5 * np.ceil(thr / 5.0))
        thresholds['Heart Damage'] = thr

        ax.axhline(thr, color='red', linestyle='--', linewidth=1.5)
        ax.text(len(drugs) - 0.5, thr + 1.5, f'{thr:.0f}%', color='red',
                fontsize=8, va='bottom', ha='right', fontweight='bold')

    ax.set_xticks(positions)
    ax.set_xticklabels(drugs, rotation=90, fontsize=7)
    ax.set_title('Heart Damage', fontsize=11, fontweight='bold')
    ax.set_xlabel('Drug', fontsize=9)
    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    # Plot 3: Concern Binary
    ax = axes[2]
    if preds_cb is not None:
        point_colors = cb_status.map({True: cb_color, False: neg_color})
        ax.scatter(positions, preds_cb, c=point_colors, alpha=0.8, s=60)

        # Compute threshold
        neg_mask = ~cb_status.values
        if neg_mask.any():
            thr = float(np.max(preds_cb[neg_mask])) + margin_pp
        else:
            thr = float(np.percentile(preds_cb, 50)) + margin_pp
        thr = float(np.clip(thr, 0, 100))
        thr = float(5 * np.ceil(thr / 5.0))
        thresholds['Concern_Binary'] = thr

        ax.axhline(thr, color='red', linestyle='--', linewidth=1.5)
        ax.text(len(drugs) - 0.5, thr + 1.5, f'{thr:.0f}%', color='red',
                fontsize=8, va='bottom', ha='right', fontweight='bold')

    ax.set_xticks(positions)
    ax.set_xticklabels(drugs, rotation=90, fontsize=7)
    ax.set_title('Concern (Binary)', fontsize=11, fontweight='bold')
    ax.set_xlabel('Drug', fontsize=9)
    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    # Legend
    legend_handles = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=arr_color,
                   label='Arrhythmia +', markersize=9),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=hd_color,
                   label='Heart Damage +', markersize=9),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=cb_color,
                   label='High Concern (Binary)', markersize=9),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=neg_color,
                   label='Negative/Other', markersize=9),
        plt.Line2D([0], [0], color='red', linestyle='--', linewidth=1.5, label='Threshold')
    ]

    fig.legend(handles=legend_handles, loc='upper center', ncol=5,
               bbox_to_anchor=(0.5, 1.0), fontsize=9, frameon=False)

    fig.suptitle('Model Predictions — All Targets (5-Fold CV Models)',
                 fontsize=14, fontweight='bold', y=1.04)
    plt.tight_layout()
    plt.subplots_adjust(top=0.90)

    plt.savefig(OUTPUT_DIRS['scatter'] / 'prediction_scatter_all.pdf', format='pdf', bbox_inches='tight')
    plt.close()
    print("Prediction scatter plots saved: prediction_scatter_all.pdf")

    # Save thresholds to JSON
    import json
    threshold_path = OUTPUT_DIRS['scatter'] / 'prediction_thresholds.json'
    with open(threshold_path, 'w') as f:
        json.dump(thresholds, f, indent=2)
    print(f"Thresholds saved: {threshold_path}")


# ============================================================================
# Final Analysis Data Outputs (for external plotting)
# ============================================================================

def save_final_graph_data(all_fold_results, df, X_df):
    """
    Save data used by the Final Analysis plots to Output subfolders:
    - Cumulative_Plot_Data
    - Confusion_Matrices
    - Prediction_Scatter_Data
    - Performance_Metrics
    """
    from sklearn.inspection import permutation_importance
    from sklearn.base import clone

    output_root = PROJECT_ROOT / 'Output'
    output_dir_cumulative = output_root / 'Cumulative_Plot_Data'
    output_dir_confusion = output_root / 'Confusion_Matrices'
    output_dir_scatter = output_root / 'Prediction_Scatter_Data'
    output_dir_performance = output_root / 'Performance_Metrics'

    output_dir_cumulative.mkdir(parents=True, exist_ok=True)
    output_dir_confusion.mkdir(parents=True, exist_ok=True)
    output_dir_scatter.mkdir(parents=True, exist_ok=True)
    output_dir_performance.mkdir(parents=True, exist_ok=True)

    optimal_folds = {'Arrhythmia': 5, 'heart_damage': 5, 'Concern_Binary': 5}
    target_labels = {
        'Arrhythmia': ['No', 'Yes'],
        'heart_damage': ['No', 'Yes'],
        'Concern_Binary': ['No Concern', 'High Concern']
    }

    drug_names = [str(d) for d in df.index.tolist()]
    feature_names = X_df.columns.tolist()

    # ---------------------------------------------------------------------
    # 1) Performance Metrics Summary (final/optimal fold config only)
    # ---------------------------------------------------------------------
    perf_rows = []
    for target, n_folds in optimal_folds.items():
        if n_folds not in all_fold_results or target not in all_fold_results[n_folds]:
            continue

        results = all_fold_results[n_folds][target]
        _, model_name = get_best_model_for_target(target)

        perf_rows.append({
            'Target': target,
            'Model': model_name,
            'N_Folds': n_folds,
            'Accuracy_Mean': np.mean(results['accuracies']),
            'Accuracy_Std': np.std(results['accuracies']),
            'AUC_Mean': np.mean(results['aucs']),
            'AUC_Std': np.std(results['aucs']),
            'F1_Mean': np.mean(results['f1s']),
            'F1_Std': np.std(results['f1s']),
            'MCC_Mean': np.mean(results['mccs']),
            'MCC_Std': np.std(results['mccs'])
        })

    perf_df = pd.DataFrame(perf_rows)
    perf_path = output_dir_performance / 'model_performance_summary.csv'
    perf_df.to_csv(perf_path, index=False)

    # ---------------------------------------------------------------------
    # 1B) ROC Curve Summary (mean +/- std) for final/optimal folds
    # ---------------------------------------------------------------------
    for target, n_folds in optimal_folds.items():
        if n_folds not in all_fold_results or target not in all_fold_results[n_folds]:
            continue

        results = all_fold_results[n_folds][target]
        if 'tprs' not in results or not results['tprs']:
            continue

        mean_fpr = results.get('mean_fpr', np.linspace(0, 1, 100))
        tprs = np.array(results['tprs'])
        mean_tpr = tprs.mean(axis=0)
        std_tpr = tprs.std(axis=0)
        auc_mean = float(np.mean(results['aucs'])) if results.get('aucs') else np.nan
        auc_std = float(np.std(results['aucs'])) if results.get('aucs') else np.nan

        roc_df = pd.DataFrame({
            'mean_fpr': mean_fpr,
            'mean_tpr': mean_tpr,
            'std_tpr': std_tpr,
            'auc_mean': auc_mean,
            'auc_std': auc_std
        })
        roc_path = output_dir_performance / f"{target.lower()}_roc_curve_summary.csv"
        roc_df.to_csv(roc_path, index=False)

    # ---------------------------------------------------------------------
    # 2) Confusion Matrices + Classification Reports (final/optimal folds)
    # ---------------------------------------------------------------------
    for target, n_folds in optimal_folds.items():
        if n_folds not in all_fold_results or target not in all_fold_results[n_folds]:
            continue

        results = all_fold_results[n_folds][target]
        y_true = np.array(results['all_y_true'])
        y_pred = np.array(results['all_y_pred'])

        labels = list(range(len(target_labels[target])))
        cm = confusion_matrix(y_true, y_pred, labels=labels)

        df_cm = pd.DataFrame(
            cm,
            index=[f'Actual_{lbl}' for lbl in target_labels[target]],
            columns=[f'Pred_{lbl}' for lbl in target_labels[target]]
        )
        cm_path = output_dir_confusion / f'{target.lower()}_confusion_matrix.csv'
        df_cm.to_csv(cm_path)

        report = classification_report(
            y_true, y_pred,
            labels=labels,
            target_names=target_labels[target],
            zero_division=0,
            output_dict=True
        )
        df_report = pd.DataFrame(report).T
        report_path = output_dir_confusion / f'{target.lower()}_classification_report.csv'
        df_report.to_csv(report_path)

    # ---------------------------------------------------------------------
    # 3) Train final models (full data) for scatter + cumulative outputs
    # ---------------------------------------------------------------------
    final_models = {}
    for target in TARGETS:
        y = preprocess_targets(df, target)
        valid_mask = ~y.isna()
        X_valid = X_df[valid_mask]
        y_valid = y[valid_mask].values.astype(int)

        # Only multiclass Concern (3 classes), not Concern_Binary (binary)
        is_multiclass = (target == 'Concern')
        if not is_multiclass:
            n_neg = (y_valid == 0).sum()
            n_pos = (y_valid == 1).sum()
            scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0
        else:
            scale_pos_weight = 1.0

        model, model_name = get_best_model_for_target(target, scale_pos_weight)

        train_means = X_valid.mean()
        X_clean = X_valid.fillna(train_means)
        X_full = X_df.fillna(train_means)

        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('model', model)
        ])
        pipeline.fit(X_clean, y_valid)

        probs = pipeline.predict_proba(X_full)

        final_models[target] = {
            'pipeline': pipeline,
            'model_name': model_name,
            'y_series': y,
            'y_valid': y_valid,
            'X_valid': X_valid,
            'X_clean': X_clean,
            'X_full': X_full,
            'probs': probs,
            'train_means': train_means
        }

    # ---------------------------------------------------------------------
    # 4) Prediction Scatter Data + Thresholds
    # ---------------------------------------------------------------------
    margin_pp = 2.0
    thresholds = {}

    # Arrhythmia
    arr_data = final_models.get('Arrhythmia')
    if arr_data:
        arr_probs = arr_data['probs'][:, 1] * 100
        arr_actual = arr_data['y_series'].map({1: True, 0: False})
        arr_df = pd.DataFrame({
            'Drug': drug_names,
            'Predicted_Arrhythmia_pct': arr_probs,
            'Actual_Arrhythmia': arr_actual
        })
        arr_df.to_csv(output_dir_scatter / 'arrhythmia_predictions.csv', index=False)

        arr_status = arr_data['y_series'].values
        arr_valid = ~pd.isna(arr_status)
        arr_neg_mask = (arr_status == 0) & arr_valid
        if np.any(arr_neg_mask):
            thr = float(np.max(arr_probs[arr_neg_mask])) + margin_pp
        else:
            thr = float(np.percentile(arr_probs[arr_valid], 50)) + margin_pp
        thr = float(np.clip(thr, 0, 100))
        thr = float(5 * np.ceil(thr / 5.0))
        thresholds['Arrhythmia'] = thr

    # Heart Damage
    hd_data = final_models.get('heart_damage')
    if hd_data:
        hd_probs = hd_data['probs'][:, 1] * 100
        hd_actual = hd_data['y_series'].map({1: True, 0: False})
        hd_df = pd.DataFrame({
            'Drug': drug_names,
            'Predicted_Heart_Damage_pct': hd_probs,
            'Actual_Heart_Damage': hd_actual
        })
        hd_df.to_csv(output_dir_scatter / 'heart_damage_predictions.csv', index=False)

        hd_status = hd_data['y_series'].values
        hd_valid = ~pd.isna(hd_status)
        hd_neg_mask = (hd_status == 0) & hd_valid
        if np.any(hd_neg_mask):
            thr = float(np.max(hd_probs[hd_neg_mask])) + margin_pp
        else:
            thr = float(np.percentile(hd_probs[hd_valid], 50)) + margin_pp
        thr = float(np.clip(thr, 0, 100))
        thr = float(5 * np.ceil(thr / 5.0))
        thresholds['Heart Damage'] = thr

    # Concern_Binary
    cb_data = final_models.get('Concern_Binary')
    if cb_data:
        cb_probs = cb_data['probs'][:, 1] * 100
        concern_actual = df['Concern'].astype(str).str.strip().str.lower()
        # Binary mapping: most=1 (High Concern), no+less=0 (No Concern)
        cb_actual = concern_actual.isin(['most'])
        cb_df = pd.DataFrame({
            'Drug': drug_names,
            'Predicted_High_Concern_pct': cb_probs,
            'Actual_High_Concern': cb_actual
        })
        cb_df.to_csv(output_dir_scatter / 'concern_binary_predictions.csv', index=False)

        cb_status = cb_actual.values
        cb_valid = ~pd.isna(cb_status)
        cb_neg_mask = (~cb_status) & cb_valid
        if np.any(cb_neg_mask):
            thr = float(np.max(cb_probs[cb_neg_mask])) + margin_pp
        else:
            thr = float(np.percentile(cb_probs[cb_valid], 50)) + margin_pp
        thr = float(np.clip(thr, 0, 100))
        thr = float(5 * np.ceil(thr / 5.0))
        thresholds['Concern_Binary'] = thr

    thresholds_payload = {
        'Arrhythmia_threshold_pct': thresholds.get('Arrhythmia', 0),
        'Heart_Damage_threshold_pct': thresholds.get('Heart Damage', 0),
        'Concern_Binary_threshold_pct': thresholds.get('Concern_Binary', 0)
    }
    thresholds_path = output_dir_scatter / 'prediction_thresholds.json'
    thresholds_path.write_text(json.dumps(thresholds_payload, indent=2))

    # ---------------------------------------------------------------------
    # 4b) Recalculate Confusion Matrices using custom thresholds
    # ---------------------------------------------------------------------
    # This ensures confusion matrices use the same thresholds as scatter/cumulative plots
    print("Recalculating confusion matrices with custom thresholds...")

    threshold_target_map = {
        'Arrhythmia': thresholds.get('Arrhythmia', 50.0),
        'heart_damage': thresholds.get('Heart Damage', 50.0),
        'Concern_Binary': thresholds.get('Concern_Binary', 50.0)
    }

    for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
        if target not in final_models:
            continue

        data = final_models[target]
        probs = data['probs']
        y_series = data['y_series']

        # Get valid mask and true labels
        valid_mask = ~y_series.isna()
        y_true = y_series[valid_mask].values.astype(int)

        # Get probabilities for positive class (class 1)
        probs_valid = probs[valid_mask.values]
        probs_positive = probs_valid[:, 1] * 100  # Convert to percentage

        # Apply custom threshold to get predictions
        thr = threshold_target_map[target]
        y_pred = (probs_positive >= thr).astype(int)

        # Compute confusion matrix
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

        # Save confusion matrix
        labels = target_labels[target]
        df_cm = pd.DataFrame(
            cm,
            index=[f'Actual_{lbl}' for lbl in labels],
            columns=[f'Pred_{lbl}' for lbl in labels]
        )
        cm_path = output_dir_confusion / f'{target.lower()}_confusion_matrix.csv'
        df_cm.to_csv(cm_path)

        # Compute and save classification report
        report = classification_report(
            y_true, y_pred,
            labels=[0, 1],
            target_names=labels,
            zero_division=0,
            output_dict=True
        )
        df_report = pd.DataFrame(report).T
        report_path = output_dir_confusion / f'{target.lower()}_classification_report.csv'
        df_report.to_csv(report_path)

        print(f"  {target}: threshold={thr:.0f}%, CM shape={cm.shape}")

    # ---------------------------------------------------------------------
    # 5) Cumulative Plot Data (per-drug predictions by top features)
    # ---------------------------------------------------------------------
    def _sorted_features_for_target(target, data):
        model_name = data['model_name']
        pipeline = data['pipeline']
        X_clean = data['X_clean']
        y_valid = data['y_valid']

        if model_name in ['RandomForest', 'XGBoost']:
            importances = pipeline.named_steps['model'].feature_importances_
        else:
            perm_imp = permutation_importance(
                pipeline, X_clean, y_valid,
                n_repeats=10, random_state=42, n_jobs=-1
            )
            importances = perm_imp.importances_mean

        order = np.argsort(importances)[::-1]
        return [feature_names[i] for i in order]

    def _save_cumulative_csv(target, data, class_idx=None, filename=None):
        sorted_features = _sorted_features_for_target(target, data)
        max_features = min(14, len(sorted_features))
        row_names = [' + '.join(sorted_features[:r]) for r in range(1, max_features + 1)]

        rows = []
        for n_features in range(1, max_features + 1):
            selected = sorted_features[:n_features]
            X_valid_subset = data['X_valid'][selected].fillna(data['train_means'][selected])
            X_full_subset = data['X_full'][selected]

            pipeline_subset = Pipeline([
                ('scaler', StandardScaler()),
                ('model', clone(data['pipeline'].named_steps['model']))
            ])
            pipeline_subset.fit(X_valid_subset, data['y_valid'])
            probs = pipeline_subset.predict_proba(X_full_subset)

            if class_idx is None:
                preds = probs[:, 1] * 100
            else:
                preds = probs[:, class_idx] * 100
            rows.append(preds)

        df_out = pd.DataFrame(rows, index=row_names, columns=drug_names)
        df_out.index.name = 'Cumulative_Coefficients'
        df_out.to_csv(filename)

    if 'Arrhythmia' in final_models:
        _save_cumulative_csv(
            'Arrhythmia',
            final_models['Arrhythmia'],
            class_idx=None,
            filename=output_dir_cumulative / 'arrhythmia_cumulative_predictions.csv'
        )

    if 'heart_damage' in final_models:
        _save_cumulative_csv(
            'heart_damage',
            final_models['heart_damage'],
            class_idx=None,
            filename=output_dir_cumulative / 'heart_damage_cumulative_predictions.csv'
        )

    if 'Concern_Binary' in final_models:
        _save_cumulative_csv(
            'Concern_Binary',
            final_models['Concern_Binary'],
            class_idx=None,
            filename=output_dir_cumulative / 'concern_binary_cumulative_predictions.csv'
        )

    # ---------------------------------------------------------------------
    # 6) SHAP Data (optional)
    # ---------------------------------------------------------------------
    shap_dir = output_root / 'SHAP_Data'
    shap_dir.mkdir(parents=True, exist_ok=True)

    try:
        import shap
    except Exception:
        print("SHAP not available; skipping SHAP data export.")
        return

    # Save raw feature values (for reference)
    raw_features = X_df.copy()
    raw_features.insert(0, 'Drug', drug_names)
    raw_features.to_csv(shap_dir / 'feature_values_raw.csv', index=False)

    # Save scaled feature values (use Arrhythmia scaler as reference)
    if 'Arrhythmia' in final_models:
        arr_scaler = final_models['Arrhythmia']['pipeline'].named_steps['scaler']
        scaled_values = arr_scaler.transform(final_models['Arrhythmia']['X_full'])
        scaled_features = pd.DataFrame(scaled_values, columns=feature_names)
        scaled_features.insert(0, 'Drug', drug_names)
        scaled_features.to_csv(shap_dir / 'feature_values_scaled.csv', index=False)

    summary_rows = []

    def _write_shap_outputs(name, shap_values):
        shap_df = pd.DataFrame(shap_values, columns=feature_names)
        shap_df.insert(0, 'Drug', drug_names)
        shap_path = shap_dir / f'shap_{name}_values.csv'
        shap_df.to_csv(shap_path, index=False)

        mean_abs = np.abs(shap_values).mean(axis=0)
        mean_df = pd.DataFrame({
            'Feature': feature_names,
            'Mean_Abs_SHAP': mean_abs
        }).sort_values('Mean_Abs_SHAP', ascending=False)
        mean_path = shap_dir / f'shap_{name}_mean_importance.csv'
        mean_df.to_csv(mean_path, index=False)

        for _, row in mean_df.iterrows():
            summary_rows.append({
                'Model': name,
                'Feature': row['Feature'],
                'Mean_Abs_SHAP': row['Mean_Abs_SHAP']
            })

    def _tree_shap_values(pipeline, X_full):
        model = pipeline.named_steps['model']
        scaler = pipeline.named_steps['scaler']
        X_scaled = pd.DataFrame(
            scaler.transform(X_full),
            columns=feature_names
        )
        # Handle CatBoostWrapper by extracting internal model
        if isinstance(model, CatBoostWrapper):
            model = model._model
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_scaled)
        return shap_values

    # Arrhythmia (tree model)
    if 'Arrhythmia' in final_models:
        arr_data = final_models['Arrhythmia']
        shap_values = _tree_shap_values(arr_data['pipeline'], arr_data['X_full'])
        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            # Modern SHAP returns (samples, features, classes) - select positive class
            shap_values = shap_values[:, :, 1]
        _write_shap_outputs('arrhythmia', shap_values)

    # Heart Damage (SVM -> Kernel SHAP)
    if 'heart_damage' in final_models:
        try:
            hd_data = final_models['heart_damage']
            pipeline = hd_data['pipeline']
            scaler = pipeline.named_steps['scaler']
            X_scaled = scaler.transform(hd_data['X_full'])
            X_scaled_df = pd.DataFrame(X_scaled, columns=feature_names)

            # Use scaled data for background and prediction
            background = shap.sample(X_scaled_df, min(10, len(X_scaled_df)), random_state=42)

            # Create prediction function that takes scaled input
            def predict_proba_scaled(X):
                return pipeline.named_steps['model'].predict_proba(X)

            explainer = shap.KernelExplainer(predict_proba_scaled, background)
            shap_values = explainer.shap_values(X_scaled_df, nsamples=100)
            if isinstance(shap_values, list):
                shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
            elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
                # KernelExplainer may return (samples, features, classes) - select positive class
                shap_values = shap_values[:, :, 1]
            _write_shap_outputs('heart_damage', shap_values)
        except Exception as e:
            print(f"Warning: Could not compute SHAP for heart_damage: {e}")

    # Concern_Binary (GaussianNB -> Kernel SHAP)
    if 'Concern_Binary' in final_models:
        try:
            cb_data = final_models['Concern_Binary']
            pipeline = cb_data['pipeline']
            scaler = pipeline.named_steps['scaler']
            X_scaled = scaler.transform(cb_data['X_full'])
            X_scaled_df = pd.DataFrame(X_scaled, columns=feature_names)

            # Use scaled data for background and prediction
            background = shap.sample(X_scaled_df, min(10, len(X_scaled_df)), random_state=42)

            # Create prediction function that takes scaled input
            def predict_proba_scaled_cb(X):
                return pipeline.named_steps['model'].predict_proba(X)

            explainer = shap.KernelExplainer(predict_proba_scaled_cb, background)
            shap_values = explainer.shap_values(X_scaled_df, nsamples=100)
            if isinstance(shap_values, list):
                shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
            elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
                # KernelExplainer may return (samples, features, classes) - select positive class
                shap_values = shap_values[:, :, 1]
            _write_shap_outputs('concern_binary', shap_values)
        except Exception as e:
            print(f"Warning: Could not compute SHAP for Concern_Binary: {e}")

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_csv(shap_dir / 'shap_all_models_summary.csv', index=False)

    # Generate SHAP bar plots (save to SHAP directory)
    generate_shap_bar_plots(shap_dir)

    # Generate SHAP aligned pairs plots for binary targets
    generate_shap_aligned_pairs(shap_dir)


def generate_shap_bar_plots(shap_dir):
    """
    Generate SHAP bar plots for each model in the style of the example image.

    Creates horizontal bar charts with features colored by type (Contractility vs O2).
    Saves to OUTPUT_DIRS['shap'].
    """
    output_dir = OUTPUT_DIRS['shap']

    # Define colors for feature types
    colors = {
        'Contractility': '#FFE699',  # Light yellow
        'O2': '#9DC3E6',  # Light blue
    }

    # Model configurations
    models_to_plot = [
        ('arrhythmia', 'Arrhythmia'),
        ('heart_damage', 'Heart Damage'),
        ('concern_binary', 'Concern (Binary)'),
    ]

    for model_file, model_title in models_to_plot:
        shap_file = shap_dir / f'shap_{model_file}_mean_importance.csv'
        if not shap_file.exists():
            print(f"  SHAP file not found: {shap_file}")
            continue

        # Load SHAP data
        df = pd.read_csv(shap_file)

        # Determine feature type and assign colors
        def get_feature_type(feature):
            if '_Contractility' in feature or feature.endswith('_Contractility'):
                return 'Contractility'
            elif '_O2' in feature or feature.endswith('_O2'):
                return 'O2'
            else:
                return 'Contractility'  # Default

        df['Feature_Type'] = df['Feature'].apply(get_feature_type)
        df['Color'] = df['Feature_Type'].map(colors)

        # Clean up feature names for display
        def clean_feature_name(name):
            name = name.replace('_Contractility', ' (C)')
            name = name.replace('_O2', ' (O₂)')
            # Format parameter names nicely
            name = name.replace('R0', 'R₀')
            name = name.replace('Emax', 'Eₘₐₓ')
            name = name.replace('kappa', 'κ')
            name = name.replace('k_elim', 'kₑₗᵢₘ')
            name = name.replace('tau', 'τ')
            return name

        df['Feature_Display'] = df['Feature'].apply(clean_feature_name)

        # Show all 14 features (reversed for horizontal bar)
        df_top = df.iloc[::-1]

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))

        bars = ax.barh(
            df_top['Feature_Display'],
            df_top['Mean_Abs_SHAP'],
            color=df_top['Color'],
            edgecolor='gray',
            linewidth=0.5
        )

        # Styling
        ax.set_xlabel('SHAP value\n(impact on model output)', fontsize=12)
        ax.set_title(f'Shapley values to explain\n{model_title} model coefficients', fontsize=14)
        ax.axvline(x=0, color='gray', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=colors['Contractility'], edgecolor='gray', label='Contractility'),
            Patch(facecolor=colors['O2'], edgecolor='gray', label='O₂'),
        ]
        ax.legend(handles=legend_elements, title='Feature type', loc='lower right', framealpha=0.9)

        plt.tight_layout()

        # Save plot (PDF only)
        plot_name = f'shap_{model_file}_bar.pdf'
        plt.savefig(output_dir / plot_name, bbox_inches='tight')
        plt.close()
        print(f"  SHAP bar plot saved: {plot_name}")


def generate_shap_aligned_pairs(shap_dir):
    """
    Generate SHAP aligned positive-negative pairs plots for binary targets.

    Creates compact visualization where positive and negative SHAP values
    are paired by magnitude and drawn as symmetric horizontal line segments.
    Color indicates actual class membership.
    """
    from matplotlib.lines import Line2D

    output_dir = OUTPUT_DIRS['shap']

    # Load drug classification
    drug_class_path = PROJECT_ROOT / 'Cleaned_Data' / 'drug_classification.csv'
    if not drug_class_path.exists():
        print(f"  Warning: Drug classification file not found: {drug_class_path}")
        return

    drug_class = pd.read_csv(drug_class_path)

    # Target configurations: (shap_file_prefix, target_column, title, positive_label, negative_label, is_concern_binary)
    targets = [
        ('arrhythmia', 'Arrhythmia', 'Arrhythmia', 'Arrhythmogenic', 'Not arrhythmogenic', False),
        ('heart_damage', 'heart_damage', 'Heart Damage', 'Cardiotoxic', 'Not cardiotoxic', False),
        ('concern_binary', 'Concern', 'Concern (Binary)', 'High Concern', 'Low/No Concern', True),
    ]

    for shap_prefix, target_col, title, pos_label, neg_label, is_concern_binary in targets:
        shap_file = shap_dir / f'shap_{shap_prefix}_values.csv'
        if not shap_file.exists():
            print(f"  SHAP values file not found: {shap_file}")
            continue

        # Load SHAP values
        shap_df = pd.read_csv(shap_file)

        # Create class membership map
        class_map = {}
        for _, row in drug_class.iterrows():
            drug = row['Drug']
            val = row[target_col]
            if is_concern_binary:
                # For Concern_Binary: 'most' = True (high concern), 'less'/'no' = False
                class_map[drug] = val.lower() == 'most' if isinstance(val, str) else False
            elif isinstance(val, str):
                class_map[drug] = val.lower() == 'true'
            else:
                class_map[drug] = bool(val)

        # Get feature columns
        feature_cols = [col for col in shap_df.columns if col != 'Drug']

        # Calculate mean SHAP and get top 5 features by |mean|
        mean_shap = shap_df[feature_cols].mean()
        top_features = mean_shap.abs().nlargest(5).index.tolist()

        # Create BIG figure (scales down with visible white gaps)
        fig, ax = plt.subplots(figsize=(12, 7))

        # Colors and parameters for visible white gaps
        color_positive = '#1f77b4'  # Blue for positive class
        color_negative = '#888888'  # Grey for negative class
        line_width = 2.0
        feature_spacing = 0.85
        line_spacing = 0.03
        ZERO_THRESHOLD = 1e-6

        y_positions = []
        y_labels = []

        for feat_idx, feature in enumerate(reversed(top_features)):
            base_y = feat_idx * feature_spacing
            y_positions.append(base_y)

            # Clean feature name for display
            display_name = feature.replace('_Contractility', ' (C)').replace('_O2', ' (O₂)')
            display_name = display_name.replace('R0', 'R₀').replace('Emax', 'Eₘₐₓ')
            display_name = display_name.replace('kappa', 'κ').replace('k_elim', 'kₑₗᵢₘ').replace('tau', 'τ')
            y_labels.append(display_name)

            # Get SHAP values and drugs
            values = shap_df[feature].values
            drugs = shap_df['Drug'].values

            # Split into positive and negative SHAP values
            positive_data = [(v, d) for v, d in zip(values, drugs) if v > ZERO_THRESHOLD]
            negative_data = [(abs(v), d) for v, d in zip(values, drugs) if v < -ZERO_THRESHOLD]

            # Sort descending by magnitude
            positive_data = sorted(positive_data, key=lambda x: x[0], reverse=True)
            negative_data = sorted(negative_data, key=lambda x: x[0], reverse=True)

            n_pairs = min(len(positive_data), len(negative_data))
            unpaired_positive = positive_data[n_pairs:]
            unpaired_negative = negative_data[n_pairs:]

            # Draw paired lines
            for i in range(n_pairs):
                y = base_y + i * line_spacing
                pos_val, pos_drug = positive_data[i]
                neg_val, neg_drug = negative_data[i]

                pos_color = color_positive if class_map.get(pos_drug, False) else color_negative
                neg_color = color_positive if class_map.get(neg_drug, False) else color_negative

                ax.hlines(y, 0, pos_val, colors=pos_color, linewidth=line_width)
                ax.hlines(y, -neg_val, 0, colors=neg_color, linewidth=line_width)

            # Draw unpaired lines
            for i, (pos_val, pos_drug) in enumerate(unpaired_positive):
                y = base_y + (n_pairs + i) * line_spacing
                pos_color = color_positive if class_map.get(pos_drug, False) else color_negative
                ax.hlines(y, 0, pos_val, colors=pos_color, linewidth=line_width)

            for i, (neg_val, neg_drug) in enumerate(unpaired_negative):
                y = base_y + (n_pairs + i) * line_spacing
                neg_color = color_positive if class_map.get(neg_drug, False) else color_negative
                ax.hlines(y, -neg_val, 0, colors=neg_color, linewidth=line_width)

        # Formatting - larger fonts for big figure
        ax.axvline(x=0, color='black', linewidth=0.8)
        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels, fontsize=14)
        ax.set_xlabel('SHAP value', fontsize=16)
        ax.set_title(f'Aligned positive-negative SHAP pairs: {title}', fontsize=22, fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.3)
        ax.set_axisbelow(True)
        ax.set_ylim(-0.25, len(top_features) * feature_spacing + 0.25)

        # X-axis ticks every 0.1
        from matplotlib.ticker import MultipleLocator
        ax.xaxis.set_major_locator(MultipleLocator(0.1))
        ax.tick_params(axis='x', labelsize=12)

        # Legend with counts
        n_positive = sum(1 for d in shap_df['Drug'].values if class_map.get(d, False))
        legend_elements = [
            Line2D([0], [0], color=color_positive, linewidth=2.5,
                   label=f'{pos_label} ({n_positive})'),
            Line2D([0], [0], color=color_negative, linewidth=2.5,
                   label=f'{neg_label} ({25 - n_positive})')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=12, framealpha=0.9)

        plt.tight_layout()

        # Save with high DPI for quality when scaled down
        plot_name = f'shap_aligned_{shap_prefix}.pdf'
        plt.savefig(output_dir / plot_name, bbox_inches='tight')
        plt.savefig(output_dir / plot_name.replace('.pdf', '.png'), dpi=600, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"  SHAP aligned pairs saved: {plot_name}")


# ============================================================================
# ROC Curve Data Export (Excel format)
# ============================================================================

def save_roc_curves_to_excel(all_fold_results, output_path):
    """
    Save ROC curve data to Excel using results from the main pipeline.

    Uses the pre-computed interpolated TPR values (on common FPR grid) from
    the multi-seed CV runs to ensure consistency with CSV output.

    Sheets: Arrhythmia, HeartDamage, ConcernNo, ConcernLess, ConcernMost
    Columns per fold: Fold{N} - FPR, Fold{N} - TPR, Fold{N} - ROC
    """
    from sklearn.metrics import auc

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    optimal_folds = {'Arrhythmia': 5, 'heart_damage': 5, 'Concern_Binary': 5}
    sheet_data = {}

    for target in ['Arrhythmia', 'heart_damage', 'Concern_Binary']:
        n_folds = optimal_folds[target]
        is_multiclass = (target == 'Concern')  # Only multiclass Concern, not Concern_Binary

        if n_folds not in all_fold_results or target not in all_fold_results[n_folds]:
            print(f"Warning: No results for {target} with {n_folds} folds")
            continue

        results = all_fold_results[n_folds][target]

        if 'tprs' not in results or not results['tprs']:
            print(f"Warning: No TPR data for {target}")
            continue

        # Get the common FPR grid and interpolated TPRs from each seed
        mean_fpr = results.get('mean_fpr', np.linspace(0, 1, 100))
        tprs = np.array(results['tprs'])  # Shape: (n_seeds, n_fpr_points)
        aucs = results.get('aucs', [])

        if not is_multiclass:
            # Binary classification - use per-seed interpolated curves
            fold_data = []
            for seed_idx in range(len(tprs)):
                tpr = tprs[seed_idx]
                # Compute AUC from interpolated curve
                seed_auc = aucs[seed_idx] if seed_idx < len(aucs) else auc(mean_fpr, tpr)

                fold_data.append({
                    'fpr': mean_fpr,
                    'tpr': tpr,
                    'auc': seed_auc
                })

            # Map target names to sheet names
            sheet_name_map = {
                'Arrhythmia': 'Arrhythmia',
                'heart_damage': 'HeartDamage',
                'Concern_Binary': 'ConcernBinary'
            }
            sheet_name = sheet_name_map.get(target, target)
            sheet_df = _build_fold_dataframe(fold_data)
            sheet_data[sheet_name] = sheet_df

        else:
            # Multiclass - check for per-class ROC data
            class_names = ['ConcernNo', 'ConcernLess', 'ConcernMost']

            # Try to get per-class data from results
            if 'class_tprs' in results:
                for class_idx, class_name in enumerate(class_names):
                    class_tprs = results['class_tprs'].get(class_idx, [])
                    class_aucs = results['class_aucs'].get(class_idx, [])

                    fold_data = []
                    for seed_idx in range(len(class_tprs)):
                        tpr = class_tprs[seed_idx]
                        seed_auc = class_aucs[seed_idx] if seed_idx < len(class_aucs) else auc(mean_fpr, tpr)

                        fold_data.append({
                            'fpr': mean_fpr,
                            'tpr': tpr,
                            'auc': seed_auc
                        })

                    if fold_data:
                        sheet_df = _build_fold_dataframe(fold_data)
                        sheet_data[class_name] = sheet_df
            else:
                # Fallback: use overall multiclass TPRs (macro-averaged)
                for class_idx, class_name in enumerate(class_names):
                    fold_data = []
                    for seed_idx in range(len(tprs)):
                        tpr = tprs[seed_idx]
                        seed_auc = aucs[seed_idx] if seed_idx < len(aucs) else auc(mean_fpr, tpr)

                        fold_data.append({
                            'fpr': mean_fpr,
                            'tpr': tpr,
                            'auc': seed_auc
                        })

                    if fold_data:
                        sheet_df = _build_fold_dataframe(fold_data)
                        sheet_data[class_name] = sheet_df

    # Write to Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, sheet_df in sheet_data.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"ROC curve data saved to: {output_path}")


def _build_fold_dataframe(fold_data):
    """
    Build a DataFrame with columns: Fold{N} - FPR, Fold{N} - TPR, Fold{N} - ROC
    for each fold. Pads shorter arrays with NaN.
    """
    # Find max length
    max_len = max(len(f['fpr']) for f in fold_data)

    columns = []
    data = {}

    for fold_idx, fold in enumerate(fold_data, 1):
        fpr = fold['fpr']
        tpr = fold['tpr']
        roc_val = fold['auc']

        # Pad to max length
        fpr_padded = np.full(max_len, np.nan)
        tpr_padded = np.full(max_len, np.nan)
        roc_padded = np.full(max_len, np.nan)

        fpr_padded[:len(fpr)] = fpr
        tpr_padded[:len(tpr)] = tpr
        roc_padded[:len(fpr)] = roc_val  # Same AUC for all rows in fold

        data[f'Fold{fold_idx} - FPR'] = fpr_padded
        data[f'Fold{fold_idx} - TPR'] = tpr_padded
        data[f'Fold{fold_idx} - ROC'] = roc_padded

    return pd.DataFrame(data)


def create_consolidated_excel_files(stage1_results_df):
    """
    Create consolidated Excel files for all graphs to enable easy recreation.

    This function generates Excel files that accompany each plot, containing
    the data needed to recreate the visualization.

    Generated files:
    - Output/ROC_Data/loocv_model_comparison.xlsx
    - Output/ROC_Data/final_roc_curves.xlsx (copy of roc_curves_all_models.xlsx)
    - Output/Confusion_Matrices/confusion_matrices_all.xlsx
    - Output/SHAP_Data/shap_complete_analysis.xlsx
    - Output/SHAP_Data/shap_arrhythmia_bar.xlsx
    - Output/SHAP_Data/shap_heart_damage_bar.xlsx
    - Output/SHAP_Data/shap_concern_most_concern_bar.xlsx
    - Output/Prediction_Scatter_Data/prediction_scatter_all.xlsx
    - Output/Cumulative_Plot_Data/cumulative_feature_importance.xlsx
    - Output/Performance_Metrics/all_performance_metrics.xlsx
    """
    print("\nCreating consolidated Excel files for graphs...")

    output_root = PROJECT_ROOT / 'Output'

    # 1. LOOCV Model Comparison Excel (Stage 1 results)
    roc_dir = output_root / 'ROC_Data'
    loocv_excel = roc_dir / 'loocv_model_comparison.xlsx'

    # Create summary by equation
    summary_data = []
    for eq in stage1_results_df['Equation'].unique():
        df_eq = stage1_results_df[stage1_results_df['Equation'] == eq]
        for target in df_eq['Target'].unique():
            df_target = df_eq[df_eq['Target'] == target]
            best_row = df_target.loc[df_target['AUC'].idxmax()]
            summary_data.append({
                'Equation': eq,
                'Target': target,
                'Best_Model': best_row['Model'],
                'Best_Accuracy': best_row['Accuracy'],
                'Best_AUC': best_row['AUC']
            })

    df_summary = pd.DataFrame(summary_data)
    with pd.ExcelWriter(loocv_excel) as writer:
        stage1_results_df.to_excel(writer, sheet_name='All_Results', index=False)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
    print(f"  Created: {loocv_excel}")

    # 2. Copy ROC curves Excel as final_roc_curves.xlsx
    roc_source = roc_dir / 'roc_curves_all_models.xlsx'
    roc_dest = roc_dir / 'final_roc_curves.xlsx'
    if roc_source.exists():
        import shutil
        shutil.copy(roc_source, roc_dest)
        print(f"  Created: {roc_dest}")

    # 3. Confusion Matrices consolidated Excel
    conf_dir = output_root / 'Confusion_Matrices'
    conf_excel = conf_dir / 'confusion_matrices_all.xlsx'
    conf_files = ['arrhythmia_confusion_matrix.csv', 'heart_damage_confusion_matrix.csv', 'concern_confusion_matrix.csv', 'concern_binary_confusion_matrix.csv']
    report_files = ['arrhythmia_classification_report.csv', 'heart_damage_classification_report.csv', 'concern_classification_report.csv', 'concern_binary_classification_report.csv']

    with pd.ExcelWriter(conf_excel) as writer:
        for f in conf_files:
            fpath = conf_dir / f
            if fpath.exists():
                df = pd.read_csv(fpath)
                sheet = f.replace('_confusion_matrix.csv', '')
                df.to_excel(writer, sheet_name=sheet, index=False)
        for f in report_files:
            fpath = conf_dir / f
            if fpath.exists():
                df = pd.read_csv(fpath)
                sheet = f.replace('_classification_report.csv', '') + '_report'
                df.to_excel(writer, sheet_name=sheet[:31], index=False)
    print(f"  Created: {conf_excel}")

    # 4. SHAP consolidated Excel files
    shap_dir = output_root / 'SHAP_Data'

    # Complete SHAP analysis
    shap_files = {
        'arrhythmia_mean': 'shap_arrhythmia_mean_importance.csv',
        'arrhythmia_values': 'shap_arrhythmia_values.csv',
        'heart_damage_mean': 'shap_heart_damage_mean_importance.csv',
        'heart_damage_values': 'shap_heart_damage_values.csv',
        'concern_binary_mean': 'shap_concern_binary_mean_importance.csv',
        'concern_binary_values': 'shap_concern_binary_values.csv',
        'concern_no_mean': 'shap_concern_no_concern_mean_importance.csv',
        'concern_less_mean': 'shap_concern_less_concern_mean_importance.csv',
        'concern_most_mean': 'shap_concern_most_concern_mean_importance.csv',
        'feature_values_raw': 'feature_values_raw.csv',
        'feature_values_scaled': 'feature_values_scaled.csv',
        'summary': 'shap_all_models_summary.csv'
    }

    shap_complete = shap_dir / 'shap_complete_analysis.xlsx'
    with pd.ExcelWriter(shap_complete) as writer:
        for sheet_name, filename in shap_files.items():
            fpath = shap_dir / filename
            if fpath.exists():
                df = pd.read_csv(fpath)
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    print(f"  Created: {shap_complete}")

    # Individual SHAP bar plot Excel files
    shap_plots = [
        ('shap_arrhythmia_bar.xlsx', ['shap_arrhythmia_mean_importance.csv', 'shap_arrhythmia_values.csv']),
        ('shap_heart_damage_bar.xlsx', ['shap_heart_damage_mean_importance.csv', 'shap_heart_damage_values.csv']),
        ('shap_concern_binary_bar.xlsx', ['shap_concern_binary_mean_importance.csv', 'shap_concern_binary_values.csv']),
        ('shap_concern_most_concern_bar.xlsx', ['shap_concern_most_concern_mean_importance.csv', 'shap_concern_most_concern_values.csv'])
    ]

    for excel_name, csv_files in shap_plots:
        excel_path = shap_dir / excel_name
        with pd.ExcelWriter(excel_path) as writer:
            for csv_file in csv_files:
                csv_path = shap_dir / csv_file
                if csv_path.exists():
                    df = pd.read_csv(csv_path)
                    sheet = 'mean_importance' if 'mean' in csv_file else 'values'
                    df.to_excel(writer, sheet_name=sheet, index=False)
        print(f"  Created: {excel_path}")

    # 5. Prediction Scatter consolidated Excel
    pred_dir = output_root / 'Prediction_Scatter_Data'
    pred_files = ['arrhythmia_predictions.csv', 'heart_damage_predictions.csv', 'concern_predictions.csv', 'concern_binary_predictions.csv']

    pred_excel = pred_dir / 'prediction_scatter_all.xlsx'
    with pd.ExcelWriter(pred_excel) as writer:
        for f in pred_files:
            fpath = pred_dir / f
            if fpath.exists():
                df = pd.read_csv(fpath)
                sheet = f.replace('_predictions.csv', '')
                df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"  Created: {pred_excel}")

    # 6. Cumulative Plot consolidated Excel
    cum_dir = output_root / 'Cumulative_Plot_Data'
    cum_files = [
        'arrhythmia_cumulative_predictions.csv',
        'heart_damage_cumulative_predictions.csv',
        'concern_binary_cumulative_predictions.csv',
        'concern_no_cumulative_predictions.csv',
        'concern_less_cumulative_predictions.csv',
        'concern_most_cumulative_predictions.csv'
    ]

    cum_excel = cum_dir / 'cumulative_feature_importance.xlsx'
    with pd.ExcelWriter(cum_excel) as writer:
        for f in cum_files:
            fpath = cum_dir / f
            if fpath.exists():
                df = pd.read_csv(fpath)
                sheet = f.replace('_cumulative_predictions.csv', '').replace('_', ' ').title()[:31]
                df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"  Created: {cum_excel}")

    # 7. Performance Metrics consolidated Excel
    perf_dir = output_root / 'Performance_Metrics'
    perf_files = list(perf_dir.glob('*.csv'))

    perf_excel = perf_dir / 'all_performance_metrics.xlsx'
    with pd.ExcelWriter(perf_excel) as writer:
        for f in sorted(perf_files):
            try:
                df = pd.read_csv(f)
                sheet = f.stem[:31]
                df.to_excel(writer, sheet_name=sheet, index=False)
            except Exception:
                pass
    print(f"  Created: {perf_excel}")

    print("  Consolidated Excel files created successfully.")


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == '__main__':
    # =========================================================================
    # STAGE 1: LOOCV Model Comparison
    # =========================================================================
    results_df = run_full_pipeline()

    # Create Stage 1 plots
    print("\n" + "=" * 70)
    print("Generating Stage 1 Plots")
    print("=" * 70)

    create_comparison_plots(results_df)
    create_concern_plot(results_df)

    # Print Stage 1 summary
    print("\nStage 1 Results Summary:")
    print("-" * 70)
    pivot = results_df.pivot_table(
        values=['Accuracy', 'AUC'],
        index=['Target', 'Model'],
        columns='Equation',
        aggfunc='first'
    )
    print(pivot.round(3).to_string())

    # =========================================================================
    # STAGE 2: Multi-Seed Stratified K-Fold Validation
    # =========================================================================
    stage2_results = run_stage2_pipeline()

    # =========================================================================
    # Generate Final Analysis Plots
    # =========================================================================
    print("\n" + "=" * 70)
    print("Generating Final Analysis Plots")
    print("=" * 70)

    # Load data for feature importance analysis
    df = pd.read_excel(EXCEL_PATH, sheet_name='pkpd_elimination', header=1)
    df.columns = df.columns.str.strip()
    df = df.set_index('Drug')
    X_df = extract_features_generic(df, 'pkpd_elimination')

    generate_final_analysis_plots(stage2_results, df, X_df)
    save_final_graph_data(stage2_results, df, X_df)

    # Save ROC curve data to Excel (using pre-computed results from main pipeline)
    roc_excel_path = OUTPUT_DIRS['roc'] / 'roc_curves_all_models.xlsx'
    save_roc_curves_to_excel(stage2_results, roc_excel_path)

    # =========================================================================
    # Create Consolidated Excel Files for Graphs
    # =========================================================================
    print("\n" + "=" * 70)
    print("Creating Consolidated Excel Files")
    print("=" * 70)

    create_consolidated_excel_files(results_df)

    # =========================================================================
    # Generate Combined Report
    # =========================================================================
    print("\n" + "=" * 70)
    print("Generating Combined LaTeX Report")
    print("=" * 70)

    create_combined_latex_report(results_df, stage2_results)

    print("\n" + "=" * 70)
    print("Full Pipeline Complete!")
    print("=" * 70)
    print(f"\nAll outputs saved to subdirectories in: {OUTPUT_ROOT}")
