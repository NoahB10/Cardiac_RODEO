"""
Prepare DIQT dataset for MoLFormer-XL-CNN training.

Converts the DIQT.xlsx file into train/valid/test CSV splits for 5-fold CV.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import StratifiedKFold

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MOLFORMER_REPO = PROJECT_ROOT / "MoLFormer_XL_CNN_repo"
DATASETS_DIR = MOLFORMER_REPO / "Datasets"
DATA_DIR = MOLFORMER_REPO / "data"

def prepare_diqt_folds():
    """Prepare 5-fold CV splits for DIQT dataset."""

    # Load DIQT dataset
    diqt_path = DATASETS_DIR / "DIQT.xlsx"
    df = pd.read_excel(diqt_path)

    print(f"Loaded DIQT dataset: {len(df)} samples")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Label distribution:\n{df['label'].value_counts()}")

    # Ensure canonical_smiles column exists
    if 'canonical_smiles' not in df.columns:
        print("Warning: canonical_smiles column not found, using SMILES column")
        df['canonical_smiles'] = df['SMILES']

    # Keep only required columns
    df_clean = df[['canonical_smiles', 'label']].dropna()
    print(f"After dropping NaN: {len(df_clean)} samples")

    # Create 5-fold CV splits
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(df_clean, df_clean['label']), 1):
        # Split train into train/valid (80/20)
        train_data = df_clean.iloc[train_idx]
        test_data = df_clean.iloc[test_idx]

        # Further split train into train/valid
        train_size = int(len(train_data) * 0.8)
        train_final = train_data.iloc[:train_size]
        valid_data = train_data.iloc[train_size:]

        # Create output directory
        fold_dir = DATA_DIR / "DIQT" / str(fold_idx)
        fold_dir.mkdir(parents=True, exist_ok=True)

        # Save splits
        train_final.to_csv(fold_dir / "train.csv", index=False)
        valid_data.to_csv(fold_dir / "valid.csv", index=False)
        test_data.to_csv(fold_dir / "test.csv", index=False)

        print(f"Fold {fold_idx}: train={len(train_final)}, valid={len(valid_data)}, test={len(test_data)}")

    print(f"\nDataset splits saved to: {DATA_DIR / 'DIQT'}")
    return df_clean

def prepare_cardiac_rodeo_data():
    """Prepare Cardiac RODEO drugs in the same format."""

    # Load drug SMILES
    smiles_path = PROJECT_ROOT / "Cleaned_Data" / "drug_smiles.csv"
    class_path = PROJECT_ROOT / "Cleaned_Data" / "drug_classification.csv"

    smiles_df = pd.read_csv(smiles_path)
    class_df = pd.read_csv(class_path)

    # Merge
    merged = smiles_df.merge(class_df, on='Drug')

    # Prepare for inference
    merged['canonical_smiles'] = merged['SMILES']
    merged['Arrhythmia_label'] = merged['Arrhythmia'].map({'True': 1, 'False': 0, True: 1, False: 0})
    merged['heart_damage_label'] = merged['heart_damage'].map({'True': 1, 'False': 0, True: 1, False: 0})

    # Save for inference
    output_path = DATA_DIR / "cardiac_rodeo_inference.csv"
    merged.to_csv(output_path, index=False)

    print(f"\nCardiac RODEO data saved to: {output_path}")
    print(f"Total drugs: {len(merged)}")
    print(f"Arrhythmia distribution: {merged['Arrhythmia_label'].value_counts().to_dict()}")
    print(f"Heart damage distribution: {merged['heart_damage_label'].value_counts().to_dict()}")

    return merged

if __name__ == "__main__":
    print("=" * 60)
    print("Preparing DIQT Dataset for MoLFormer-XL-CNN")
    print("=" * 60)

    diqt_df = prepare_diqt_folds()

    print("\n" + "=" * 60)
    print("Preparing Cardiac RODEO Data for Inference")
    print("=" * 60)

    cardiac_df = prepare_cardiac_rodeo_data()

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
