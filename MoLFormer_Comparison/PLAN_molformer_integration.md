# MoLFormer-XL-CNN Integration Plan for Cardiac RODEO

## User Configuration
- **GPU:** NVIDIA GPU available (CUDA environment)
- **Primary Focus:** DIQT vs Arrhythmia comparison
- **Validation:** Reproduce paper results first, then run on 25 drugs

## Overview

Integrate MoLFormer-XL-CNN (Lin et al., 2024 - MDPI) for drug toxicity prediction, enabling comparison against organoid-based PK-PD models. Follows the established ADMET comparison pattern.

**Primary Target Alignment:**
| MoLFormer Target | Organoid Target | Description |
|------------------|-----------------|-------------|
| **DIQT** (QT prolongation) | **Arrhythmia** | **PRIMARY** - QT prolongation causes arrhythmias |

**Secondary (optional):**
| MoLFormer Target | Organoid Target | Description |
|------------------|-----------------|-------------|
| DIR (Rhabdomyolysis) | heart_damage | Muscle/cardiac damage correlation |
| DIT (Teratogenicity) | -- | Additional toxicity context |

---

## Phase 1: Repository Setup

### 1.1 Clone Repository
```powershell
cd "C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO"
git clone https://github.com/LiSH7450/MoLFormer-XL-CNN_model.git MoLFormer_XL_CNN_repo
```

### 1.2 Create Folder Structure
```
MoLFormer_Comparison/
├── Scripts/
│   ├── __init__.py
│   ├── full_analysis.py           # Main comparison script
│   ├── run_inference.py           # Inference on 25 drugs
│   ├── reproduce_paper.py         # Reproduce benchmark results
│   └── environment_check.py       # Validate environment
├── Models/
│   └── checkpoints/               # Downloaded pre-trained models
├── Data/
│   └── intermediate/              # Processing files
└── README.md

Output/MoLFormer_Comparison/
├── figures/                       # PDF figures
├── molformer_predictions_25.csv
├── molformer_metrics.csv
├── DIQT_vs_Arrhythmia_comparison.csv
├── DIR_vs_HeartDamage_comparison.csv
├── roc_curves_molformer.xlsx
├── confusion_matrices_molformer.xlsx
├── final_comparison_all_models.csv
└── *.png (plots)
```

---

## Phase 2: Environment Setup

### GPU Environment (Selected)
```powershell
conda create --name molformer_env python=3.8.10
conda activate molformer_env

# PyTorch with CUDA 11
conda install pytorch==1.7.1 cudatoolkit=11.0 -c pytorch
conda install rdkit==2022.03.2 -c conda-forge
pip install transformers==4.6.0 pytorch-lightning==1.1.5
pip install pytorch-fast-transformers==0.4.0 datasets==1.6.2

# NVIDIA Apex (for optimized training/inference)
git clone https://github.com/NVIDIA/apex && cd apex
pip install -v --no-cache-dir --global-option="--cpp_ext" --global-option="--cuda_ext" ./
```

---

## Phase 3: Script Development

### 3.1 `environment_check.py`
- Validate CUDA/CPU availability
- Check all dependencies with versions
- Verify model checkpoint files exist
- Run diagnostic before main analysis

### 3.2 `reproduce_paper.py`
- Load original DIQT/DIR/DIT datasets from repository
- Run 5-fold CV matching paper methodology
- Compute 9 metrics: Accuracy, Recall, Precision, MCC, BACC, F1, AUROC, AUPRC, Specificity
- Validate: DIQT AUC ~0.83, DIR AUC ~0.70, DIT AUC ~0.70 (from paper Table 1)

### 3.3 `run_inference.py`
- Load 25 drugs from `Cleaned_Data/drug_smiles.csv`
- Canonicalize SMILES with RDKit
- Run inference for DIQT, DIR, DIT targets
- Output: `molformer_predictions_25.csv`

### 3.4 `full_analysis.py` (Main Script)
Following ADMET pattern (`ADMET_Comparison/Scripts/full_analysis.py`):

**Section 1:** Reproduce paper results
**Section 2:** Load Cardiac RODEO drug database (25 drugs)
**Section 3:** MoLFormer predictions on 25 drugs
**Section 4:** Compare DIQT vs Arrhythmia labels
**Section 5:** Compare DIR vs heart_damage labels
**Section 6:** Load organoid LOOCV results
**Section 7:** Combined ROC analysis (MoLFormer + Organoid + ADMET)
**Section 8:** Generate confusion matrices
**Section 9:** Excel summaries
**Section 10:** LaTeX report

---

## Phase 4: Output Files

### CSV Files
| File | Contents |
|------|----------|
| `molformer_predictions_25.csv` | Drug, SMILES, DIQT_prob, DIR_prob, DIT_prob |
| `molformer_metrics.csv` | Per-target metrics (Acc, AUC, MCC, etc.) |
| `DIQT_vs_Arrhythmia_comparison.csv` | Drug, DIQT_prob, Arrhythmia_label, Organoid_prob |
| `DIR_vs_HeartDamage_comparison.csv` | Drug, DIR_prob, HeartDamage_label, Organoid_prob |
| `final_comparison_all_models.csv` | Summary: MoLFormer vs ADMET vs Organoid |

### Plots (PNG + PDF)
- `MoLFormer_ROC_25.png` - ROC curves for DIQT/DIR
- `MoLFormer_vs_Organoid_ROC.png` - Overlay comparison
- `Overall_Comparison_ROC.png` - All 4+ models combined
- `MoLFormer_Confusion_Matrices.png` - Side-by-side CMs
- `Accuracy_AUC_Comparison_All.png` - Bar chart comparison

### Excel Files
- `molformer_analysis_summary.xlsx` (Predictions, Metrics, ROC_Data sheets)
- `roc_curves_molformer.xlsx`
- `confusion_matrices_molformer.xlsx`

---

## Phase 5: Verification Steps

### Step 1: Environment
```powershell
python MoLFormer_Comparison/Scripts/environment_check.py
# Expected: All checks passed
```

### Step 2: Paper Reproduction
```powershell
python MoLFormer_Comparison/Scripts/reproduce_paper.py
# Expected: DIQT AUC within 2% of 0.829, DIR AUC within 2% of 0.703
```

### Step 3: Inference
```powershell
python MoLFormer_Comparison/Scripts/run_inference.py
# Expected: 25/25 (or 23/25) drugs processed
```

### Step 4: Full Analysis
```powershell
python MoLFormer_Comparison/Scripts/full_analysis.py
# Expected: All outputs generated in Output/MoLFormer_Comparison/
```

---

## Phase 6: Fallback Options

### If No GPU Available
- Use CPU-only environment (slower but functional)
- Alternatively: Google Colab with free GPU

### If Checkpoints Unavailable
- Contact paper authors
- Or retrain on paper datasets using their hyperparameters

### If SMILES Parsing Fails
- Document failed drugs (expect similar to SwissADME: 23/25)
- Run analysis on available subset
- Report N values clearly

---

## Critical Files Reference

| Purpose | File |
|---------|------|
| ADMET pattern template | `ADMET_Comparison/Scripts/full_analysis.py` |
| Drug SMILES source | `Cleaned_Data/drug_smiles.csv` |
| Ground truth labels | `Cleaned_Data/drug_classification.csv` |
| Organoid metrics | `Output/Performance_Metrics/loocv_results.csv` |
| ADMET predictions | `Output/ADMET_Comparison/dictrank_retrain_predictions_25.csv` |

---

## Expected Comparison Results

The final comparison table will include:

| Model | Target | N Drugs | Accuracy | ROC AUC |
|-------|--------|---------|----------|---------|
| MoLFormer DIQT | Arrhythmia | 25 | ? | ? |
| MoLFormer DIR | heart_damage | 25 | ? | ? |
| ADMET-AI DICTrank | heart_damage | 25 | 0.52 | 0.53 |
| SwissADME DICTrank | heart_damage | 23 | 0.57 | 0.55 |
| Organoid XGBoost | Arrhythmia | 25 | 0.72 | 0.78 |
| Organoid XGBoost | heart_damage | 25 | 0.72 | 0.71 |

This enables direct comparison of structure-based (MoLFormer, ADMET) vs functional (Organoid) approaches for cardiac toxicity prediction.
