"""
Model Definitions

Defines the ML models and pipelines for cardiac outcome prediction.
"""
from typing import Dict, Any, Optional
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from xgboost import XGBClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier

from . import config


def create_arrhythmia_model(params: Optional[Dict[str, Any]] = None) -> Pipeline:
    """
    Create XGBoost pipeline for Arrhythmia prediction.

    Parameters:
    -----------
    params : dict, optional
        Override default XGBoost parameters

    Returns:
    --------
    Pipeline
        Scikit-learn pipeline with imputer, scaler, and XGBoost classifier
    """
    xgb_params = config.XGBOOST_PARAMS.copy()
    if params:
        xgb_params.update(params)

    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('xgb', XGBClassifier(**xgb_params))
    ])

    return pipeline


def create_heart_damage_model(params: Optional[Dict[str, Any]] = None) -> Pipeline:
    """
    Create RBF SVM pipeline for Heart Damage prediction.

    Parameters:
    -----------
    params : dict, optional
        Override default SVM parameters

    Returns:
    --------
    Pipeline
        Scikit-learn pipeline with imputer, scaler, and SVM classifier
    """
    svm_params = config.SVM_PARAMS.copy()
    if params:
        svm_params.update(params)

    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('svm', SVC(**svm_params))
    ])

    return pipeline


def create_concern_model(params: Optional[Dict[str, Any]] = None) -> Pipeline:
    """
    Create Random Forest pipeline for Concern prediction (multiclass).

    Parameters:
    -----------
    params : dict, optional
        Override default Random Forest parameters

    Returns:
    --------
    Pipeline
        Scikit-learn pipeline with imputer, scaler, and Random Forest classifier
    """
    rf_params = config.RF_PARAMS.copy()
    if params:
        rf_params.update(params)

    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('rf', RandomForestClassifier(**rf_params))
    ])

    return pipeline


def get_model_step_name(model_type: str) -> str:
    """
    Get the classifier step name for a given model type.

    Parameters:
    -----------
    model_type : str
        One of 'arrhythmia', 'heart_damage', 'concern'

    Returns:
    --------
    str
        Step name in the pipeline
    """
    step_names = {
        'arrhythmia': 'xgb',
        'heart_damage': 'svm',
        'concern': 'rf'
    }
    return step_names.get(model_type, 'classifier')


def get_model_display_name(model_type: str) -> str:
    """
    Get display name for a model type.

    Parameters:
    -----------
    model_type : str
        One of 'arrhythmia', 'heart_damage', 'concern'

    Returns:
    --------
    str
        Human-readable model name
    """
    display_names = {
        'arrhythmia': 'XGBoost (Arrhythmia)',
        'heart_damage': 'RBF SVM (Heart Damage)',
        'concern': 'Random Forest (Concern)'
    }
    return display_names.get(model_type, model_type)


def create_all_models() -> Dict[str, Pipeline]:
    """
    Create all three prediction models.

    Returns:
    --------
    Dict[str, Pipeline]
        Dictionary mapping model names to pipelines
    """
    return {
        'arrhythmia': create_arrhythmia_model(),
        'heart_damage': create_heart_damage_model(),
        'concern': create_concern_model()
    }


if __name__ == "__main__":
    # Test model creation
    models = create_all_models()

    for name, model in models.items():
        print(f"\n{get_model_display_name(name)}:")
        print(f"  Steps: {[step[0] for step in model.steps]}")
        print(f"  Classifier step: {get_model_step_name(name)}")
