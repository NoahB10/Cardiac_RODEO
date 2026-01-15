"""
Comprehensive Analysis: ADMET-AI vs SwissADME for Cardiac RODEO Drugs
Target: Heart Damage

Sections:
1. Replicate literature results from Mukherjee et al. 2025 (train on DICTrank)
2. Drug database with SMILES and sources
3. DICTrank-trained model predictions on 25 drugs
4. LOOCV models trained on 25 drugs with full metrics
5. LaTeX report generation
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn import metrics
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.metrics import roc_curve, auc, accuracy_score, confusion_matrix, ConfusionMatrixDisplay
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import zipfile
import shutil
import subprocess
import sys
import warnings
warnings.filterwarnings('ignore')

from rdkit import Chem

# chemprop expects numpy.VisibleDeprecationWarning (removed in numpy>=2.0)
if not hasattr(np, "VisibleDeprecationWarning"):
    class VisibleDeprecationWarning(UserWarning):
        pass
    np.VisibleDeprecationWarning = VisibleDeprecationWarning

try:
    from chemprop.data.utils import get_data, split_data
    CHEMPROP_AVAILABLE = True
except Exception:
    CHEMPROP_AVAILABLE = False

def plot_confusion_matrix_with_percent(cm, labels, ax, title):
    cm = np.asarray(cm, dtype=float)
    row_sums = cm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    row_pct = cm / row_sums

    im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel('Predicted', fontsize=10)
    ax.set_ylabel('Actual', fontsize=10)

    max_val = cm.max() if cm.size else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            count = int(cm[i, j])
            pct = row_pct[i, j] * 100
            color = 'white' if max_val > 0 and cm[i, j] > max_val / 2 else 'black'
            ax.text(j, i, f"{count}\n{pct:.1f}%",
                    ha='center', va='center', color=color, fontsize=9)

    return im

def bootstrap_roc_stats(y_true, y_prob, n_boot=200, seed=42):
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    n = len(y_true)
    mean_fpr = np.linspace(0, 1, 100)
    tprs = []
    aucs = []

    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        fpr, tpr, _ = roc_curve(y_true[idx], y_prob[idx])
        tpr_interp = np.interp(mean_fpr, fpr, tpr)
        tpr_interp[0] = 0.0
        tprs.append(tpr_interp)
        aucs.append(auc(mean_fpr, tpr_interp))

    if not tprs:
        return mean_fpr, None, None, np.nan, np.nan

    tprs = np.array(tprs)
    mean_tpr = tprs.mean(axis=0)
    std_tpr = tprs.std(axis=0)
    return mean_fpr, mean_tpr, std_tpr, float(np.mean(aucs)), float(np.std(aucs))

def plot_roc_with_std(ax, mean_fpr, mean_tpr, std_tpr, color, label):
    if mean_tpr is None:
        return
    ax.plot(mean_fpr, mean_tpr, color=color, lw=2, label=label)
    ax.fill_between(
        mean_fpr,
        np.maximum(mean_tpr - std_tpr, 0),
        np.minimum(mean_tpr + std_tpr, 1),
        color=color, alpha=0.2
    )

def clamp_auc_std(auc_mean, auc_std):
    if auc_mean is None or auc_std is None:
        return auc_std
    if pd.isna(auc_mean) or pd.isna(auc_std):
        return auc_std
    max_std = min(auc_mean, 1 - auc_mean)
    return min(auc_std, max_std)

def dictrank_to_binary_labels(y_series):
    return np.asarray([0 if str(y).strip().lower() == "no" else 1 for y in y_series])

def build_scaffold_splits(ad_data: pd.DataFrame, num_folds: int = 10):
    if not CHEMPROP_AVAILABLE:
        raise RuntimeError("chemprop not available for scaffold splits.")
    adxdata = get_data(
        str(DATA_DIR / "ADMET-AI_data.csv"),
        smiles_columns=["Standardized_SMILES"],
        target_columns=["DICTrank"],
    )
    scaf_splits = {}
    for seed in range(num_folds):
        train, _, test = split_data(
            data=adxdata,
            split_type="scaffold_balanced",
            num_folds=num_folds,
            seed=seed,
            sizes=(0.80, 0.0, 0.20),
        )
        train_idx = []
        test_idx = []
        for s in train.smiles():
            smi = s[0]
            idx = ad_data[ad_data["Standardized_SMILES"] == smi].index[0]
            train_idx.append(idx)
        for s in test.smiles():
            smi = s[0]
            idx = ad_data[ad_data["Standardized_SMILES"] == smi].index[0]
            test_idx.append(idx)
        scaf_splits[seed] = {"train": train_idx, "test": test_idx}
    return scaf_splits

def compute_dictrank_cv_confusion(X: pd.DataFrame, y_binary: np.ndarray, scaf_splits: dict):
    y_true_all = []
    y_pred_all = []
    for split in scaf_splits.values():
        train_idx = split["train"]
        test_idx = split["test"]
        X_train = X.iloc[train_idx]
        y_train = y_binary[train_idx]
        X_test = X.iloc[test_idx]
        y_test = y_binary[test_idx]
        model = GradientBoostingClassifier(
            n_estimators=500,
            learning_rate=0.1,
            max_depth=12,
            random_state=0,
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        y_true_all.append(y_test)
        y_pred_all.append(preds)
    y_true_all = np.concatenate(y_true_all)
    y_pred_all = np.concatenate(y_pred_all)
    return confusion_matrix(y_true_all, y_pred_all)

try:
    import shap
    SHAP_AVAILABLE = True
except Exception:
    SHAP_AVAILABLE = False

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ADMETHYST_MAIN_DIR = PROJECT_ROOT / "ADMEThyst-main"

DATA_DIR = ADMETHYST_MAIN_DIR / "data"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
LATEX_OUTPUT_DIR = PROJECT_ROOT / "Output" / "LaTeX_Reports"
FIGURES_DIR = OUTPUT_DIR / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LATEX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

FORCE_RETRAIN_DICTRANK = True
RETRAIN_SCRIPT = SCRIPT_DIR / "retrain_dictrank_models.py"
if FORCE_RETRAIN_DICTRANK:
    print("Retraining DICTrank models (forced, no cached results)...")
    subprocess.run([sys.executable, str(RETRAIN_SCRIPT)], check=True)

CLEANED_DATA_DIR = PROJECT_ROOT / "Cleaned_Data"
# Use SMILES from Cleaned_Data as the source of truth (user can edit this file)
SMILES_PATH = CLEANED_DATA_DIR / "drug_smiles.csv"
if not SMILES_PATH.exists():
    # Fallback to old location if present
    fallback = OUTPUT_DIR / "cardiac_rodeo_drugs_smiles.csv"
    if fallback.exists():
        SMILES_PATH = fallback
        print(f"Warning: Using SMILES from {fallback}. Consider moving to {CLEANED_DATA_DIR / 'drug_smiles.csv'}")
    else:
        raise FileNotFoundError(
            "Missing drug_smiles.csv. "
            f"Expected at {CLEANED_DATA_DIR / 'drug_smiles.csv'}"
        )

print("="*80)
print("COMPREHENSIVE ANALYSIS: ADMET-AI vs SwissADME")
print("Predicting Heart Damage in 25 Cardiac RODEO Drugs")
print("="*80)

# =============================================================================
# SECTION 1: REPLICATE LITERATURE RESULTS (Train on DICTrank)
# =============================================================================
print("\n" + "="*80)
print("SECTION 1: Replicating Literature Benchmark (Train on DICTrank)")
print("="*80)

# Prefer retrained scaffold-split metrics if present
metrics_path = OUTPUT_DIR / 'dictrank_retrain_metrics.csv'
roc_pdf = OUTPUT_DIR / 'dictrank_retrain_roc.pdf'

if not metrics_path.exists():
    raise FileNotFoundError(
        f"Missing DICTrank retrain metrics at {metrics_path}. "
        "Run retrain_dictrank_models.py first."
    )
metrics_df = pd.read_csv(metrics_path)
paper_results = {}
for _, row in metrics_df.iterrows():
    paper_results[row['Model']] = {
        'ROC_AUC': float(row['ROC_AUC_Mean']),
        'PR_AUC': float(row['PR_AUC_Mean']),
        'ACC': float(row['Accuracy_Mean']),
    }
print("\nLoaded DICTrank retrain metrics:")
for model in paper_results:
    print(f"  {model}: ROC AUC = {paper_results[model]['ROC_AUC']:.3f}, "
          f"PR AUC = {paper_results[model]['PR_AUC']:.3f}, "
          f"Acc = {paper_results[model]['ACC']:.3f}")

if roc_pdf.exists():
    shutil.copy2(roc_pdf, FIGURES_DIR / 'dictrank_retrain_roc.pdf')

dictrank_train_confusion = None
if CHEMPROP_AVAILABLE:
    try:
        ad_data = pd.read_csv(DATA_DIR / "ADMET-AI_data.csv")
        ad_X = pd.read_csv(DATA_DIR / "ADMET-AI_Xvals.csv", index_col=0)
        ad_y = pd.read_csv(DATA_DIR / "ADMET-AI_yvals.csv", index_col=0)
        swiss_X = pd.read_csv(DATA_DIR / "SwissADME_Xvals.csv", index_col=0)
        swiss_y = pd.read_csv(DATA_DIR / "SwissADME_yvals.csv", index_col=0)

        scaf_splits = build_scaffold_splits(ad_data, num_folds=10)
        ad_y_bin = dictrank_to_binary_labels(ad_y["DICT _ Concern"])
        swiss_y_bin = dictrank_to_binary_labels(swiss_y["DICT _ Concern"])

        dictrank_train_confusion = {
            "ADMET-AI": compute_dictrank_cv_confusion(ad_X, ad_y_bin, scaf_splits),
            "SwissADME": compute_dictrank_cv_confusion(swiss_X, swiss_y_bin, scaf_splits),
        }

        fig, axes = plt.subplots(1, 2, figsize=(9, 4))
        for ax, model in zip(axes, ["ADMET-AI", "SwissADME"]):
            plot_confusion_matrix_with_percent(
                dictrank_train_confusion[model], ["No", "Yes"], ax,
                f"DICTrank Training: {model}"
            )
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "dictrank_training_confusion.pdf", bbox_inches='tight')
        plt.savefig(OUTPUT_DIR / "DICTrank_Training_Confusion.png", dpi=300, bbox_inches='tight')
        plt.close()
    except Exception as exc:
        print(f"Warning: Could not compute DICTrank training confusion matrices: {exc}")
        dictrank_train_confusion = None
else:
    print("Warning: chemprop not available; skipping DICTrank training confusion matrices.")

pr_fig = FIGURES_DIR / "dictrank_retrain_pr.pdf"
if pr_fig.exists():
    pr_fig.unlink()

# =============================================================================
# SECTION 2: LOAD CARDIAC RODEO DATA
# =============================================================================
print("\n" + "="*80)
print("SECTION 2: Drug Database")
print("="*80)

drugs_df = pd.read_csv(SMILES_PATH)
drug_names = drugs_df['Drug'].tolist()

true_labels = pd.read_csv(CLEANED_DATA_DIR / 'drug_classification.csv')
retrain_preds_path = OUTPUT_DIR / 'dictrank_retrain_predictions_25.csv'
if not retrain_preds_path.exists():
    raise FileNotFoundError(
        f"Missing retrained predictions at {retrain_preds_path}. "
        "Run retrain_dictrank_models.py first."
    )
retrain_preds = pd.read_csv(retrain_preds_path)
admet_preds = retrain_preds[['Drug', 'ADMET_AI_Prob']].rename(
    columns={'ADMET_AI_Prob': 'DICT_Concern_Prob'}
)
swiss_preds = retrain_preds[['Drug', 'SwissADME_Prob']]
# Load ADMET features (25 drugs) and SwissADME features (23 drugs - missing Dactinomycin, Plicamycin)
admet_features = pd.read_csv(OUTPUT_DIR / 'cardiac_rodeo_full_ADMET.csv')
swiss_features_raw = pd.read_csv(OUTPUT_DIR / 'cardiac_rodeo_full_swissadme.csv')

# SwissADME now has 'Drug' column directly - no need for SMILES matching
print(f"ADMET features: {len(admet_features)} drugs")
print(f"SwissADME features: {len(swiss_features_raw)} drugs (missing Dactinomycin, Plicamycin)")

# Swiss features already have Drug column - just use as-is
swiss_features = swiss_features_raw.copy()
swiss_drug_names = swiss_features['Drug'].tolist()

# Create merged dataframe for 25 drugs (ADMET)
merged = true_labels.merge(admet_preds[['Drug', 'DICT_Concern_Prob']], on='Drug', how='left')
merged = merged.merge(swiss_preds[['Drug', 'SwissADME_Prob']], on='Drug', how='left')
merged = merged.merge(drugs_df[['Drug', 'SMILES', 'CID', 'MolecularWeight']], on='Drug', how='left')
merged['HD_binary'] = (merged['heart_damage'] == True).astype(int)

# Create separate merged dataframe for 23 SwissADME drugs (aligned to Swiss order)
merged_swiss = merged.set_index('Drug').loc[swiss_drug_names].reset_index()

print(f"\nLoaded {len(merged)} drugs from Cardiac RODEO dataset (ADMET)")
print(f"Loaded {len(merged_swiss)} drugs for SwissADME analysis (23 drugs)")
print(f"Heart Damage (all 25): {merged['HD_binary'].sum()}/25 positive")
print(f"Heart Damage (23 SwissADME): {merged_swiss['HD_binary'].sum()}/23 positive")

# =============================================================================
# SECTION 3: DICTrank-TRAINED MODEL PREDICTIONS
# =============================================================================
print("\n" + "="*80)
print("SECTION 3: DICTrank-Trained Model Predictions on 25 Drugs")
print("="*80)

results_dictrank = {}

# ADMET-AI (25 drugs)
y_true_admet = merged['HD_binary'].values
y_prob_admet = merged['DICT_Concern_Prob'].values
y_pred_admet = (y_prob_admet >= 0.5).astype(int)
acc_admet = accuracy_score(y_true_admet, y_pred_admet)
fpr_admet, tpr_admet, _ = roc_curve(y_true_admet, y_prob_admet)
roc_auc_admet = auc(fpr_admet, tpr_admet)
cm_admet = confusion_matrix(y_true_admet, y_pred_admet)
mean_fpr_admet, mean_tpr_admet, std_tpr_admet, auc_mean_admet, auc_std_admet = bootstrap_roc_stats(
    y_true_admet, y_prob_admet, n_boot=300, seed=42
)
results_dictrank['ADMET-AI'] = {
    'accuracy': acc_admet,
    'auc': roc_auc_admet,
    'fpr': fpr_admet,
    'tpr': tpr_admet,
    'mean_fpr': mean_fpr_admet,
    'mean_tpr': mean_tpr_admet,
    'std_tpr': std_tpr_admet,
    'auc_mean': auc_mean_admet,
    'auc_std': auc_std_admet,
    'y_prob': y_prob_admet,
    'y_pred': y_pred_admet,
    'confusion_matrix': cm_admet,
    'n_samples': int(len(y_true_admet)),
}

print("\nADMET-AI:")
print(f"  Accuracy: {acc_admet:.3f}")
print(f"  ROC AUC:  {roc_auc_admet:.3f}")
print(f"  TP={cm_admet[1,1]}, FN={cm_admet[1,0]}, TN={cm_admet[0,0]}, FP={cm_admet[0,1]}")

# SwissADME (23 drugs)
merged_swiss_valid = merged_swiss[merged_swiss['SwissADME_Prob'].notna()].reset_index(drop=True)
y_true_swiss = merged_swiss_valid['HD_binary'].values
y_prob_swiss = merged_swiss_valid['SwissADME_Prob'].values
y_pred_swiss = (y_prob_swiss >= 0.5).astype(int)
acc_swiss = accuracy_score(y_true_swiss, y_pred_swiss)
fpr_swiss, tpr_swiss, _ = roc_curve(y_true_swiss, y_prob_swiss)
roc_auc_swiss = auc(fpr_swiss, tpr_swiss)
cm_swiss = confusion_matrix(y_true_swiss, y_pred_swiss)
mean_fpr_swiss, mean_tpr_swiss, std_tpr_swiss, auc_mean_swiss, auc_std_swiss = bootstrap_roc_stats(
    y_true_swiss, y_prob_swiss, n_boot=300, seed=42
)
results_dictrank['SwissADME'] = {
    'accuracy': acc_swiss,
    'auc': roc_auc_swiss,
    'fpr': fpr_swiss,
    'tpr': tpr_swiss,
    'mean_fpr': mean_fpr_swiss,
    'mean_tpr': mean_tpr_swiss,
    'std_tpr': std_tpr_swiss,
    'auc_mean': auc_mean_swiss,
    'auc_std': auc_std_swiss,
    'y_prob': y_prob_swiss,
    'y_pred': y_pred_swiss,
    'confusion_matrix': cm_swiss,
    'n_samples': int(len(y_true_swiss)),
}

print("\nSwissADME:")
print(f"  Accuracy: {acc_swiss:.3f}")
print(f"  ROC AUC:  {roc_auc_swiss:.3f}")
print(f"  TP={cm_swiss[1,1]}, FN={cm_swiss[1,0]}, TN={cm_swiss[0,0]}, FP={cm_swiss[0,1]}")

# Plot: DICTrank confusion matrices (25 drugs)
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, model in zip(axes, ['ADMET-AI', 'SwissADME']):
    cm = results_dictrank[model]['confusion_matrix']
    plot_confusion_matrix_with_percent(
        cm, ['No', 'Yes'], ax, f'DICTrank: {model}'
    )

plt.tight_layout()
plt.savefig(FIGURES_DIR / 'dictrank_confusion_matrices.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'DICTrank_Confusion_Matrices.png', dpi=300, bbox_inches='tight')
plt.close()

# =============================================================================
# SECTION 4: LOOCV MODELS
# =============================================================================
print("\n" + "="*80)
print("SECTION 4: LOOCV Models")
print("="*80)
print("Retraining ADMET-AI (25 drugs) and SwissADME (23 drugs) models.")

# Prepare ADMET features (25 drugs)
admet_feature_cols = [c for c in admet_features.columns if c not in ['Drug', 'Arrhythmia', 'heart_damage', 'Concern']]
X_admet = admet_features[admet_feature_cols].copy()
y_admet = merged.set_index('Drug').loc[drug_names, 'HD_binary'].values

# Prepare SwissADME features (23 drugs)
binary_cols = ['GI absorption', 'BBB permeant', 'Pgp substrate',
               'CYP1A2 inhibitor', 'CYP2C19 inhibitor', 'CYP2C9 inhibitor',
               'CYP2D6 inhibitor', 'CYP3A4 inhibitor']

swiss_clean = swiss_features.copy()
for col in swiss_clean.columns:
    if col in binary_cols:
        swiss_clean[col] = swiss_clean[col].map({'Yes': 1, 'No': 0, 'High': 1, 'Low': 0, 1: 1, 0: 0})
    elif col != 'Drug' and swiss_clean[col].dtype == 'object':
        swiss_clean[col] = pd.to_numeric(swiss_clean[col], errors='coerce')
swiss_clean = swiss_clean.fillna(0)

swiss_feature_cols = [c for c in swiss_clean.columns if c not in ['Drug', 'Arrhythmia', 'heart_damage', 'Concern']]
X_swiss = swiss_clean[swiss_feature_cols].copy()
y_swiss = merged_swiss['HD_binary'].values

print(f"\nADMET-AI: {X_admet.shape[0]} samples, {X_admet.shape[1]} features")
print(f"SwissADME: {X_swiss.shape[0]} samples, {X_swiss.shape[1]} features")

results_loocv = {}
loo = LeaveOneOut()

# Train ADMET-AI model (25 drugs)
print(f"\nTraining ADMET-AI model (LOOCV on 25 drugs)...")
pipeline_admet = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler()),
    ('clf', GradientBoostingClassifier(n_estimators=500, max_depth=12,
                                        learning_rate=0.1, random_state=0))
])

y_prob_admet = cross_val_predict(pipeline_admet, X_admet, y_admet, cv=loo, method='predict_proba')[:, 1]
y_pred_admet = (y_prob_admet >= 0.5).astype(int)
acc_admet = accuracy_score(y_admet, y_pred_admet)
fpr_admet, tpr_admet, _ = roc_curve(y_admet, y_prob_admet)
roc_auc_admet = auc(fpr_admet, tpr_admet)
cm_admet = confusion_matrix(y_admet, y_pred_admet)
mean_fpr_admet, mean_tpr_admet, std_tpr_admet, auc_mean_admet, auc_std_admet = bootstrap_roc_stats(
    y_admet, y_prob_admet, n_boot=300, seed=42
)

results_loocv['ADMET-AI'] = {
    'accuracy': acc_admet,
    'auc': roc_auc_admet,
    'fpr': fpr_admet,
    'tpr': tpr_admet,
    'mean_fpr': mean_fpr_admet,
    'mean_tpr': mean_tpr_admet,
    'std_tpr': std_tpr_admet,
    'auc_mean': auc_mean_admet,
    'auc_std': auc_std_admet,
    'y_prob': y_prob_admet,
    'y_pred': y_pred_admet,
    'confusion_matrix': cm_admet,
    'n_samples': 25
}
print(f"  Accuracy: {acc_admet:.3f}")
print(f"  ROC AUC:  {roc_auc_admet:.3f}")
print(f"  TP={cm_admet[1,1]}, FN={cm_admet[1,0]}, TN={cm_admet[0,0]}, FP={cm_admet[0,1]}")

# Train SwissADME model (23 drugs)
print(f"\nTraining SwissADME model (LOOCV on 23 drugs)...")
pipeline_swiss = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler()),
    ('clf', GradientBoostingClassifier(n_estimators=500, max_depth=12,
                                        learning_rate=0.1, random_state=0))
])

y_prob_swiss = cross_val_predict(pipeline_swiss, X_swiss, y_swiss, cv=loo, method='predict_proba')[:, 1]
y_pred_swiss = (y_prob_swiss >= 0.5).astype(int)
acc_swiss = accuracy_score(y_swiss, y_pred_swiss)
fpr_swiss, tpr_swiss, _ = roc_curve(y_swiss, y_prob_swiss)
roc_auc_swiss = auc(fpr_swiss, tpr_swiss)
cm_swiss = confusion_matrix(y_swiss, y_pred_swiss)
mean_fpr_swiss, mean_tpr_swiss, std_tpr_swiss, auc_mean_swiss, auc_std_swiss = bootstrap_roc_stats(
    y_swiss, y_prob_swiss, n_boot=300, seed=42
)

results_loocv['SwissADME'] = {
    'accuracy': acc_swiss,
    'auc': roc_auc_swiss,
    'fpr': fpr_swiss,
    'tpr': tpr_swiss,
    'mean_fpr': mean_fpr_swiss,
    'mean_tpr': mean_tpr_swiss,
    'std_tpr': std_tpr_swiss,
    'auc_mean': auc_mean_swiss,
    'auc_std': auc_std_swiss,
    'y_prob': y_prob_swiss,
    'y_pred': y_pred_swiss,
    'confusion_matrix': cm_swiss,
    'n_samples': 23
}
print(f"  Accuracy: {acc_swiss:.3f}")
print(f"  ROC AUC:  {roc_auc_swiss:.3f}")
print(f"  TP={cm_swiss[1,1]}, FN={cm_swiss[1,0]}, TN={cm_swiss[0,0]}, FP={cm_swiss[0,1]}")

# =============================================================================
# SECTION 4B: LOOCV MODEL COMPARISON PIPELINE (Heart Damage)
# =============================================================================
print("\n" + "="*80)
print("SECTION 4B: LOOCV Model Comparison Pipeline (Heart Damage)")
print("="*80)

loocv_perf_path = PROJECT_ROOT / "Output" / "Performance_Metrics" / "model_performance_summary.csv"
loocv_cm_path = PROJECT_ROOT / "Output" / "Confusion_Matrices" / "heart_damage_confusion_matrix.csv"
loocv_report_path = PROJECT_ROOT / "Output" / "Confusion_Matrices" / "heart_damage_classification_report.csv"

results_loocv_comparison_hd = None

if loocv_perf_path.exists():
    perf_df = pd.read_csv(loocv_perf_path)
    perf_df['Target'] = perf_df['Target'].astype(str).str.lower()
    row = perf_df[perf_df['Target'] == 'heart_damage']
    if not row.empty:
        row = row.iloc[0]
        results_loocv_comparison_hd = {
            'accuracy_mean': float(row.get('Accuracy_Mean', np.nan)),
            'accuracy_std': float(row.get('Accuracy_Std', np.nan)),
            'auc_mean': float(row.get('AUC_Mean', np.nan)),
            'auc_std': float(row.get('AUC_Std', np.nan)),
            'f1_mean': float(row.get('F1_Mean', np.nan)),
            'f1_std': float(row.get('F1_Std', np.nan)),
            'mcc_mean': float(row.get('MCC_Mean', np.nan)),
            'mcc_std': float(row.get('MCC_Std', np.nan)),
            'n_folds': int(row.get('N_Folds', 0)) if not pd.isna(row.get('N_Folds', np.nan)) else None,
            'model': row.get('Model', 'Unknown')
        }
        print("Loaded LOOCV comparison metrics for Heart Damage.")
    else:
        print("LOOCV comparison metrics found, but no heart_damage row present.")
else:
    print("LOOCV comparison metrics not found.")

if loocv_cm_path.exists():
    cm_df = pd.read_csv(loocv_cm_path, index_col=0)
    if results_loocv_comparison_hd is None:
        results_loocv_comparison_hd = {}
    results_loocv_comparison_hd['confusion_matrix'] = cm_df.values
    results_loocv_comparison_hd['confusion_matrix_labels'] = list(cm_df.columns)
    print(f"Loaded LOOCV comparison confusion matrix: {loocv_cm_path}")
else:
    print("LOOCV comparison confusion matrix not found.")

if loocv_report_path.exists():
    report_df = pd.read_csv(loocv_report_path, index_col=0)
    if results_loocv_comparison_hd is None:
        results_loocv_comparison_hd = {}
    results_loocv_comparison_hd['classification_report'] = report_df
    print(f"Loaded LOOCV comparison classification report: {loocv_report_path}")
else:
    print("LOOCV comparison classification report not found.")

organoid_fpr = None
organoid_tpr = None
organoid_roc_auc = None
organoid_mean_fpr = None
organoid_mean_tpr = None
organoid_std_tpr = None
organoid_auc_mean = None
organoid_auc_std = None
organoid_cm = None
organoid_labels = ['No', 'Yes']
organoid_y_true = None
organoid_y_prob = None

# =============================================================================
# Load Organoid ROC data from new Excel file (roc_curves_all_models.xlsx)
# =============================================================================
organoid_roc_excel_path = PROJECT_ROOT / "Output" / "ROC_Data" / "roc_curves_all_models.xlsx"
if organoid_roc_excel_path.exists():
    try:
        roc_excel = pd.read_excel(organoid_roc_excel_path, sheet_name='HeartDamage')
        print(f"Loaded organoid ROC data from: {organoid_roc_excel_path}")

        # Extract fold data and compute mean/std
        fold_indices = []
        for col in roc_excel.columns:
            if isinstance(col, str) and col.startswith('Fold') and ' - FPR' in col:
                try:
                    fold_idx = int(col.split(' - ')[0].replace('Fold', ''))
                    fold_indices.append(fold_idx)
                except ValueError:
                    continue
        fold_indices = sorted(set(fold_indices))
        fold_aucs = []
        fold_fprs = []
        fold_tprs = []

        for fold_idx in fold_indices:
            fpr_col = f'Fold{fold_idx} - FPR'
            tpr_col = f'Fold{fold_idx} - TPR'
            roc_col = f'Fold{fold_idx} - ROC'

            if fpr_col in roc_excel.columns and tpr_col in roc_excel.columns:
                fpr_vals = roc_excel[fpr_col].dropna().values
                tpr_vals = roc_excel[tpr_col].dropna().values
                roc_val = roc_excel[roc_col].dropna().values[0] if roc_col in roc_excel.columns else np.nan

                if len(fpr_vals) > 0 and len(tpr_vals) > 0:
                    fold_fprs.append(fpr_vals)
                    fold_tprs.append(tpr_vals)
                    fold_aucs.append(roc_val)

        # Interpolate all folds to common FPR grid
        mean_fpr_grid = np.linspace(0, 1, 100)
        interp_tprs = []

        for fpr_vals, tpr_vals in zip(fold_fprs, fold_tprs):
            interp_tpr = np.interp(mean_fpr_grid, fpr_vals, tpr_vals)
            interp_tpr[0] = 0.0
            interp_tprs.append(interp_tpr)

        if interp_tprs:
            interp_tprs = np.array(interp_tprs)
            organoid_mean_fpr = mean_fpr_grid
            organoid_mean_tpr = np.mean(interp_tprs, axis=0)
            organoid_mean_tpr[-1] = 1.0
            organoid_std_tpr = np.std(interp_tprs, axis=0)
            organoid_auc_mean = np.mean(fold_aucs)
            organoid_auc_std = np.std(fold_aucs)
            organoid_auc_std = clamp_auc_std(organoid_auc_mean, organoid_auc_std)
            print(f"  Computed ROC from {len(fold_aucs)} folds: AUC = {organoid_auc_mean:.3f} ± {organoid_auc_std:.3f}")
    except Exception as e:
        print(f"Error loading ROC Excel: {e}")
else:
    # Fallback to old CSV format
    organoid_roc_summary_path = PROJECT_ROOT / "Output" / "Performance_Metrics" / "heart_damage_roc_curve_summary.csv"
    if organoid_roc_summary_path.exists():
        roc_df = pd.read_csv(organoid_roc_summary_path)
        if {'mean_fpr', 'mean_tpr', 'std_tpr'}.issubset(set(roc_df.columns)):
            organoid_mean_fpr = roc_df['mean_fpr'].values
            organoid_mean_tpr = roc_df['mean_tpr'].values
            organoid_std_tpr = roc_df['std_tpr'].values
            if 'auc_mean' in roc_df.columns:
                organoid_auc_mean = float(roc_df['auc_mean'].iloc[0])
            if 'auc_std' in roc_df.columns:
                organoid_auc_std = float(roc_df['auc_std'].iloc[0])
            organoid_auc_std = clamp_auc_std(organoid_auc_mean, organoid_auc_std)
            print(f"Loaded organoid ROC summary (fallback): {organoid_roc_summary_path}")

# =============================================================================
# Load Organoid confusion matrix from LOOCV Comparison output
# =============================================================================
organoid_cm_path = PROJECT_ROOT / "Output" / "Confusion_Matrices" / "heart_damage_confusion_matrix.csv"
if organoid_cm_path.exists():
    cm_df = pd.read_csv(organoid_cm_path, index_col=0)
    organoid_cm = cm_df.values
    # Normalize to per-drug counts (divide by number of CV iterations if aggregated)
    # The confusion matrix from LOOCV comparison is aggregated across 10 seeds × 3 folds = 30 iterations
    # Normalize to approximate single-run counts
    total_samples = organoid_cm.sum()
    if total_samples > 25:  # If aggregated, normalize
        scale_factor = 25 / total_samples
        organoid_cm = np.round(organoid_cm * scale_factor).astype(int)
    print(f"Loaded organoid confusion matrix from: {organoid_cm_path}")

# Fallback to predictions file for confusion matrix if needed
organoid_pred_path = PROJECT_ROOT / "Output" / "Prediction_Scatter_Data" / "heart_damage_predictions.csv"
if organoid_cm is None and organoid_pred_path.exists():
    organoid_df = pd.read_csv(organoid_pred_path)
    if 'Actual_Heart_Damage' in organoid_df.columns and 'Predicted_Heart_Damage_pct' in organoid_df.columns:
        organoid_y_true = organoid_df['Actual_Heart_Damage'].astype(str).str.lower().isin(['true', '1', 'yes']).astype(int).values
        organoid_y_prob = organoid_df['Predicted_Heart_Damage_pct'].astype(float).values
        if np.nanmax(organoid_y_prob) > 1.5:
            organoid_y_prob = organoid_y_prob / 100.0
        organoid_fpr, organoid_tpr, _ = roc_curve(organoid_y_true, organoid_y_prob)
        organoid_roc_auc = auc(organoid_fpr, organoid_tpr)
        y_pred = (organoid_y_prob >= 0.5).astype(int)
        organoid_cm = confusion_matrix(organoid_y_true, y_pred)
        print(f"Loaded organoid predictions from: {organoid_pred_path}")
    else:
        print("Organoid prediction file missing required columns.")
elif organoid_cm is None:
    print("Organoid prediction/confusion matrix file not found.")

# =============================================================================
# SECTION 5: SCAFFOLD-BALANCED CV MODELS
# =============================================================================
print("\n" + "="*80)
print("SECTION 5: Scaffold-Balanced CV Models")
print("="*80)
print("Note: ADMET-AI uses 25 drugs, SwissADME uses 23 drugs")

results_scaffold = {}
num_folds_scaffold = 10

if not CHEMPROP_AVAILABLE:
    print("chemprop not available; scaffold-balanced CV skipped.")
else:
    # ADMET-AI Scaffold CV (25 drugs)
    print("\n--- ADMET-AI Scaffold CV (25 drugs) ---")
    scaffold_input_admet = OUTPUT_DIR / 'cardiac_rodeo_scaffold_input.csv'
    smiles_ordered_admet = merged.set_index('Drug').loc[drug_names, 'SMILES'].values
    scaffold_df_admet = pd.DataFrame({'SMILES': smiles_ordered_admet, 'HD': y_admet})
    scaffold_df_admet.to_csv(scaffold_input_admet, index=False)

    adxdata_admet = get_data(
        str(scaffold_input_admet),
        smiles_columns=["SMILES"],
        target_columns=["HD"],
    )

    scaf_splits_admet = {}
    for seed in range(num_folds_scaffold):
        train, val, test = split_data(
            data=adxdata_admet,
            split_type='scaffold_balanced',
            num_folds=num_folds_scaffold,
            seed=seed,
            sizes=(0.80, 0.0, 0.20)
        )
        scaf_splits_admet[seed] = {}
        for split, name in [(train, "train"), (val, "val"), (test, "test")]:
            indices = []
            for i, s in enumerate(split.smiles()):
                smi = s[0]
                idx = scaffold_df_admet[scaffold_df_admet["SMILES"] == smi].index[0]
                indices.append(idx)
            scaf_splits_admet[seed][name] = pd.DataFrame({"data_index": indices})

    # Train ADMET-AI with scaffold CV
    print(f"\nTraining ADMET-AI model (Scaffold-balanced CV on 25 drugs)...")
    probs_sum_admet = np.zeros(len(y_admet))
    counts_admet = np.zeros(len(y_admet))
    roc_aucs_admet = []
    pr_aucs_admet = []
    accs_admet = []
    cm_sum_admet = np.zeros((2, 2), dtype=int)

    for seed in scaf_splits_admet:
        train_index = list(scaf_splits_admet[seed]['train']['data_index'].values)
        test_index = list(scaf_splits_admet[seed]['test']['data_index'].values)
        if len(test_index) == 0:
            continue

        X_train = X_admet.iloc[train_index]
        y_train = y_admet[train_index]
        X_test = X_admet.iloc[test_index]
        y_test = y_admet[test_index]

        xgb = GradientBoostingClassifier(n_estimators=500, learning_rate=0.1, max_depth=12, random_state=0)
        xgb.fit(X_train, y_train)
        fold_probs = xgb.predict_proba(X_test)[:, 1]
        fold_preds = (fold_probs >= 0.5).astype(int)

        probs_sum_admet[test_index] += fold_probs
        counts_admet[test_index] += 1
        cm_sum_admet += confusion_matrix(y_test, fold_preds)

        accs_admet.append(accuracy_score(y_test, fold_preds))
        if len(np.unique(y_test)) > 1:
            roc_aucs_admet.append(metrics.roc_auc_score(y_test, fold_probs))
            pr_aucs_admet.append(metrics.average_precision_score(y_test, fold_probs))
        else:
            roc_aucs_admet.append(np.nan)
            pr_aucs_admet.append(np.nan)

    avg_probs_admet = np.divide(probs_sum_admet, counts_admet, out=np.zeros_like(probs_sum_admet), where=counts_admet > 0)
    avg_preds_admet = (avg_probs_admet >= 0.5).astype(int)

    fpr_admet_scaf, tpr_admet_scaf, _ = roc_curve(y_admet, avg_probs_admet)
    roc_auc_admet_scaf = auc(fpr_admet_scaf, tpr_admet_scaf)
    cm_admet_scaf = cm_sum_admet if cm_sum_admet.sum() else confusion_matrix(y_admet, avg_preds_admet)
    mean_fpr_admet_scaf, mean_tpr_admet_scaf, std_tpr_admet_scaf, auc_mean_admet_scaf, auc_std_admet_scaf = bootstrap_roc_stats(
        y_admet, avg_probs_admet, n_boot=300, seed=42
    )

    results_scaffold['ADMET-AI'] = {
        'accuracy': float(np.mean(accs_admet)) if accs_admet else np.nan,
        'accuracy_std': float(np.std(accs_admet)) if accs_admet else np.nan,
        'auc': roc_auc_admet_scaf,
        'auc_mean': float(np.nanmean(roc_aucs_admet)) if roc_aucs_admet else np.nan,
        'auc_std': float(np.nanstd(roc_aucs_admet)) if roc_aucs_admet else np.nan,
        'pr_auc_mean': float(np.nanmean(pr_aucs_admet)) if pr_aucs_admet else np.nan,
        'pr_auc_std': float(np.nanstd(pr_aucs_admet)) if pr_aucs_admet else np.nan,
        'fpr': fpr_admet_scaf,
        'tpr': tpr_admet_scaf,
        'mean_fpr': mean_fpr_admet_scaf,
        'mean_tpr': mean_tpr_admet_scaf,
        'std_tpr': std_tpr_admet_scaf,
        'y_prob': avg_probs_admet,
        'y_pred': avg_preds_admet,
        'confusion_matrix': cm_admet_scaf,
        'n_samples': 25
    }
    print(f"  Accuracy: {results_scaffold['ADMET-AI']['accuracy']:.3f}")
    print(f"  ROC AUC:  {results_scaffold['ADMET-AI']['auc']:.3f}")

    # SwissADME Scaffold CV (23 drugs)
    print("\n--- SwissADME Scaffold CV (23 drugs) ---")
    scaffold_input_swiss = OUTPUT_DIR / 'cardiac_rodeo_scaffold_input_swiss.csv'
    smiles_ordered_swiss = merged_swiss.set_index('Drug').loc[swiss_drug_names, 'SMILES'].values
    scaffold_df_swiss = pd.DataFrame({'SMILES': smiles_ordered_swiss, 'HD': y_swiss})
    scaffold_df_swiss.to_csv(scaffold_input_swiss, index=False)

    adxdata_swiss = get_data(
        str(scaffold_input_swiss),
        smiles_columns=["SMILES"],
        target_columns=["HD"],
    )

    scaf_splits_swiss = {}
    for seed in range(num_folds_scaffold):
        train, val, test = split_data(
            data=adxdata_swiss,
            split_type='scaffold_balanced',
            num_folds=num_folds_scaffold,
            seed=seed,
            sizes=(0.80, 0.0, 0.20)
        )
        scaf_splits_swiss[seed] = {}
        for split, name in [(train, "train"), (val, "val"), (test, "test")]:
            indices = []
            for i, s in enumerate(split.smiles()):
                smi = s[0]
                idx = scaffold_df_swiss[scaffold_df_swiss["SMILES"] == smi].index[0]
                indices.append(idx)
            scaf_splits_swiss[seed][name] = pd.DataFrame({"data_index": indices})

    # Train SwissADME with scaffold CV
    print(f"\nTraining SwissADME model (Scaffold-balanced CV on 23 drugs)...")
    probs_sum_swiss = np.zeros(len(y_swiss))
    counts_swiss = np.zeros(len(y_swiss))
    roc_aucs_swiss = []
    pr_aucs_swiss = []
    accs_swiss = []
    cm_sum_swiss = np.zeros((2, 2), dtype=int)

    for seed in scaf_splits_swiss:
        train_index = list(scaf_splits_swiss[seed]['train']['data_index'].values)
        test_index = list(scaf_splits_swiss[seed]['test']['data_index'].values)
        if len(test_index) == 0:
            continue

        X_train = X_swiss.iloc[train_index]
        y_train = y_swiss[train_index]
        X_test = X_swiss.iloc[test_index]
        y_test = y_swiss[test_index]

        xgb = GradientBoostingClassifier(n_estimators=500, learning_rate=0.1, max_depth=12, random_state=0)
        xgb.fit(X_train, y_train)
        fold_probs = xgb.predict_proba(X_test)[:, 1]
        fold_preds = (fold_probs >= 0.5).astype(int)

        probs_sum_swiss[test_index] += fold_probs
        counts_swiss[test_index] += 1
        cm_sum_swiss += confusion_matrix(y_test, fold_preds)

        accs_swiss.append(accuracy_score(y_test, fold_preds))
        if len(np.unique(y_test)) > 1:
            roc_aucs_swiss.append(metrics.roc_auc_score(y_test, fold_probs))
            pr_aucs_swiss.append(metrics.average_precision_score(y_test, fold_probs))
        else:
            roc_aucs_swiss.append(np.nan)
            pr_aucs_swiss.append(np.nan)

    avg_probs_swiss = np.divide(probs_sum_swiss, counts_swiss, out=np.zeros_like(probs_sum_swiss), where=counts_swiss > 0)
    avg_preds_swiss = (avg_probs_swiss >= 0.5).astype(int)

    fpr_swiss_scaf, tpr_swiss_scaf, _ = roc_curve(y_swiss, avg_probs_swiss)
    roc_auc_swiss_scaf = auc(fpr_swiss_scaf, tpr_swiss_scaf)
    cm_swiss_scaf = cm_sum_swiss if cm_sum_swiss.sum() else confusion_matrix(y_swiss, avg_preds_swiss)
    mean_fpr_swiss_scaf, mean_tpr_swiss_scaf, std_tpr_swiss_scaf, auc_mean_swiss_scaf, auc_std_swiss_scaf = bootstrap_roc_stats(
        y_swiss, avg_probs_swiss, n_boot=300, seed=42
    )

    results_scaffold['SwissADME'] = {
        'accuracy': float(np.mean(accs_swiss)) if accs_swiss else np.nan,
        'accuracy_std': float(np.std(accs_swiss)) if accs_swiss else np.nan,
        'auc': roc_auc_swiss_scaf,
        'auc_mean': float(np.nanmean(roc_aucs_swiss)) if roc_aucs_swiss else np.nan,
        'auc_std': float(np.nanstd(roc_aucs_swiss)) if roc_aucs_swiss else np.nan,
        'pr_auc_mean': float(np.nanmean(pr_aucs_swiss)) if pr_aucs_swiss else np.nan,
        'pr_auc_std': float(np.nanstd(pr_aucs_swiss)) if pr_aucs_swiss else np.nan,
        'fpr': fpr_swiss_scaf,
        'tpr': tpr_swiss_scaf,
        'mean_fpr': mean_fpr_swiss_scaf,
        'mean_tpr': mean_tpr_swiss_scaf,
        'std_tpr': std_tpr_swiss_scaf,
        'y_prob': avg_probs_swiss,
        'y_pred': avg_preds_swiss,
        'confusion_matrix': cm_swiss_scaf,
        'n_samples': 23
    }
    print(f"  Accuracy: {results_scaffold['SwissADME']['accuracy']:.3f}")
    print(f"  ROC AUC:  {results_scaffold['SwissADME']['auc']:.3f}")

# =============================================================================
# SECTION 6: SHAP FEATURE IMPORTANCE (ADMET-AI)
# =============================================================================
print("\n" + "="*80)
print("SECTION 6: SHAP Feature Importance (ADMET-AI)")
print("="*80)

shap_top_features = {'DICTrank': None, 'LOOCV': None, 'Scaffold': None}

def compute_tree_shap(model, X_values):
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_values)
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1] if len(shap_vals) > 1 else shap_vals[0]
    return np.asarray(shap_vals)

def build_shap_summary(shap_values, feature_names, top_n=10, order=None):
    mean_shap = np.mean(shap_values, axis=0)
    mean_abs = np.abs(shap_values).mean(axis=0)
    df = pd.DataFrame({
        'Feature': feature_names,
        'MeanSHAP': mean_shap,
        'MeanAbsSHAP': mean_abs
    })
    if order:
        df = df.set_index('Feature').reindex(order).dropna().reset_index()
    else:
        df = df.sort_values('MeanAbsSHAP', ascending=False).head(top_n)
    return df

def plot_shap_bar(shap_df, output_path, title, feature_type_map=None):
    if shap_df is None or shap_df.empty:
        return

    colors = None
    if feature_type_map:
        type_colors = {
            'Absorption': '#F3E79B',
            'Metabolism': '#B9B4E5',
            'Toxicity': '#F4A6A6',
            'Other': '#C0C0C0'
        }
        colors = [
            type_colors.get(feature_type_map.get(feat, 'Other'), '#C0C0C0')
            for feat in shap_df['Feature']
        ]

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    plot_df = shap_df.iloc[::-1].reset_index(drop=True)
    ax.barh(plot_df['Feature'], plot_df['MeanSHAP'], color=colors)
    ax.axvline(0, color='black', linewidth=1)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('Mean SHAP Value', fontsize=10)
    ax.grid(axis='x', alpha=0.3)
    if feature_type_map:
        from matplotlib.patches import Patch
        legend_items = [
            Patch(color='#F3E79B', label='Absorption'),
            Patch(color='#B9B4E5', label='Metabolism'),
            Patch(color='#F4A6A6', label='Toxicity')
        ]
        ax.legend(handles=legend_items, title='Feature type', loc='lower right', fontsize=8, title_fontsize=8)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()

FEATURE_TYPE_MAP = {
    'CYP2D6 Substrate': 'Metabolism',
    'Nrf2-Antioxidant Responsive Element': 'Toxicity',
    'Heat Shock Factor Response Element': 'Toxicity',
    'Hydration Free Energy': 'Absorption',
    'CYP1A2 Inhibition': 'Metabolism',
    'Drug Induced Liver Injury': 'Toxicity',
    'Human Intestinal Absorption': 'Absorption',
    'Aromatase': 'Metabolism',
    'Aqueous Solubility': 'Absorption',
    'CYP2D6 Inhibition': 'Metabolism'
}

# DICTrank SHAP values from ADMEThyst (no shap dependency)
dictrank_shap_path = ADMETHYST_MAIN_DIR / "data" / "ADMET-AI_xGB_shap_vals.csv"
if dictrank_shap_path.exists():
    dictrank_shap = pd.read_csv(dictrank_shap_path)
    dictrank_shap = dictrank_shap.drop(
        columns=[c for c in dictrank_shap.columns if c.lower().startswith('unnamed')],
        errors='ignore'
    )
    paper_order = [
        'CYP2D6 Substrate',
        'Nrf2-Antioxidant Responsive Element',
        'Heat Shock Factor Response Element',
        'Hydration Free Energy',
        'CYP1A2 Inhibition',
        'Drug Induced Liver Injury',
        'Human Intestinal Absorption',
        'Aromatase',
        'Aqueous Solubility',
        'CYP2D6 Inhibition'
    ]
    dictrank_shap_df = build_shap_summary(
        dictrank_shap.values,
        dictrank_shap.columns.tolist(),
        top_n=10,
        order=paper_order
    )
    shap_top_features['DICTrank'] = dictrank_shap_df.sort_values('MeanAbsSHAP', ascending=False).head(5)
    dictrank_shap_df.to_csv(OUTPUT_DIR / 'dictrank_shap_mean_abs.csv', index=False)
    plot_shap_bar(
        dictrank_shap_df,
        FIGURES_DIR / 'dictrank_shap_features.pdf',
        'DICTrank ADMET-AI Feature Influence',
        feature_type_map=FEATURE_TYPE_MAP
    )
    print("Loaded DICTrank SHAP values for ADMET-AI.")
else:
    print("DICTrank SHAP file not found; skipping DICTrank SHAP.")

if not SHAP_AVAILABLE:
    print("SHAP is not available; skipping LOOCV/Scaffold SHAP computation.")
else:
    # LOOCV SHAP values (ADMET-AI features)
    try:
        loocv_shap_values = []
        loo = LeaveOneOut()
        for train_idx, test_idx in loo.split(X_admet):
            X_train = X_admet.iloc[train_idx]
            y_train = y_admet[train_idx]
            X_test = X_admet.iloc[test_idx]

            pipeline = Pipeline([
                ('imputer', SimpleImputer(strategy='mean')),
                ('scaler', StandardScaler()),
                ('clf', GradientBoostingClassifier(
                    n_estimators=500, max_depth=12, learning_rate=0.1, random_state=0
                ))
            ])
            pipeline.fit(X_train, y_train)

            X_test_imp = pipeline.named_steps['imputer'].transform(X_test)
            X_test_scaled = pipeline.named_steps['scaler'].transform(X_test_imp)
            model = pipeline.named_steps['clf']
            shap_vals = compute_tree_shap(model, X_test_scaled)
            loocv_shap_values.append(np.atleast_2d(shap_vals))

        if loocv_shap_values:
            loocv_shap_values = np.vstack(loocv_shap_values)
            loocv_shap_df = build_shap_summary(
                loocv_shap_values,
                X_admet.columns.tolist(),
                top_n=10
            )
            shap_top_features['LOOCV'] = loocv_shap_df.sort_values('MeanAbsSHAP', ascending=False).head(5)
            loocv_shap_df.to_csv(OUTPUT_DIR / 'loocv_admet_shap_mean_abs.csv', index=False)
            plot_shap_bar(
                loocv_shap_df,
                FIGURES_DIR / 'loocv_shap_features.pdf',
                'LOOCV ADMET-AI Feature Influence'
            )
            print("Computed LOOCV SHAP values for ADMET-AI.")
    except Exception as exc:
        print(f"LOOCV SHAP computation failed: {exc}")

    # Scaffold CV SHAP values (ADMET-AI features)
    if results_scaffold and CHEMPROP_AVAILABLE:
        try:
            scaffold_shap_values = []
            for seed in scaf_splits:
                train_index = list(scaf_splits[seed]['train']['data_index'].values)
                test_index = list(scaf_splits[seed]['test']['data_index'].values)
                if len(test_index) == 0:
                    continue

                X_train = X_admet.iloc[train_index]
                y_train = y[train_index]
                X_test = X_admet.iloc[test_index]

                imputer = SimpleImputer(strategy='mean')
                X_train_imp = imputer.fit_transform(X_train)
                X_test_imp = imputer.transform(X_test)

                model = GradientBoostingClassifier(
                    n_estimators=500,
                    learning_rate=0.1,
                    max_depth=12,
                    random_state=0
                )
                model.fit(X_train_imp, y_train)
                shap_vals = compute_tree_shap(model, X_test_imp)
                scaffold_shap_values.append(np.atleast_2d(shap_vals))

            if scaffold_shap_values:
                scaffold_shap_values = np.vstack(scaffold_shap_values)
                scaffold_shap_df = build_shap_summary(
                    scaffold_shap_values,
                    X_admet.columns.tolist(),
                    top_n=10
                )
                shap_top_features['Scaffold'] = scaffold_shap_df.sort_values('MeanAbsSHAP', ascending=False).head(5)
                scaffold_shap_df.to_csv(OUTPUT_DIR / 'scaffold_admet_shap_mean_abs.csv', index=False)
                plot_shap_bar(
                    scaffold_shap_df,
                    FIGURES_DIR / 'scaffold_shap_features.pdf',
                    'Scaffold CV ADMET-AI Feature Influence'
                )
                print("Computed Scaffold CV SHAP values for ADMET-AI.")
        except Exception as exc:
            print(f"Scaffold SHAP computation failed: {exc}")
    else:
        print("Scaffold SHAP skipped (scaffold CV not available).")

# =============================================================================
# GENERATE PLOTS
# =============================================================================
print("\n" + "="*80)
print("GENERATING PLOTS")
print("="*80)

colors = {'ADMET-AI': '#2196F3', 'SwissADME': '#FF9800'}

organoid_acc = np.nan
organoid_auc = np.nan
organoid_model_label = "Organoid (LOOCV pipeline)"
if results_loocv_comparison_hd:
    organoid_acc = results_loocv_comparison_hd.get('accuracy_mean', np.nan)
    organoid_auc = results_loocv_comparison_hd.get('auc_mean', np.nan)
    model_name = results_loocv_comparison_hd.get('model')
    if isinstance(model_name, str) and model_name.strip():
        organoid_model_label = f"Organoid ({model_name})"
if organoid_auc_mean is not None and not pd.isna(organoid_auc_mean):
    organoid_auc = organoid_auc_mean
if pd.isna(organoid_auc) and organoid_roc_auc is not None:
    organoid_auc = organoid_roc_auc
if pd.isna(organoid_acc) and organoid_cm is not None:
    organoid_acc = (organoid_cm[0, 0] + organoid_cm[1, 1]) / np.sum(organoid_cm)
if organoid_cm is None and results_loocv_comparison_hd and 'confusion_matrix' in results_loocv_comparison_hd:
    organoid_cm = np.array(results_loocv_comparison_hd['confusion_matrix'])
if organoid_mean_fpr is None and organoid_y_true is not None and organoid_y_prob is not None:
    organoid_mean_fpr, organoid_mean_tpr, organoid_std_tpr, organoid_auc_mean, organoid_auc_std = bootstrap_roc_stats(
        organoid_y_true, organoid_y_prob, n_boot=300, seed=42
    )
    organoid_auc_std = clamp_auc_std(organoid_auc_mean, organoid_auc_std)

# DICTrank training accuracy bar
train_accs = [
    paper_results['ADMET-AI'].get('ACC'),
    paper_results['SwissADME'].get('ACC')
]
train_accs = [val if val is not None else np.nan for val in train_accs]
fig, ax = plt.subplots(figsize=(4.5, 3.2))
ax.bar(['ADMET-AI', 'SwissADME'], train_accs, width=0.35, color=['#2196F3', '#FF9800'], edgecolor='black')
ax.set_ylim(0, 1.0)
ax.set_ylabel('Accuracy', fontsize=11, fontweight='bold')
ax.set_title('DICTrank Training Accuracy (10-Fold CV)', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
for idx, val in enumerate(train_accs):
    if not np.isnan(val):
        ax.text(idx, val + 0.02, f"{val:.2f}", ha='center', fontsize=9)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'dictrank_training_accuracy.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'DICTrank_Training_Accuracy.png', dpi=300, bbox_inches='tight')
plt.close()

# DICTrank 25 drugs accuracy + AUC bars
dictrank_accs = [results_dictrank[m]['accuracy'] for m in ['ADMET-AI', 'SwissADME']]
dictrank_aucs = [results_dictrank[m]['auc'] for m in ['ADMET-AI', 'SwissADME']]

fig, ax = plt.subplots(figsize=(4.5, 3.2))
ax.bar(['ADMET-AI', 'SwissADME'], dictrank_accs, width=0.35, color=['#2196F3', '#FF9800'], edgecolor='black')
ax.set_ylim(0, 1.0)
ax.set_ylabel('Accuracy', fontsize=11, fontweight='bold')
ax.set_title('DICTrank Accuracy on 25 Drugs', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
for idx, val in enumerate(dictrank_accs):
    ax.text(idx, val + 0.02, f"{val:.2f}", ha='center', fontsize=9)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'dictrank_accuracy_bar.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'DICTrank_Accuracy_Bar.png', dpi=300, bbox_inches='tight')
plt.close()


# DICTrank 25 drugs ROC curves (mean +/- std)
fig, ax = plt.subplots(figsize=(7, 5))
for model in ['ADMET-AI', 'SwissADME']:
    r = results_dictrank[model]
    label = f"{model} (AUC={r['auc_mean']:.2f}±{r['auc_std']:.2f})"
    plot_roc_with_std(ax, r['mean_fpr'], r['mean_tpr'], r['std_tpr'], colors[model], label)
ax.plot([0, 1], [0, 1], 'k--', lw=1, label='Random')
ax.set_xlabel('False Positive Rate', fontsize=11)
ax.set_ylabel('True Positive Rate', fontsize=11)
ax.set_title('DICTrank ROC Curves on 25 Drugs', fontsize=12, fontweight='bold')
ax.legend(loc='lower right', fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'dictrank_roc_25.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'DICTrank_ROC_25.png', dpi=300, bbox_inches='tight')
plt.close()

# LOOCV accuracy + AUC bars
loocv_accs = [results_loocv[m]['accuracy'] for m in ['ADMET-AI', 'SwissADME']]
loocv_aucs = [results_loocv[m]['auc'] for m in ['ADMET-AI', 'SwissADME']]

fig, ax = plt.subplots(figsize=(4.5, 3.2))
ax.bar(['ADMET-AI', 'SwissADME'], loocv_accs, width=0.35, color=['#2196F3', '#FF9800'], edgecolor='black')
ax.set_ylim(0, 1.0)
ax.set_ylabel('Accuracy', fontsize=11, fontweight='bold')
ax.set_title('LOOCV Accuracy on 25 Drugs', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
for idx, val in enumerate(loocv_accs):
    ax.text(idx, val + 0.02, f"{val:.2f}", ha='center', fontsize=9)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'loocv_accuracy_bar.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'LOOCV_Accuracy_Bar.png', dpi=300, bbox_inches='tight')
plt.close()


# Scaffold accuracy + AUC bars
if results_scaffold:
    scaffold_accs = [results_scaffold[m]['accuracy'] for m in ['ADMET-AI', 'SwissADME']]
    scaffold_aucs = [results_scaffold[m]['auc_mean'] for m in ['ADMET-AI', 'SwissADME']]

    fig, ax = plt.subplots(figsize=(4.5, 3.2))
    ax.bar(['ADMET-AI', 'SwissADME'], scaffold_accs, width=0.35, color=['#2196F3', '#FF9800'], edgecolor='black')
    ax.set_ylim(0, 1.0)
    ax.set_ylabel('Accuracy', fontsize=11, fontweight='bold')
    ax.set_title('Scaffold CV Accuracy on 25 Drugs', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    for idx, val in enumerate(scaffold_accs):
        ax.text(idx, val + 0.02, f"{val:.2f}", ha='center', fontsize=9)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'scaffold_accuracy_bar.pdf', bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'Scaffold_Accuracy_Bar.png', dpi=300, bbox_inches='tight')
    plt.close()


# Organoid accuracy + AUC bars
fig, ax = plt.subplots(figsize=(4.0, 3.2))
ax.bar([organoid_model_label], [organoid_acc], width=0.35, color='#6D6D6D', edgecolor='black')
ax.set_ylim(0, 1.0)
ax.set_ylabel('Accuracy', fontsize=11, fontweight='bold')
ax.set_title('Organoid Accuracy on 25 Drugs', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
if not np.isnan(organoid_acc):
    ax.text(0, organoid_acc + 0.02, f"{organoid_acc:.2f}", ha='center', fontsize=9)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'organoid_accuracy_bar.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'Organoid_Accuracy_Bar.png', dpi=300, bbox_inches='tight')
plt.close()


# Organoid ROC curve
if organoid_mean_fpr is not None and organoid_mean_tpr is not None and organoid_std_tpr is not None:
    fig, ax = plt.subplots(figsize=(7, 5))
    auc_label = organoid_auc_mean if organoid_auc_mean is not None else organoid_auc
    auc_std_label = organoid_auc_std if organoid_auc_std is not None else 0.0
    label = f"{organoid_model_label} (AUC={auc_label:.2f}±{auc_std_label:.2f})"
    plot_roc_with_std(ax, organoid_mean_fpr, organoid_mean_tpr, organoid_std_tpr, '#6D6D6D', label)
    ax.plot([0, 1], [0, 1], 'k--', lw=1, label='Random')
    ax.set_xlabel('False Positive Rate', fontsize=11)
    ax.set_ylabel('True Positive Rate', fontsize=11)
    ax.set_title('Organoid ROC Curve on 25 Drugs', fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'organoid_roc.pdf', bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'Organoid_ROC.png', dpi=300, bbox_inches='tight')
    plt.close()

# Final comparison ROC overlay (ADMET-AI + organoid, mean +/- std)
fig, ax = plt.subplots(figsize=(7.5, 5.5))
dic = results_dictrank['ADMET-AI']
plot_roc_with_std(
    ax, dic['mean_fpr'], dic['mean_tpr'], dic['std_tpr'], '#1B5E90',
    f"DICTrank ADMET-AI (AUC={dic['auc_mean']:.2f}±{dic['auc_std']:.2f})"
)
loo = results_loocv['ADMET-AI']
plot_roc_with_std(
    ax, loo['mean_fpr'], loo['mean_tpr'], loo['std_tpr'], '#2196F3',
    f"LOOCV ADMET-AI (AUC={loo['auc_mean']:.2f}±{loo['auc_std']:.2f})"
)
if results_scaffold:
    sca = results_scaffold['ADMET-AI']
    plot_roc_with_std(
        ax, sca['mean_fpr'], sca['mean_tpr'], sca['std_tpr'], '#4CAF50',
        f"Scaffold ADMET-AI (AUC={sca['auc_mean']:.2f}±{sca['auc_std']:.2f})"
    )
if organoid_mean_fpr is not None and organoid_mean_tpr is not None and organoid_std_tpr is not None:
    auc_label = organoid_auc_mean if organoid_auc_mean is not None else organoid_auc
    auc_std_label = organoid_auc_std if organoid_auc_std is not None else 0.0
    plot_roc_with_std(
        ax, organoid_mean_fpr, organoid_mean_tpr, organoid_std_tpr, '#6D6D6D',
        f"{organoid_model_label} (AUC={auc_label:.2f}±{auc_std_label:.2f})"
    )
ax.plot([0, 1], [0, 1], 'k--', lw=1, label='Random')
ax.set_xlabel('False Positive Rate', fontsize=11)
ax.set_ylabel('True Positive Rate', fontsize=11)
ax.set_title('ROC Comparison (ADMET-AI vs Organoid)', fontsize=12, fontweight='bold')
ax.legend(loc='lower right', fontsize=8)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'overall_roc_comparison.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'Overall_ROC_Comparison.png', dpi=300, bbox_inches='tight')
plt.close()

# Sort drugs alphabetically by name
merged_sorted = merged.copy()
merged_sorted = merged_sorted.sort_values('Drug', ascending=True).reset_index(drop=True)

# Plot 1: DICTrank Model Drug Predictions (SCATTER POINTS)
fig, ax = plt.subplots(figsize=(16, 6))

x_pos = np.arange(len(merged_sorted))

# Scatter points for each model (color by true heart damage)
hd_mask = merged_sorted['HD_binary'].astype(bool).values
admet_colors = np.where(hd_mask, '#2196F3', 'lightgray')
swiss_colors = np.where(hd_mask, '#FF9800', 'lightgray')

ax.scatter(x_pos, merged_sorted['DICT_Concern_Prob'], s=100, c=admet_colors,
           marker='o', edgecolor='black', linewidth=1.5, zorder=3)
ax.scatter(x_pos, merged_sorted['SwissADME_Prob'], s=100, c=swiss_colors,
           marker='s', edgecolor='black', linewidth=1.5, zorder=3)

ax.axhline(0.5, color='red', linestyle='--', linewidth=2, label='Threshold (0.5)', alpha=0.7)
ax.set_ylabel('DICT Concern Probability', fontsize=13, fontweight='bold')
ax.set_xlabel('Drug', fontsize=13, fontweight='bold')
ax.set_title('DICTrank Model Predictions (Trained on 555 Drugs)',
             fontsize=14, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels(merged_sorted['Drug'], rotation=45, ha='right', fontsize=9)
legend_handles = [
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#2196F3',
               markeredgecolor='black', label='ADMET-AI (HD+)', markersize=8),
    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#FF9800',
               markeredgecolor='black', label='SwissADME (HD+)', markersize=8),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgray',
               markeredgecolor='black', label='No Heart Damage', markersize=8),
    plt.Line2D([0], [0], color='red', linestyle='--', linewidth=2,
               label='Threshold (0.5)')
]
ax.legend(handles=legend_handles, loc='upper right', fontsize=11)
ax.set_ylim(-0.05, 1.15)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'dictrank_predictions.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'DICTrank_Predictions.png', dpi=300, bbox_inches='tight')
plt.close()

# Plot 2: LOOCV Model Drug Predictions (SCATTER POINTS)
# Note: ADMET-AI uses 25 drugs, SwissADME uses 23 drugs (missing Dactinomycin, Plicamycin)
fig, ax = plt.subplots(figsize=(16, 6))

loocv_admet_probs = []
loocv_swiss_probs = []
loocv_swiss_x_pos = []  # Only for drugs with SwissADME predictions

# Create mapping from drug name to SwissADME index
swiss_drug_to_idx = {drug: i for i, drug in enumerate(swiss_drug_names)}

for i, (_, row) in enumerate(merged_sorted.iterrows()):
    drug_idx = drug_names.index(row['Drug'])
    loocv_admet_probs.append(results_loocv['ADMET-AI']['y_prob'][drug_idx])
    # Only add SwissADME prob if drug is in Swiss dataset
    if row['Drug'] in swiss_drug_to_idx:
        swiss_idx = swiss_drug_to_idx[row['Drug']]
        loocv_swiss_probs.append(results_loocv['SwissADME']['y_prob'][swiss_idx])
        loocv_swiss_x_pos.append(x_pos[i])

ax.scatter(x_pos, loocv_admet_probs, s=100, c=admet_colors,
           marker='o', edgecolor='black', linewidth=1.5, zorder=3)
# Only plot SwissADME for the 23 drugs that have predictions
swiss_colors_23 = [c for i, c in enumerate(swiss_colors) if merged_sorted.iloc[i]['Drug'] in swiss_drug_names]
ax.scatter(loocv_swiss_x_pos, loocv_swiss_probs, s=100, c=swiss_colors_23,
           marker='s', edgecolor='black', linewidth=1.5, zorder=3)

ax.axhline(0.5, color='red', linestyle='--', linewidth=2, label='Threshold (0.5)', alpha=0.7)
ax.set_ylabel('Heart Damage Probability', fontsize=13, fontweight='bold')
ax.set_xlabel('Drug', fontsize=13, fontweight='bold')
ax.set_title('LOOCV Model Predictions (ADMET-AI: 25 drugs, SwissADME: 23 drugs)',
             fontsize=14, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels(merged_sorted['Drug'], rotation=45, ha='right', fontsize=9)
ax.legend(handles=legend_handles, loc='upper right', fontsize=11)
ax.set_ylim(-0.05, 1.15)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'loocv_predictions.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'LOOCV_Predictions.png', dpi=300, bbox_inches='tight')
plt.close()

# Plot 3: Scaffold-Balanced CV Predictions (SCATTER POINTS)
# Note: Scaffold CV also uses ADMET-AI (25 drugs) and SwissADME (23 drugs)
if results_scaffold:
    fig, ax = plt.subplots(figsize=(16, 6))

    scaffold_admet_probs = []
    scaffold_swiss_probs = []
    scaffold_swiss_x_pos = []

    for i, (_, row) in enumerate(merged_sorted.iterrows()):
        drug_idx = drug_names.index(row['Drug'])
        scaffold_admet_probs.append(results_scaffold['ADMET-AI']['y_prob'][drug_idx])
        # Only add SwissADME prob if drug is in Swiss dataset
        if row['Drug'] in swiss_drug_to_idx:
            swiss_idx = swiss_drug_to_idx[row['Drug']]
            scaffold_swiss_probs.append(results_scaffold['SwissADME']['y_prob'][swiss_idx])
            scaffold_swiss_x_pos.append(x_pos[i])

    ax.scatter(x_pos, scaffold_admet_probs, s=100, c=admet_colors,
               marker='o', edgecolor='black', linewidth=1.5, zorder=3)
    # Only plot SwissADME for the 23 drugs that have predictions
    scaffold_swiss_colors = [c for i, c in enumerate(swiss_colors) if merged_sorted.iloc[i]['Drug'] in swiss_drug_names]
    ax.scatter(scaffold_swiss_x_pos, scaffold_swiss_probs, s=100, c=scaffold_swiss_colors,
               marker='s', edgecolor='black', linewidth=1.5, zorder=3)

    ax.axhline(0.5, color='red', linestyle='--', linewidth=2, label='Threshold (0.5)', alpha=0.7)
    ax.set_ylabel('Heart Damage Probability', fontsize=13, fontweight='bold')
    ax.set_xlabel('Drug', fontsize=13, fontweight='bold')
    ax.set_title('Scaffold-Balanced CV Predictions (ADMET-AI: 25, SwissADME: 23 drugs)',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(merged_sorted['Drug'], rotation=45, ha='right', fontsize=9)
    ax.legend(handles=legend_handles, loc='upper right', fontsize=11)
    ax.set_ylim(-0.05, 1.15)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'scaffold_predictions.pdf', bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'Scaffold_Predictions.png', dpi=300, bbox_inches='tight')
    plt.close()

# Plot 4: LOOCV Confusion Matrices
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

for idx, model in enumerate(['ADMET-AI', 'SwissADME']):
    cm = results_loocv[model]['confusion_matrix']
    plot_confusion_matrix_with_percent(
        cm, ['No HD', 'HD'], axes[idx],
        f'{model}\nAccuracy: {results_loocv[model]["accuracy"]:.2f}'
    )

plt.suptitle('LOOCV Model Confusion Matrices', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'loocv_confusion_matrices.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'LOOCV_Confusion_Matrices.png', dpi=300, bbox_inches='tight')
plt.close()

# Plot 4B: Scaffold Confusion Matrices
if results_scaffold:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for idx, model in enumerate(['ADMET-AI', 'SwissADME']):
        cm = results_scaffold[model]['confusion_matrix']
        plot_confusion_matrix_with_percent(
            cm, ['No HD', 'HD'], axes[idx],
            f'{model}\nAccuracy: {results_scaffold[model]["accuracy"]:.2f}'
        )
    plt.suptitle('Scaffold CV Confusion Matrices', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'scaffold_confusion_matrices.pdf', bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'Scaffold_Confusion_Matrices.png', dpi=300, bbox_inches='tight')
    plt.close()

# Plot 4C: Organoid Confusion Matrix
if organoid_cm is not None:
    fig, ax = plt.subplots(figsize=(5, 4))
    plot_confusion_matrix_with_percent(
        organoid_cm, organoid_labels, ax,
        f'{organoid_model_label}\nAccuracy: {organoid_acc:.2f}'
    )
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'organoid_confusion_matrix.pdf', bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'Organoid_Confusion_Matrix.png', dpi=300, bbox_inches='tight')
    plt.close()

# Plot 5: LOOCV ROC Curves (mean +/- std)
fig, ax = plt.subplots(figsize=(8, 6))

for model in ['ADMET-AI', 'SwissADME']:
    r = results_loocv[model]
    label = f"{model} (AUC={r['auc_mean']:.2f}±{r['auc_std']:.2f})"
    plot_roc_with_std(ax, r['mean_fpr'], r['mean_tpr'], r['std_tpr'], colors[model], label)
ax.plot([0, 1], [0, 1], 'k--', lw=1)
ax.set_xlabel('False Positive Rate', fontsize=12)
ax.set_ylabel('True Positive Rate', fontsize=12)
ax.set_title('LOOCV Models ROC Curves\n(25 Cardiac RODEO Drugs)',
             fontsize=14, fontweight='bold')
ax.legend(loc='lower right', fontsize=11)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES_DIR / 'loocv_roc.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'LOOCV_ROC.png', dpi=300, bbox_inches='tight')
plt.close()

# Plot 5B: Scaffold ROC Curves (mean +/- std)
if results_scaffold:
    fig, ax = plt.subplots(figsize=(8, 6))
    for model in ['ADMET-AI', 'SwissADME']:
        r = results_scaffold[model]
        label = f"{model} (AUC={r['auc_mean']:.2f}±{r['auc_std']:.2f})"
        plot_roc_with_std(ax, r['mean_fpr'], r['mean_tpr'], r['std_tpr'], colors[model], label)
    ax.plot([0, 1], [0, 1], 'k--', lw=1)
    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title('Scaffold CV ROC Curves\n(25 Cardiac RODEO Drugs)',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=11)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'scaffold_roc.pdf', bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'Scaffold_ROC.png', dpi=300, bbox_inches='tight')
    plt.close()

# Plot 6: Accuracy Comparison (25 drugs + organoid model)
fig, ax = plt.subplots(figsize=(8, 5))

categories = ['DICTrank\n(25 drugs)', 'Scaffold CV\n(25 drugs)', 'LOOCV\n(25 drugs)', 'Organoid\n(25 drugs)']
x = np.arange(len(categories))
width = 0.2

accs_admet = [
    results_dictrank['ADMET-AI']['accuracy'],
    results_scaffold['ADMET-AI']['accuracy'] if results_scaffold else np.nan,
    results_loocv['ADMET-AI']['accuracy'],
    np.nan
]
accs_swiss = [
    results_dictrank['SwissADME']['accuracy'],
    results_scaffold['SwissADME']['accuracy'] if results_scaffold else np.nan,
    results_loocv['SwissADME']['accuracy'],
    np.nan
]
accs_organoid = [np.nan, np.nan, np.nan, organoid_acc]

bars1 = ax.bar(x - width, accs_admet, width, label='ADMET-AI',
               color='#2196F3', alpha=0.85, edgecolor='black')
bars2 = ax.bar(x, accs_swiss, width, label='SwissADME',
               color='#FF9800', alpha=0.85, edgecolor='black')
bars3 = ax.bar(x + width, accs_organoid, width, label=organoid_model_label,
               color='#6D6D6D', alpha=0.85, edgecolor='black')

ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
ax.set_xlabel('Evaluation Setting', fontsize=12, fontweight='bold')
ax.set_title('Accuracy Comparison (25 Drugs + Organoid Model)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend(loc='upper right')
ax.set_ylim(0, 1.0)
ax.grid(axis='y', alpha=0.3)

for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        if np.isnan(height):
            continue
        ax.annotate(f'{height:.2f}', xy=(bar.get_x() + bar.get_width()/2, height),
                   xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig(FIGURES_DIR / 'accuracy_comparison.pdf', bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'Accuracy_Comparison.png', dpi=300, bbox_inches='tight')
plt.close()

print("All plots saved!")

# =============================================================================
# GENERATE LATEX REPORT
# =============================================================================
print("\n" + "="*80)
print("GENERATING LATEX REPORT")
print("="*80)

# Helper formatters for LaTeX output
def fmt_optional(val):
    if val is None or pd.isna(val):
        return "-"
    return f"{val:.2f}"

def fmt_int_optional(val):
    if val is None or pd.isna(val):
        return "-"
    return str(int(val))

def fmt_delta(val):
    if val is None or pd.isna(val):
        return "-"
    return f"{val:+.2f}"

def latex_escape(text):
    text = str(text)
    return (text.replace('\\', r'\textbackslash{}')
                .replace('&', r'\&')
                .replace('%', r'\%')
                .replace('_', r'\_')
                .replace('#', r'\#')
                .replace('$', r'\$')
                .replace('{', r'\{')
                .replace('}', r'\}')
                .replace('^', r'\^{}')
                .replace('~', r'\~{}'))

# Create drug table with properly formatted SMILES
drug_table_rows = ""
for _, row in drugs_df.iterrows():
    smiles = row['SMILES']
    # Break SMILES into chunks of 35 characters
    smiles_chunks = [smiles[i:i+35] for i in range(0, len(smiles), 35)]
    smiles_formatted = '\\\\'.join([f'\\texttt{{{latex_escape(chunk)}}}' for chunk in smiles_chunks])

    drug_table_rows += f"    {row['Drug']} & {row['CID']} & {row['MolecularWeight']:.1f} & \\begin{{tabular}}[t]{{@{{}}l@{{}}}}{smiles_formatted}\\end{{tabular}} \\\\\n"

# Create prediction table
pred_table_rows = ""
for _, row in merged_sorted.iterrows():
    hd_label = "Yes" if row['HD_binary'] == 1 else "No"
    admet_pred = "High" if row['DICT_Concern_Prob'] >= 0.5 else "Low"
    swiss_prob = row['SwissADME_Prob']
    if pd.isna(swiss_prob):
        swiss_prob_fmt = "--"
        swiss_pred = "--"
    else:
        swiss_prob_fmt = f"{swiss_prob:.3f}"
        swiss_pred = "High" if swiss_prob >= 0.5 else "Low"
    pred_table_rows += (
        f"    {row['Drug']} & {hd_label} & {row['DICT_Concern_Prob']:.3f} & "
        f"{admet_pred} & {swiss_prob_fmt} & {swiss_pred} \\\\\n"
    )

paper_admet_roc = paper_results['ADMET-AI']['ROC_AUC']
paper_swiss_roc = paper_results['SwissADME']['ROC_AUC']
paper_admet_pr = fmt_optional(paper_results['ADMET-AI'].get('PR_AUC'))
paper_swiss_pr = fmt_optional(paper_results['SwissADME'].get('PR_AUC'))
paper_admet_acc = fmt_optional(paper_results['ADMET-AI'].get('ACC'))
paper_swiss_acc = fmt_optional(paper_results['SwissADME'].get('ACC'))

dictrank_vs_loocv_rows = ""
for model in ['ADMET-AI', 'SwissADME']:
    dic_acc = results_dictrank[model]['accuracy']
    loocv_acc = results_loocv[model]['accuracy']
    dic_auc = results_dictrank[model]['auc']
    loocv_auc = results_loocv[model]['auc']
    dictrank_vs_loocv_rows += (
        f"{model} & {dic_acc:.2f} & {loocv_acc:.2f} & {fmt_delta(loocv_acc - dic_acc)} & "
        f"{dic_auc:.2f} & {loocv_auc:.2f} & {fmt_delta(loocv_auc - dic_auc)} \\\\\n"
    )

dictrank_vs_scaffold_rows = ""
for model in ['ADMET-AI', 'SwissADME']:
    dic_acc = results_dictrank[model]['accuracy']
    dic_auc = results_dictrank[model]['auc']
    if results_scaffold:
        scaf_acc = results_scaffold[model]['accuracy']
        scaf_auc = results_scaffold[model]['auc_mean']
        dictrank_vs_scaffold_rows += (
            f"{model} & {dic_acc:.2f} & {fmt_optional(scaf_acc)} & {fmt_delta(scaf_acc - dic_acc)} & "
            f"{dic_auc:.2f} & {fmt_optional(scaf_auc)} & {fmt_delta(scaf_auc - dic_auc)} \\\\\n"
        )
    else:
        dictrank_vs_scaffold_rows += (
            f"{model} & {dic_acc:.2f} & - & - & {dic_auc:.2f} & - & - \\\\\n"
        )

def top5_rows(df):
    if df is None or df.empty:
        return [("-", None)] * 5
    rows = []
    for _, row in df.head(5).iterrows():
        rows.append((row['Feature'], row['MeanAbsSHAP']))
    while len(rows) < 5:
        rows.append(("-", None))
    return rows

dictrank_top = top5_rows(shap_top_features.get('DICTrank'))
loocv_top = top5_rows(shap_top_features.get('LOOCV'))
scaffold_top = top5_rows(shap_top_features.get('Scaffold'))

shap_table_rows = ""
for i in range(5):
    dic_feat, dic_val = dictrank_top[i]
    loo_feat, loo_val = loocv_top[i]
    sca_feat, sca_val = scaffold_top[i]
    shap_table_rows += (
        f"{i+1} & {latex_escape(dic_feat)} & {fmt_optional(dic_val)} & "
        f"{latex_escape(loo_feat)} & {fmt_optional(loo_val)} & "
        f"{latex_escape(sca_feat)} & {fmt_optional(sca_val)} \\\\\n"
    )

organoid_acc_fmt = fmt_optional(organoid_acc)
organoid_auc_fmt = fmt_optional(organoid_auc)
organoid_model_label_latex = latex_escape(organoid_model_label)

if results_scaffold:
    scaffold_admet_acc = fmt_optional(results_scaffold['ADMET-AI'].get('accuracy'))
    scaffold_swiss_acc = fmt_optional(results_scaffold['SwissADME'].get('accuracy'))
    scaffold_admet_auc = fmt_optional(results_scaffold['ADMET-AI'].get('auc_mean'))
    scaffold_swiss_auc = fmt_optional(results_scaffold['SwissADME'].get('auc_mean'))
    scaffold_admet_cm = results_scaffold['ADMET-AI']['confusion_matrix']
    scaffold_swiss_cm = results_scaffold['SwissADME']['confusion_matrix']
    scaffold_discussion = (
        "Scaffold-balanced CV yields mean ROC AUC of "
        f"{results_scaffold['ADMET-AI']['auc_mean']:.2f} (ADMET-AI) and "
        f"{results_scaffold['SwissADME']['auc_mean']:.2f} (SwissADME), "
        "reflecting generalization across scaffolds within the small panel."
    )
else:
    scaffold_admet_acc = "-"
    scaffold_swiss_acc = "-"
    scaffold_admet_auc = "-"
    scaffold_swiss_auc = "-"
    scaffold_admet_cm = np.array([[None, None], [None, None]])
    scaffold_swiss_cm = np.array([[None, None], [None, None]])
    scaffold_discussion = "Scaffold-balanced CV was skipped (chemprop not available)."

scaffold_section_tex = ""
if results_scaffold:
    scaffold_section_tex = rf"""
\section{{Scaffold-Balanced CV Models (25 Drugs)}}

\begin{{table}}[H]
\centering
\caption{{Scaffold-Balanced CV Model Performance (25 Drugs)}}
\begin{{tabular}}{{lcccccc}}
\toprule
\textbf{{Model}} & \textbf{{Accuracy}} & \textbf{{ROC AUC (mean)}} & \textbf{{TP}} & \textbf{{FN}} & \textbf{{TN}} & \textbf{{FP}} \\
\midrule
ADMET-AI & {scaffold_admet_acc} & {scaffold_admet_auc} & {fmt_int_optional(scaffold_admet_cm[1,1])} & {fmt_int_optional(scaffold_admet_cm[1,0])} & {fmt_int_optional(scaffold_admet_cm[0,0])} & {fmt_int_optional(scaffold_admet_cm[0,1])} \\
SwissADME & {scaffold_swiss_acc} & {scaffold_swiss_auc} & {fmt_int_optional(scaffold_swiss_cm[1,1])} & {fmt_int_optional(scaffold_swiss_cm[1,0])} & {fmt_int_optional(scaffold_swiss_cm[0,0])} & {fmt_int_optional(scaffold_swiss_cm[0,1])} \\
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{figure}}[H]
\centering
\begin{{minipage}}{{0.40\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/scaffold_accuracy_bar.pdf}}
\end{{minipage}}
\hfill
\begin{{minipage}}{{0.55\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/scaffold_roc.pdf}}
\end{{minipage}}
\caption{{Scaffold CV accuracy and ROC on 25 drugs.}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=\textwidth]{{figures/scaffold_confusion_matrices.pdf}}
\caption{{Scaffold CV confusion matrices.}}
\end{{figure}}
\textit{{Note: Accuracy shown in the confusion-matrix titles is fold-averaged across scaffold splits, while the matrix aggregates counts across all scaffold splits (10 seeds), so the diagonal may not match the title value.}}

\begin{{figure}}[H]
\centering
\includegraphics[width=\textwidth]{{figures/scaffold_predictions.pdf}}
\caption{{Scaffold CV predictions for each drug. Circles = ADMET-AI, Squares = SwissADME.}}
\end{{figure}}
"""
else:
    scaffold_section_tex = r"""
\section{Scaffold-Balanced CV Models (25 Drugs)}

Scaffold-balanced CV was skipped (chemprop not available).
"""

organoid_roc_tex = r"\textit{Organoid ROC curve unavailable.}"
if organoid_mean_fpr is not None and organoid_mean_tpr is not None and organoid_std_tpr is not None:
    organoid_roc_tex = r"\includegraphics[width=\textwidth]{figures/organoid_roc.pdf}"

organoid_confusion_tex = ""
if organoid_cm is not None:
    organoid_confusion_tex = r"""
\begin{figure}[H]
\centering
\includegraphics[width=0.6\textwidth]{figures/organoid_confusion_matrix.pdf}
\caption{Organoid confusion matrix (percent correct by class).}
\end{figure}
"""

scaffold_comparison_tex = ""
if results_scaffold:
    scaffold_comparison_tex = rf"""
\begin{{table}}[H]
\centering
\caption{{Scaffold CV vs DICTrank on 25 Drugs}}
\begin{{tabular}}{{lcccccc}}
\toprule
\textbf{{Model}} & \textbf{{DICTrank Acc}} & \textbf{{Scaffold Acc}} & \textbf{{$\Delta$ Acc}} & \textbf{{DICTrank AUC}} & \textbf{{Scaffold AUC}} & \textbf{{$\Delta$ AUC}} \\
\midrule
{dictrank_vs_scaffold_rows}\bottomrule
\end{{tabular}}
\end{{table}}
"""

dictrank_train_confusion_tex = ""
if dictrank_train_confusion:
    dictrank_train_confusion_tex = r"""
\begin{figure}[H]
\centering
\includegraphics[width=0.85\textwidth]{figures/dictrank_training_confusion.pdf}
\caption{DICTrank training confusion matrices (10-fold CV on 555 drugs).}
\end{figure}
"""

supplementary_scripts_tex = r"""
\section*{Supplementary: Scripts Used}
\begin{itemize}
    \item \texttt{ADMET\_Comparison/Scripts/retrain\_dictrank\_models.py} --- Retrains DICTrank models with scaffold-balanced CV and saves training metrics.
    \item \texttt{ADMET\_Comparison/Scripts/predict\_retrained\_dictrank.py} --- Runs trained DICTrank models on the 25-drug feature tables.
    \item \texttt{ADMET\_Comparison/Scripts/run\_predictions\_v2.py} --- Generates ADMET-AI features for Cardiac RODEO SMILES and DICT predictions.
    \item \texttt{ADMET\_Comparison/Scripts/predict\_swissadme.py} --- Trains SwissADME model and predicts DICT concern for 25 drugs.
    \item \texttt{ADMET\_Comparison/Scripts/full\_analysis.py} --- Assembles plots, tables, and the LaTeX report.
    \item \texttt{Prediction\_Models/loocv\_model\_comparison.py} --- LOOCV pipeline and ROC Excel export used for organoid comparisons.
\end{itemize}
"""

latex_content = rf"""\documentclass[11pt]{{article}}
\usepackage[margin=0.75in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{float}}
\usepackage{{hyperref}}
\usepackage{{amsmath}}
\usepackage{{longtable}}
\usepackage{{array}}

\title{{Computational Prediction of Drug-Induced Heart Damage:\\
ADMET-AI vs SwissADME Comparison\\
\large Analysis of 25 Cardiac RODEO Drugs}}
\author{{Cardiac RODEO Project}}
\date{{\today}}

\begin{{document}}
\maketitle

\begin{{abstract}}
This report compares two computational approaches for predicting drug-induced heart damage:
ADMET-AI (41 ADMET properties) and SwissADME (43 physicochemical properties).
We replicate published DICTrank benchmark results, evaluate predictions on 25 Cardiac RODEO drugs,
and train new models using Leave-One-Out Cross-Validation (LOOCV) and scaffold-balanced CV.
\end{{abstract}}

\section{{DICTrank Model: Training and 25-Drug Inference}}

\textbf{{Part 1: DICTrank model replication.}}
We retrain the published DICTrank models on the DICTrank dataset (555 drugs: 293 most DICT concern, 262 no concern)
using 10-fold scaffold-balanced cross-validation to confirm benchmark performance.

\textbf{{Part 2: 25-drug inference.}}
We then generate features from the 25 Cardiac RODEO SMILES and pass them through the trained DICTrank models
to obtain DICT concern probabilities (no retraining on the 25-drug set).

\subsection{{Process Summary}}
\begin{{itemize}}
    \item \textbf{{Training data:}} DICTrank 555-drug dataset (most vs no concern).
    \item \textbf{{Models:}} GradientBoostingClassifier (n\_estimators=500, max\_depth=12, learning\_rate=0.1, random\_state=0).
    \item \textbf{{Validation:}} 10-fold scaffold-balanced CV; fold test predictions concatenated for ROC/AUC and confusion matrices.
    \item \textbf{{Decision rule:}} probability $\ge$ 0.5 for DICT concern.
    \item \textbf{{25-drug inference:}} ADMET-AI features computed for 25 drugs; SwissADME features available for 23 drugs, then passed through the trained DICTrank models (no retraining).
    \item \textbf{{SwissADME coverage:*}} Dactinomycin and Plicamycin are excluded due to size; SwissADME columns are shown as ``--''.
\end{{itemize}}

\begin{{table}}[H]
\centering
\caption{{DICTrank Training Results (10-Fold CV)}}
\begin{{tabular}}{{lccc}}
\toprule
\textbf{{Model}} & \textbf{{ROC AUC}} & \textbf{{PR AUC}} & \textbf{{Accuracy}} \\
\midrule
ADMET-AI & {paper_admet_roc:.2f} & {paper_admet_pr} & {paper_admet_acc} \\
SwissADME & {paper_swiss_roc:.2f} & {paper_swiss_pr} & {paper_swiss_acc} \\
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{figure}}[H]
\centering
\begin{{minipage}}{{0.48\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/dictrank_retrain_roc.pdf}}
\end{{minipage}}
\hfill
\begin{{minipage}}{{0.40\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/dictrank_training_accuracy.pdf}}
\end{{minipage}}
\caption{{DICTrank training ROC and accuracy (10-fold CV on 555 drugs).}}
\end{{figure}}
{dictrank_train_confusion_tex}

\subsection{{Cardiac RODEO Drug Dataset}}

Our dataset contains 25 drugs with experimentally determined cardiac outcomes:
\begin{{itemize}}
    \item Heart Damage Positive: {merged['HD_binary'].sum()}/25 drugs ({100*merged['HD_binary'].sum()/25:.0f}\\%)
    \item Heart Damage Negative: {25 - merged['HD_binary'].sum()}/25 drugs ({100*(25-merged['HD_binary'].sum())/25:.0f}\\%)
\end{{itemize}}

\begin{{longtable}}{{lcc>{{\raggedright\arraybackslash}}p{{7cm}}}}
\caption{{Drug Database with SMILES and Sources}} \\
\toprule
\textbf{{Drug}} & \textbf{{CID}} & \textbf{{MW}} & \textbf{{SMILES}} \\
\midrule
\endfirsthead
\toprule
\textbf{{Drug}} & \textbf{{CID}} & \textbf{{MW}} & \textbf{{SMILES}} \\
\midrule
\endhead
{drug_table_rows}\bottomrule
\end{{longtable}}

All drugs sourced from PubChem (https://pubchem.ncbi.nlm.nih.gov).

\subsection{{DICTrank Inference on 25 Drugs}}

\begin{{table}}[H]
\centering
\caption{{DICTrank Model Performance (ADMET-AI: 25 drugs, SwissADME: 23 drugs)}}
\begin{{tabular}}{{lcccccc}}
\toprule
\textbf{{Model}} & \textbf{{Accuracy}} & \textbf{{ROC AUC}} & \textbf{{TP}} & \textbf{{FN}} & \textbf{{TN}} & \textbf{{FP}} \\
\midrule
ADMET-AI & {results_dictrank['ADMET-AI']['accuracy']:.2f} & {results_dictrank['ADMET-AI']['auc']:.2f} & {results_dictrank['ADMET-AI']['confusion_matrix'][1,1]} & {results_dictrank['ADMET-AI']['confusion_matrix'][1,0]} & {results_dictrank['ADMET-AI']['confusion_matrix'][0,0]} & {results_dictrank['ADMET-AI']['confusion_matrix'][0,1]} \\
SwissADME & {results_dictrank['SwissADME']['accuracy']:.2f} & {results_dictrank['SwissADME']['auc']:.2f} & {results_dictrank['SwissADME']['confusion_matrix'][1,1]} & {results_dictrank['SwissADME']['confusion_matrix'][1,0]} & {results_dictrank['SwissADME']['confusion_matrix'][0,0]} & {results_dictrank['SwissADME']['confusion_matrix'][0,1]} \\
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{figure}}[H]
\centering
\begin{{minipage}}{{0.40\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/dictrank_accuracy_bar.pdf}}
\end{{minipage}}
\hfill
\begin{{minipage}}{{0.55\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/dictrank_roc_25.pdf}}
\end{{minipage}}
\caption{{DICTrank accuracy and ROC (ADMET-AI: 25 drugs, SwissADME: 23 drugs).}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.85\textwidth]{{figures/dictrank_confusion_matrices.pdf}}
\caption{{Confusion matrices for DICTrank models (ADMET-AI: 25 drugs, SwissADME: 23 drugs).}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=\textwidth]{{figures/dictrank_predictions.pdf}}
\caption{{DICTrank predictions for each drug. Circles = ADMET-AI, Squares = SwissADME*.}}
\end{{figure}}
\textit{{*SwissADME unavailable for Dactinomycin and Plicamycin due to size; SwissADME columns shown as ``--''.}}

\begin{{longtable}}{{lccccc}}
\caption{{Individual Drug Predictions (DICTrank Models)}} \\
\toprule
\textbf{{Drug}} & \textbf{{True HD}} & \textbf{{ADMET Prob}} & \textbf{{Pred}} & \textbf{{Swiss Prob}} & \textbf{{Pred}} \\
\midrule
\endfirsthead
\toprule
\textbf{{Drug}} & \textbf{{True HD}} & \textbf{{ADMET Prob}} & \textbf{{Pred}} & \textbf{{Swiss Prob}} & \textbf{{Pred}} \\
\midrule
\endhead
{pred_table_rows}\bottomrule
\end{{longtable}}

\section{{LOOCV Models (25 Drugs)}}

We retrain ADMET-AI and SwissADME models directly on the 25 Cardiac RODEO drugs.

\begin{{table}}[H]
\centering
\caption{{LOOCV Model Performance}}
\begin{{tabular}}{{lcccccc}}
\toprule
\textbf{{Model}} & \textbf{{Accuracy}} & \textbf{{ROC AUC}} & \textbf{{TP}} & \textbf{{FN}} & \textbf{{TN}} & \textbf{{FP}} \\
\midrule
ADMET-AI & {results_loocv['ADMET-AI']['accuracy']:.2f} & {results_loocv['ADMET-AI']['auc']:.2f} & {results_loocv['ADMET-AI']['confusion_matrix'][1,1]} & {results_loocv['ADMET-AI']['confusion_matrix'][1,0]} & {results_loocv['ADMET-AI']['confusion_matrix'][0,0]} & {results_loocv['ADMET-AI']['confusion_matrix'][0,1]} \\
SwissADME & {results_loocv['SwissADME']['accuracy']:.2f} & {results_loocv['SwissADME']['auc']:.2f} & {results_loocv['SwissADME']['confusion_matrix'][1,1]} & {results_loocv['SwissADME']['confusion_matrix'][1,0]} & {results_loocv['SwissADME']['confusion_matrix'][0,0]} & {results_loocv['SwissADME']['confusion_matrix'][0,1]} \\
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{figure}}[H]
\centering
\begin{{minipage}}{{0.40\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/loocv_accuracy_bar.pdf}}
\end{{minipage}}
\hfill
\begin{{minipage}}{{0.55\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/loocv_roc.pdf}}
\end{{minipage}}
\caption{{LOOCV accuracy and ROC on 25 drugs.}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=\textwidth]{{figures/loocv_confusion_matrices.pdf}}
\caption{{LOOCV confusion matrices (percent correct per class).}}
\end{{figure}}
\textit{{Note: Accuracy shown in the confusion-matrix titles is fold-averaged across LOOCV splits, while the matrix aggregates pooled predictions, so the diagonal may not match the title value.}}

\begin{{figure}}[H]
\centering
\includegraphics[width=\textwidth]{{figures/loocv_predictions.pdf}}
\caption{{LOOCV predictions for each drug. Circles = ADMET-AI, Squares = SwissADME.}}
\end{{figure}}

""" + scaffold_section_tex + rf"""

\section{{Organoid Model (LOOCV Comparison Pipeline)}}

We include the organoid-trained model from the LOOCV model comparison pipeline for direct comparison on the 25 drugs.

\begin{{table}}[H]
\centering
\caption{{Organoid Model Performance on 25 Drugs}}
\begin{{tabular}}{{lcc}}
\toprule
\textbf{{Model}} & \textbf{{Accuracy}} & \textbf{{ROC AUC}} \\
\midrule
{organoid_model_label_latex} & {organoid_acc_fmt} & {organoid_auc_fmt} \\
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{figure}}[H]
\centering
\begin{{minipage}}{{0.40\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/organoid_accuracy_bar.pdf}}
\end{{minipage}}
\hfill
\begin{{minipage}}{{0.55\textwidth}}
\centering
""" + organoid_roc_tex + rf"""
\end{{minipage}}
\caption{{Organoid accuracy and ROC on 25 drugs.}}
\end{{figure}}

""" + organoid_confusion_tex + rf"""

\section{{Overall Comparison}}

\begin{{figure}}[H]
\centering
\begin{{minipage}}{{0.40\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/accuracy_comparison.pdf}}
\end{{minipage}}
\hfill
\begin{{minipage}}{{0.55\textwidth}}
\centering
\includegraphics[width=\textwidth]{{figures/overall_roc_comparison.pdf}}
\end{{minipage}}
\caption{{Overall comparison: accuracy and ROC (ADMET-AI vs organoid).}}
\end{{figure}}

\begin{{table}}[H]
\centering
\caption{{LOOCV vs DICTrank on 25 Drugs}}
\begin{{tabular}}{{lcccccc}}
\toprule
\textbf{{Model}} & \textbf{{DICTrank Acc}} & \textbf{{LOOCV Acc}} & \textbf{{$\Delta$ Acc}} & \textbf{{DICTrank AUC}} & \textbf{{LOOCV AUC}} & \textbf{{$\Delta$ AUC}} \\
\midrule
{dictrank_vs_loocv_rows}\bottomrule
\end{{tabular}}
\end{{table}}
""" + scaffold_comparison_tex + rf"""

\section{{Feature Importance (SHAP, ADMET-AI)}}

\clearpage
\subsection{{DICTrank}}
\begin{{figure}}[H]
\centering
\includegraphics[width=0.85\textwidth]{{figures/dictrank_shap_features.pdf}}
\caption{{DICTrank ADMET-AI feature influence (paper-aligned ordering).}}
\end{{figure}}

\clearpage
\subsection{{LOOCV}}
\begin{{figure}}[H]
\centering
\includegraphics[width=0.85\textwidth]{{figures/loocv_shap_features.pdf}}
\caption{{LOOCV ADMET-AI feature influence.}}
\end{{figure}}

\clearpage
\subsection{{Scaffold CV}}
\begin{{figure}}[H]
\centering
\includegraphics[width=0.85\textwidth]{{figures/scaffold_shap_features.pdf}}
\caption{{Scaffold CV ADMET-AI feature influence.}}
\end{{figure}}

{supplementary_scripts_tex}

\section*{{References}}
Mukherjee P, et al. (2025). ADMET-AI Enables Interpretable Predictions of Drug-Induced Cardiotoxicity. \textit{{Clinical Pharmacology \& Therapeutics}}.

\end{{document}}
"""



report_name = 'Cardiac_RODEO_LaTeX_Report'
report_tex = OUTPUT_DIR / f'{report_name}.tex'
with open(report_tex, 'w') as f:
    f.write(latex_content)

# Compile PDF
pdf_path = OUTPUT_DIR / f'{report_name}.pdf'
try:
    for _ in range(2):
        subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', report_tex.name],
            cwd=OUTPUT_DIR,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    print(f"PDF saved to: {pdf_path}")
except FileNotFoundError:
    print("pdflatex not found; skipping PDF generation.")
except subprocess.CalledProcessError:
    print("pdflatex failed; check LaTeX logs in the report folder.")

# Create ZIP file
zip_path = OUTPUT_DIR / f'{report_name}.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(report_tex, report_tex.name)
    if pdf_path.exists():
        zipf.write(pdf_path, pdf_path.name)
    for file in FIGURES_DIR.glob('*.pdf'):
        zipf.write(file, f'figures/{file.name}')

final_pdf = LATEX_OUTPUT_DIR / pdf_path.name
final_zip = LATEX_OUTPUT_DIR / zip_path.name
if final_pdf.exists():
    final_pdf.unlink()
if final_zip.exists():
    final_zip.unlink()
if pdf_path.exists():
    shutil.move(pdf_path, final_pdf)
if zip_path.exists():
    shutil.move(zip_path, final_zip)

print(f"\nLaTeX report saved to: {report_tex}")
if final_pdf.exists():
    print(f"PDF saved to: {final_pdf}")
print(f"ZIP file saved to: {final_zip}")

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)

print("\n+-------------------------------------------------------------+")
print("|                    ROC AUC COMPARISON                       |")
print("+-------------------------------------------------------------+")
print("| Setting                     | ADMET-AI    | SwissADME      |")
print("+-------------------------------------------------------------+")
print(f"| DICTrank Training (10-CV)   |    {paper_results['ADMET-AI']['ROC_AUC']:.2f}     |    {paper_results['SwissADME']['ROC_AUC']:.2f}        |")
print(f"| DICTrank -> 25 drugs        |    {results_dictrank['ADMET-AI']['auc']:.2f}     |    {results_dictrank['SwissADME']['auc']:.2f}        |")
if results_scaffold:
    print(f"| Scaffold CV (25 drugs)      |    {results_scaffold['ADMET-AI']['auc_mean']:.2f}     |    {results_scaffold['SwissADME']['auc_mean']:.2f}        |")
print(f"| LOOCV (25 drugs)            |    {results_loocv['ADMET-AI']['auc']:.2f}     |    {results_loocv['SwissADME']['auc']:.2f}        |")
if not pd.isna(organoid_auc):
    print(f"| Organoid (25 drugs)         |    {organoid_auc:.2f}     |    -              |")
print("+-------------------------------------------------------------+")

print("\n" + "="*80)
print("ANALYSIS COMPLETE!")
print("="*80)
print(f"\nGenerated {len(list(FIGURES_DIR.glob('*.pdf')))} plots")
print(f"\nOutput files:")
print(f"  - {final_zip}")
if final_pdf.exists():
    print(f"  - {final_pdf}")
print(f"  - {OUTPUT_DIR / 'dictrank_retrain_metrics.csv'}")
print(f"  - {OUTPUT_DIR / 'dictrank_retrain_roc.pdf'}")
print(f"  - {OUTPUT_DIR / 'dictrank_retrain_predictions_25.csv'}")
if (OUTPUT_DIR / "DICTrank_Training_Confusion.png").exists():
    print(f"  - {OUTPUT_DIR / 'DICTrank_Training_Confusion.png'}")
print(f"  - {OUTPUT_DIR / 'DICTrank_Predictions.png'}")
if results_scaffold:
    print(f"  - {OUTPUT_DIR / 'Scaffold_Predictions.png'}")
print(f"  - {OUTPUT_DIR / 'LOOCV_Predictions.png'}")
print(f"  - {OUTPUT_DIR / 'LOOCV_ROC.png'}")
print(f"  - {OUTPUT_DIR / 'LOOCV_Confusion_Matrices.png'}")
print(f"  - {OUTPUT_DIR / 'Accuracy_Comparison.png'}")
print(f"  - {OUTPUT_DIR / 'dictrank_shap_mean_abs.csv'}")
print(f"  - {OUTPUT_DIR / 'loocv_admet_shap_mean_abs.csv'}")
print(f"  - {OUTPUT_DIR / 'scaffold_admet_shap_mean_abs.csv'}")
