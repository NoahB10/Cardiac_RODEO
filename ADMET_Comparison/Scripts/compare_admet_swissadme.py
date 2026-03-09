"""
Compare ADMET-AI vs SwissADME predictions for Cardiac RODEO drugs.
Computes SwissADME-like features using RDKit and trains XGBoost model.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import pickle
import warnings
warnings.filterwarnings('ignore')

# RDKit imports
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, Crippen, MolSurf, rdMolDescriptors

# Set up paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ADMETHYST_MAIN_DIR = PROJECT_ROOT / "ADMEThyst-main"

DATA_DIR = ADMETHYST_MAIN_DIR / "data"
MODELS_DIR = ADMETHYST_MAIN_DIR / "models" / "ensemble"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("="*80)
print("ADMET-AI vs SwissADME Comparison")
print("="*80)

# Resolve Cardiac RODEO SMILES file
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

# ============================================================================
# STEP 1: Load ADMET-AI predictions (already computed)
# ============================================================================
print("\n[1] Loading ADMET-AI predictions...")
admet_preds = pd.read_csv(OUTPUT_DIR / "cardiac_rodeo_DICT_predictions.csv")
print(f"    Loaded {len(admet_preds)} ADMET-AI predictions")

# ============================================================================
# STEP 2: Compute SwissADME-like features using RDKit
# ============================================================================
print("\n[2] Computing SwissADME-like features using RDKit...")

def compute_swissadme_features(smiles):
    """Compute SwissADME-like descriptors using RDKit."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    features = {}

    # Basic properties
    features['MW'] = Descriptors.MolWt(mol)
    features['#Heavy atoms'] = Descriptors.HeavyAtomCount(mol)
    features['#Aromatic heavy atoms'] = len([a for a in mol.GetAtoms() if a.GetIsAromatic()])
    features['Fraction Csp3'] = rdMolDescriptors.CalcFractionCSP3(mol)
    features['#Rotatable bonds'] = Descriptors.NumRotatableBonds(mol)
    features['#H-bond acceptors'] = Descriptors.NumHAcceptors(mol)
    features['#H-bond donors'] = Descriptors.NumHDonors(mol)
    features['MR'] = Crippen.MolMR(mol)
    features['TPSA'] = Descriptors.TPSA(mol)

    # LogP values
    features['Consensus Log P'] = Crippen.MolLogP(mol)  # Using RDKit's LogP as consensus
    features['WLOGP'] = Crippen.MolLogP(mol)

    # Solubility estimate (ESOL)
    features['ESOL Log S'] = 0.16 - 0.63 * features['Consensus Log P'] - 0.0062 * features['MW'] + 0.066 * features['#Rotatable bonds'] - 0.74 * features['#Aromatic heavy atoms'] / features['#Heavy atoms'] if features['#Heavy atoms'] > 0 else 0

    # Permeability estimate
    features['log Kp (cm/s)'] = -2.5 + 0.0256 * features['MW'] - 0.5 * features['TPSA'] / 10

    # Lipinski violations
    lipinski_violations = 0
    if features['MW'] > 500: lipinski_violations += 1
    if features['Consensus Log P'] > 5: lipinski_violations += 1
    if features['#H-bond donors'] > 5: lipinski_violations += 1
    if features['#H-bond acceptors'] > 10: lipinski_violations += 1
    features['Lipinski #violations'] = lipinski_violations

    # Bioavailability score (simplified)
    features['Bioavailability Score'] = 0.55 if lipinski_violations <= 1 else 0.17

    # Synthetic accessibility
    features['Synthetic Accessibility'] = rdMolDescriptors.CalcNumRings(mol) + features['#Rotatable bonds'] / 5

    return features

# Load our drug SMILES
drugs_df = pd.read_csv(SMILES_PATH)

# Compute features for each drug
swissadme_features = []
for _, row in drugs_df.iterrows():
    feats = compute_swissadme_features(row['SMILES'])
    if feats:
        feats['Drug'] = row['Drug']
        swissadme_features.append(feats)

swissadme_df = pd.DataFrame(swissadme_features)
print(f"    Computed {len(swissadme_df.columns)-1} SwissADME-like features for {len(swissadme_df)} drugs")

# ============================================================================
# STEP 3: Train SwissADME-based XGBoost model on DICTrank data
# ============================================================================
print("\n[3] Training SwissADME-based XGBoost model...")

# Load SwissADME training data
swissadme_Xvals = pd.read_csv(DATA_DIR / "SwissADME_Xvals.csv", index_col=0)
swissadme_yvals = pd.read_csv(DATA_DIR / "SwissADME_yvals.csv", index_col=0)

print(f"    Training data: {len(swissadme_Xvals)} samples, {len(swissadme_Xvals.columns)} features")

# Get common features between training data and our computed features
common_features = [col for col in swissadme_Xvals.columns if col in swissadme_df.columns]
print(f"    Common features: {len(common_features)}")

# If not enough common features, use what we have
if len(common_features) < 5:
    print("    WARNING: Few common features. Using available features.")
    common_features = [col for col in swissadme_df.columns if col != 'Drug']

# Prepare training data
X_train = swissadme_Xvals[common_features].fillna(0)
y_train = swissadme_yvals.values.ravel()

# Train XGBoost model
from sklearn.ensemble import GradientBoostingClassifier
swissadme_model = GradientBoostingClassifier(
    n_estimators=100,
    max_depth=3,
    learning_rate=0.1,
    random_state=42
)
swissadme_model.fit(X_train, y_train)
print(f"    SwissADME XGBoost model trained!")

# Predict for our drugs
X_test = swissadme_df[common_features].fillna(0)
swissadme_probs = swissadme_model.predict_proba(X_test)[:, 1]
swissadme_df['SwissADME_Prob'] = swissadme_probs

print(f"    SwissADME predictions complete!")

# ============================================================================
# STEP 4: Load actual labels and merge all data
# ============================================================================
print("\n[4] Loading actual cardiotoxicity labels...")

excel_path = PROJECT_ROOT / "EQN_Coefficients" / "all_equations_coefficients.xlsx"
df_labels = pd.read_excel(excel_path, sheet_name='pkpd_elimination', header=1)
df_labels.columns = df_labels.columns.str.strip()
drugs_labels = df_labels[['Drug', 'Arrhythmia', 'heart_damage', 'Concern']].drop_duplicates()
drugs_labels = drugs_labels.dropna(subset=['Arrhythmia', 'heart_damage', 'Concern'])

# Merge all data
merged = admet_preds.merge(swissadme_df[['Drug', 'SwissADME_Prob']], on='Drug')
merged = merged.merge(drugs_labels, on='Drug')

# Convert labels to binary
def to_binary(val):
    val_str = str(val).lower().strip()
    return 1 if val_str == 'true' else 0

merged['AR_binary'] = merged['Arrhythmia'].apply(to_binary)
merged['HD_binary'] = merged['heart_damage'].apply(to_binary)
merged['Any_Cardiotox'] = ((merged['AR_binary'] == 1) | (merged['HD_binary'] == 1)).astype(int)

print(f"    Merged {len(merged)} drugs with all predictions and labels")

# ============================================================================
# STEP 5: Create overlaid ROC curves
# ============================================================================
print("\n[5] Generating overlaid ROC curves...")

fig, axes = plt.subplots(1, 3, figsize=(16, 5))

targets = [
    ('Arrhythmia', merged['AR_binary'].values),
    ('Heart Damage', merged['HD_binary'].values),
    ('Any Cardiotoxicity', merged['Any_Cardiotox'].values),
]

admet_color = '#2196F3'  # Blue
swiss_color = '#FF9800'  # Orange

for ax, (name, y_true) in zip(axes, targets):
    # ADMET-AI ROC
    fpr_admet, tpr_admet, _ = roc_curve(y_true, merged['DICT_Concern_Prob'].values)
    auc_admet = auc(fpr_admet, tpr_admet)

    # SwissADME ROC
    fpr_swiss, tpr_swiss, _ = roc_curve(y_true, merged['SwissADME_Prob'].values)
    auc_swiss = auc(fpr_swiss, tpr_swiss)

    # Plot both
    ax.plot(fpr_admet, tpr_admet, color=admet_color, lw=3,
            label=f'ADMET-AI (AUC = {auc_admet:.3f})')
    ax.fill_between(fpr_admet, tpr_admet, alpha=0.2, color=admet_color)

    ax.plot(fpr_swiss, tpr_swiss, color=swiss_color, lw=3, linestyle='--',
            label=f'SwissADME (AUC = {auc_swiss:.3f})')
    ax.fill_between(fpr_swiss, tpr_swiss, alpha=0.2, color=swiss_color)

    ax.plot([0, 1], [0, 1], 'k:', lw=1.5, label='Random (AUC = 0.500)')

    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title(f'ROC: {name}', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=10)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.grid(True, alpha=0.3)

    print(f"\n    {name}:")
    print(f"      ADMET-AI AUC: {auc_admet:.3f}")
    print(f"      SwissADME AUC: {auc_swiss:.3f}")
    print(f"      Difference: {auc_admet - auc_swiss:+.3f}")

plt.tight_layout()
fig.savefig(OUTPUT_DIR / "ADMET_vs_SwissADME_ROC.png", dpi=300, bbox_inches='tight')
fig.savefig(OUTPUT_DIR / "ADMET_vs_SwissADME_ROC.pdf", bbox_inches='tight')
print(f"\n    ROC comparison saved to: {OUTPUT_DIR / 'ADMET_vs_SwissADME_ROC.png'}")
plt.close()

# ============================================================================
# STEP 6: Create comparison scatter plot
# ============================================================================
print("\n[6] Generating comparison scatter plots...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Sort by ADMET-AI prediction
merged_sorted = merged.sort_values('DICT_Concern_Prob', ascending=False).reset_index(drop=True)
drugs = merged_sorted['Drug'].tolist()
positions = np.arange(len(drugs))

admet_pct = merged_sorted['DICT_Concern_Prob'].values * 100
swiss_pct = merged_sorted['SwissADME_Prob'].values * 100

# Left plot: Side by side bars
ax = axes[0]
width = 0.35
ax.bar(positions - width/2, admet_pct, width, label='ADMET-AI', color=admet_color, alpha=0.8)
ax.bar(positions + width/2, swiss_pct, width, label='SwissADME', color=swiss_color, alpha=0.8)
ax.axhline(50, color='red', linestyle='--', linewidth=2, label='Threshold (50%)')
ax.set_xticks(positions)
ax.set_xticklabels(drugs, rotation=45, ha='right', fontsize=9)
ax.set_ylabel('DICT Concern Probability (%)', fontsize=12)
ax.set_title('ADMET-AI vs SwissADME Predictions', fontsize=13, fontweight='bold')
ax.legend(loc='upper right')
ax.set_ylim(0, 105)
ax.grid(True, axis='y', alpha=0.3)

# Right plot: Scatter comparing the two predictions
ax = axes[1]
cardiotox = merged_sorted['Any_Cardiotox'] == 1
ax.scatter(admet_pct[cardiotox], swiss_pct[cardiotox],
           c='#f8b4b4', s=100, alpha=0.8, edgecolors='black', linewidth=0.5,
           label='Cardiotoxic (Actual)')
ax.scatter(admet_pct[~cardiotox], swiss_pct[~cardiotox],
           c='lightgray', s=100, alpha=0.8, edgecolors='black', linewidth=0.5,
           label='Non-cardiotoxic (Actual)')

# Add drug labels
for i, drug in enumerate(drugs):
    ax.annotate(drug, (admet_pct[i], swiss_pct[i]), fontsize=7,
                xytext=(3, 3), textcoords='offset points', alpha=0.7)

ax.plot([0, 100], [0, 100], 'k--', lw=1.5, alpha=0.5, label='y=x (agreement)')
ax.axhline(50, color='orange', linestyle=':', alpha=0.7)
ax.axvline(50, color='blue', linestyle=':', alpha=0.7)

ax.set_xlabel('ADMET-AI Prediction (%)', fontsize=12)
ax.set_ylabel('SwissADME Prediction (%)', fontsize=12)
ax.set_title('Prediction Agreement', fontsize=13, fontweight='bold')
ax.legend(loc='lower right', fontsize=9)
ax.set_xlim(0, 105)
ax.set_ylim(0, 105)
ax.grid(True, alpha=0.3)

plt.tight_layout()
fig.savefig(OUTPUT_DIR / "ADMET_vs_SwissADME_comparison.png", dpi=300, bbox_inches='tight')
fig.savefig(OUTPUT_DIR / "ADMET_vs_SwissADME_comparison.pdf", bbox_inches='tight')
print(f"    Comparison plots saved to: {OUTPUT_DIR / 'ADMET_vs_SwissADME_comparison.png'}")
plt.close()

# ============================================================================
# STEP 7: Summary table
# ============================================================================
print("\n" + "="*80)
print("PREDICTION COMPARISON SUMMARY")
print("="*80)
print(f"\n{'Drug':<18} {'ADMET-AI':>10} {'SwissADME':>10} {'Actual':>12} {'Agreement':>10}")
print("-"*70)
for _, row in merged_sorted.iterrows():
    admet_class = 'High' if row['DICT_Concern_Prob'] >= 0.5 else 'Low'
    swiss_class = 'High' if row['SwissADME_Prob'] >= 0.5 else 'Low'
    actual = 'Cardiotoxic' if row['Any_Cardiotox'] == 1 else 'Safe'
    agree = 'Yes' if admet_class == swiss_class else 'NO'
    print(f"{row['Drug']:<18} {row['DICT_Concern_Prob']*100:>9.1f}% {row['SwissADME_Prob']*100:>9.1f}% {actual:>12} {agree:>10}")

# Agreement statistics
admet_high = (merged['DICT_Concern_Prob'] >= 0.5)
swiss_high = (merged['SwissADME_Prob'] >= 0.5)
agreement = (admet_high == swiss_high).mean() * 100

print(f"\n{'='*70}")
print(f"Overall Agreement: {agreement:.1f}%")
print(f"ADMET-AI High Risk: {admet_high.sum()}/25")
print(f"SwissADME High Risk: {swiss_high.sum()}/25")

# Save comparison CSV
comparison_df = merged_sorted[['Drug', 'DICT_Concern_Prob', 'SwissADME_Prob',
                               'Arrhythmia', 'heart_damage', 'Any_Cardiotox']].copy()
comparison_df.columns = ['Drug', 'ADMET_AI_Prob', 'SwissADME_Prob', 'Arrhythmia', 'Heart_Damage', 'Any_Cardiotox']
comparison_df.to_csv(OUTPUT_DIR / "ADMET_vs_SwissADME_comparison.csv", index=False)
print(f"\nComparison saved to: {OUTPUT_DIR / 'ADMET_vs_SwissADME_comparison.csv'}")

print("\n" + "="*80)
print("COMPARISON COMPLETE!")
print("="*80)
