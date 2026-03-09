"""
MoLFormer-XL-CNN on Cardiac RODEO 25 Drugs
Same process as paper but on our 25 drugs instead of DIQT 255 drugs.

Process:
1. Load pre-trained MoLFormer checkpoint
2. 5-fold CV on 25 drugs (train ~20, test ~5 per fold)
3. Fine-tune CNN + classifier
4. Report AUC
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import warnings
warnings.filterwarnings('ignore')

import os
from pathlib import Path
from functools import partial

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, accuracy_score, confusion_matrix, f1_score, matthews_corrcoef

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MOLFORMER_REPO = PROJECT_ROOT / "MoLFormer_XL_CNN_repo"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "MoLFormer_Comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(MOLFORMER_REPO / "linear_attention_rotary"))

from fast_transformers.masking import LengthMask as LM
from fast_transformers.feature_maps import GeneralizedRandomFeatures
from rotate_attention.rotate_builder import RotateEncoderBuilder as rotate_builder
from tokenizer.tokenizer import MolTranBertTokenizer


class CNN(nn.Module):
    def __init__(self, dim=768):
        super().__init__()
        self.conv_block = nn.Sequential(
            nn.Conv1d(dim, dim*3, kernel_size=3, padding=1),
            nn.BatchNorm1d(dim*3),
            nn.ReLU(),
            nn.Conv1d(dim*3, dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(dim),
            nn.ReLU(),
        )

    def forward(self, x):
        return self.conv_block(x.permute(0, 2, 1)).permute(0, 2, 1)


class MoLFormerCNN(nn.Module):
    def __init__(self, n_vocab, n_embd=768, n_head=12, n_layer=12, num_feats=32, dropout=0.2):
        super().__init__()
        self.tok_emb = nn.Embedding(n_vocab, n_embd)
        self.drop = nn.Dropout(dropout)

        builder = rotate_builder.from_kwargs(
            n_layers=n_layer, n_heads=n_head,
            query_dimensions=n_embd // n_head,
            value_dimensions=n_embd // n_head,
            feed_forward_dimensions=n_embd,
            attention_type='linearwweights',
            feature_map=partial(GeneralizedRandomFeatures, n_dims=num_feats),
            activation='gelu',
        )
        self.blocks = builder.get()
        self.cnn = CNN(n_embd)
        self.classifier = nn.Sequential(
            nn.Linear(n_embd, n_embd),
            nn.Dropout(dropout),
            nn.ReLU(),
            nn.Linear(n_embd, 2),
        )

    def forward(self, idx, mask):
        x = self.drop(self.tok_emb(idx))
        x, _ = self.blocks(x, length_mask=LM(mask.sum(-1)))

        mask_expanded = mask.unsqueeze(-1).float()
        x = x * mask_expanded
        x = self.cnn(x)

        pooled = (x * mask_expanded).sum(1) / mask_expanded.sum(1).clamp(min=1e-9)
        return self.classifier(pooled)


def load_pretrained(model, checkpoint_path, device):
    checkpoint = torch.load(checkpoint_path, map_location=device)
    state_dict = checkpoint['state_dict']

    model_state = model.state_dict()
    loaded = 0
    for k, v in state_dict.items():
        if k.startswith('tok_emb') or k.startswith('blocks'):
            if k in model_state:
                model_state[k] = v
                loaded += 1

    model.load_state_dict(model_state)
    print(f"Loaded {loaded} pre-trained weights")
    return model


def collate_fn(batch):
    tokens, masks, labels = zip(*batch)
    max_len = max(len(t) for t in tokens)

    padded_tokens = torch.zeros(len(tokens), max_len, dtype=torch.long)
    padded_masks = torch.zeros(len(tokens), max_len, dtype=torch.long)

    for i, (t, m) in enumerate(zip(tokens, masks)):
        padded_tokens[i, :len(t)] = t
        padded_masks[i, :len(m)] = m

    return padded_tokens, padded_masks, torch.stack(labels)


class SimpleDataset(torch.utils.data.Dataset):
    def __init__(self, smiles_list, labels, tokenizer):
        self.data = []
        for smiles, label in zip(smiles_list, labels):
            tokens = tokenizer.encode(smiles, add_special_tokens=True)
            mask = [1] * len(tokens)
            self.data.append((
                torch.tensor(tokens, dtype=torch.long),
                torch.tensor(mask, dtype=torch.long),
                torch.tensor(label, dtype=torch.long)
            ))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]


def main():
    print("="*60)
    print("MoLFormer-XL-CNN on 25 Cardiac RODEO Drugs")
    print("Same methodology as paper, different dataset")
    print("="*60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load tokenizer
    vocab_path = MOLFORMER_REPO / "linear_attention_rotary" / "bert_vocab.txt"
    tokenizer = MolTranBertTokenizer(str(vocab_path))
    print(f"Tokenizer: {len(tokenizer.vocab)} tokens")

    # Load checkpoint path
    checkpoint_path = MOLFORMER_REPO / "data" / "Pretrained MoLFormer" / "checkpoints" / "N-Step-Checkpoint_3_30000.ckpt"

    # Load Cardiac RODEO data
    cardiac_path = MOLFORMER_REPO / "data" / "cardiac_rodeo_inference.csv"
    df = pd.read_csv(cardiac_path)

    smiles_list = df['canonical_smiles'].tolist()
    labels = df['Arrhythmia_label'].values
    drug_names = df['Drug'].tolist()

    print(f"\nCardiac RODEO: {len(df)} drugs")
    print(f"Arrhythmia positive: {labels.sum()}/{len(labels)} ({100*labels.mean():.1f}%)")

    # 5-fold CV (same as paper)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    all_probs = np.zeros(len(labels))
    all_preds = np.zeros(len(labels))
    fold_aucs = []
    fold_accs = []
    fold_f1s = []
    fold_mccs = []

    for fold, (train_idx, test_idx) in enumerate(cv.split(smiles_list, labels)):
        print(f"\n--- Fold {fold+1}/5 ---")
        print(f"  Train: {len(train_idx)}, Test: {len(test_idx)}")

        train_smiles = [smiles_list[i] for i in train_idx]
        train_labels = labels[train_idx]
        test_smiles = [smiles_list[i] for i in test_idx]
        test_labels = labels[test_idx]

        train_dataset = SimpleDataset(train_smiles, train_labels, tokenizer)
        test_dataset = SimpleDataset(test_smiles, test_labels, tokenizer)

        # Small batch size due to small dataset
        train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=4, shuffle=True, collate_fn=collate_fn)
        test_loader = torch.utils.data.DataLoader(
            test_dataset, batch_size=len(test_idx), collate_fn=collate_fn)

        # Create model and load pre-trained weights
        model = MoLFormerCNN(len(tokenizer.vocab)).to(device)
        model = load_pretrained(model, checkpoint_path, device)

        # Training setup - same hyperparameters as paper
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        criterion = nn.CrossEntropyLoss()

        # Train for more epochs since small dataset
        best_model_state = None
        best_loss = float('inf')

        for epoch in range(30):  # More epochs for small dataset
            model.train()
            total_loss = 0

            for batch in train_loader:
                idx, mask, lab = [x.to(device) for x in batch]
                optimizer.zero_grad()
                logits = model(idx, mask)
                loss = criterion(logits, lab)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / len(train_loader)

            if avg_loss < best_loss:
                best_loss = avg_loss
                best_model_state = {k: v.clone() for k, v in model.state_dict().items()}

            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1}: loss={avg_loss:.4f}")

        # Load best model and evaluate
        if best_model_state:
            model.load_state_dict(best_model_state)

        model.eval()
        with torch.no_grad():
            for batch in test_loader:
                idx, mask, lab = batch
                idx, mask = idx.to(device), mask.to(device)
                logits = model(idx, mask)
                probs = F.softmax(logits, dim=1)[:, 1].cpu().numpy()
                preds = (probs >= 0.5).astype(int)

        # Store predictions
        all_probs[test_idx] = probs
        all_preds[test_idx] = preds

        # Fold metrics
        try:
            fold_auc = roc_auc_score(test_labels, probs)
            fold_aucs.append(fold_auc)
            print(f"  Fold AUC: {fold_auc:.4f}")
        except:
            fold_aucs.append(np.nan)
            print(f"  Fold AUC: N/A (single class in test)")

        # Per-fold F1 and MCC (real CV-based metrics)
        fold_acc = accuracy_score(test_labels, preds)
        fold_f1 = f1_score(test_labels, preds, zero_division=0)
        fold_mcc = matthews_corrcoef(test_labels, preds)
        fold_accs.append(fold_acc)
        fold_f1s.append(fold_f1)
        fold_mccs.append(fold_mcc)
        print(f"  Fold Acc: {fold_acc:.4f}, F1: {fold_f1:.4f}, MCC: {fold_mcc:.4f}")

    # Overall results
    print("\n" + "="*60)
    print("5-Fold CV Results on 25 Cardiac RODEO Drugs")
    print("="*60)

    overall_auc = roc_auc_score(labels, all_probs)
    overall_acc = accuracy_score(labels, all_preds)

    # Compute overall F1 and MCC from aggregated predictions
    overall_f1 = f1_score(labels, all_preds, zero_division=0)
    overall_mcc = matthews_corrcoef(labels, all_preds)

    print(f"Overall AUC: {overall_auc:.4f}")
    print(f"Overall Accuracy: {overall_acc:.4f} ({int(overall_acc*25)}/25)")
    print(f"Overall F1: {overall_f1:.4f}")
    print(f"Overall MCC: {overall_mcc:.4f}")
    print(f"\nPer-fold AUCs: {[f'{a:.3f}' for a in fold_aucs]}")
    print(f"Mean fold AUC: {np.nanmean(fold_aucs):.4f} +/- {np.nanstd(fold_aucs):.4f}")
    print(f"Mean fold Acc: {np.mean(fold_accs):.4f} +/- {np.std(fold_accs):.4f}")
    print(f"Mean fold F1:  {np.mean(fold_f1s):.4f} +/- {np.std(fold_f1s):.4f}")
    print(f"Mean fold MCC: {np.mean(fold_mccs):.4f} +/- {np.std(fold_mccs):.4f}")

    # Confusion matrix
    tn, fp, fn, tp = confusion_matrix(labels, all_preds).ravel()
    print(f"\nConfusion Matrix:")
    print(f"  TP={tp}, FP={fp}, FN={fn}, TN={tn}")
    print(f"  Sensitivity: {tp/(tp+fn):.3f}")
    print(f"  Specificity: {tn/(tn+fp):.3f}")

    # Per-drug predictions
    print(f"\n{'Drug':<20} {'True':>6} {'Prob':>8} {'Pred':>6} {'Correct':>8}")
    print("-"*55)
    for i, drug in enumerate(drug_names):
        true_label = "+" if labels[i] == 1 else "-"
        pred_label = "+" if all_preds[i] == 1 else "-"
        correct = "Yes" if labels[i] == all_preds[i] else "No"
        print(f"{drug:<20} {true_label:>6} {all_probs[i]:>8.4f} {pred_label:>6} {correct:>8}")

    # Save results
    results_df = df.copy()
    results_df['CNN_25_prob'] = all_probs
    results_df['CNN_25_pred'] = all_preds.astype(int)
    results_df['CNN_25_correct'] = (labels == all_preds).astype(int)
    results_df.to_csv(OUTPUT_DIR / "molformer_cnn_25drugs_cv.csv", index=False)

    # Save metrics with real CV-based F1 and MCC std
    metrics = {
        'Model': 'MoLFormer-XL-CNN (25 drugs)',
        'N_drugs': 25,
        'CV_folds': 5,
        'AUC': overall_auc,
        'AUC_Mean': float(np.nanmean(fold_aucs)),
        'AUC_Std': float(np.nanstd(fold_aucs)),
        'Accuracy': overall_acc,
        'Accuracy_Mean': float(np.mean(fold_accs)),
        'Accuracy_Std': float(np.std(fold_accs)),
        'F1': overall_f1,
        'F1_Mean': float(np.mean(fold_f1s)),
        'F1_Std': float(np.std(fold_f1s)),
        'MCC': overall_mcc,
        'MCC_Mean': float(np.mean(fold_mccs)),
        'MCC_Std': float(np.std(fold_mccs)),
        'Sensitivity': tp/(tp+fn),
        'Specificity': tn/(tn+fp),
    }
    pd.DataFrame([metrics]).to_csv(OUTPUT_DIR / "molformer_cnn_25drugs_metrics.csv", index=False)

    print(f"\nResults saved to {OUTPUT_DIR}")
    print("DONE!")


if __name__ == "__main__":
    main()
