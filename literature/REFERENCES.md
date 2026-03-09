# Cardiotoxicity Prediction Literature References

This folder contains papers on computational cardiotoxicity prediction.

---

## Download Summary

| Paper | Status | Filename |
|-------|--------|----------|
| Iftkhar et al. 2022 (cardioToxCSM) | **DOWNLOADED** | `Iftkhar_2022_cardioToxCSM_preprint.pdf` |
| Li et al. 2025 (Ensemble ML) | **DOWNLOADED** | `Li_2025_Ensemble_ML.pdf` |
| Llopis-Lorente et al. 2020 | Requires institutional access | - |
| Lin et al. 2024 (MoLFormer) | Paper not found/unclear reference | - |
| Vinh et al. 2024 (Attention GNN) | Requires institutional access | - |
| He et al. 2025 (ToxBERT) | Requires institutional access | - |
| Rouen et al. 2025 (Molecular Sim) | **DOWNLOADED** | `Rouen_2025_TdP_Arrhythmia_Risk_Molecular_Simulations.pdf` |

### Bonus Papers Downloaded (Highly Relevant)

| Paper | Filename | Description |
|-------|----------|-------------|
| AttenhERG 2024 | `AttenhERG_2024_GNN_hERG.pdf` | GNN for hERG blocker prediction (BMC, open access) |
| Benchmarking 2024 | `Benchmarking_hERG_Nav_Cav_2024.pdf` | Feature representations for ion channel toxicity (bioRxiv) |
| DICTrank Classifiers 2024 | `DICTrank_Classifiers_2024_preprint.pdf` | FDA cardiotoxicity rank classifiers (bioRxiv) |
| Frontiers 2021 | `Frontiers_2021_ANN_Proarrhythmicity.pdf` | ANN for proarrhythmicity assessment |
| Frontiers 2020 | `Frontiers_Cardiotoxicity_2020.pdf` | Dual transcriptomic + ML cardiotoxicity |
| Semisupervised 2024 | `Semisupervised_hERG_Nav_Cav_2024.pdf` | Semisupervised learning for ion channels (bioRxiv) |

**Total: 9 PDFs downloaded**

---

## Original Papers Requested

### 1. Iftkhar et al. (2022) - cardioToxCSM [DOWNLOADED]

**Title:** cardioToxCSM: A Web Server for Predicting Cardiotoxicity of Small Molecules

**Authors:** Saba Iftkhar, Alex G. C. de Sa, Joao P. L. Velloso, Raghad Aljarf, Douglas E. V. Pires, David B. Ascher

**Journal:** Journal of Chemical Information and Modeling, 2022, 62(20), 4827-4836

**DOI:** https://doi.org/10.1021/acs.jcim.2c00822

**Model:** Random Forest, Gradient Boosting, XGBoost using graph-based signatures and molecular fingerprints

**Predicted Endpoints:** Arrhythmia, Cardiac Failure, Heart Block, hERG toxicity, Hypertension, Myocardial Infarction

**Performance:** AUC up to 0.898 on 5-fold cross-validation

**Downloaded:** `Iftkhar_2022_cardioToxCSM_preprint.pdf` (bioRxiv preprint version)

**Web Server:** https://biosig.lab.uq.edu.au/cardiotoxcsm/

---

### 2. Li et al. (2025) - Ensemble ML/DL [DOWNLOADED]

**Title:** In silico prediction of drug-induced cardiotoxicity with ensemble machine learning and structural pattern recognition

**Authors:** Li S., Xu H., Liu F., et al.

**Journal:** Molecular Diversity, 2025

**DOI:** https://doi.org/10.1007/s11030-025-11266-8

**Model:** Ensemble of 7 ML and 5 Deep Learning models (110 total models per endpoint)

**Predicted Endpoints:** Heart failure, Arrhythmia, Heart block, Hypertension, Heart attack

**Downloaded:** `Li_2025_Ensemble_ML.pdf`

---

### 3. Llopis-Lorente et al. (2020) - In Silico Classifiers [NOT DOWNLOADED]

**Title:** In Silico Classifiers for the Assessment of Drug Proarrhythmicity

**Authors:** Jordi Llopis-Lorente, Julio Gomis-Tena, Jordi Cano, Lucia Romero, Javier Saiz, Beatriz Trenor

**Journal:** Journal of Chemical Information and Modeling, 2020, 60(10), 5172-5187

**DOI:** https://doi.org/10.1021/acs.jcim.0c00201

**Model:** Decision Tree using electrophysiological parameters (Tx, TqNet)

**Performance:** Combined classifier achieved 94.5% accuracy

**Status:** Requires institutional access (ACS paywall)

**Access Links:**
- Publisher: https://pubs.acs.org/doi/10.1021/acs.jcim.0c00201
- PubMed: https://pubmed.ncbi.nlm.nih.gov/32786710/
- Repository: https://riunet.upv.es/handle/10251/161698

---

### 4. Lin et al. (2024) - MoLFormer-XL-CNN [NOT FOUND]

**Note:** The specific paper about MoLFormer-XL-CNN for cardiotoxicity was referenced in scoping reviews but the exact paper could not be located. The reference may be:

- Lin J. et al. "Advancing Adverse Drug Reaction Prediction with Deep Chemical Language Model for Drug Safety Evaluation" Int. J. Mol. Sci. 2024

**Related:** MoLFormer is available on HuggingFace: https://huggingface.co/ibm-research/MoLFormer-XL-both-10pct

---

### 5. Vinh et al. (2024) - Attention-Based GNN [NOT DOWNLOADED]

**Title:** Predicting Cardiotoxicity of Molecules Using Attention-Based Graph Neural Networks

**Authors:** Tuan Vinh, Loc Nguyen, Quang H. Trinh, Thanh-Hoang Nguyen-Vo, Binh P. Nguyen

**Journal:** Journal of Chemical Information and Modeling, 2024, 64(6), 1816-1827

**DOI:** https://doi.org/10.1021/acs.jcim.3c01286

**Model:** Attention-based Graph Neural Network

**Status:** Requires institutional access (ACS paywall)

**Access:** https://pubs.acs.org/doi/10.1021/acs.jcim.3c01286

---

### 6. He et al. (2025) - ToxBERT [NOT DOWNLOADED]

**Title:** ToxBERT: An explainable AI framework for enhancing prediction of adverse drug reactions and structural insights

**Authors:** Yujie He, Xiang Lv, Wuling Long, Shengqiu Zhai, Menglong Li, Zhining Wen

**Journal:** Journal of Pharmaceutical Analysis, 2025

**DOI:** https://doi.org/10.1016/j.jpha.2025.101387

**Model:** ToxBERT (Transformer-based BERT model)

**Predicted Endpoints:** DIQT (QT prolongation), DIR, DILI

**Status:** Open access but direct PDF download failed

**Access:** https://www.sciencedirect.com/science/article/pii/S2095177925002047

---

### 7. Rouen et al. (2025) - Molecular Simulation + RF [DOWNLOADED]

**Title:** Prediction of TdP Arrhythmia Risk Through Molecular Simulations of Conformation-specific Drug Interactions with the hERG K+, NaV1.5, and CaV1.2 Channels

**Authors:** Kyle C. Rouen, Kush Narang, et al.

**Journal:** bioRxiv (Preprint), September 2025

**DOI:** https://doi.org/10.1101/2025.09.25.678690

**Model:** Random Forest with SILCS physics-based ensemble docking

**Performance:** 94% accuracy with NaV1.5 inclusion

**Downloaded:** `Rouen_2025_TdP_Arrhythmia_Risk_Molecular_Simulations.pdf`

---

## Bonus Papers (Highly Relevant)

### AttenhERG (2024) [DOWNLOADED]

**Title:** AttenhERG: a reliable and interpretable graph neural network framework for predicting hERG channel blockers

**Journal:** Journal of Cheminformatics (BMC, Open Access)

**DOI:** https://doi.org/10.1186/s13321-024-00940-y

**Downloaded:** `AttenhERG_2024_GNN_hERG.pdf`

---

### Benchmarking hERG, Nav1.5, Cav1.2 (2024) [DOWNLOADED]

**Title:** Benchmarking of Small Molecule Feature Representations for hERG, Nav1.5, and Cav1.2 Cardiotoxicity Prediction

**Journal:** bioRxiv (Preprint)

**DOI:** https://doi.org/10.1101/2023.08.15.553429

**Downloaded:** `Benchmarking_hERG_Nav_Cav_2024.pdf`

---

### DICTrank Classifiers (2024) [DOWNLOADED]

**Title:** Insights into Drug Cardiotoxicity from Biological and Chemical Data: The First Public Classifiers for FDA Drug-Induced Cardiotoxicity Rank

**Journal:** bioRxiv (Preprint)

**DOI:** https://doi.org/10.1101/2023.10.15.562398

**Downloaded:** `DICTrank_Classifiers_2024_preprint.pdf`

---

### Frontiers ANN Proarrhythmicity (2021) [DOWNLOADED]

**Title:** Assessment of Drug Proarrhythmicity Using Artificial Neural Networks With in silico Deterministic Model Outputs

**Journal:** Frontiers in Physiology (Open Access)

**DOI:** https://doi.org/10.3389/fphys.2021.761691

**Downloaded:** `Frontiers_2021_ANN_Proarrhythmicity.pdf`

---

### Frontiers Dual Transcriptomic (2020) [DOWNLOADED]

**Title:** Dual Transcriptomic and Molecular Machine Learning Predicts all Major Clinical Forms of Drug Cardiotoxicity

**Journal:** Frontiers in Pharmacology (Open Access)

**DOI:** https://doi.org/10.3389/fphar.2020.00639

**Downloaded:** `Frontiers_Cardiotoxicity_2020.pdf`

---

### Semisupervised Learning (2024) [DOWNLOADED]

**Title:** Semi-Supervised Learning to Boost hERG, Nav1.5, and Cav1.2 Cardiac Ion Channel Toxicity Prediction by Mining a Large Unlabeled Small Molecule Data Set

**Journal:** bioRxiv (Preprint)

**DOI:** https://doi.org/10.1101/2024.05.25.595894

**Downloaded:** `Semisupervised_hERG_Nav_Cav_2024.pdf`

---

## How to Access Paywalled Papers

For papers requiring institutional access:

1. **Institutional Access:** Use your university library portal
2. **Author Contact:** Email corresponding authors via ResearchGate
3. **Interlibrary Loan:** Request through your library
4. **PubMed Central:** Check if free PMC version exists
5. **Preprint Servers:** Search bioRxiv, arXiv for author manuscripts

---

## Web Servers and Tools

| Tool | URL | Description |
|------|-----|-------------|
| cardioToxCSM | https://biosig.lab.uq.edu.au/cardiotoxcsm/ | Multi-endpoint cardiotoxicity prediction |
| OCHEM | https://ochem.eu/article/166881 | Online Chemical Modeling Environment |
| DICTrank Dataset | https://www.fda.gov/science-research/bioinformatics-tools/drug-induced-cardiotoxicity-rank-dictrank-dataset | FDA cardiotoxicity ranking |
| deephERG (GitHub) | https://github.com/ChengF-Lab/deephERG | Deep learning hERG prediction code |

---

*Generated: January 27, 2026*
*Total PDFs: 9*
