"""
Prepare SMILES file for SwissADME web upload
"""
import pandas as pd
from pathlib import Path

# Load drugs
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ADMETHYST_MAIN_DIR = PROJECT_ROOT / "ADMEThyst-main"

DATA_DIR = ADMETHYST_MAIN_DIR / "data"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"

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

drugs_df = pd.read_csv(SMILES_PATH)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
output_path = OUTPUT_DIR / "swissadme_input.txt"

# Create SwissADME input format (Drug name followed by SMILES, one per line)
with open(output_path, 'w') as f:
    for _, row in drugs_df.iterrows():
        f.write(f"{row['Drug']} {row['SMILES']}\n")

print(f"Created {output_path}")
print("\nNext steps:")
print("1. Go to http://www.swissadme.ch/")
print("2. Paste the contents of swissadme_input.txt")
print("3. Click 'Run Screening'")
print("4. Download the CSV results")
print("\nFile contents preview:")
print("-" * 70)
with open(output_path, 'r') as f:
    print(f.read()[:500])
