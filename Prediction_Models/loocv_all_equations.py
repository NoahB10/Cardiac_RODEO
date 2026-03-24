"""LOOCV analysis across ALL 12 equation types.

Replicates the exact LOOCV pipeline from loocv_model_comparison.py but
runs all 12 equations instead of just 3. Saves to a separate output folder.

Output: Output/All_Equations_LOOCV/
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
from sklearn.base import clone
from xgboost import XGBClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
EXCEL_PATH = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / 'All_Equations_LOOCV'

# ── All 12 equations with their parameter names ────────────────────────────────
EQUATION_PARAMS = {
    'dual_exponential': ['R0', 'A_benefit', 'A_tox', 'kb', 'kt', 'tau_b', 'tau_t', 'nb', 'nt', 'mb', 'mt'],
    'bivariate_gaussian': ['R0', 'A1', 'A2', 'muC1', 'muT1', 'sigC1', 'sigT1', 'rho1', 'muC2', 'muT2', 'sigC2', 'sigT2', 'rho2'],
    'gaussian_hill_hybrid': ['R0', 'Emax', 'mu_c', 'sigma_c', 'tau', 'm', 'E_tox', 'n', 'TC50_norm', 'tau_tox'],
    'modified_hill_hormesis': ['R0', 'E_benefit', 'E_tox', 'EC50_b_norm', 'TC50_norm', 'nb', 'nt', 'tau_b', 'tau_t'],
    'gaussian_ridge': ['R0', 'A', 'B', 'mu_c', 'sigma_c', 'mu_tox', 'sigma_tox', 'kappa', 'tau', 'm', 'lam'],
    'adaptive_response': ['R0', 'Emax', 'EC50_norm', 'n', 'tau_onset', 'tau_adapt'],
    'biphasic_response': ['R0', 'E_stim', 'E_inhib', 'EC50_stim_norm', 'IC50_norm', 'n1', 'n2', 'tau_stim', 'tau_inhib'],
    'cumulative_exposure': ['R0', 'E_tox', 'alpha', 'TC50_norm', 'k_elim'],
    'recovery_model': ['R0', 'E_damage', 'k_damage', 'k_recovery'],
    'modified_hill_simple': ['R0', 'Emax', 'kappa', 'tau', 'n', 'm'],
    'pkpd_elimination': ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim'],
    'hormesis_v0': ['R0', 'E_benefit', 'E_tox', 'EC50_b_norm', 'TC50_norm', 'nb', 'nt', 'tau_b', 'tau_t'],
}

TARGETS = ['Arrhythmia', 'heart_damage', 'Concern_Binary']


# ── Model definitions (identical to loocv_model_comparison.py) ─────────────────
def get_models(scale_pos_weight=1.0):
    return {
        'XGBoost': XGBClassifier(
            n_estimators=150, max_depth=4, learning_rate=0.08,
            subsample=0.9, scale_pos_weight=scale_pos_weight,
            objective='binary:logistic', eval_metric='logloss',
            random_state=42, n_jobs=-1, tree_method='hist'
        ),
        'SVM_RBF': SVC(
            kernel='rbf', C=1.0, gamma='scale',
            class_weight='balanced', probability=True, random_state=42
        ),
        'RandomForest': RandomForestClassifier(
            n_estimators=150, max_depth=5,
            class_weight='balanced', random_state=42, n_jobs=-1
        ),
        'GaussianNB': GaussianNB()
    }


# ── Feature extraction (identical logic) ───────────────────────────────────────
def extract_features_generic(df, equation_name):
    param_names = EQUATION_PARAMS[equation_name]
    features = []
    feature_names = []

    for param in param_names:
        features.append(df[param].values if param in df.columns
                        else np.full(len(df), np.nan))
        feature_names.append(f'{param}_Contractility')

    for param in param_names:
        param_o2 = f'{param}.1'
        features.append(df[param_o2].values if param_o2 in df.columns
                        else np.full(len(df), np.nan))
        feature_names.append(f'{param}_O2')

    return pd.DataFrame(np.column_stack(features),
                        columns=feature_names, index=df.index)


def preprocess_targets(df, target_column):
    if target_column == 'Concern_Binary':
        target_series = df['Concern'].copy()
    else:
        target_series = df[target_column].copy()

    target_series = target_series.astype(str).str.strip().str.lower()

    if target_column in ['Arrhythmia', 'heart_damage']:
        mapping = {'true': 1, 'false': 0, '1': 1, '0': 0}
    elif target_column == 'Concern_Binary':
        mapping = {'most': 1, 'less': 0, 'no': 0, '2': 1, '1': 0, '0': 0}
    else:
        return pd.to_numeric(target_series, errors='coerce')

    return target_series.map(mapping)


# ── LOOCV (identical logic) ────────────────────────────────────────────────────
def run_loocv(X, y, model):
    loo = LeaveOneOut()
    y_true, y_pred, y_proba = [], [], []

    base_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', model)
    ])

    if isinstance(X, np.ndarray):
        X = pd.DataFrame(X)

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        train_means = X_train.mean()
        X_train = X_train.fillna(train_means)
        X_test = X_test.fillna(train_means)

        pipeline_fold = clone(base_pipeline)
        pipeline_fold.fit(X_train, y_train)

        y_pred.append(pipeline_fold.predict(X_test)[0])
        y_true.append(y_test[0])

        model_step = pipeline_fold.named_steps['model']
        is_svm = type(model_step).__name__ == 'SVC'

        if is_svm and hasattr(pipeline_fold, 'decision_function'):
            y_proba.append(pipeline_fold.decision_function(X_test)[0])
        elif hasattr(pipeline_fold, 'predict_proba'):
            y_proba.append(pipeline_fold.predict_proba(X_test)[0])

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_proba = np.array(y_proba)

    accuracy = accuracy_score(y_true, y_pred)

    used_svm_decision = (y_proba.ndim == 1) or \
        (y_proba.ndim == 2 and y_proba.shape[1] != len(np.unique(y_true)))

    try:
        if used_svm_decision or y_proba.ndim == 1:
            auc = roc_auc_score(y_true, y_proba)
        else:
            auc = roc_auc_score(y_true, y_proba[:, 1])
    except (ValueError, IndexError):
        auc = np.nan

    return {
        'accuracy': accuracy,
        'auc': auc,
        'y_true': y_true,
        'y_pred': y_pred,
        'confusion_matrix': confusion_matrix(y_true, y_pred)
    }


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("LOOCV — All 12 Equations")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    xl = pd.ExcelFile(EXCEL_PATH)

    for equation_name in EQUATION_PARAMS:
        print(f"\n{'='*70}")
        print(f"  {equation_name}  ({len(EQUATION_PARAMS[equation_name])} params -> "
              f"{2*len(EQUATION_PARAMS[equation_name])} features)")
        print("=" * 70)

        df = pd.read_excel(xl, sheet_name=equation_name, header=1)
        df.columns = df.columns.str.strip()
        df = df.set_index('Drug')

        X_df = extract_features_generic(df, equation_name)
        X = X_df.values

        for target in TARGETS:
            y = preprocess_targets(df, target)
            valid_mask = ~y.isna()
            X_valid = X[valid_mask]
            y_valid = y[valid_mask].values.astype(int)

            n_neg = (y_valid == 0).sum()
            n_pos = (y_valid == 1).sum()
            scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

            print(f"\n  {target}: {len(y_valid)} samples, "
                  f"pos={n_pos}, neg={n_neg}")

            for model_name, model in get_models(scale_pos_weight).items():
                print(f"    {model_name}...", end=" ")
                try:
                    result = run_loocv(X_valid, y_valid, model)
                    results.append({
                        'Equation': equation_name,
                        'Target': target,
                        'Model': model_name,
                        'Accuracy': result['accuracy'],
                        'AUC': result['auc'],
                        'N_samples': len(y_valid),
                        'N_features': X_df.shape[1],
                        'Confusion_Matrix': result['confusion_matrix'].tolist()
                    })
                    print(f"Acc={result['accuracy']:.3f}  AUC={result['auc']:.3f}")
                except Exception as e:
                    print(f"ERROR: {e}")
                    results.append({
                        'Equation': equation_name,
                        'Target': target,
                        'Model': model_name,
                        'Accuracy': np.nan,
                        'AUC': np.nan,
                        'N_samples': len(y_valid),
                        'N_features': X_df.shape[1],
                        'Confusion_Matrix': None
                    })

    # Save CSV
    results_df = pd.DataFrame(results)
    csv_path = OUTPUT_DIR / 'loocv_all_equations.csv'
    results_df.to_csv(csv_path, index=False)
    print(f"\n\nCSV saved: {csv_path}")

    # Save Excel with summary sheets
    xlsx_path = OUTPUT_DIR / 'loocv_all_equations.xlsx'
    with pd.ExcelWriter(str(xlsx_path), engine='openpyxl') as writer:
        results_df.to_excel(writer, sheet_name='All_Results', index=False)

        # Best model per equation+target
        idx = results_df.groupby(['Equation', 'Target'])['AUC'].idxmax()
        best_df = results_df.loc[idx].reset_index(drop=True)
        best_df.to_excel(writer, sheet_name='Best_Per_Equation_Target', index=False)

        # Summary pivot: best AUC per equation × target
        pivot = best_df.pivot_table(index='Equation', columns='Target',
                                    values='AUC', aggfunc='max')
        pivot['Mean_AUC'] = pivot.mean(axis=1)
        pivot = pivot.sort_values('Mean_AUC', ascending=False)
        pivot.to_excel(writer, sheet_name='AUC_Summary')

    print(f"Excel saved: {xlsx_path}")
    print(f"\nTotal combinations: {len(results_df)} "
          f"(12 equations × {len(TARGETS)} targets × 4 models)")

    return results_df


if __name__ == '__main__':
    main()
