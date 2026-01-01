"""
Full comparison of 3 prediction methods:
1. ADMET-AI (41 features from ADMEThyst)
2. SwissADME (RDKit-computed features)
3. Cardiac Organoid (PK-PD coefficients from your notebook)

Creates overlaid ROC curves and comprehensive analysis.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc, confusion_matrix
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from pathlib import Path
import joblib
import pickle
import warnings
warnings.filterwarnings('ignore')

# RDKit imports
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors

# Set up paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ADMETHYST_MAIN_DIR = PROJECT_ROOT / "ADMEThyst-main"

DATA_DIR = ADMETHYST_MAIN_DIR / "data"
MODELS_DIR = ADMETHYST_MAIN_DIR / "models" / "ensemble"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
ORGANOID_MODELS_DIR = PROJECT_ROOT / "Output" / "Model_Properties"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SMILES_PATH = OUTPUT_DIR / "cardiac_rodeo_drugs_smiles.csv"
if not SMILES_PATH.exists():
    fallback = DATA_DIR / "cardiac_rodeo_drugs_smiles.csv"
    if fallback.exists():
        SMILES_PATH = fallback
    else:
        raise FileNotFoundError(
            "Missing cardiac_rodeo_drugs_smiles.csv. "
            f"Expected at {OUTPUT_DIR / 'cardiac_rodeo_drugs_smiles.csv'} "
            f"(or {fallback})."
        )

print("="*80)
print("THREE-WAY COMPARISON: ADMET-AI vs SwissADME vs Cardiac Organoid")
print("="*80)

# ============================================================================
# LOAD DATA
# ============================================================================
print("\n[1] Loading data...")

# Load actual labels
excel_path = PROJECT_ROOT / "EQN_Coefficients" / "all_equations_coefficients.xlsx"
df_raw = pd.read_excel(excel_path, sheet_name='pkpd_elimination', header=1)
df_raw.columns = df_raw.columns.str.strip()

# Get unique drugs with labels
drugs_labels = df_raw[['Drug', 'Arrhythmia', 'heart_damage', 'Concern']].drop_duplicates()
drugs_labels = drugs_labels.dropna(subset=['Arrhythmia', 'heart_damage', 'Concern'])

# Convert labels to binary
def to_binary(val):
    val_str = str(val).lower().strip()
    return 1 if val_str == 'true' else 0

drugs_labels['AR_binary'] = drugs_labels['Arrhythmia'].apply(to_binary)
drugs_labels['HD_binary'] = drugs_labels['heart_damage'].apply(to_binary)
drugs_labels['Any_Cardiotox'] = ((drugs_labels['AR_binary'] == 1) | (drugs_labels['HD_binary'] == 1)).astype(int)

print(f"    Loaded labels for {len(drugs_labels)} drugs")

# ============================================================================
# METHOD 1: ADMET-AI predictions (already computed)
# ============================================================================
print("\n[2] Loading ADMET-AI predictions...")
admet_preds = pd.read_csv(OUTPUT_DIR / "cardiac_rodeo_DICT_predictions.csv")
print(f"    ADMET-AI: {len(admet_preds)} predictions loaded")

# ============================================================================
# METHOD 2: SwissADME predictions
# ============================================================================
print("\n[3] Computing SwissADME predictions...")

def compute_swissadme_features(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    features = {}
    features['MW'] = Descriptors.MolWt(mol)
    features['#Heavy atoms'] = Descriptors.HeavyAtomCount(mol)
    features['#Aromatic heavy atoms'] = len([a for a in mol.GetAtoms() if a.GetIsAromatic()])
    features['Fraction Csp3'] = rdMolDescriptors.CalcFractionCSP3(mol)
    features['#Rotatable bonds'] = Descriptors.NumRotatableBonds(mol)
    features['#H-bond acceptors'] = Descriptors.NumHAcceptors(mol)
    features['#H-bond donors'] = Descriptors.NumHDonors(mol)
    features['MR'] = Crippen.MolMR(mol)
    features['TPSA'] = Descriptors.TPSA(mol)
    features['Consensus Log P'] = Crippen.MolLogP(mol)
    features['WLOGP'] = Crippen.MolLogP(mol)
    ha = features['#Heavy atoms'] if features['#Heavy atoms'] > 0 else 1
    features['ESOL Log S'] = 0.16 - 0.63 * features['Consensus Log P'] - 0.0062 * features['MW'] + 0.066 * features['#Rotatable bonds'] - 0.74 * features['#Aromatic heavy atoms'] / ha
    features['log Kp (cm/s)'] = -2.5 + 0.0256 * features['MW'] - 0.5 * features['TPSA'] / 10
    lipinski_violations = sum([
        features['MW'] > 500,
        features['Consensus Log P'] > 5,
        features['#H-bond donors'] > 5,
        features['#H-bond acceptors'] > 10
    ])
    features['Lipinski #violations'] = lipinski_violations
    features['Bioavailability Score'] = 0.55 if lipinski_violations <= 1 else 0.17
    features['Synthetic Accessibility'] = rdMolDescriptors.CalcNumRings(mol) + features['#Rotatable bonds'] / 5
    return features

drugs_smiles = pd.read_csv(SMILES_PATH)
swissadme_features = []
for _, row in drugs_smiles.iterrows():
    feats = compute_swissadme_features(row['SMILES'])
    if feats:
        feats['Drug'] = row['Drug']
        swissadme_features.append(feats)
swissadme_df = pd.DataFrame(swissadme_features)

# Train SwissADME model on DICTrank data
swissadme_Xvals = pd.read_csv(DATA_DIR / "SwissADME_Xvals.csv", index_col=0)
swissadme_yvals = pd.read_csv(DATA_DIR / "SwissADME_yvals.csv", index_col=0)
common_features = [col for col in swissadme_Xvals.columns if col in swissadme_df.columns]

X_train = swissadme_Xvals[common_features].fillna(0)
y_train = swissadme_yvals.values.ravel()
swissadme_model = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
swissadme_model.fit(X_train, y_train)

X_test = swissadme_df[common_features].fillna(0)
swissadme_df['SwissADME_Prob'] = swissadme_model.predict_proba(X_test)[:, 1]
print(f"    SwissADME: {len(swissadme_df)} predictions computed")

# ============================================================================
# METHOD 3: Cardiac Organoid PK-PD Model
# ============================================================================
print("\n[4] Loading Cardiac Organoid PK-PD models...")

# Extract PK-PD features (same as in utils.py from your notebook)
pkpd_coef_names = ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim']

def extract_features(df):
    """Extract 14 features from PK-PD coefficients (7 Contractility + 7 O2)"""
    features = []
    # Contractility coefficients (no suffix)
    for param in pkpd_coef_names:
        if param in df.columns:
            features.append(df[param].values)
        else:
            features.append(np.full(len(df), np.nan))
    # O2 coefficients (with .1 suffix)
    for param in pkpd_coef_names:
        param_o2 = f'{param}.1'
        if param_o2 in df.columns:
            features.append(df[param_o2].values)
        else:
            features.append(np.full(len(df), np.nan))
    # Feature names - MUST match what the models were trained with
    feature_names = [f'{p}_Contractility' for p in pkpd_coef_names] + \
                    [f'{p}_O2' for p in pkpd_coef_names]
    features_df = pd.DataFrame(
        np.column_stack(features),
        columns=feature_names,
        index=df.index
    )
    return features_df

# Get unique drug rows and extract features
drug_rows = []
for drug in drugs_labels['Drug'].values:
    drug_data = df_raw[df_raw['Drug'] == drug].iloc[0:1]  # Get first row for this drug
    if len(drug_data) > 0:
        drug_rows.append(drug_data)

if drug_rows:
    combined_drug_data = pd.concat(drug_rows, ignore_index=True)
    organoid_features = extract_features(combined_drug_data)
    organoid_features['Drug'] = combined_drug_data['Drug'].values
    organoid_df = organoid_features

print(f"    Extracted {len(organoid_df.columns)-1} PK-PD features for {len(organoid_df)} drugs")

# Merge features with labels to train/predict
feature_cols = [c for c in organoid_df.columns if c != 'Drug']
organoid_with_labels = organoid_df.merge(drugs_labels[['Drug', 'AR_binary', 'HD_binary']], on='Drug')
X_organoid = organoid_with_labels[feature_cols].fillna(0)
y_arrhythmia = organoid_with_labels['AR_binary'].values
y_heart_damage = organoid_with_labels['HD_binary'].values

from sklearn.model_selection import cross_val_predict, LeaveOneOut
from xgboost import XGBClassifier

# Use LeaveOneOut cross-validation (LOOCV)
loo = LeaveOneOut()

# Train Heart Damage model with LOOCV (focus on Heart Damage only)
print("    Training Heart Damage XGBoost with LOOCV...")
hd_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler()),
    ('xgb', XGBClassifier(n_estimators=50, max_depth=2, random_state=42, eval_metric='logloss'))
])
hd_probs = cross_val_predict(hd_pipeline, X_organoid, y_heart_damage, cv=loo, method='predict_proba')[:, 1]
organoid_with_labels['Organoid_HD_Prob'] = hd_probs
print(f"    Heart Damage CV predictions complete!")

# Transfer back to organoid_df (Heart Damage only)
organoid_df = organoid_with_labels[['Drug', 'Organoid_HD_Prob']].copy()

# ============================================================================
# MERGE ALL DATA
# ============================================================================
print("\n[5] Merging all predictions...")

merged = drugs_labels.merge(admet_preds[['Drug', 'DICT_Concern_Prob']], on='Drug')
merged = merged.merge(swissadme_df[['Drug', 'SwissADME_Prob']], on='Drug')
merged = merged.merge(organoid_df[['Drug', 'Organoid_HD_Prob']], on='Drug')

print(f"    Merged data for {len(merged)} drugs")

# ============================================================================
# CREATE OVERLAID ROC PLOT (ALL 3 METHODS - Heart Damage only)
# ============================================================================
print("\n[6] Generating overlaid ROC curve (3 methods - Heart Damage)...")

# Colors for each method
admet_color = '#2196F3'    # Blue
swiss_color = '#FF9800'    # Orange
organoid_color = '#4CAF50'  # Green

fig, ax = plt.subplots(figsize=(8, 7))

# Heart Damage target only
y_true = merged['HD_binary'].values

# ADMET-AI ROC
fpr_admet, tpr_admet, _ = roc_curve(y_true, merged['DICT_Concern_Prob'].values)
auc_admet = auc(fpr_admet, tpr_admet)

# SwissADME ROC
fpr_swiss, tpr_swiss, _ = roc_curve(y_true, merged['SwissADME_Prob'].values)
auc_swiss = auc(fpr_swiss, tpr_swiss)

# Organoid ROC
fpr_org, tpr_org, _ = roc_curve(y_true, merged['Organoid_HD_Prob'].values)
auc_org = auc(fpr_org, tpr_org)

results_summary = [{
    'Target': 'Heart Damage',
    'ADMET-AI AUC': auc_admet,
    'SwissADME AUC': auc_swiss,
    'Organoid AUC': auc_org
}]

# Plot all three
ax.plot(fpr_admet, tpr_admet, color=admet_color, lw=3,
        label=f'ADMET-AI (AUC = {auc_admet:.3f})')
ax.fill_between(fpr_admet, tpr_admet, alpha=0.15, color=admet_color)

ax.plot(fpr_swiss, tpr_swiss, color=swiss_color, lw=3, linestyle='--',
        label=f'SwissADME (AUC = {auc_swiss:.3f})')
ax.fill_between(fpr_swiss, tpr_swiss, alpha=0.15, color=swiss_color)

ax.plot(fpr_org, tpr_org, color=organoid_color, lw=3, linestyle='-.',
        label=f'Cardiac Organoid (AUC = {auc_org:.3f})')
ax.fill_between(fpr_org, tpr_org, alpha=0.15, color=organoid_color)

ax.plot([0, 1], [0, 1], 'k:', lw=1.5, label='Random (AUC = 0.500)')

ax.set_xlabel('False Positive Rate', fontsize=12)
ax.set_ylabel('True Positive Rate', fontsize=12)
ax.set_title('ROC Comparison: Heart Damage Prediction', fontsize=14, fontweight='bold')
ax.legend(loc='lower right', fontsize=10)
ax.set_xlim([0.0, 1.0])
ax.set_ylim([0.0, 1.05])
ax.grid(True, alpha=0.3)

plt.tight_layout()
fig.savefig(OUTPUT_DIR / "Three_Method_ROC_Comparison.png", dpi=300, bbox_inches='tight')
fig.savefig(OUTPUT_DIR / "Three_Method_ROC_Comparison.pdf", bbox_inches='tight')
print(f"    Saved: Three_Method_ROC_Comparison.png")
plt.close()

# ============================================================================
# PRINT RESULTS SUMMARY
# ============================================================================
print("\n" + "="*80)
print("ROC AUC COMPARISON SUMMARY")
print("="*80)
print(f"\n{'Target':<22} {'ADMET-AI':>12} {'SwissADME':>12} {'Organoid':>12} {'Best':>12}")
print("-"*70)
for r in results_summary:
    aucs = [r['ADMET-AI AUC'], r['SwissADME AUC'], r['Organoid AUC']]
    names = ['ADMET-AI', 'SwissADME', 'Organoid']
    best_idx = np.argmax(aucs)
    best = names[best_idx]
    print(f"{r['Target']:<22} {r['ADMET-AI AUC']:>12.3f} {r['SwissADME AUC']:>12.3f} {r['Organoid AUC']:>12.3f} {best:>12}")

# Average AUC
avg_admet = np.mean([r['ADMET-AI AUC'] for r in results_summary])
avg_swiss = np.mean([r['SwissADME AUC'] for r in results_summary])
avg_org = np.mean([r['Organoid AUC'] for r in results_summary])
print("-"*70)
print(f"{'AVERAGE':<22} {avg_admet:>12.3f} {avg_swiss:>12.3f} {avg_org:>12.3f}")

# ============================================================================
# CREATE COMPARISON BAR CHART
# ============================================================================
print("\n[7] Generating summary bar chart...")

fig, ax = plt.subplots(figsize=(8, 6))

# For Heart Damage only
methods = ['ADMET-AI', 'SwissADME', 'Cardiac Organoid']
aucs = [auc_admet, auc_swiss, auc_org]
colors = [admet_color, swiss_color, organoid_color]

x = np.arange(len(methods))
bars = ax.bar(x, aucs, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

ax.axhline(0.5, color='red', linestyle='--', linewidth=2, label='Random (0.5)')
ax.set_ylabel('ROC AUC', fontsize=14)
ax.set_title('Heart Damage Prediction: Method Comparison', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(methods, fontsize=12)
ax.legend(loc='lower right', fontsize=10)
ax.set_ylim(0, 1.1)
ax.grid(True, axis='y', alpha=0.3)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.annotate(f'{height:.3f}',
               xy=(bar.get_x() + bar.get_width() / 2, height),
               xytext=(0, 5), textcoords="offset points",
               ha='center', va='bottom', fontsize=12, fontweight='bold')

plt.tight_layout()
fig.savefig(OUTPUT_DIR / "Three_Method_AUC_Comparison.png", dpi=300, bbox_inches='tight')
fig.savefig(OUTPUT_DIR / "Three_Method_AUC_Comparison.pdf", bbox_inches='tight')
print(f"    Saved: Three_Method_AUC_Comparison.png")
plt.close()

# ============================================================================
# SAVE FULL COMPARISON CSV
# ============================================================================
comparison_df = merged[['Drug', 'Arrhythmia', 'heart_damage', 'HD_binary',
                        'DICT_Concern_Prob', 'SwissADME_Prob', 'Organoid_HD_Prob']].copy()
comparison_df.columns = ['Drug', 'Arrhythmia_Label', 'HeartDamage_Label', 'HD_Binary',
                         'ADMET_AI_Prob', 'SwissADME_Prob', 'Organoid_HD_Prob']
comparison_df = comparison_df.sort_values('ADMET_AI_Prob', ascending=False)
comparison_df.to_csv(OUTPUT_DIR / "Three_Method_Full_Comparison.csv", index=False)
print(f"\n    Full comparison saved: Three_Method_Full_Comparison.csv")

# Summary statistics CSV
summary_df = pd.DataFrame(results_summary)
summary_df.to_csv(OUTPUT_DIR / "Three_Method_AUC_Summary.csv", index=False)

print("\n" + "="*80)
print("THREE-WAY COMPARISON COMPLETE!")
print("="*80)
