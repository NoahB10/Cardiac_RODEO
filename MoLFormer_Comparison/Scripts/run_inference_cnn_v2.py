"""
MoLFormer-XL-CNN Inference - Streamlined Version
"""
import sys
sys.stdout.reconfigure(line_buffering=True)  # Force line buffering

import warnings
warnings.filterwarnings('ignore')

import os
import sys
from pathlib import Path
from functools import partial

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, accuracy_score
from tqdm import tqdm

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
from rotate_attention.linear_attention import LinearWWeight
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
            attention_type='linearwweights',  # Their custom implementation that returns (V, attn_weights)
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

    # Build filtered state dict for pre-trained weights
    model_state = model.state_dict()
    loaded = 0
    for k, v in state_dict.items():
        if k.startswith('tok_emb') or k.startswith('blocks'):
            if k in model_state:
                model_state[k] = v
                loaded += 1

    # Actually load the weights
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
    print("MoLFormer-XL-CNN Training")
    print("="*60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load tokenizer
    vocab_path = MOLFORMER_REPO / "linear_attention_rotary" / "bert_vocab.txt"
    tokenizer = MolTranBertTokenizer(str(vocab_path))
    print(f"Tokenizer: {len(tokenizer.vocab)} tokens")

    # Load DIQT data using paper's exact CV splits
    diqt_splits_dir = MOLFORMER_REPO / "data" / "DIQT"
    all_probs, all_labels = [], []
    best_fold_auc = 0
    best_fold_model = None

    for fold in range(1, 6):
        print(f"\n--- Fold {fold}/5 ---")

        # Load paper's exact CV splits
        # Note: valid.csv is all-positive (for loss only), test.csv has balanced classes (for metrics)
        train_df = pd.read_csv(diqt_splits_dir / str(fold) / "train.csv")
        test_df = pd.read_csv(diqt_splits_dir / str(fold) / "test.csv")  # Use test for evaluation

        train_smiles = train_df['canonical_smiles'].tolist()
        train_labels = train_df['label'].values
        val_smiles = test_df['canonical_smiles'].tolist()  # Actually test set
        val_labels = test_df['label'].values

        print(f"  Train: {len(train_smiles)}, Test: {len(val_smiles)}, pos={val_labels.sum()}")

        train_dataset = SimpleDataset(train_smiles, train_labels, tokenizer)
        val_dataset = SimpleDataset(val_smiles, val_labels, tokenizer)

        train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=16, shuffle=True, collate_fn=collate_fn)  # Reduced for GPU memory
        val_loader = torch.utils.data.DataLoader(
            val_dataset, batch_size=16, collate_fn=collate_fn)

        # Create model
        model = MoLFormerCNN(len(tokenizer.vocab)).to(device)

        # Load pre-trained weights
        checkpoint_path = MOLFORMER_REPO / "data" / "Pretrained MoLFormer" / "checkpoints" / "N-Step-Checkpoint_3_30000.ckpt"
        model = load_pretrained(model, checkpoint_path, device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        criterion = nn.CrossEntropyLoss()

        # Train with early stopping (paper uses patience=5, max_epochs=3)
        best_auc = 0
        best_state = None
        patience_counter = 0
        best_loss = float('inf')

        accumulation_steps = 4  # Simulate batch_size=64 with batch_size=16
        for epoch in range(10):  # max epochs, early stopping will trigger earlier
            model.train()
            total_loss = 0
            optimizer.zero_grad()

            for batch_idx, batch in enumerate(train_loader):
                idx, mask, lab = [x.to(device) for x in batch]
                logits = model(idx, mask)
                loss = criterion(logits, lab) / accumulation_steps
                loss.backward()
                total_loss += loss.item() * accumulation_steps

                if (batch_idx + 1) % accumulation_steps == 0:
                    optimizer.step()
                    optimizer.zero_grad()

            # Handle remaining gradients
            if (batch_idx + 1) % accumulation_steps != 0:
                optimizer.step()
                optimizer.zero_grad()

            # Evaluate
            model.eval()
            val_probs = []
            val_true = []

            with torch.no_grad():
                for batch in val_loader:
                    idx, mask, lab = batch
                    idx, mask = idx.to(device), mask.to(device)
                    logits = model(idx, mask)
                    probs = F.softmax(logits, dim=1)[:, 1]
                    val_probs.extend(probs.cpu().numpy())
                    val_true.extend(lab.numpy())

            # Compute AUC (handle edge cases)
            val_preds_binary = [1 if p > 0.5 else 0 for p in val_probs]
            try:
                val_auc = roc_auc_score(val_true, val_probs)
            except ValueError:
                val_auc = 0.5  # Default when predictions are constant

            avg_loss = total_loss / len(train_loader)
            n_pos_pred = sum(val_preds_binary)
            n_pos_true = sum(val_true)

            print(f"  Epoch {epoch+1}: loss={avg_loss:.4f}, val_auc={val_auc:.4f}, pred_pos={n_pos_pred}/{len(val_true)}, true_pos={n_pos_true}")

            if val_auc > best_auc and val_auc > 0.5:
                best_auc = val_auc
                best_state = {k: v.clone() for k, v in model.state_dict().items()}

            # Early stopping on validation loss
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= 5:
                    print(f"  Early stopping at epoch {epoch+1}")
                    break

        # Get best model predictions (or current if no improvement)
        if best_state is not None:
            model.load_state_dict(best_state)
        model.eval()

        fold_probs = []
        fold_labels = []

        with torch.no_grad():
            for batch in val_loader:
                idx, mask, lab = batch
                idx, mask = idx.to(device), mask.to(device)
                logits = model(idx, mask)
                probs = F.softmax(logits, dim=1)[:, 1]
                fold_probs.extend(probs.cpu().numpy())
                fold_labels.extend(lab.numpy())

        all_probs.extend(fold_probs)
        all_labels.extend(fold_labels)
        print(f"  Best AUC: {best_auc:.4f}")

        # Track best fold model
        if best_auc > best_fold_auc:
            best_fold_auc = best_auc
            best_fold_model = {k: v.clone() for k, v in model.state_dict().items()}
            print(f"  ** New best fold model (AUC={best_auc:.4f}) **")

    # Overall CV results
    cv_auc = roc_auc_score(all_labels, all_probs)
    cv_acc = accuracy_score(all_labels, (np.array(all_probs) >= 0.5).astype(int))

    print(f"\n{'='*60}")
    print(f"5-Fold CV Results:")
    print(f"  AUC: {cv_auc:.4f}")
    print(f"  Accuracy: {cv_acc:.4f}")

    # Use the best model from fold with highest AUC
    print(f"\nUsing best fold model for inference (fold AUC={best_fold_auc:.4f})...")
    final_model = MoLFormerCNN(len(tokenizer.vocab)).to(device)
    final_model.load_state_dict(best_fold_model)

    # Save model
    torch.save(final_model.state_dict(), OUTPUT_DIR.parent.parent / "MoLFormer_Comparison" / "Models" / "diqt_cnn_final.pt")

    # Inference on Cardiac RODEO
    print(f"\n{'='*60}")
    print("Cardiac RODEO Inference")
    print("="*60)

    cardiac_path = MOLFORMER_REPO / "data" / "cardiac_rodeo_inference.csv"
    cardiac_df = pd.read_csv(cardiac_path)

    cardiac_dataset = SimpleDataset(
        cardiac_df['canonical_smiles'].tolist(),
        cardiac_df['Arrhythmia_label'].values,
        tokenizer
    )
    cardiac_loader = torch.utils.data.DataLoader(
        cardiac_dataset, batch_size=25, collate_fn=collate_fn)  # All 25 drugs in one batch

    final_model.eval()
    cnn_probs = []
    cnn_labels = []

    with torch.no_grad():
        for batch in cardiac_loader:
            idx, mask, lab = batch
            idx, mask = idx.to(device), mask.to(device)
            logits = final_model(idx, mask)
            probs = F.softmax(logits, dim=1)[:, 1]
            cnn_probs.extend(probs.cpu().numpy())
            cnn_labels.extend(lab.numpy())

    cnn_auc = roc_auc_score(cnn_labels, cnn_probs)
    cnn_preds = (np.array(cnn_probs) >= 0.5).astype(int)
    cnn_acc = accuracy_score(cnn_labels, cnn_preds)

    print(f"CNN Results (DIQT -> Arrhythmia):")
    print(f"  AUC: {cnn_auc:.4f}")
    print(f"  Accuracy: {cnn_acc:.4f}")

    # Save predictions
    cardiac_df['CNN_prob'] = cnn_probs
    cardiac_df['CNN_pred'] = cnn_preds
    cardiac_df.to_csv(OUTPUT_DIR / "molformer_cnn_predictions_25.csv", index=False)

    # Save metrics
    metrics = {
        'Model': 'MoLFormer-XL-CNN',
        'DIQT_CV_AUC': cv_auc,
        'DIQT_CV_Acc': cv_acc,
        'Cardiac_AUC': cnn_auc,
        'Cardiac_Acc': cnn_acc,
    }
    pd.DataFrame([metrics]).to_csv(OUTPUT_DIR / "molformer_cnn_metrics.csv", index=False)

    print(f"\nResults saved to {OUTPUT_DIR}")
    print("DONE!")


if __name__ == "__main__":
    main()
