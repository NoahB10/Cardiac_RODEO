"""
Model Evaluation

Computes metrics, confusion matrices, and classification reports.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, confusion_matrix, classification_report
)

from . import config


def compute_binary_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Compute metrics for binary classification.

    Parameters:
    -----------
    y_true : np.ndarray
        True labels
    y_pred : np.ndarray
        Predicted labels
    y_prob : np.ndarray, optional
        Probability scores for AUC computation

    Returns:
    --------
    Dict[str, float]
        Dictionary of metric values
    """
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'f1': f1_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'sensitivity': recall_score(y_true, y_pred, zero_division=0),  # Same as recall
        'specificity': recall_score(y_true, y_pred, pos_label=0, zero_division=0)
    }

    if y_prob is not None:
        try:
            metrics['auc'] = roc_auc_score(y_true, y_prob)
        except ValueError:
            metrics['auc'] = np.nan

    return metrics


def compute_multiclass_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    class_labels: List[str] = None
) -> Dict[str, Any]:
    """
    Compute metrics for multiclass classification.

    Parameters:
    -----------
    y_true : np.ndarray
        True labels
    y_pred : np.ndarray
        Predicted labels
    y_prob : np.ndarray, optional
        Probability matrix (n_samples x n_classes)
    class_labels : List[str], optional
        Class label names

    Returns:
    --------
    Dict[str, Any]
        Dictionary of metric values
    """
    if class_labels is None:
        class_labels = config.CONCERN_LABELS

    n_classes = len(class_labels)

    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'f1_macro': f1_score(y_true, y_pred, average='macro'),
        'f1_weighted': f1_score(y_true, y_pred, average='weighted'),
        'precision_macro': precision_score(y_true, y_pred, average='macro', zero_division=0),
        'recall_macro': recall_score(y_true, y_pred, average='macro', zero_division=0)
    }

    # Per-class metrics
    per_class_accuracy = {}
    per_class_f1 = {}

    for i, label in enumerate(class_labels):
        y_true_binary = (y_true == i).astype(int)
        y_pred_binary = (y_pred == i).astype(int)

        per_class_accuracy[label] = accuracy_score(y_true_binary, y_pred_binary)
        per_class_f1[label] = f1_score(y_true_binary, y_pred_binary, zero_division=0)

    metrics['per_class_accuracy'] = per_class_accuracy
    metrics['per_class_f1'] = per_class_f1

    # Per-class AUC
    if y_prob is not None:
        per_class_auc = {}
        for i, label in enumerate(class_labels):
            y_true_binary = (y_true == i).astype(int)
            try:
                per_class_auc[label] = roc_auc_score(y_true_binary, y_prob[:, i])
            except ValueError:
                per_class_auc[label] = np.nan
        metrics['per_class_auc'] = per_class_auc
        metrics['mean_auc'] = np.nanmean(list(per_class_auc.values()))

    return metrics


def compute_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: Optional[List] = None
) -> np.ndarray:
    """
    Compute confusion matrix.

    Parameters:
    -----------
    y_true : np.ndarray
        True labels
    y_pred : np.ndarray
        Predicted labels
    labels : List, optional
        Label ordering

    Returns:
    --------
    np.ndarray
        Confusion matrix
    """
    return confusion_matrix(y_true, y_pred, labels=labels)


def get_classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target_names: Optional[List[str]] = None
) -> str:
    """
    Generate classification report string.

    Parameters:
    -----------
    y_true : np.ndarray
        True labels
    y_pred : np.ndarray
        Predicted labels
    target_names : List[str], optional
        Class names

    Returns:
    --------
    str
        Classification report
    """
    return classification_report(y_true, y_pred, target_names=target_names, zero_division=0)


def evaluate_all_models(
    results: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Evaluate all trained models.

    Parameters:
    -----------
    results : Dict[str, Dict]
        Training results from train_all_models

    Returns:
    --------
    Dict[str, Dict]
        Evaluation metrics for each model
    """
    print("="*60)
    print("EVALUATING ALL MODELS")
    print("="*60)

    evaluations = {}

    # Binary models
    for model_name in ['arrhythmia', 'heart_damage']:
        if model_name not in results:
            continue

        res = results[model_name]
        metrics = compute_binary_metrics(
            res['y_true'], res['y_pred'], res['y_prob']
        )
        cm = compute_confusion_matrix(res['y_true'], res['y_pred'])

        evaluations[model_name] = {
            'metrics': metrics,
            'confusion_matrix': cm,
            'classification_report': get_classification_report(
                res['y_true'], res['y_pred'],
                target_names=['Negative', 'Positive']
            )
        }

        print(f"\n{model_name.upper()}:")
        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  F1-Score: {metrics['f1']:.4f}")
        print(f"  AUC-ROC:  {metrics.get('auc', 'N/A'):.4f}" if metrics.get('auc') else "  AUC: N/A")
        print(f"  Sensitivity: {metrics['sensitivity']:.4f}")
        print(f"  Specificity: {metrics['specificity']:.4f}")

    # Multiclass model (Concern)
    if 'concern' in results:
        res = results['concern']
        metrics = compute_multiclass_metrics(
            res['y_true'], res['y_pred'], res['y_prob'],
            class_labels=config.CONCERN_LABELS
        )
        cm = compute_confusion_matrix(
            res['y_true'], res['y_pred'],
            labels=[0, 1, 2]
        )

        evaluations['concern'] = {
            'metrics': metrics,
            'confusion_matrix': cm,
            'classification_report': get_classification_report(
                res['y_true'], res['y_pred'],
                target_names=config.CONCERN_LABELS
            )
        }

        print(f"\nCONCERN (Multiclass):")
        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  F1-Macro: {metrics['f1_macro']:.4f}")
        print(f"  Mean AUC: {metrics.get('mean_auc', 'N/A'):.4f}" if metrics.get('mean_auc') else "  Mean AUC: N/A")
        print(f"  Per-class AUC: {metrics.get('per_class_auc', {})}")

    print("\n" + "="*60)

    return evaluations


def save_metrics(
    evaluations: Dict[str, Dict[str, Any]],
    output_dir: Optional[str] = None
) -> None:
    """
    Save evaluation metrics to CSV files.

    Parameters:
    -----------
    evaluations : Dict[str, Dict]
        Evaluation results
    output_dir : str, optional
        Output directory path
    """
    if output_dir is None:
        output_dir = config.METRICS_OUTPUT_DIR

    print("\nSaving metrics...")

    for model_name, eval_data in evaluations.items():
        # Save metrics
        metrics_df = pd.DataFrame([eval_data['metrics']])
        metrics_path = output_dir / f"{model_name}_metrics.csv"
        metrics_df.to_csv(metrics_path, index=False)
        print(f"  Saved: {metrics_path.name}")

        # Save confusion matrix
        cm_df = pd.DataFrame(eval_data['confusion_matrix'])
        cm_path = output_dir / f"{model_name}_confusion_matrix.csv"
        cm_df.to_csv(cm_path, index=False)

        # Save classification report
        report_path = output_dir / f"{model_name}_classification_report.txt"
        with open(report_path, 'w') as f:
            f.write(eval_data['classification_report'])


if __name__ == "__main__":
    # Test evaluation with dummy data
    import numpy as np

    # Dummy results
    dummy_results = {
        'arrhythmia': {
            'y_true': np.array([0, 1, 1, 0, 1, 0, 1, 1, 0, 0]),
            'y_pred': np.array([0, 1, 1, 0, 0, 0, 1, 1, 1, 0]),
            'y_prob': np.array([0.2, 0.8, 0.9, 0.3, 0.4, 0.1, 0.7, 0.85, 0.6, 0.25])
        }
    }

    evaluations = evaluate_all_models(dummy_results)
    print("\nEvaluation complete!")
