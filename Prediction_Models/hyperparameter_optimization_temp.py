"""
Hyperparameter Optimization with Nested 5-Fold CV + GridSearchCV

This is a STANDALONE TEMPORARY script for testing hyperparameter optimization.
It does NOT modify any existing files. Delete this file if you don't want it.

Targets:
- arrhythmia_rf: RandomForest (baseline: accuracy=0.736, AUC=0.802)
- arrhythmia_xgb: XGBoost (baseline: accuracy=0.80)
- heart_damage: SVM RBF (baseline: accuracy=0.804, AUC=0.779)
- concern_binary: RandomForest (baseline: accuracy=0.736, AUC=0.747)

Strategy:
- Outer loop: Stratified 5-fold CV for unbiased performance estimation
- Inner loop: Stratified 5-fold CV for hyperparameter selection
- Multiple seeds (10) for stability

Usage:
    python hyperparameter_optimization_temp.py
    python hyperparameter_optimization_temp.py --quick
    python hyperparameter_optimization_temp.py --target arrhythmia_xgb
"""

import warnings
warnings.filterwarnings('ignore')

import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, List
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
COEFFICIENTS_FILE = PROJECT_ROOT / "EQN_Coefficients" / "all_equations_coefficients.xlsx"

OUTPUT_DIR = PROJECT_ROOT / "Output" / "Hyperparameter_Optimization_Temp"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# TARGET CONFIGURATIONS
# =============================================================================

TARGET_CONFIG = {
    'arrhythmia_rf': {
        'target_col': 'Arrhythmia',
        'model_type': 'RandomForest',
        'baseline_params': {
            'n_estimators': 150, 'max_depth': 5, 'class_weight': 'balanced',
            'random_state': 42, 'n_jobs': -1
        },
        'expected': {'accuracy': 0.736, 'auc': 0.802},
    },
    'arrhythmia_xgb': {
        'target_col': 'Arrhythmia',
        'model_type': 'XGBoost',
        'baseline_params': {
            'n_estimators': 150, 'max_depth': 4, 'learning_rate': 0.08,
            'subsample': 0.9, 'objective': 'binary:logistic',
            'eval_metric': 'logloss', 'tree_method': 'hist',
            'random_state': 42, 'n_jobs': -1
            # scale_pos_weight computed dynamically
        },
        'use_scale_pos_weight': True,
        'expected': {'accuracy': 0.80, 'auc': 0.83},
    },
    'heart_damage': {
        'target_col': 'heart_damage',
        'model_type': 'SVM_RBF',
        'baseline_params': {
            'kernel': 'rbf', 'C': 1.0, 'gamma': 'scale',
            'class_weight': 'balanced', 'probability': True, 'random_state': 42
        },
        'expected': {'accuracy': 0.804, 'auc': 0.779},
    },
    'concern_binary': {
        'target_col': 'Concern',
        'model_type': 'RandomForest',
        'is_binary_concern': True,
        'baseline_params': {
            'n_estimators': 150, 'max_depth': 5, 'class_weight': 'balanced',
            'random_state': 42, 'n_jobs': -1
        },
        'expected': {'accuracy': 0.736, 'auc': 0.747},
    },
}

# =============================================================================
# PARAMETER GRIDS
# =============================================================================

PARAM_GRIDS_FULL = {
    'RandomForest': {
        'clf__n_estimators': [100, 150, 200, 250],
        'clf__max_depth': [3, 5, 7, 10, None],
        'clf__min_samples_split': [2, 5, 10],
        'clf__min_samples_leaf': [1, 2, 4],
        'clf__class_weight': ['balanced', 'balanced_subsample'],
    },
    'XGBoost': {
        'clf__n_estimators': [100, 150, 200],
        'clf__max_depth': [3, 4, 5, 6],
        'clf__learning_rate': [0.05, 0.08, 0.1, 0.15],
        'clf__subsample': [0.8, 0.9, 1.0],
        'clf__colsample_bytree': [0.8, 0.9, 1.0],
        'clf__min_child_weight': [1, 3, 5],
    },
    'SVM_RBF': {
        'clf__C': [0.1, 0.5, 1.0, 5.0, 10.0],
        'clf__gamma': ['scale', 'auto', 0.001, 0.01, 0.1],
        'clf__class_weight': ['balanced', None],
    },
}

PARAM_GRIDS_QUICK = {
    'RandomForest': {
        'clf__n_estimators': [100, 150, 200],
        'clf__max_depth': [3, 5, 7, None],
        'clf__min_samples_split': [2, 5],
        'clf__class_weight': ['balanced', 'balanced_subsample'],
    },
    'XGBoost': {
        'clf__n_estimators': [100, 150, 200],
        'clf__max_depth': [3, 4, 5],
        'clf__learning_rate': [0.05, 0.08, 0.1],
        'clf__subsample': [0.8, 0.9, 1.0],
    },
    'SVM_RBF': {
        'clf__C': [0.1, 1.0, 10.0],
        'clf__gamma': ['scale', 0.01, 0.1],
        'clf__class_weight': ['balanced', None],
    },
}

# =============================================================================
# DATA LOADING
# =============================================================================

def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load PKPD elimination coefficient data."""
    print(f"\nLoading data from: {COEFFICIENTS_FILE}")

    df = pd.read_excel(COEFFICIENTS_FILE, sheet_name='pkpd_elimination', header=1)
    df.columns = df.columns.str.strip()

    if 'Drug' in df.columns:
        df = df.set_index('Drug')

    excluded = ['DMSO', 'Troglitazone', 'Troglitarazine']
    df = df.drop([d for d in excluded if d in df.index], errors='ignore')

    param_names = ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim']
    contractility_cols = [p for p in param_names if p in df.columns]
    o2_cols = [f"{p}.1" for p in param_names if f"{p}.1" in df.columns]

    X = df[contractility_cols + o2_cols].copy()

    rename_map = {col: f"{col}_Contractility" for col in contractility_cols}
    rename_map.update({col: f"{col.replace('.1', '')}_O2" for col in o2_cols})
    X = X.rename(columns=rename_map)

    print(f"Loaded {len(X)} drugs with {len(X.columns)} features")
    return X, df


def get_target(df: pd.DataFrame, target_name: str) -> np.ndarray:
    """Get target labels for a given target configuration."""
    config = TARGET_CONFIG[target_name]
    col = config['target_col']
    y = df[col].copy()

    if config.get('is_binary_concern'):
        # Binary: 'most' vs 'no'+'less'
        if y.dtype == object:
            y = y.str.lower().map({'most': 1, 'less': 0, 'no': 0})
        else:
            y = y.map({'most': 1, 'less': 0, 'no': 0})
    else:
        # Standard binary (handle both string and boolean)
        if y.dtype == bool:
            y = y.astype(int)
        else:
            mapping = {'true': 1, 'false': 0, True: 1, False: 0}
            y = y.replace(mapping)
            if y.dtype == object:
                y = y.str.lower().map({'true': 1, 'false': 0})

    return y.astype(int).values


# =============================================================================
# MODEL FACTORIES
# =============================================================================

def create_classifier(model_type: str, params: Dict = None, y: np.ndarray = None):
    """Create a classifier of the specified type."""
    params = params or {}

    if model_type == 'RandomForest':
        return RandomForestClassifier(**params)
    elif model_type == 'XGBoost':
        # Compute scale_pos_weight from y if provided (for binary classification)
        if y is not None and 'scale_pos_weight' not in params:
            n_neg = (y == 0).sum()
            n_pos = (y == 1).sum()
            if n_pos > 0:
                params = params.copy()
                params['scale_pos_weight'] = n_neg / n_pos
        return XGBClassifier(**params)
    elif model_type == 'SVM_RBF':
        return SVC(**params)
    raise ValueError(f"Unknown model type: {model_type}")


def create_pipeline(target_name: str, use_baseline: bool = True, y: np.ndarray = None) -> Pipeline:
    """Create sklearn pipeline for target."""
    config = TARGET_CONFIG[target_name]
    model_type = config['model_type']

    if use_baseline:
        clf = create_classifier(model_type, config['baseline_params'], y=y)
    else:
        # Create with minimal params for grid search
        if model_type == 'RandomForest':
            clf = RandomForestClassifier(random_state=42, n_jobs=-1)
        elif model_type == 'XGBoost':
            # Compute scale_pos_weight for XGBoost
            params = {'eval_metric': 'logloss', 'objective': 'binary:logistic',
                      'tree_method': 'hist', 'random_state': 42, 'n_jobs': -1}
            if y is not None:
                n_neg = (y == 0).sum()
                n_pos = (y == 1).sum()
                if n_pos > 0:
                    params['scale_pos_weight'] = n_neg / n_pos
            clf = XGBClassifier(**params)
        elif model_type == 'SVM_RBF':
            clf = SVC(kernel='rbf', probability=True, random_state=42)

    return Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('clf', clf)
    ])


# =============================================================================
# CROSS-VALIDATION
# =============================================================================

def run_baseline_cv(X_df: pd.DataFrame, y: np.ndarray, target_name: str,
                    n_folds: int = 5, n_seeds: int = 10) -> Dict[str, Any]:
    """Run stratified K-fold CV with baseline parameters across multiple seeds.

    Matches the exact methodology from loocv_model_comparison.py:
    - Manual NaN imputation using training set means
    - Pipeline with scaler + model (no imputer)
    """
    all_acc, all_auc = [], []

    config = TARGET_CONFIG[target_name]
    print(f"\nBaseline {n_folds}-fold CV (x{n_seeds} seeds) for: {target_name} [{config['model_type']}]")

    for seed in range(n_seeds):
        cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
        y_true_all, y_prob_all, y_pred_all = [], [], []

        for train_idx, test_idx in cv.split(X_df, y):
            X_train = X_df.iloc[train_idx].copy()
            X_test = X_df.iloc[test_idx].copy()
            y_train, y_test = y[train_idx], y[test_idx]

            # Manual NaN handling (matching original code)
            train_means = X_train.mean()
            X_train = X_train.fillna(train_means)
            X_test = X_test.fillna(train_means)

            # Create model with class balancing
            clf = create_classifier(config['model_type'], config['baseline_params'], y=y)

            # Pipeline without imputer (already handled NaN)
            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('model', clf)
            ])
            pipeline.fit(X_train, y_train)

            y_pred_all.extend(pipeline.predict(X_test))
            y_prob_all.extend(pipeline.predict_proba(X_test)[:, 1])
            y_true_all.extend(y_test)

        all_acc.append(accuracy_score(y_true_all, y_pred_all))
        try:
            all_auc.append(roc_auc_score(y_true_all, y_prob_all))
        except ValueError:
            all_auc.append(np.nan)

    mean_acc, std_acc = np.mean(all_acc), np.std(all_acc)
    mean_auc, std_auc = np.nanmean(all_auc), np.nanstd(all_auc)

    expected = config['expected']
    print(f"  Result:   Accuracy = {mean_acc:.3f} +/- {std_acc:.3f}, AUC = {mean_auc:.3f} +/- {std_auc:.3f}")
    print(f"  Expected: Accuracy = {expected['accuracy']:.3f}, AUC = {expected['auc']:.3f}")

    return {
        'accuracy': mean_acc, 'accuracy_std': std_acc,
        'auc': mean_auc, 'auc_std': std_auc,
    }


def run_nested_cv(X_df: pd.DataFrame, y: np.ndarray, target_name: str,
                  param_grid: Dict, outer_folds: int = 5, inner_folds: int = 5,
                  n_seeds: int = 10) -> Dict[str, Any]:
    """Nested CV with GridSearchCV for hyperparameter optimization.

    Uses same NaN handling as baseline for fair comparison.
    """
    all_acc, all_auc, all_params = [], [], []

    config = TARGET_CONFIG[target_name]
    grid_size = np.prod([len(v) for v in param_grid.values()])

    print(f"\n{'='*60}")
    print(f"Nested {outer_folds}-fold CV (x{n_seeds} seeds): {target_name} [{config['model_type']}]")
    print(f"{'='*60}")
    print(f"Grid size: {grid_size} combinations")

    for seed in range(n_seeds):
        outer_cv = StratifiedKFold(n_splits=outer_folds, shuffle=True, random_state=seed)
        inner_cv = StratifiedKFold(n_splits=inner_folds, shuffle=True, random_state=seed)

        y_true_all, y_prob_all, y_pred_all = [], [], []
        seed_params = []

        for train_idx, test_idx in outer_cv.split(X_df, y):
            X_train = X_df.iloc[train_idx].copy()
            X_test = X_df.iloc[test_idx].copy()
            y_train, y_test = y[train_idx], y[test_idx]

            # Manual NaN handling
            train_means = X_train.mean()
            X_train = X_train.fillna(train_means)
            X_test = X_test.fillna(train_means)

            # Create model for grid search
            model_type = config['model_type']
            if model_type == 'RandomForest':
                clf = RandomForestClassifier(random_state=42, n_jobs=-1)
            elif model_type == 'XGBoost':
                params = {'eval_metric': 'logloss', 'objective': 'binary:logistic',
                          'tree_method': 'hist', 'random_state': 42, 'n_jobs': -1}
                n_neg, n_pos = (y == 0).sum(), (y == 1).sum()
                if n_pos > 0:
                    params['scale_pos_weight'] = n_neg / n_pos
                clf = XGBClassifier(**params)
            elif model_type == 'SVM_RBF':
                clf = SVC(kernel='rbf', probability=True, random_state=42)

            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('clf', clf)
            ])

            grid_search = GridSearchCV(
                pipeline, param_grid, cv=inner_cv, scoring='roc_auc',
                n_jobs=-1, refit=True
            )
            grid_search.fit(X_train, y_train)

            seed_params.append(grid_search.best_params_)
            y_pred_all.extend(grid_search.predict(X_test))
            y_prob_all.extend(grid_search.predict_proba(X_test)[:, 1])
            y_true_all.extend(y_test)

        acc = accuracy_score(y_true_all, y_pred_all)
        try:
            auc = roc_auc_score(y_true_all, y_prob_all)
        except ValueError:
            auc = np.nan

        all_acc.append(acc)
        all_auc.append(auc)
        all_params.append(seed_params)

        if (seed + 1) % 3 == 0 or seed == 0:
            print(f"  Seed {seed + 1}/{n_seeds}: Acc = {acc:.3f}, AUC = {auc:.3f}")

    mean_acc, std_acc = np.mean(all_acc), np.std(all_acc)
    mean_auc, std_auc = np.nanmean(all_auc), np.nanstd(all_auc)

    # Find consensus params
    flat_params = [str(sorted(p.items())) for sp in all_params for p in sp]
    most_common_str, count = Counter(flat_params).most_common(1)[0]
    consensus = None
    for sp in all_params:
        for p in sp:
            if str(sorted(p.items())) == most_common_str:
                consensus = p
                break
        if consensus:
            break

    return {
        'accuracy': mean_acc, 'accuracy_std': std_acc,
        'auc': mean_auc, 'auc_std': std_auc,
        'consensus_params': consensus,
        'consensus_count': count,
        'total_folds': n_seeds * outer_folds,
    }


# =============================================================================
# MAIN
# =============================================================================

def run_optimization(quick_mode: bool = False, target_filter: str = None):
    """Run full hyperparameter optimization."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    X_df, df_raw = load_data()
    X = X_df.values

    grids = PARAM_GRIDS_QUICK if quick_mode else PARAM_GRIDS_FULL
    print(f"\n*** {'QUICK' if quick_mode else 'FULL'} mode ***")

    targets = list(TARGET_CONFIG.keys())
    if target_filter:
        targets = [t for t in targets if t == target_filter]

    results = {}
    rows = []

    for target_name in targets:
        config = TARGET_CONFIG[target_name]
        model_type = config['model_type']

        print(f"\n{'#'*60}")
        print(f"# {target_name.upper()} ({model_type})")
        print(f"{'#'*60}")

        y = get_target(df_raw, target_name)
        print(f"Class distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

        baseline = run_baseline_cv(X_df, y, target_name)
        optimized = run_nested_cv(X_df, y, target_name, grids[model_type])

        results[target_name] = {'baseline': baseline, 'optimized': optimized}

        # Print comparison
        print(f"\n{'='*60}")
        print(f"COMPARISON: {target_name}")
        print(f"{'='*60}")
        print(f"{'Metric':<12} {'Baseline':>18} {'Optimized':>18} {'Change':>10}")
        print("-" * 60)

        for metric in ['accuracy', 'auc']:
            bv, bs = baseline[metric], baseline[f'{metric}_std']
            ov, os = optimized[metric], optimized[f'{metric}_std']
            ch = ov - bv
            print(f"{metric:<12} {bv:>7.3f} +/- {bs:.3f} {ov:>7.3f} +/- {os:.3f} {'+' if ch >= 0 else ''}{ch:>8.3f}")

        print(f"\nBest params ({optimized['consensus_count']}/{optimized['total_folds']} folds):")
        for k, v in optimized['consensus_params'].items():
            print(f"  {k.replace('clf__', '')}: {v}")

        rows.append({
            'target': target_name,
            'model': model_type,
            'baseline_acc': baseline['accuracy'],
            'baseline_auc': baseline['auc'],
            'optimized_acc': optimized['accuracy'],
            'optimized_auc': optimized['auc'],
            'acc_change': optimized['accuracy'] - baseline['accuracy'],
            'auc_change': optimized['auc'] - baseline['auc'],
            'best_params': str(optimized['consensus_params']),
        })

    # Save
    pd.DataFrame(rows).to_csv(OUTPUT_DIR / f"optimization_{timestamp}.csv", index=False)
    print(f"\n\nResults saved to: {OUTPUT_DIR}")

    # Print recommended params
    print("\n" + "=" * 60)
    print("RECOMMENDED PARAMETERS")
    print("=" * 60)

    for name, res in results.items():
        config = TARGET_CONFIG[name]
        params = res['optimized']['consensus_params']
        print(f"\n# {name} ({config['model_type']})")
        print(f"# Baseline: Acc={res['baseline']['accuracy']:.3f}, AUC={res['baseline']['auc']:.3f}")
        print(f"# Optimized: Acc={res['optimized']['accuracy']:.3f}, AUC={res['optimized']['auc']:.3f}")
        print("{")
        for k, v in params.items():
            print(f"    '{k.replace('clf__', '')}': {repr(v)},")
        print("}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--target', choices=list(TARGET_CONFIG.keys()))
    args = parser.parse_args()

    run_optimization(quick_mode=args.quick, target_filter=args.target)
    print("\nDone!")
