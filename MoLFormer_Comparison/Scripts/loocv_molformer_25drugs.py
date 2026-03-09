"""
MoLFormer LOOCV on 25 Cardiac RODEO Drugs

Fair comparison with Organoid PK-PD model:
- Same 25 drugs
- Same LOOCV methodology
- Same target (Arrhythmia)

Features: MoLFormer-XL embeddings (768-dim)
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import torch
from pathlib import Path
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MOLFORMER_REPO = PROJECT_ROOT / "MoLFormer_XL_CNN_repo"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "MoLFormer_Comparison"

def load_molformer_and_extract_embeddings():
    """Load MoLFormer and extract embeddings for 25 drugs."""
    from transformers import AutoModel, AutoTokenizer

    print("Loading MoLFormer-XL from HuggingFace...")
    model_name = "ibm/MoLFormer-XL-both-10pct"

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_name, deterministic_eval=True, trust_remote_code=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    print(f"Model loaded on {device}")

    # Load Cardiac RODEO data
    cardiac_path = MOLFORMER_REPO / "data" / "cardiac_rodeo_inference.csv"
    df = pd.read_csv(cardiac_path)

    print(f"\nExtracting embeddings for {len(df)} drugs...")

    smiles_list = df['canonical_smiles'].tolist()
    embeddings = []

    with torch.no_grad():
        for i, smiles in enumerate(smiles_list):
            inputs = tokenizer([smiles], padding=True, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = model(**inputs)
            emb = outputs.pooler_output.cpu().numpy()[0]
            embeddings.append(emb)

    embeddings = np.array(embeddings)
    print(f"Embeddings shape: {embeddings.shape}")

    return df, embeddings


def run_loocv(X, y, classifier_name, classifier):
    """Run LOOCV and return predictions."""
    loo = LeaveOneOut()
    y_true = []
    y_pred = []
    y_prob = []

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train and predict
        clf = classifier.__class__(**classifier.get_params())
        clf.fit(X_train_scaled, y_train)

        pred = clf.predict(X_test_scaled)[0]

        if hasattr(clf, 'predict_proba'):
            prob = clf.predict_proba(X_test_scaled)[0, 1]
        else:
            prob = clf.decision_function(X_test_scaled)[0]
            prob = 1 / (1 + np.exp(-prob))  # Sigmoid for SVM

        y_true.append(y_test[0])
        y_pred.append(pred)
        y_prob.append(prob)

    return np.array(y_true), np.array(y_pred), np.array(y_prob)


def main():
    print("="*60)
    print("MoLFormer LOOCV on 25 Cardiac RODEO Drugs")
    print("="*60)

    # Extract embeddings
    df, X = load_molformer_and_extract_embeddings()
    y = df['Arrhythmia_label'].values
    drug_names = df['Drug'].values

    print(f"\nLabel distribution: {np.sum(y)} positive, {len(y) - np.sum(y)} negative")

    # Define classifiers (same as organoid comparison)
    classifiers = {
        'XGBoost': XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1,
                                  random_state=42, use_label_encoder=False, eval_metric='logloss'),
        'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
        'SVM_RBF': SVC(kernel='rbf', probability=True, random_state=42),
        'GaussianNB': GaussianNB(),
    }

    results = {}

    print("\n" + "="*60)
    print("LOOCV Results")
    print("="*60)

    for name, clf in classifiers.items():
        print(f"\n{name}...")
        y_true, y_pred, y_prob = run_loocv(X, y, name, clf)

        auc = roc_auc_score(y_true, y_prob)
        acc = accuracy_score(y_true, y_pred)

        results[name] = {
            'y_true': y_true,
            'y_pred': y_pred,
            'y_prob': y_prob,
            'AUC': auc,
            'Accuracy': acc
        }

        print(f"  AUC: {auc:.4f}")
        print(f"  Accuracy: {acc:.4f} ({int(acc * 25)}/25)")

    # Comparison with Organoid results
    print("\n" + "="*60)
    print("Comparison: MoLFormer LOOCV vs Organoid LOOCV")
    print("="*60)

    # Organoid results from loocv_results.csv
    organoid_results = {
        'XGBoost': {'AUC': 0.779, 'Accuracy': 0.72},
        'RandomForest': {'AUC': 0.795, 'Accuracy': 0.76},
        'SVM_RBF': {'AUC': 0.565, 'Accuracy': 0.52},
        'GaussianNB': {'AUC': 0.584, 'Accuracy': 0.60},
    }

    print(f"\n{'Model':<15} {'MoLFormer AUC':>15} {'Organoid AUC':>15} {'Diff':>10}")
    print("-"*60)

    for name in classifiers.keys():
        mol_auc = results[name]['AUC']
        org_auc = organoid_results[name]['AUC']
        diff = mol_auc - org_auc
        print(f"{name:<15} {mol_auc:>15.3f} {org_auc:>15.3f} {diff:>+10.3f}")

    # Save detailed results
    print("\n" + "="*60)
    print("Per-Drug Predictions (Best Model)")
    print("="*60)

    # Use XGBoost as reference
    best = results['XGBoost']

    print(f"\n{'Drug':<20} {'True':>6} {'Prob':>8} {'Pred':>6} {'Match':>6}")
    print("-"*50)

    for i, drug in enumerate(drug_names):
        true_label = "+" if best['y_true'][i] == 1 else "-"
        pred_label = "+" if best['y_pred'][i] == 1 else "-"
        match = "✓" if best['y_true'][i] == best['y_pred'][i] else "✗"
        print(f"{drug:<20} {true_label:>6} {best['y_prob'][i]:>8.3f} {pred_label:>6} {match:>6}")

    # Save results
    results_df = pd.DataFrame({
        'Drug': drug_names,
        'Arrhythmia_label': y,
        'MoLFormer_XGB_prob': results['XGBoost']['y_prob'],
        'MoLFormer_XGB_pred': results['XGBoost']['y_pred'],
        'MoLFormer_RF_prob': results['RandomForest']['y_prob'],
        'MoLFormer_RF_pred': results['RandomForest']['y_pred'],
    })
    results_df.to_csv(OUTPUT_DIR / "molformer_loocv_25drugs.csv", index=False)

    # Save metrics comparison
    metrics_comparison = []
    for name in classifiers.keys():
        metrics_comparison.append({
            'Model': name,
            'MoLFormer_AUC': results[name]['AUC'],
            'MoLFormer_Acc': results[name]['Accuracy'],
            'Organoid_AUC': organoid_results[name]['AUC'],
            'Organoid_Acc': organoid_results[name]['Accuracy'],
        })

    pd.DataFrame(metrics_comparison).to_csv(OUTPUT_DIR / "loocv_comparison_molformer_vs_organoid.csv", index=False)

    # Plot ROC comparison
    fig, ax = plt.subplots(figsize=(8, 8))

    colors = {'XGBoost': 'blue', 'RandomForest': 'green', 'SVM_RBF': 'orange', 'GaussianNB': 'red'}

    for name in ['XGBoost', 'RandomForest']:
        fpr, tpr, _ = roc_curve(results[name]['y_true'], results[name]['y_prob'])
        ax.plot(fpr, tpr, color=colors[name], linestyle='-', linewidth=2,
                label=f'MoLFormer {name} (AUC={results[name]["AUC"]:.3f})')

        # Add organoid reference line
        ax.axhline(y=organoid_results[name]['AUC'], color=colors[name], linestyle='--', alpha=0.5,
                   label=f'Organoid {name} AUC={organoid_results[name]["AUC"]:.3f}')

    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random (AUC=0.500)')
    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title('MoLFormer vs Organoid LOOCV (N=25 drugs)\nArrhythmia Prediction', fontsize=14)
    ax.legend(loc='lower right', fontsize=9)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'LOOCV_MoLFormer_vs_Organoid.png', dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\nResults saved to {OUTPUT_DIR}")
    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)

    best_mol = max(results.items(), key=lambda x: x[1]['AUC'])
    best_org = max(organoid_results.items(), key=lambda x: x[1]['AUC'])

    print(f"\nBest MoLFormer LOOCV: {best_mol[0]} with AUC {best_mol[1]['AUC']:.3f}")
    print(f"Best Organoid LOOCV:  {best_org[0]} with AUC {best_org[1]['AUC']:.3f}")

    if best_mol[1]['AUC'] > best_org[1]['AUC']:
        print(f"\n→ MoLFormer outperforms Organoid by {best_mol[1]['AUC'] - best_org[1]['AUC']:.3f} AUC")
    else:
        print(f"\n→ Organoid outperforms MoLFormer by {best_org[1]['AUC'] - best_mol[1]['AUC']:.3f} AUC")

    print("\nDONE!")


if __name__ == "__main__":
    main()
