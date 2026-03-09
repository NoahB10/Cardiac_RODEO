"""
Diagnostic script to investigate why SwissADME LOOCV shows 0.00 AUC
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_curve, auc, accuracy_score, confusion_matrix

# Load the SwissADME data
swiss_path = r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\Output\ADMET_Comparison\cardiac_rodeo_full_swissadme.csv'
swiss_df = pd.read_csv(swiss_path)

print("SwissADME Data Shape:", swiss_df.shape)
print("\nColumns:", swiss_df.columns.tolist())
print("\nHeart Damage Distribution:")
print(swiss_df['heart_damage'].value_counts())

# Create binary target - handle both capitalized and lowercase
swiss_df['HD_binary'] = swiss_df['heart_damage'].astype(str).str.lower().map({'true': 1, 'false': 0})

print("\nHD_binary Distribution:")
print(swiss_df['HD_binary'].value_counts())

# Prepare features
feature_cols = [c for c in swiss_df.columns if c not in ['Drug', 'Arrhythmia', 'heart_damage', 'Concern', 'HD_binary']]
print(f"\nNumber of features: {len(feature_cols)}")

X_swiss = swiss_df[feature_cols].copy()
y_swiss = swiss_df['HD_binary'].values

print(f"\nX_swiss shape: {X_swiss.shape}")
print(f"y_swiss shape: {y_swiss.shape}")
print(f"y_swiss distribution: {np.bincount(y_swiss)}")

# Train with LOOCV
loo = LeaveOneOut()
pipeline_swiss = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler()),
    ('clf', GradientBoostingClassifier(n_estimators=500, max_depth=12,
                                        learning_rate=0.1, random_state=0))
])

print("\nRunning LOOCV cross-validation...")
y_prob_swiss = cross_val_predict(pipeline_swiss, X_swiss, y_swiss, cv=loo, method='predict_proba')[:, 1]
y_pred_swiss = (y_prob_swiss >= 0.5).astype(int)

print("\n=== DIAGNOSTIC RESULTS ===")
print(f"\ny_prob_swiss statistics:")
print(f"  Min: {y_prob_swiss.min():.6f}")
print(f"  Max: {y_prob_swiss.max():.6f}")
print(f"  Mean: {y_prob_swiss.mean():.6f}")
print(f"  Median: {np.median(y_prob_swiss):.6f}")

print(f"\ny_prob_swiss for negative class (y=0):")
neg_probs = y_prob_swiss[y_swiss == 0]
print(f"  Values: {neg_probs}")
print(f"  All > 0.5? {np.all(neg_probs > 0.5)}")

print(f"\ny_prob_swiss for positive class (y=1):")
pos_probs = y_prob_swiss[y_swiss == 1]
print(f"  Min: {pos_probs.min():.6f}")
print(f"  Max: {pos_probs.max():.6f}")
print(f"  Mean: {pos_probs.mean():.6f}")

print(f"\ny_pred_swiss distribution: {np.bincount(y_pred_swiss)}")

# Calculate metrics
acc_swiss = accuracy_score(y_swiss, y_pred_swiss)
cm_swiss = confusion_matrix(y_swiss, y_pred_swiss)

print(f"\nAccuracy: {acc_swiss:.4f}")
print(f"\nConfusion Matrix:")
print(cm_swiss)
print(f"  TN={cm_swiss[0,0]}, FP={cm_swiss[0,1]}")
print(f"  FN={cm_swiss[1,0]}, TP={cm_swiss[1,1]}")

# Calculate ROC curve
fpr_swiss, tpr_swiss, thresholds_swiss = roc_curve(y_swiss, y_prob_swiss)
roc_auc_swiss = auc(fpr_swiss, tpr_swiss)

print(f"\nROC Curve Analysis:")
print(f"  Number of points in ROC curve: {len(fpr_swiss)}")
print(f"  FPR range: [{fpr_swiss.min():.6f}, {fpr_swiss.max():.6f}]")
print(f"  TPR range: [{tpr_swiss.min():.6f}, {tpr_swiss.max():.6f}]")
print(f"  ROC AUC: {roc_auc_swiss:.6f}")

print(f"\nFPR values: {fpr_swiss}")
print(f"TPR values: {tpr_swiss}")
print(f"Thresholds (first 10): {thresholds_swiss[:10]}")

# Check if any drugs have specific issues
print("\n=== Per-Drug Analysis ===")
results_df = pd.DataFrame({
    'Drug': swiss_df['Drug'].values,
    'Actual': y_swiss,
    'Predicted_Prob': y_prob_swiss,
    'Predicted_Class': y_pred_swiss,
    'Correct': y_swiss == y_pred_swiss
})

print("\nDrugs with y=0 (not cardiotoxic):")
print(results_df[results_df['Actual'] == 0].to_string(index=False))

print("\nIncorrectly predicted drugs:")
print(results_df[~results_df['Correct']].to_string(index=False))
