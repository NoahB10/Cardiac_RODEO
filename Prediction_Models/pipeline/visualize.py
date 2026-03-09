"""
Visualization Functions

Creates plots for ROC curves, confusion matrices, and feature importance.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
from sklearn.metrics import roc_curve, auc

from . import config


def set_plot_style():
    """Set consistent plot style."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['figure.dpi'] = config.FIGURE_DPI
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['axes.labelsize'] = 10


def plot_roc_curve_binary(
    fpr: np.ndarray,
    tpr: np.ndarray,
    auc_value: float,
    title: str = "ROC Curve",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot ROC curve for binary classification.

    Parameters:
    -----------
    fpr : np.ndarray
        False positive rates
    tpr : np.ndarray
        True positive rates
    auc_value : float
        Area under curve
    title : str
        Plot title
    save_path : Path, optional
        Path to save figure

    Returns:
    --------
    plt.Figure
        Matplotlib figure
    """
    set_plot_style()

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC (AUC = {auc_value:.3f})')
    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random')
    ax.fill_between(fpr, tpr, alpha=0.2)

    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.05])
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title(title)
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=config.FIGURE_DPI, transparent=config.SAVE_TRANSPARENT)
        print(f"  Saved: {save_path.name}")

    return fig


def plot_roc_curves_multiclass(
    per_class_fpr: Dict[int, np.ndarray],
    per_class_tpr: Dict[int, np.ndarray],
    per_class_auc: Dict[int, float],
    class_labels: List[str],
    title: str = "ROC Curves",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot ROC curves for multiclass classification.

    Parameters:
    -----------
    per_class_fpr : Dict[int, np.ndarray]
        FPR for each class
    per_class_tpr : Dict[int, np.ndarray]
        TPR for each class
    per_class_auc : Dict[int, float]
        AUC for each class
    class_labels : List[str]
        Class label names
    title : str
        Plot title
    save_path : Path, optional
        Path to save figure

    Returns:
    --------
    plt.Figure
        Matplotlib figure
    """
    set_plot_style()

    fig, ax = plt.subplots(figsize=(8, 6))

    colors = plt.cm.Set1(np.linspace(0, 1, len(class_labels)))

    for i, label in enumerate(class_labels):
        fpr = per_class_fpr[i]
        tpr = per_class_tpr[i]
        auc_val = per_class_auc[i]

        ax.plot(fpr, tpr, color=colors[i], linewidth=2,
                label=f'{label} (AUC = {auc_val:.3f})')

    ax.plot([0, 1], [0, 1], 'k--', linewidth=1)

    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.05])
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title(title)
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=config.FIGURE_DPI, transparent=config.SAVE_TRANSPARENT)
        print(f"  Saved: {save_path.name}")

    return fig


def plot_confusion_matrix(
    cm: np.ndarray,
    labels: List[str],
    title: str = "Confusion Matrix",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot confusion matrix as heatmap.

    Parameters:
    -----------
    cm : np.ndarray
        Confusion matrix
    labels : List[str]
        Class labels
    title : str
        Plot title
    save_path : Path, optional
        Path to save figure

    Returns:
    --------
    plt.Figure
        Matplotlib figure
    """
    set_plot_style()

    fig, ax = plt.subplots(figsize=(6, 5))

    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=labels, yticklabels=labels, ax=ax)

    ax.set_xlabel('Predicted')
    ax.set_ylabel('True')
    ax.set_title(title)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=config.FIGURE_DPI, transparent=config.SAVE_TRANSPARENT)
        print(f"  Saved: {save_path.name}")

    return fig


def plot_feature_importance(
    importance_df: pd.DataFrame,
    top_n: int = 10,
    title: str = "Feature Importance",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot feature importance as horizontal bar chart.

    Parameters:
    -----------
    importance_df : pd.DataFrame
        DataFrame with Feature and Importance columns
    top_n : int
        Number of top features to show
    title : str
        Plot title
    save_path : Path, optional
        Path to save figure

    Returns:
    --------
    plt.Figure
        Matplotlib figure
    """
    set_plot_style()

    top_features = importance_df.head(top_n).copy()
    top_features = top_features.iloc[::-1]  # Reverse for horizontal bar

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.barh(top_features['Feature'], top_features['Importance'], color='steelblue')

    ax.set_xlabel('Importance')
    ax.set_ylabel('Feature')
    ax.set_title(title)

    # Add value labels
    for bar, val in zip(bars, top_features['Importance']):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                f'{val:.3f}', va='center', fontsize=8)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=config.FIGURE_DPI, transparent=config.SAVE_TRANSPARENT)
        print(f"  Saved: {save_path.name}")

    return fig


def plot_all_roc_curves(
    results: Dict[str, Dict[str, Any]],
    save_dir: Optional[Path] = None
) -> Dict[str, plt.Figure]:
    """
    Plot ROC curves for all models.

    Parameters:
    -----------
    results : Dict[str, Dict]
        Training results
    save_dir : Path, optional
        Directory to save figures

    Returns:
    --------
    Dict[str, plt.Figure]
        Dictionary of figures
    """
    print("\nPlotting ROC curves...")

    if save_dir is None:
        save_dir = config.PLOTS_OUTPUT_DIR

    figures = {}

    # Binary models
    for model_name in ['arrhythmia', 'heart_damage']:
        if model_name not in results:
            continue

        res = results[model_name]
        display_name = model_name.replace('_', ' ').title()

        save_path = save_dir / f"roc_{model_name}.png"
        fig = plot_roc_curve_binary(
            res['fpr'], res['tpr'], res['auc'],
            title=f"ROC Curve - {display_name}",
            save_path=save_path
        )
        figures[model_name] = fig

    # Multiclass (Concern)
    if 'concern' in results:
        res = results['concern']
        save_path = save_dir / "roc_concern.png"
        fig = plot_roc_curves_multiclass(
            res['per_class_fpr'],
            res['per_class_tpr'],
            res['per_class_auc'],
            config.CONCERN_LABELS,
            title="ROC Curves - Concern (Multiclass)",
            save_path=save_path
        )
        figures['concern'] = fig

    return figures


def plot_all_confusion_matrices(
    evaluations: Dict[str, Dict[str, Any]],
    save_dir: Optional[Path] = None
) -> Dict[str, plt.Figure]:
    """
    Plot confusion matrices for all models.

    Parameters:
    -----------
    evaluations : Dict[str, Dict]
        Evaluation results
    save_dir : Path, optional
        Directory to save figures

    Returns:
    --------
    Dict[str, plt.Figure]
        Dictionary of figures
    """
    print("\nPlotting confusion matrices...")

    if save_dir is None:
        save_dir = config.PLOTS_OUTPUT_DIR

    figures = {}

    for model_name, eval_data in evaluations.items():
        if 'confusion_matrix' not in eval_data:
            continue

        display_name = model_name.replace('_', ' ').title()

        if model_name == 'concern':
            labels = config.CONCERN_LABELS
        else:
            labels = ['Negative', 'Positive']

        save_path = save_dir / f"cm_{model_name}.png"
        fig = plot_confusion_matrix(
            eval_data['confusion_matrix'],
            labels,
            title=f"Confusion Matrix - {display_name}",
            save_path=save_path
        )
        figures[model_name] = fig

    return figures


def plot_all_feature_importances(
    explanations: Dict[str, Dict[str, Any]],
    save_dir: Optional[Path] = None
) -> Dict[str, plt.Figure]:
    """
    Plot feature importances for all models.

    Parameters:
    -----------
    explanations : Dict[str, Dict]
        Explanation results
    save_dir : Path, optional
        Directory to save figures

    Returns:
    --------
    Dict[str, plt.Figure]
        Dictionary of figures
    """
    print("\nPlotting feature importances...")

    if save_dir is None:
        save_dir = config.PLOTS_OUTPUT_DIR

    figures = {}

    for model_name, expl_data in explanations.items():
        if 'feature_importances' not in expl_data:
            continue

        display_name = model_name.replace('_', ' ').title()

        save_path = save_dir / f"importance_{model_name}.png"
        fig = plot_feature_importance(
            expl_data['feature_importances'],
            top_n=config.TOP_N_FEATURES,
            title=f"Top Features - {display_name}",
            save_path=save_path
        )
        figures[model_name] = fig

    return figures


def create_summary_figure(
    results: Dict[str, Dict[str, Any]],
    evaluations: Dict[str, Dict[str, Any]],
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Create a summary figure with all ROC curves and metrics.

    Parameters:
    -----------
    results : Dict[str, Dict]
        Training results
    evaluations : Dict[str, Dict]
        Evaluation results
    save_path : Path, optional
        Path to save figure

    Returns:
    --------
    plt.Figure
        Matplotlib figure
    """
    set_plot_style()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Arrhythmia
    if 'arrhythmia' in results:
        ax = axes[0]
        res = results['arrhythmia']
        ax.plot(res['fpr'], res['tpr'], 'b-', linewidth=2)
        ax.plot([0, 1], [0, 1], 'k--', linewidth=1)
        ax.fill_between(res['fpr'], res['tpr'], alpha=0.2)
        ax.set_title(f"Arrhythmia (AUC = {res['auc']:.3f})")
        ax.set_xlabel('FPR')
        ax.set_ylabel('TPR')
        ax.grid(True, alpha=0.3)

    # Heart Damage
    if 'heart_damage' in results:
        ax = axes[1]
        res = results['heart_damage']
        ax.plot(res['fpr'], res['tpr'], 'r-', linewidth=2)
        ax.plot([0, 1], [0, 1], 'k--', linewidth=1)
        ax.fill_between(res['fpr'], res['tpr'], alpha=0.2, color='red')
        ax.set_title(f"Heart Damage (AUC = {res['auc']:.3f})")
        ax.set_xlabel('FPR')
        ax.set_ylabel('TPR')
        ax.grid(True, alpha=0.3)

    # Concern
    if 'concern' in results:
        ax = axes[2]
        res = results['concern']
        colors = ['green', 'orange', 'purple']
        for i, (label, color) in enumerate(zip(config.CONCERN_LABELS, colors)):
            ax.plot(res['per_class_fpr'][i], res['per_class_tpr'][i],
                    color=color, linewidth=2, label=f"{label} ({res['per_class_auc'][i]:.3f})")
        ax.plot([0, 1], [0, 1], 'k--', linewidth=1)
        ax.set_title("Concern (Multiclass)")
        ax.set_xlabel('FPR')
        ax.set_ylabel('TPR')
        ax.legend(loc='lower right', fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=config.FIGURE_DPI, transparent=config.SAVE_TRANSPARENT)
        print(f"  Saved: {save_path.name}")

    return fig


if __name__ == "__main__":
    # Test plotting functions
    print("Visualization module loaded successfully")
    set_plot_style()
    print("Plot style set")
