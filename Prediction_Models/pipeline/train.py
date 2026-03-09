"""
Model Training with Leave-One-Out Cross-Validation

Trains models using LOOCV and collects predictions for evaluation.
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Any, Optional
from sklearn.model_selection import LeaveOneOut
from sklearn.base import clone
from sklearn.metrics import roc_curve, auc
import joblib
from pathlib import Path

from . import config
from .models import (
    create_arrhythmia_model,
    create_heart_damage_model,
    create_concern_model,
    get_model_step_name,
    get_model_display_name
)


def train_binary_loocv(
    model,
    X: pd.DataFrame,
    y: np.ndarray,
    model_name: str = "model",
    use_decision_function: bool = False
) -> Dict[str, Any]:
    """
    Train a binary classifier using Leave-One-Out Cross-Validation.

    Parameters:
    -----------
    model : sklearn Pipeline
        The model pipeline to train
    X : pd.DataFrame
        Feature matrix
    y : np.ndarray
        Binary target array
    model_name : str
        Name of the model for logging
    use_decision_function : bool
        If True, use decision_function instead of predict_proba for scores

    Returns:
    --------
    Dict containing:
        - y_true: True labels
        - y_pred: Predictions
        - y_prob: Probability scores
        - fpr, tpr, thresholds: ROC curve data
        - final_model: Model trained on all data
    """
    print(f"\nTraining {model_name} with LOOCV...")

    loo = LeaveOneOut()
    n_samples = len(X)

    y_true_all = []
    y_pred_all = []
    y_prob_all = []

    for fold_idx, (train_idx, test_idx) in enumerate(loo.split(X)):
        # Split data
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Clone and fit
        model_fold = clone(model)
        model_fold.fit(X_train, y_train)

        # Predict
        y_pred = model_fold.predict(X_test)

        if use_decision_function:
            y_scores = model_fold.decision_function(X_test)
        else:
            y_scores = model_fold.predict_proba(X_test)[:, 1]

        # Store results
        y_true_all.append(y_test[0])
        y_pred_all.append(y_pred[0])
        y_prob_all.append(y_scores[0] if hasattr(y_scores, '__len__') else y_scores)

        if (fold_idx + 1) % 10 == 0 or fold_idx == n_samples - 1:
            print(f"  Completed {fold_idx + 1}/{n_samples} folds")

    # Convert to arrays
    y_true = np.array(y_true_all)
    y_pred = np.array(y_pred_all)
    y_prob = np.array(y_prob_all)

    # Compute ROC curve
    fpr, tpr, thresholds = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)

    # Train final model on all data
    print(f"  Training final model on all data...")
    final_model = clone(model)
    final_model.fit(X, y)

    print(f"  LOOCV complete. AUC: {roc_auc:.4f}")

    return {
        'y_true': y_true,
        'y_pred': y_pred,
        'y_prob': y_prob,
        'fpr': fpr,
        'tpr': tpr,
        'thresholds': thresholds,
        'auc': roc_auc,
        'final_model': final_model
    }


def train_multiclass_loocv(
    model,
    X: pd.DataFrame,
    y: np.ndarray,
    n_classes: int = 3,
    model_name: str = "model"
) -> Dict[str, Any]:
    """
    Train a multiclass classifier using Leave-One-Out Cross-Validation.

    Parameters:
    -----------
    model : sklearn Pipeline
        The model pipeline to train
    X : pd.DataFrame
        Feature matrix
    y : np.ndarray
        Multiclass target array
    n_classes : int
        Number of classes
    model_name : str
        Name of the model for logging

    Returns:
    --------
    Dict containing:
        - y_true: True labels
        - y_pred: Predictions
        - y_prob: Probability matrix (n_samples x n_classes)
        - per_class_fpr, per_class_tpr: ROC data for each class
        - final_model: Model trained on all data
    """
    print(f"\nTraining {model_name} with LOOCV ({n_classes} classes)...")

    loo = LeaveOneOut()
    n_samples = len(X)

    y_true_all = []
    y_pred_all = []
    y_prob_all = []

    for fold_idx, (train_idx, test_idx) in enumerate(loo.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model_fold = clone(model)
        model_fold.fit(X_train, y_train)

        y_pred = model_fold.predict(X_test)
        y_probs = model_fold.predict_proba(X_test)

        y_true_all.append(y_test[0])
        y_pred_all.append(y_pred[0])
        y_prob_all.append(y_probs[0])

        if (fold_idx + 1) % 10 == 0 or fold_idx == n_samples - 1:
            print(f"  Completed {fold_idx + 1}/{n_samples} folds")

    y_true = np.array(y_true_all)
    y_pred = np.array(y_pred_all)
    y_prob = np.array(y_prob_all)

    # Compute per-class ROC curves
    per_class_fpr = {}
    per_class_tpr = {}
    per_class_auc = {}

    for i in range(n_classes):
        y_true_binary = (y_true == i).astype(int)
        fpr, tpr, _ = roc_curve(y_true_binary, y_prob[:, i])
        per_class_fpr[i] = fpr
        per_class_tpr[i] = tpr
        per_class_auc[i] = auc(fpr, tpr)

    # Train final model
    print(f"  Training final model on all data...")
    final_model = clone(model)
    final_model.fit(X, y)

    mean_auc = np.mean(list(per_class_auc.values()))
    print(f"  LOOCV complete. Mean AUC: {mean_auc:.4f}")

    return {
        'y_true': y_true,
        'y_pred': y_pred,
        'y_prob': y_prob,
        'per_class_fpr': per_class_fpr,
        'per_class_tpr': per_class_tpr,
        'per_class_auc': per_class_auc,
        'final_model': final_model
    }


def train_all_models(
    features_df: pd.DataFrame,
    targets: Dict[str, np.ndarray],
    save_models: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Train all three models using LOOCV.

    Parameters:
    -----------
    features_df : pd.DataFrame
        Feature matrix
    targets : Dict[str, np.ndarray]
        Dictionary of target arrays
    save_models : bool
        Whether to save trained models to disk

    Returns:
    --------
    Dict[str, Dict]
        Results for each model
    """
    print("="*60)
    print("TRAINING ALL MODELS WITH LOOCV")
    print("="*60)

    results = {}

    # 1. Arrhythmia (XGBoost)
    if 'arrhythmia' in targets:
        model = create_arrhythmia_model()
        results['arrhythmia'] = train_binary_loocv(
            model, features_df, targets['arrhythmia'],
            model_name=get_model_display_name('arrhythmia'),
            use_decision_function=False
        )

    # 2. Heart Damage (RBF SVM)
    if 'heart_damage' in targets:
        model = create_heart_damage_model()
        results['heart_damage'] = train_binary_loocv(
            model, features_df, targets['heart_damage'],
            model_name=get_model_display_name('heart_damage'),
            use_decision_function=True  # SVM uses decision_function
        )

    # 3. Concern (Random Forest, multiclass)
    if 'concern' in targets:
        model = create_concern_model()
        results['concern'] = train_multiclass_loocv(
            model, features_df, targets['concern'],
            n_classes=3,
            model_name=get_model_display_name('concern')
        )

    # Save models
    if save_models:
        print("\nSaving trained models...")
        for name, result in results.items():
            model_path = config.MODEL_OUTPUT_DIR / f"model_{name}.joblib"
            joblib.dump(result['final_model'], model_path)
            print(f"  Saved: {model_path.name}")

    print("\n" + "="*60)
    print("TRAINING COMPLETE")
    print("="*60)

    return results


if __name__ == "__main__":
    # Test training
    from .data_loader import load_and_prepare_data

    df_raw, features_df, targets = load_and_prepare_data("dual_exponential")
    results = train_all_models(features_df, targets, save_models=True)

    print("\nResults summary:")
    for name, result in results.items():
        if 'auc' in result:
            print(f"  {name}: AUC = {result['auc']:.4f}")
        elif 'per_class_auc' in result:
            aucs = result['per_class_auc']
            print(f"  {name}: Per-class AUC = {[f'{v:.4f}' for v in aucs.values()]}")
