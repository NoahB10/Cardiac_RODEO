"""Run ADMEThyst predictions on Cardiac RODEO drugs - Version 2"""
import os
import pickle
import shutil
import numpy as np
import pandas as pd
from pathlib import Path

# Set up paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ADMETHYST_MAIN_DIR = PROJECT_ROOT / "ADMEThyst-main"

DATA_DIR = ADMETHYST_MAIN_DIR / "data"
MODELS_DIR = ADMETHYST_MAIN_DIR / "models" / "ensemble"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load our drug data
SMILES_PATH = OUTPUT_DIR / "cardiac_rodeo_drugs_smiles.csv"
if not SMILES_PATH.exists():
    fallback = DATA_DIR / "cardiac_rodeo_drugs_smiles.csv"
    if fallback.exists():
        shutil.copy2(fallback, SMILES_PATH)
    else:
        raise FileNotFoundError(
            "Missing cardiac_rodeo_drugs_smiles.csv. "
            f"Expected at {SMILES_PATH} (or {fallback})."
        )

drugs_df = pd.read_csv(SMILES_PATH)
smiles_list = drugs_df['SMILES'].tolist()
drug_names = drugs_df['Drug'].tolist()

print(f"Loaded {len(smiles_list)} drugs")

# ADMET-AI feature names in exact order expected by ADMEThyst XGBoost models
admet_ai_feats = [
    'AMES', 'BBB_Martins', 'Bioavailability_Ma', 'CYP1A2_Veith',
    'CYP2C19_Veith', 'CYP2C9_Substrate_CarbonMangels', 'CYP2C9_Veith',
    'CYP2D6_Substrate_CarbonMangels', 'CYP2D6_Veith',
    'CYP3A4_Substrate_CarbonMangels', 'CYP3A4_Veith', 'Carcinogens_Lagunin',
    'ClinTox', 'DILI', 'HIA_Hou', 'NR-AR-LBD', 'NR-AR', 'NR-AhR',
    'NR-Aromatase', 'NR-ER-LBD', 'NR-ER', 'NR-PPAR-gamma', 'PAMPA_NCATS',
    'Pgp_Broccatelli', 'SR-ARE', 'SR-ATAD5', 'SR-HSE', 'SR-MMP', 'SR-p53',
    'Skin_Reaction', 'hERG', 'Caco2_Wang', 'Clearance_Hepatocyte_AZ',
    'Clearance_Microsome_AZ', 'Half_Life_Obach',
    'HydrationFreeEnergy_FreeSolv', 'LD50_Zhu', 'Lipophilicity_AstraZeneca',
    'PPBR_AZ', 'Solubility_AqSolDB', 'VDss_Lombardo'
]

# Human readable feature names - EXACT names used during model training
feat_name_dict = {
    'HIA_Hou': 'Human Intestinal Absorption',
    'Bioavailability_Ma': 'Oral Bioavailability',
    'Solubility_AqSolDB': 'Aqueous Solubility',
    'Lipophilicity_AstraZeneca': 'Lipophilicity',
    'HydrationFreeEnergy_FreeSolv': 'Hydration Free Energy',
    'Caco2_Wang': 'Cell Effective Permeability',
    'PAMPA_NCATS': 'PAMPA Permeability',
    'Pgp_Broccatelli': 'P-glycoprotein Inhibition',
    'BBB_Martins': 'Blood-Brain Barrier Penetration',
    'PPBR_AZ': 'Plasma Protein Binding Rate',
    'VDss_Lombardo': 'Volume of Distribution at Steady State',
    'Half_Life_Obach': 'Half Life',
    'Clearance_Hepatocyte_AZ': 'Drug Clearance (Hepatocyte)',
    'Clearance_Microsome_AZ': 'Drug Clearance (Microsome)',
    'CYP1A2_Veith': 'CYP1A2 Inhibition',
    'CYP2C19_Veith': 'CYP2C19 Inhibition',
    'CYP2C9_Substrate_CarbonMangels': 'CYP2C9 Substrate',
    'CYP2C9_Veith': 'CYP2C9 Inhibition',
    'CYP2D6_Substrate_CarbonMangels': 'CYP2D6 Substrate',
    'CYP2D6_Veith': 'CYP2D6 Inhibition',
    'CYP3A4_Substrate_CarbonMangels': 'CYP3A4 Substrate',
    'CYP3A4_Veith': 'CYP3A4 Inhibition',
    'hERG': 'hERG Blocking',
    'ClinTox': 'Clinical Toxicity',
    'AMES': 'Mutagenicity',
    'DILI': 'Drug Induced Liver Injury',
    'Carcinogens_Lagunin': 'Carcinogenicity',
    'LD50_Zhu': 'Acute Toxicity LD50',
    'Skin_Reaction': 'Skin Reaction',
    'NR-AR': 'Androgen Receptor (Full Length)',
    'NR-AR-LBD': 'Androgen Receptor (Ligand Binding Domain)',
    'NR-AhR': 'Aryl Hydrocarbon Receptor',
    'NR-Aromatase': 'Aromatase',
    'NR-ER': 'Estrogen Receptor (Full Length)',
    'NR-ER-LBD': 'Estrogen Receptor (Ligand Binding Domain)',
    'NR-PPAR-gamma': 'Peroxisome Proliferator-Activated Receptor Gamma',
    'SR-ARE': 'Nrf2-Antioxidant Responsive Element',
    'SR-ATAD5': 'ATPase Family AAA Domain-Containing Protein 5 (ATAD5)',
    'SR-HSE': 'Heat Shock Factor Response Element',
    'SR-MMP': 'Mitochondrial Membrane Potential',
    'SR-p53': 'Tumor Protein p53',
}

# Load ensemble models
print("Loading XGBoost ensemble models...")
xgbs = []
for fname in sorted(os.listdir(MODELS_DIR)):
    if fname.endswith('.sav'):
        model_path = MODELS_DIR / fname
        with open(model_path, 'rb') as f:
            xgbs.append(pickle.load(f))
print(f"Loaded {len(xgbs)} ensemble models")

# Run ADMET-AI predictions
print("Running ADMET-AI predictions...")
from admet_ai import ADMETModel
model = ADMETModel()
preds_full = model.predict(smiles=smiles_list)

# Extract only the 41 features needed for XGBoost and rename to human-readable names
# IMPORTANT: Models were trained with human-readable names!
preds = preds_full[admet_ai_feats].rename(columns=feat_name_dict)
print(f"Extracted and renamed {len(admet_ai_feats)} ADMET features")

# Run XGBoost ensemble predictions
print("Running DICT concern predictions...")
probs = []
for i, xgb_model in enumerate(xgbs):
    try:
        p = xgb_model.predict_proba(preds)[:, 1]
        probs.append(p)
        print(f"  Model {i+1}/{len(xgbs)} complete")
    except Exception as e:
        print(f"  Model {i+1} error: {e}")
        raise

dictrank_probs = np.mean(np.asarray(probs), axis=0)
print("Predictions complete!")

# Build results DataFrame
results = drugs_df[['Drug', 'CID', 'MolecularFormula', 'MolecularWeight', 'SMILES']].copy()
results['DICT_Concern_Prob'] = dictrank_probs
results['DICT_Class'] = ['High Risk' if p >= 0.5 else 'Low Risk' for p in dictrank_probs]

# Add key ADMET properties (top predictive features from SHAP)
# Note: Using exact human-readable column names after renaming
results['CYP2D6_Substrate'] = preds['CYP2D6 Substrate'].values
results['CYP2D6_Inhibition'] = preds['CYP2D6 Inhibition'].values
results['Nrf2_ARE'] = preds['Nrf2-Antioxidant Responsive Element'].values
results['Aromatase'] = preds['Aromatase'].values

# Add cardiotoxicity-relevant features
results['hERG_Blocking'] = preds['hERG Blocking'].values
results['Clinical_Toxicity'] = preds['Clinical Toxicity'].values
results['DILI'] = preds['Drug Induced Liver Injury'].values
results['Mutagenicity'] = preds['Mutagenicity'].values

# Sort by DICT concern probability (highest risk first)
results = results.sort_values('DICT_Concern_Prob', ascending=False).reset_index(drop=True)

# Save main results
results.to_csv(OUTPUT_DIR / 'cardiac_rodeo_DICT_predictions.csv', index=False)

# Save full ADMET predictions (already has readable names)
preds_with_drugs = preds.copy()
preds_with_drugs.insert(0, 'Drug', drug_names)
preds_with_drugs.to_csv(OUTPUT_DIR / 'cardiac_rodeo_full_ADMET.csv', index=False)

# Print summary
print(f"\n{'='*70}")
print("DICT CONCERN PREDICTIONS - Cardiac RODEO Drugs")
print('='*70)
print(f"{'#':<3} {'Drug':<18} {'Formula':<15} {'MW':>8} {'DICT Prob':>10} {'Risk':>10}")
print('-'*70)
for i, row in results.iterrows():
    formula = row['MolecularFormula'][:14] if pd.notna(row['MolecularFormula']) else 'N/A'
    mw = f"{row['MolecularWeight']:.1f}" if pd.notna(row['MolecularWeight']) else 'N/A'
    print(f"{i+1:<3} {row['Drug']:<18} {formula:<15} {mw:>8} {row['DICT_Concern_Prob']:>10.3f} {row['DICT_Class']:>10}")

print('-'*70)
high_risk = (results['DICT_Class'] == 'High Risk').sum()
print(f"\nSummary: {high_risk}/25 drugs classified as HIGH RISK for cardiotoxicity")
print(f"         {25-high_risk}/25 drugs classified as LOW RISK")

print(f"\nResults saved to: {OUTPUT_DIR}")
print("  - cardiac_rodeo_DICT_predictions.csv (main results)")
print("  - cardiac_rodeo_full_ADMET.csv (all 41 ADMET properties)")
