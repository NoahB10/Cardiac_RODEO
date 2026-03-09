"""
MoLFormer-XL-CNN Inference using Original Architecture.

Uses pytorch-fast-transformers for the rotary attention mechanism
and the TextCNN layers from the original paper.
"""
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
from sklearn.metrics import (
    accuracy_score, roc_auc_score, precision_score, recall_score,
    f1_score, confusion_matrix, matthews_corrcoef, balanced_accuracy_score,
    average_precision_score, roc_curve
)

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MOLFORMER_REPO = PROJECT_ROOT / "MoLFormer_XL_CNN_repo"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "MoLFormer_Comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Add paths for imports
sys.path.insert(0, str(MOLFORMER_REPO / "linear_attention_rotary"))

# pytorch-fast-transformers imports
from fast_transformers.masking import LengthMask as LM
from fast_transformers.feature_maps import GeneralizedRandomFeatures

# Local imports from MoLFormer repo
from rotate_attention.rotate_builder import RotateEncoderBuilder as rotate_builder
from rotate_attention.linear_attention import LinearWWeight  # Import to register the attention type
from tokenizer.tokenizer import MolTranBertTokenizer


class CNN(nn.Module):
    """TextCNN block from the MoLFormer-XL-CNN paper."""
    def __init__(self, smiles_embed_dim=768):
        super(CNN, self).__init__()
        self.conv_block = nn.Sequential(
            nn.Conv1d(in_channels=smiles_embed_dim, out_channels=smiles_embed_dim*3, kernel_size=3, padding=1),
            nn.BatchNorm1d(num_features=smiles_embed_dim*3),
            nn.ReLU(),
            nn.Conv1d(in_channels=smiles_embed_dim*3, out_channels=smiles_embed_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(num_features=smiles_embed_dim),
            nn.ReLU(),
        )

    def forward(self, x):
        x = x.permute(0, 2, 1)  # (batch, seq_len, embed) -> (batch, embed, seq_len)
        x = self.conv_block(x)
        return x


class MoLFormerCNN(nn.Module):
    """Full MoLFormer-XL-CNN model."""
    def __init__(self, tokenizer, n_embd=768, n_head=12, n_layer=12,
                 num_feats=32, dropout=0.2, num_classes=2):
        super().__init__()
        self.n_embd = n_embd
        n_vocab = len(tokenizer.vocab)

        # Token embedding
        self.tok_emb = nn.Embedding(n_vocab, n_embd)
        self.drop = nn.Dropout(dropout)

        # Transformer encoder with rotary embeddings
        # Use 'linearwweights' attention type (custom from MoLFormer repo that returns attention weights)
        builder = rotate_builder.from_kwargs(
            n_layers=n_layer,
            n_heads=n_head,
            query_dimensions=n_embd // n_head,
            value_dimensions=n_embd // n_head,
            feed_forward_dimensions=n_embd,
            attention_type='linearwweights',
            feature_map=partial(GeneralizedRandomFeatures, n_dims=num_feats),
            activation='gelu',
        )
        self.blocks = builder.get()

        # CNN layers
        self.net = CNN(n_embd)

        # Classification head
        self.ffn = nn.Sequential(
            nn.Linear(n_embd, n_embd),
            nn.Dropout(dropout),
            nn.ReLU(),
            nn.Linear(n_embd, num_classes),
        )

    def forward(self, idx, mask):
        b = idx.shape[0]

        # Token embeddings
        token_embeddings = self.tok_emb(idx)
        x = self.drop(token_embeddings)

        # Transformer blocks (VizEncoder returns tuple: (x, attention_list))
        x, _ = self.blocks(x, length_mask=LM(mask.sum(-1)))
        token_embeddings = x

        # Apply mask
        input_mask_expanded = mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        token_embeddings = token_embeddings * input_mask_expanded

        # CNN
        token_embeddings = self.net(token_embeddings)
        token_embeddings = token_embeddings.permute(0, 2, 1)  # Back to (batch, seq_len, embed)

        # Mean pooling
        sum_embeddings = torch.sum(token_embeddings, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        pooled = sum_embeddings / sum_mask

        # Classification
        logits = self.ffn(pooled)
        return logits


def load_pretrained_molformer(model, checkpoint_path, device):
    """Load pre-trained MoLFormer weights (tok_emb and blocks only)."""
    print(f"Loading pre-trained MoLFormer from: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)
    state_dict = checkpoint['state_dict']

    # Filter to only MoLFormer weights (tok_emb and blocks)
    molformer_weights = {}
    for k, v in state_dict.items():
        if k.startswith('tok_emb') or k.startswith('blocks'):
            molformer_weights[k] = v

    # Load with strict=False (CNN and FFN are randomly initialized)
    missing, unexpected = model.load_state_dict(molformer_weights, strict=False)
    print(f"Loaded {len(molformer_weights)} MoLFormer weights")
    print(f"Missing keys (will be trained): {len(missing)} (CNN + FFN)")

    return model


def compute_metrics(y_true, y_pred, y_prob):
    """Compute classification metrics."""
    metrics = {
        'Accuracy': accuracy_score(y_true, y_pred),
        'Precision': precision_score(y_true, y_pred, zero_division=0),
        'Recall': recall_score(y_true, y_pred, zero_division=0),
        'F1': f1_score(y_true, y_pred, zero_division=0),
        'MCC': matthews_corrcoef(y_true, y_pred),
        'AUROC': roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else 0,
        'AUPRC': average_precision_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else 0,
    }
    return metrics


def train_epoch(model, train_loader, optimizer, criterion, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0

    for batch in train_loader:
        idx, mask, labels = batch
        idx, mask, labels = idx.to(device), mask.to(device), labels.to(device)

        optimizer.zero_grad()
        logits = model(idx, mask)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(train_loader)


def evaluate(model, val_loader, device):
    """Evaluate model."""
    model.eval()
    all_preds = []
    all_probs = []
    all_labels = []

    with torch.no_grad():
        for batch in val_loader:
            idx, mask, labels = batch
            idx, mask = idx.to(device), mask.to(device)

            logits = model(idx, mask)
            probs = F.softmax(logits, dim=1)[:, 1]
            preds = logits.argmax(dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
            all_labels.extend(labels.numpy())

    return np.array(all_labels), np.array(all_preds), np.array(all_probs)


class DIQTDataset(torch.utils.data.Dataset):
    """Dataset for DIQT training."""
    def __init__(self, smiles_list, labels, tokenizer, max_len=512):
        self.smiles_list = smiles_list
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.smiles_list)

    def __getitem__(self, idx):
        smiles = self.smiles_list[idx]
        label = self.labels[idx]

        tokens = self.tokenizer.encode(smiles, add_special_tokens=True)
        if len(tokens) > self.max_len:
            tokens = tokens[:self.max_len]

        mask = [1] * len(tokens)

        return (
            torch.tensor(tokens, dtype=torch.long),
            torch.tensor(mask, dtype=torch.long),
            torch.tensor(label, dtype=torch.long)
        )


def collate_fn(batch):
    """Custom collate function with dynamic padding."""
    tokens_list, masks_list, labels_list = zip(*batch)

    # Find max length in this batch
    max_len = max(len(t) for t in tokens_list)

    # Pad all to max length
    padded_tokens = []
    padded_masks = []
    for tokens, mask in zip(tokens_list, masks_list):
        pad_len = max_len - len(tokens)
        padded_tokens.append(torch.cat([tokens, torch.zeros(pad_len, dtype=torch.long)]))
        padded_masks.append(torch.cat([mask, torch.zeros(pad_len, dtype=torch.long)]))

    return (
        torch.stack(padded_tokens),
        torch.stack(padded_masks),
        torch.stack(labels_list)
    )


def train_diqt_model(tokenizer, device, n_epochs=20, batch_size=16, lr=3e-5):
    """Train MoLFormer-XL-CNN on DIQT dataset with 5-fold CV."""
    print("\n" + "="*60)
    print("Training MoLFormer-XL-CNN on DIQT Dataset")
    print("="*60)

    # Load DIQT dataset
    diqt_path = MOLFORMER_REPO / "Datasets" / "DIQT.xlsx"
    df = pd.read_excel(diqt_path)
    df = df[['canonical_smiles', 'label']].dropna()

    smiles_list = df['canonical_smiles'].tolist()
    labels = df['label'].values

    print(f"DIQT dataset: {len(df)} samples")
    print(f"Label distribution: {dict(zip(*np.unique(labels, return_counts=True)))}")

    # 5-fold CV
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    all_val_labels = []
    all_val_probs = []

    for fold, (train_idx, val_idx) in enumerate(cv.split(smiles_list, labels)):
        print(f"\n--- Fold {fold + 1}/5 ---")

        # Split data
        train_smiles = [smiles_list[i] for i in train_idx]
        train_labels = labels[train_idx]
        val_smiles = [smiles_list[i] for i in val_idx]
        val_labels = labels[val_idx]

        # Create datasets
        train_dataset = DIQTDataset(train_smiles, train_labels, tokenizer)
        val_dataset = DIQTDataset(val_smiles, val_labels, tokenizer)

        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, collate_fn=collate_fn)

        # Create model
        model = MoLFormerCNN(tokenizer, num_classes=2).to(device)

        # Load pre-trained MoLFormer weights
        checkpoint_path = MOLFORMER_REPO / "data" / "Pretrained MoLFormer" / "checkpoints" / "N-Step-Checkpoint_3_30000.ckpt"
        model = load_pretrained_molformer(model, checkpoint_path, device)

        # Training setup
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-6)
        criterion = nn.CrossEntropyLoss()

        # Train
        best_val_auc = 0
        best_model_state = None

        for epoch in range(n_epochs):
            train_loss = train_epoch(model, train_loader, optimizer, criterion, device)

            if (epoch + 1) % 10 == 0:
                y_true, y_pred, y_prob = evaluate(model, val_loader, device)
                val_auc = roc_auc_score(y_true, y_prob)
                print(f"  Epoch {epoch+1}: train_loss={train_loss:.4f}, val_auc={val_auc:.4f}")

                if val_auc > best_val_auc:
                    best_val_auc = val_auc
                    best_model_state = model.state_dict().copy()

        # Load best model and get final predictions
        model.load_state_dict(best_model_state)
        y_true, y_pred, y_prob = evaluate(model, val_loader, device)

        all_val_labels.extend(y_true)
        all_val_probs.extend(y_prob)

        print(f"  Fold {fold+1} best AUC: {best_val_auc:.4f}")

    # Overall CV metrics
    all_val_labels = np.array(all_val_labels)
    all_val_probs = np.array(all_val_probs)
    all_val_preds = (all_val_probs >= 0.5).astype(int)

    cv_metrics = compute_metrics(all_val_labels, all_val_preds, all_val_probs)

    print("\n" + "-"*40)
    print("5-Fold CV Results (MoLFormer-XL-CNN):")
    print("-"*40)
    for name, value in cv_metrics.items():
        print(f"  {name}: {value:.4f}")

    # Train final model on all data
    print("\nTraining final model on all DIQT data...")
    full_dataset = DIQTDataset(smiles_list, labels, tokenizer)
    full_loader = torch.utils.data.DataLoader(full_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)

    final_model = MoLFormerCNN(tokenizer, num_classes=2).to(device)
    final_model = load_pretrained_molformer(final_model, checkpoint_path, device)

    optimizer = torch.optim.AdamW(final_model.parameters(), lr=lr, weight_decay=1e-6)

    for epoch in range(n_epochs):
        train_loss = train_epoch(final_model, full_loader, optimizer, criterion, device)
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}: train_loss={train_loss:.4f}")

    # Save model
    model_path = PROJECT_ROOT / "MoLFormer_Comparison" / "Models" / "diqt_cnn_classifier.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(final_model.state_dict(), model_path)
    print(f"Model saved to: {model_path}")

    return final_model, cv_metrics


def run_cardiac_rodeo_inference(model, tokenizer, device):
    """Run inference on Cardiac RODEO drugs."""
    print("\n" + "="*60)
    print("Running CNN Inference on Cardiac RODEO Drugs")
    print("="*60)

    # Load Cardiac RODEO data
    cardiac_path = MOLFORMER_REPO / "data" / "cardiac_rodeo_inference.csv"
    df = pd.read_csv(cardiac_path)

    print(f"Cardiac RODEO drugs: {len(df)}")

    # Create dataset
    smiles_list = df['canonical_smiles'].tolist()
    labels = df['Arrhythmia_label'].values

    dataset = DIQTDataset(smiles_list, labels, tokenizer)
    loader = torch.utils.data.DataLoader(dataset, batch_size=8, collate_fn=collate_fn)

    # Get predictions
    y_true, y_pred, y_prob = evaluate(model, loader, device)

    # Add predictions to dataframe
    df['CNN_pred'] = y_pred
    df['CNN_prob'] = y_prob

    # Compute metrics
    metrics = compute_metrics(y_true, y_pred, y_prob)

    print("\n" + "-"*40)
    print("CNN DIQT → Arrhythmia Metrics:")
    print("-"*40)
    for name, value in metrics.items():
        print(f"  {name}: {value:.4f}")

    # Per-drug results
    print("\n" + "-"*60)
    print(f"{'Drug':<20} {'CNN_prob':>10} {'CNN_pred':>10} {'Arrhythmia':>12} {'Match':>8}")
    print("-"*60)

    for _, row in df.iterrows():
        match = "Yes" if row['CNN_pred'] == row['Arrhythmia_label'] else "No"
        arr_str = "True" if row['Arrhythmia_label'] == 1 else "False"
        print(f"{row['Drug']:<20} {row['CNN_prob']:>10.4f} {row['CNN_pred']:>10} {arr_str:>12} {match:>8}")

    # Save results
    output_path = OUTPUT_DIR / "molformer_cnn_predictions_25.csv"
    df.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")

    # Save metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_df['Model'] = 'MoLFormer-XL-CNN'
    metrics_df['Target'] = 'DIQT → Arrhythmia'
    metrics_df['N_drugs'] = len(df)
    metrics_df.to_csv(OUTPUT_DIR / "molformer_cnn_metrics.csv", index=False)

    return df, metrics


def main():
    print("="*60)
    print("MoLFormer-XL-CNN Inference")
    print("Using Original Architecture with pytorch-fast-transformers")
    print("="*60)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load tokenizer
    vocab_path = MOLFORMER_REPO / "linear_attention_rotary" / "bert_vocab.txt"
    tokenizer = MolTranBertTokenizer(str(vocab_path))
    print(f"Tokenizer loaded: {len(tokenizer.vocab)} tokens")

    # Train on DIQT
    model, diqt_metrics = train_diqt_model(tokenizer, device, n_epochs=20)

    # Inference on Cardiac RODEO
    results_df, cardiac_metrics = run_cardiac_rodeo_inference(model, tokenizer, device)

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
