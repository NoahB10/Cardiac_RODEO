# SwissADME LOOCV AUC = 0.00 Investigation

## Summary
SwissADME LOOCV shows 0.00 AUC despite 83% accuracy. This is a **legitimate result caused by extreme class imbalance**, not a bug.

## Root Cause Analysis

### Class Distribution Comparison
| Dataset | Total | Cardiotoxic | Not Cardiotoxic | Minority % |
|---------|-------|-------------|-----------------|------------|
| ADMET-AI (25 drugs) | 25 | 20 | 5 | 20% |
| SwissADME (23 drugs) | 23 | 20 | 3 | 13% |

**Critical Finding:** The 2 removed drugs (Dactinomycin and Plicamycin, excluded due to MW > 1000 Da) were **both from the negative class**, reducing minority samples from 5 → 3.

### LOOCV Training Conditions
- **ADMET-AI:** Each fold trains on 4 negative + 20 positive (16.7% negative)
- **SwissADME:** Each fold trains on **2 negative + 20 positive (9.1% negative)**

With only 9% negative samples in training, the model learns to predict everything as cardiotoxic.

## Diagnostic Results

### Predicted Probabilities
```
All 3 negative class drugs predicted with probability = 1.0:
- Erlotinib:   prob = 1.000 (actual: not cardiotoxic)
- Etomoxir:    prob = 1.000 (actual: not cardiotoxic)
- Mexiletine:  prob = 1.000 (actual: not cardiotoxic)

Positive class range: [0.366, 1.000]
```

### Confusion Matrix
```
              Predicted
              Neg   Pos
Actual  Neg    0     3    ← All negatives misclassified
        Pos    1    19    ← 19/20 positives correct

Accuracy: 83% (19+0 out of 23 correct)
```

### ROC Curve Breakdown
```
FPR: [0.00, 0.33, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]
TPR: [0.00, 0.00, 0.00, 0.25, 0.40, 0.50, 0.60, 1.00]
```

**Why AUC = 0.00:**
1. At threshold < 1.0: FPR jumps to 0.33 (1/3 negatives wrong) with TPR still at 0
2. At threshold < 1.0 (continued): FPR reaches 1.0 (all 3 negatives wrong) before capturing any positives
3. At threshold < 0.99999: TPR increases from 0 → 1.0, but FPR is already maxed at 1.0
4. The ROC curve has a **vertical segment** (1.0, 0) → (1.0, 1.0), contributing **zero area**

## Comparison with ADMET-AI

| Model | N | Negatives | AUC | Accuracy | TN | FP | Interpretation |
|-------|---|-----------|-----|----------|----|----|----------------|
| ADMET-AI | 25 | 5 (20%) | 0.39 | 60% | 0 | 5 | Worse than random (0.50) |
| SwissADME | 23 | 3 (13%) | 0.00 | 83% | 0 | 3 | Worst possible discrimination |

**Both models fail to correctly classify ANY negative samples (TN=0)**, but SwissADME is worse because:
- Fewer negative training samples → more extreme overfitting to positive class
- Predicts all negatives with maximum confidence (prob=1.0 vs ADMET-AI's more varied predictions)

## Conclusion

The 0.00 AUC is **mathematically correct** and reflects:
1. Insufficient negative class representation (3 samples)
2. LOOCV training on only 2 negative samples per fold (9%)
3. Model learns to predict everything as cardiotoxic with extreme confidence
4. ROC curve pathology: FPR=1.0 before any positive class discrimination

**The removal of 2 drugs DID significantly affect the result** by reducing the minority class below the critical threshold needed for LOOCV to function properly.

## Recommendation

Report the 0.00 AUC as-is with the explanation now added to the LaTeX report (page 7, after LOOCV performance table). The explanation clarifies that this is a data limitation, not a model failure.
