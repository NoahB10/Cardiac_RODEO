"""
Predict DICT concern using retrained DICTrank models.

Defaults to the 25 Cardiac RODEO drugs, but can be pointed at any
feature CSVs as long as columns match the training feature sets.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import joblib


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ADMETHYST_MAIN_DIR = PROJECT_ROOT / "ADMEThyst-main"
ADMET_COMPARE_DIR = PROJECT_ROOT / "ADMET_Comparison"

DATA_DIR = ADMETHYST_MAIN_DIR / "data"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
DEFAULT_MODELS_DIR = ADMET_COMPARE_DIR / "Models" / "dictrank_retrain"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SMILES_PATH = OUTPUT_DIR / "cardiac_rodeo_drugs_smiles.csv"
if not SMILES_PATH.exists():
    fallback = DATA_DIR / "cardiac_rodeo_drugs_smiles.csv"
    if fallback.exists():
        SMILES_PATH = fallback


def prepare_swiss_features(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    feat = df[feature_cols].copy()
    for col in feature_cols:
        if feat[col].dtype == "object":
            feat[col] = feat[col].map({"Yes": 1, "No": 0, "High": 1, "Low": 0}).fillna(feat[col])
            feat[col] = pd.to_numeric(feat[col], errors="coerce")
    return feat.fillna(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models_dir",
        default=str(DEFAULT_MODELS_DIR),
        help="Directory containing retrained models.",
    )
    parser.add_argument(
        "--admet_features",
        default=str(OUTPUT_DIR / "cardiac_rodeo_full_ADMET.csv"),
        help="CSV with ADMET-AI features for prediction.",
    )
    parser.add_argument(
        "--swiss_features",
        default=str(OUTPUT_DIR / "cardiac_rodeo_full_swissadme.csv"),
        help="CSV with SwissADME features for prediction.",
    )
    parser.add_argument(
        "--drug_names",
        default=str(SMILES_PATH),
        help="CSV with Drug column for naming predictions.",
    )
    parser.add_argument(
        "--out",
        default=str(OUTPUT_DIR / "dictrank_retrain_predictions_25.csv"),
        help="Output CSV for predictions.",
    )
    args = parser.parse_args()

    models_dir = Path(args.models_dir)
    admet_model = joblib.load(models_dir / "ADMET-AI_xgb.pkl")
    swiss_model = joblib.load(models_dir / "SwissADME_xgb.pkl")

    admet_Xcols = pd.read_csv(DATA_DIR / "ADMET-AI_Xvals.csv", index_col=0).columns.tolist()
    swiss_Xcols = pd.read_csv(DATA_DIR / "SwissADME_Xvals.csv", index_col=0).columns.tolist()

    admet_df = pd.read_csv(args.admet_features)
    swiss_df = pd.read_csv(args.swiss_features)
    drug_names_path = Path(args.drug_names)
    if not drug_names_path.exists():
        fallback = DATA_DIR / "cardiac_rodeo_drugs_smiles.csv"
        if fallback.exists():
            drug_names_path = fallback
        else:
            raise FileNotFoundError(
                "Missing cardiac_rodeo_drugs_smiles.csv. "
                f"Expected at {SMILES_PATH} (or {fallback})."
            )
    drug_names = pd.read_csv(drug_names_path)["Drug"].tolist()

    X_admet = admet_df[admet_Xcols].copy()
    X_swiss = prepare_swiss_features(swiss_df, swiss_Xcols)

    admet_probs = admet_model.predict_proba(X_admet)[:, 1]
    swiss_probs = swiss_model.predict_proba(X_swiss)[:, 1]

    out_df = pd.DataFrame(
        {
            "Drug": drug_names,
            "ADMET_AI_Prob": admet_probs,
            "SwissADME_Prob": swiss_probs,
        }
    )
    out_path = Path(args.out)
    out_df.to_csv(out_path, index=False)
    print(f"Saved predictions to {out_path}")


if __name__ == "__main__":
    main()
