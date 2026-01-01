"""
Predict DICT concern using SwissADME features
1. Train XGBoost on DICTrank SwissADME data (555 drugs)
2. Predict on your 25 drugs using real SwissADME features
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ADMETHYST_MAIN_DIR = PROJECT_ROOT / "ADMEThyst-main"

DATA_DIR = ADMETHYST_MAIN_DIR / "data"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("="*70)
print("SwissADME DICT PREDICTION")
print("="*70)

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

# =============================================================================
# LOAD YOUR SwissADME FEATURES
# =============================================================================
print("\n[1] Loading your SwissADME features...")
your_swiss = pd.read_csv(OUTPUT_DIR / 'cardiac_rodeo_full_swissadme.csv')
print(f"    Loaded {len(your_swiss)} drugs with {len(your_swiss.columns)} columns")

# Load drug names for mapping
drugs_df = pd.read_csv(SMILES_PATH)
drug_names = drugs_df['Drug'].tolist()

# =============================================================================
# LOAD DICTrank TRAINING DATA
# =============================================================================
print("\n[2] Loading DICTrank SwissADME training data...")
train_X = pd.read_csv(DATA_DIR / 'SwissADME_Xvals.csv', index_col=0)
train_y = pd.read_csv(DATA_DIR / 'SwissADME_yvals.csv', index_col=0)

# Convert labels to binary
y_binary = (train_y['DICT _ Concern'] == 'most').astype(int).values
print(f"    Training set: {len(train_X)} drugs ({y_binary.sum()} high risk, {len(y_binary) - y_binary.sum()} low risk)")

# =============================================================================
# PREPARE TEST DATA - Convert categorical to numeric
# =============================================================================
print("\n[3] Preparing test data...")

# Columns that need Yes/No -> 1/0 conversion
binary_cols = ['GI absorption', 'BBB permeant', 'Pgp substrate',
               'CYP1A2 inhibitor', 'CYP2C19 inhibitor', 'CYP2C9 inhibitor',
               'CYP2D6 inhibitor', 'CYP3A4 inhibitor']

# Create a copy and convert
test_df = your_swiss.copy()

for col in test_df.columns:
    if col in binary_cols:
        # Convert Yes/No or High/Low to 1/0
        test_df[col] = test_df[col].map({'Yes': 1, 'No': 0, 'High': 1, 'Low': 0})
    elif test_df[col].dtype == 'object':
        # Try to convert to numeric, if fails set to 0
        test_df[col] = pd.to_numeric(test_df[col], errors='coerce')

# Fill NaN with 0
test_df = test_df.fillna(0)

# Get only the columns that match training data
train_cols = list(train_X.columns)
available_cols = [c for c in train_cols if c in test_df.columns]
missing_cols = [c for c in train_cols if c not in test_df.columns]

print(f"    Matching features: {len(available_cols)}/{len(train_cols)}")
if missing_cols:
    print(f"    Missing (will be filled with 0): {missing_cols[:5]}...")

# Build aligned test data
test_X = pd.DataFrame(index=range(len(test_df)))
for col in train_cols:
    if col in test_df.columns:
        test_X[col] = test_df[col].values
    else:
        test_X[col] = 0

# =============================================================================
# TRAIN MODEL
# =============================================================================
print("\n[4] Training XGBoost on DICTrank (500 trees, depth=12)...")

model = GradientBoostingClassifier(
    n_estimators=500,
    learning_rate=0.1,
    max_depth=12,
    random_state=0
)

# Fill any NaN in training data
train_X_clean = train_X.fillna(0)
model.fit(train_X_clean, y_binary)
print("    Training complete!")

# =============================================================================
# PREDICT
# =============================================================================
print("\n[5] Predicting DICT concern for your 25 drugs...")

swissadme_probs = model.predict_proba(test_X)[:, 1]
print("    Predictions complete!")

# =============================================================================
# LOAD ADMET-AI PREDICTIONS FOR COMPARISON
# =============================================================================
print("\n[6] Loading ADMET-AI predictions for comparison...")
admet_results = pd.read_csv(OUTPUT_DIR / 'cardiac_rodeo_DICT_predictions.csv')

# Create mapping from drug name to ADMET prob
admet_dict = dict(zip(admet_results['Drug'], admet_results['DICT_Concern_Prob']))

# =============================================================================
# COMBINE RESULTS
# =============================================================================
print("\n[7] Combining results...")

results = pd.DataFrame({
    'Drug': drug_names,
    'ADMET_AI_Prob': [admet_dict.get(d, np.nan) for d in drug_names],
    'SwissADME_Prob': swissadme_probs,
})

results['ADMET_AI_Risk'] = ['High' if p >= 0.5 else 'Low' for p in results['ADMET_AI_Prob']]
results['SwissADME_Risk'] = ['High' if p >= 0.5 else 'Low' for p in results['SwissADME_Prob']]
results['Agreement'] = results['ADMET_AI_Risk'] == results['SwissADME_Risk']

# Sort by ADMET-AI probability
results = results.sort_values('ADMET_AI_Prob', ascending=False).reset_index(drop=True)

# Save
results.to_csv(OUTPUT_DIR / 'ADMET_vs_SwissADME_Predictions.csv', index=False)

# =============================================================================
# PRINT RESULTS
# =============================================================================
print("\n" + "="*70)
print("DICT CONCERN PREDICTIONS COMPARISON")
print("="*70)
print(f"\n{'#':<3} {'Drug':<18} {'ADMET-AI':>10} {'Risk':>6} {'SwissADME':>10} {'Risk':>6} {'Agree':>6}")
print("-"*70)

for i, row in results.iterrows():
    agree = 'Y' if row['Agreement'] else 'N'
    print(f"{i+1:<3} {row['Drug']:<18} {row['ADMET_AI_Prob']:>10.3f} {row['ADMET_AI_Risk']:>6} "
          f"{row['SwissADME_Prob']:>10.3f} {row['SwissADME_Risk']:>6} {agree:>6}")

print("-"*70)

# Summary
admet_high = (results['ADMET_AI_Risk'] == 'High').sum()
swiss_high = (results['SwissADME_Risk'] == 'High').sum()
both_high = ((results['ADMET_AI_Risk'] == 'High') & (results['SwissADME_Risk'] == 'High')).sum()
agreement = results['Agreement'].sum()

print(f"\nSUMMARY:")
print(f"  ADMET-AI High Risk:  {admet_high}/25 drugs")
print(f"  SwissADME High Risk: {swiss_high}/25 drugs")
print(f"  Both High Risk:      {both_high}/25 drugs")
print(f"  Agreement:           {agreement}/25 drugs ({100*agreement/25:.0f}%)")

# Correlation
corr = results['ADMET_AI_Prob'].corr(results['SwissADME_Prob'])
print(f"  Correlation:         {corr:.3f}")

print(f"\nSaved: {OUTPUT_DIR / 'ADMET_vs_SwissADME_Predictions.csv'}")
