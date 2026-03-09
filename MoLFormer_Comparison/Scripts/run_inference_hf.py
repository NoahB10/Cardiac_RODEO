"""
Run MoLFormer-XL inference using HuggingFace model.

This script uses the HuggingFace MoLFormer-XL model to extract embeddings
and then trains/uses a classifier for DIQT (QT prolongation) prediction.

Approach:
1. Load HuggingFace MoLFormer-XL for molecular embeddings
2. Train a simple classifier on DIQT dataset
3. Run inference on Cardiac RODEO drugs
4. Compare predictions with Arrhythmia labels
"""
import os
import sys
import warnings
warnings.filterwarnings('ignore')

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import (
    accuracy_score, roc_auc_score, precision_score, recall_score,
    f1_score, confusion_matrix, matthews_corrcoef, balanced_accuracy_score,
    average_precision_score, roc_curve
)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
import joblib

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MOLFORMER_REPO = PROJECT_ROOT / "MoLFormer_XL_CNN_repo"
DATA_DIR = MOLFORMER_REPO / "data"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "MoLFormer_Comparison"

# Ensure output dir exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_molformer_model():
    """Load HuggingFace MoLFormer-XL model."""
    from transformers import AutoModel, AutoTokenizer

    print("Loading MoLFormer-XL from HuggingFace...")
    model_name = "ibm/MoLFormer-XL-both-10pct"

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        model_name,
        deterministic_eval=True,
        trust_remote_code=True
    )

    # Move to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()

    print(f"Model loaded on {device}")
    return model, tokenizer, device

def extract_embeddings(smiles_list, model, tokenizer, device, batch_size=16):
    """Extract MoLFormer embeddings for a list of SMILES."""
    embeddings = []

    for i in range(0, len(smiles_list), batch_size):
        batch = smiles_list[i:i+batch_size]

        # Tokenize
        inputs = tokenizer(batch, padding=True, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Forward pass
        with torch.no_grad():
            outputs = model(**inputs)

        # Get pooled output (768-dim embedding per molecule)
        batch_embeddings = outputs.pooler_output.cpu().numpy()
        embeddings.append(batch_embeddings)

        if (i + batch_size) % 100 == 0 or i + batch_size >= len(smiles_list):
            print(f"  Processed {min(i + batch_size, len(smiles_list))}/{len(smiles_list)} molecules")

    return np.vstack(embeddings)

def compute_metrics(y_true, y_pred, y_prob):
    """Compute comprehensive classification metrics."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    metrics = {
        'Accuracy': accuracy_score(y_true, y_pred),
        'Precision': precision_score(y_true, y_pred, zero_division=0),
        'Recall': recall_score(y_true, y_pred, zero_division=0),
        'Specificity': tn / (tn + fp) if (tn + fp) > 0 else 0,
        'F1': f1_score(y_true, y_pred, zero_division=0),
        'MCC': matthews_corrcoef(y_true, y_pred),
        'BACC': balanced_accuracy_score(y_true, y_pred),
        'AUROC': roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else 0,
        'AUPRC': average_precision_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else 0,
    }

    return metrics

def train_and_evaluate_diqt(model, tokenizer, device):
    """Train classifier on DIQT dataset using cross-validation."""
    print("\n" + "="*60)
    print("Training DIQT Classifier")
    print("="*60)

    # Load DIQT dataset
    diqt_path = MOLFORMER_REPO / "Datasets" / "DIQT.xlsx"
    df = pd.read_excel(diqt_path)
    df = df[['canonical_smiles', 'label']].dropna()

    print(f"DIQT dataset: {len(df)} samples")
    print(f"Label distribution: {df['label'].value_counts().to_dict()}")

    # Extract embeddings
    print("\nExtracting MoLFormer embeddings...")
    smiles_list = df['canonical_smiles'].tolist()
    X = extract_embeddings(smiles_list, model, tokenizer, device)
    y = df['label'].values

    print(f"Embeddings shape: {X.shape}")

    # Train XGBoost with LOOCV-style evaluation using 5-fold CV
    print("\nTraining XGBoost classifier with 5-fold CV...")

    clf = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )

    # 5-fold cross-validation predictions
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred_cv = cross_val_predict(clf, X, y, cv=cv, method='predict')
    y_prob_cv = cross_val_predict(clf, X, y, cv=cv, method='predict_proba')[:, 1]

    # Compute metrics
    metrics = compute_metrics(y, y_pred_cv, y_prob_cv)

    print("\n5-Fold CV Results on DIQT Dataset:")
    print("-" * 40)
    for name, value in metrics.items():
        print(f"  {name}: {value:.4f}")

    # Train final model on all data
    print("\nTraining final model on all DIQT data...")
    clf.fit(X, y)

    # Save model
    model_path = PROJECT_ROOT / "MoLFormer_Comparison" / "Models" / "diqt_xgb_classifier.joblib"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, model_path)
    print(f"Model saved to: {model_path}")

    # Save embeddings for reference
    embeddings_df = pd.DataFrame(X, columns=[f'emb_{i}' for i in range(X.shape[1])])
    embeddings_df['canonical_smiles'] = smiles_list
    embeddings_df['label'] = y
    embeddings_df['pred_prob'] = y_prob_cv
    embeddings_df.to_csv(OUTPUT_DIR / "diqt_embeddings_and_predictions.csv", index=False)

    return clf, metrics, X, y

def run_cardiac_rodeo_inference(clf, model, tokenizer, device):
    """Run inference on Cardiac RODEO drugs."""
    print("\n" + "="*60)
    print("Running Inference on Cardiac RODEO Drugs")
    print("="*60)

    # Load Cardiac RODEO data
    cardiac_path = DATA_DIR / "cardiac_rodeo_inference.csv"
    df = pd.read_csv(cardiac_path)

    print(f"Cardiac RODEO drugs: {len(df)}")

    # Extract embeddings
    print("\nExtracting MoLFormer embeddings...")
    smiles_list = df['canonical_smiles'].tolist()
    X = extract_embeddings(smiles_list, model, tokenizer, device)

    # Get predictions
    y_pred = clf.predict(X)
    y_prob = clf.predict_proba(X)[:, 1]

    # Add predictions to dataframe
    df['DIQT_pred'] = y_pred
    df['DIQT_prob'] = y_prob

    # Compare with Arrhythmia labels
    y_true = df['Arrhythmia_label'].values

    print("\n" + "-"*40)
    print("DIQT vs Arrhythmia Comparison")
    print("-"*40)

    metrics = compute_metrics(y_true, y_pred, y_prob)
    for name, value in metrics.items():
        print(f"  {name}: {value:.4f}")

    # Detailed per-drug results
    print("\n" + "-"*40)
    print("Per-Drug Predictions")
    print("-"*40)
    print(f"{'Drug':<20} {'DIQT_prob':>10} {'DIQT_pred':>10} {'Arrhythmia':>12} {'Match':>8}")
    print("-"*60)

    for _, row in df.iterrows():
        match = "Yes" if row['DIQT_pred'] == row['Arrhythmia_label'] else "No"
        arr_str = "True" if row['Arrhythmia_label'] == 1 else "False"
        print(f"{row['Drug']:<20} {row['DIQT_prob']:>10.4f} {row['DIQT_pred']:>10} {arr_str:>12} {match:>8}")

    # Save results
    output_path = OUTPUT_DIR / "molformer_predictions_25.csv"
    df.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")

    # Save metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_df['Model'] = 'MoLFormer-XL + XGBoost'
    metrics_df['Target'] = 'DIQT → Arrhythmia'
    metrics_df['N_drugs'] = len(df)
    metrics_df.to_csv(OUTPUT_DIR / "molformer_metrics.csv", index=False)

    return df, metrics

def main():
    print("="*60)
    print("MoLFormer-XL Inference for Cardiac RODEO")
    print("="*60)

    # Load MoLFormer
    molformer, tokenizer, device = load_molformer_model()

    # Train on DIQT dataset
    clf, diqt_metrics, _, _ = train_and_evaluate_diqt(molformer, tokenizer, device)

    # Run inference on Cardiac RODEO drugs
    results_df, cardiac_metrics = run_cardiac_rodeo_inference(clf, molformer, tokenizer, device)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\nDIQT Training (5-fold CV):")
    print(f"  AUROC: {diqt_metrics['AUROC']:.4f}")
    print(f"  Accuracy: {diqt_metrics['Accuracy']:.4f}")

    print(f"\nCardiac RODEO Inference (DIQT → Arrhythmia):")
    print(f"  AUROC: {cardiac_metrics['AUROC']:.4f}")
    print(f"  Accuracy: {cardiac_metrics['Accuracy']:.4f}")

    print("\n" + "="*60)
    print("DONE - Results saved to Output/MoLFormer_Comparison/")
    print("="*60)

if __name__ == "__main__":
    main()
