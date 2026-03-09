"""Quick test of MoLFormer-XL-CNN architecture."""
import warnings
warnings.filterwarnings('ignore')

import sys
from pathlib import Path
from functools import partial

import torch
import torch.nn as nn

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MOLFORMER_REPO = PROJECT_ROOT / "MoLFormer_XL_CNN_repo"

sys.path.insert(0, str(MOLFORMER_REPO / "linear_attention_rotary"))

print("Importing pytorch-fast-transformers...")
from fast_transformers.masking import LengthMask as LM
from fast_transformers.feature_maps import GeneralizedRandomFeatures
print("OK")

print("Importing MoLFormer repo modules...")
from rotate_attention.rotate_builder import RotateEncoderBuilder as rotate_builder
from rotate_attention.linear_attention import LinearWWeight  # Registers 'linearwweights'
from tokenizer.tokenizer import MolTranBertTokenizer
print("OK")

# Load tokenizer
vocab_path = MOLFORMER_REPO / "linear_attention_rotary" / "bert_vocab.txt"
tokenizer = MolTranBertTokenizer(str(vocab_path))
print(f"Tokenizer loaded: {len(tokenizer.vocab)} tokens")

# Test tokenization
test_smiles = "CCO"  # Ethanol
tokens = tokenizer.encode(test_smiles, add_special_tokens=True)
print(f"Test SMILES '{test_smiles}' -> tokens: {tokens}")

# Build simple model
print("\nBuilding transformer encoder...")
n_embd = 768
n_head = 12
n_layer = 2  # Just 2 layers for testing
num_feats = 32

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

blocks = builder.get()
tok_emb = nn.Embedding(len(tokenizer.vocab), n_embd)
print("Model built!")

# Test forward pass
print("\nTesting forward pass...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

blocks = blocks.to(device)
tok_emb = tok_emb.to(device)

# Create batch
batch_tokens = torch.tensor([tokens], dtype=torch.long).to(device)
batch_mask = torch.ones_like(batch_tokens).to(device)

# Forward
x = tok_emb(batch_tokens)
print(f"Embedding output shape: {x.shape}")

length_mask = LM(batch_mask.sum(-1))
print(f"Length mask: {batch_mask.sum(-1)}")

x, attn_list = blocks(x, length_mask=length_mask)
print(f"Transformer output shape: {x.shape}")
print(f"Number of attention layers: {len(attn_list)}")

print("\n=== SUCCESS! MoLFormer-XL-CNN architecture works! ===")
