"""
Model Explainability

Computes SHAP values and feature importances for model interpretation.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from sklearn.inspection import permutation_importance
import warnings

from . import config
from .models import get_model_step_name

# Import shap with error handling
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    warnings.warn("SHAP not installed. Install with: pip install shap")


def compute_tree_shap(
    model,
    X: pd.DataFrame,
    model_step: str = 'xgb'
) -> np.ndarray:
    """
    Compute SHAP values for tree-based models.

    Parameters:
    -----------
    model : sklearn Pipeline
        Trained model pipeline
    X : pd.DataFrame
        Feature matrix
    model_step : str
        Name of the classifier step in the pipeline

    Returns:
    --------
    np.ndarray
        SHAP values
    """
    if not SHAP_AVAILABLE:
        raise ImportError("SHAP is required for this function")

    # Get the tree model from pipeline
    tree_model = model.named_steps[model_step]

    # Scale features if scaler exists
    if 'scaler' in model.named_steps:
        X_scaled = model.named_steps['scaler'].transform(X)
        if 'imputer' in model.named_steps:
            X_scaled = model.named_steps['imputer'].transform(X_scaled)
    else:
        X_scaled = X.values

    # Create explainer and compute SHAP values
    explainer = shap.TreeExplainer(tree_model)
    shap_values = explainer.shap_values(X_scaled)

    return shap_values


def compute_kernel_shap(
    model,
    X: pd.DataFrame,
    background_samples: int = 10
) -> np.ndarray:
    """
    Compute SHAP values using KernelSHAP for non-tree models (e.g., SVM).

    Parameters:
    -----------
    model : sklearn Pipeline
        Trained model pipeline
    X : pd.DataFrame
        Feature matrix
    background_samples : int
        Number of background samples for KernelSHAP

    Returns:
    --------
    np.ndarray
        SHAP values
    """
    if not SHAP_AVAILABLE:
        raise ImportError("SHAP is required for this function")

    feature_names = X.columns.tolist()

    # Create prediction function
    def predict_fn(X_input):
        X_df = pd.DataFrame(X_input, columns=feature_names)
        return model.predict_proba(X_df)[:, 1]

    # Create background data using kmeans
    try:
        background = shap.kmeans(X, k=min(background_samples, len(X)))
    except Exception:
        background = X.sample(min(background_samples, len(X)), random_state=42).values

    # Create explainer
    explainer = shap.KernelExplainer(predict_fn, background)

    # Compute SHAP values
    print(f"  Computing KernelSHAP (this may take a while)...")
    shap_values = explainer.shap_values(X.values, nsamples='auto')

    return shap_values


def compute_permutation_importance(
    model,
    X: pd.DataFrame,
    y: np.ndarray,
    n_repeats: int = 10
) -> pd.DataFrame:
    """
    Compute permutation importance for any model.

    Parameters:
    -----------
    model : sklearn Pipeline
        Trained model pipeline
    X : pd.DataFrame
        Feature matrix
    y : np.ndarray
        Target array
    n_repeats : int
        Number of permutation repeats

    Returns:
    --------
    pd.DataFrame
        Feature importance DataFrame
    """
    print(f"  Computing permutation importance...")

    perm_result = permutation_importance(
        model, X, y,
        n_repeats=n_repeats,
        random_state=config.RANDOM_STATE,
        n_jobs=1  # n_jobs=-1 can cause issues on Windows
    )

    importance_df = pd.DataFrame({
        'Feature': X.columns,
        'Importance': perm_result.importances_mean,
        'Std': perm_result.importances_std
    }).sort_values('Importance', ascending=False)

    return importance_df


def get_tree_feature_importance(
    model,
    feature_names: List[str],
    model_step: str = 'xgb'
) -> pd.DataFrame:
    """
    Get feature importance from tree-based models.

    Parameters:
    -----------
    model : sklearn Pipeline
        Trained model pipeline
    feature_names : List[str]
        Feature names
    model_step : str
        Name of the classifier step

    Returns:
    --------
    pd.DataFrame
        Feature importance DataFrame
    """
    tree_model = model.named_steps[model_step]
    importances = tree_model.feature_importances_

    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': importances
    }).sort_values('Importance', ascending=False)

    return importance_df


def compute_all_explanations(
    results: Dict[str, Dict[str, Any]],
    features_df: pd.DataFrame,
    targets: Dict[str, np.ndarray]
) -> Dict[str, Dict[str, Any]]:
    """
    Compute SHAP and feature importances for all models.

    Parameters:
    -----------
    results : Dict[str, Dict]
        Training results containing final models
    features_df : pd.DataFrame
        Feature matrix
    targets : Dict[str, np.ndarray]
        Target arrays

    Returns:
    --------
    Dict[str, Dict]
        Explanations for each model
    """
    print("="*60)
    print("COMPUTING MODEL EXPLANATIONS")
    print("="*60)

    explanations = {}

    # 1. Arrhythmia (XGBoost) - TreeSHAP + Feature Importance
    if 'arrhythmia' in results:
        print("\n1. Computing SHAP for Arrhythmia (XGBoost)...")
        model = results['arrhythmia']['final_model']

        explanations['arrhythmia'] = {
            'feature_importances': get_tree_feature_importance(
                model, features_df.columns.tolist(), 'xgb'
            )
        }

        if SHAP_AVAILABLE:
            try:
                shap_values = compute_tree_shap(model, features_df, 'xgb')
                explanations['arrhythmia']['shap_values'] = shap_values
                print("  TreeSHAP computed successfully")
            except Exception as e:
                print(f"  Warning: Could not compute TreeSHAP: {e}")

    # 2. Heart Damage (SVM) - Permutation Importance + KernelSHAP
    if 'heart_damage' in results:
        print("\n2. Computing importance for Heart Damage (RBF SVM)...")
        model = results['heart_damage']['final_model']

        explanations['heart_damage'] = {
            'feature_importances': compute_permutation_importance(
                model, features_df, targets['heart_damage']
            )
        }

        if SHAP_AVAILABLE:
            try:
                shap_values = compute_kernel_shap(
                    model, features_df,
                    background_samples=config.SHAP_BACKGROUND_SAMPLES
                )
                explanations['heart_damage']['shap_values'] = shap_values
                print("  KernelSHAP computed successfully")
            except Exception as e:
                print(f"  Warning: Could not compute KernelSHAP: {e}")

    # 3. Concern (Random Forest) - TreeSHAP + Feature Importance
    if 'concern' in results:
        print("\n3. Computing SHAP for Concern (Random Forest)...")
        model = results['concern']['final_model']

        explanations['concern'] = {
            'feature_importances': get_tree_feature_importance(
                model, features_df.columns.tolist(), 'rf'
            )
        }

        if SHAP_AVAILABLE:
            try:
                shap_values = compute_tree_shap(model, features_df, 'rf')
                # For multiclass, shap_values is a list
                if isinstance(shap_values, list):
                    explanations['concern']['shap_values'] = shap_values
                else:
                    # Handle different SHAP output formats
                    n_classes = shap_values.shape[2] if len(shap_values.shape) == 3 else 3
                    explanations['concern']['shap_values'] = [
                        shap_values[:, :, i] for i in range(n_classes)
                    ]
                print("  TreeSHAP computed successfully")
            except Exception as e:
                print(f"  Warning: Could not compute TreeSHAP: {e}")

    print("\n" + "="*60)
    print("EXPLANATIONS COMPLETE")
    print("="*60)

    return explanations


def save_explanations(
    explanations: Dict[str, Dict[str, Any]],
    output_dir: Optional[str] = None
) -> None:
    """
    Save feature importances to CSV files.

    Parameters:
    -----------
    explanations : Dict[str, Dict]
        Explanation results
    output_dir : str, optional
        Output directory path
    """
    if output_dir is None:
        output_dir = config.SHAP_OUTPUT_DIR

    print("\nSaving feature importances...")

    for model_name, expl_data in explanations.items():
        if 'feature_importances' in expl_data:
            imp_path = output_dir / f"{model_name}_feature_importances.csv"
            expl_data['feature_importances'].to_csv(imp_path, index=False)
            print(f"  Saved: {imp_path.name}")


if __name__ == "__main__":
    print("SHAP available:", SHAP_AVAILABLE)

    # Test with dummy data
    if SHAP_AVAILABLE:
        print("\nSHAP module loaded successfully")
