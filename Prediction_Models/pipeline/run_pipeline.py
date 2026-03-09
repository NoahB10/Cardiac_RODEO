"""
Prediction Models Pipeline - Main Entry Point

This script runs the complete prediction models pipeline:
1. Load and prepare data
2. Train models with LOOCV
3. Evaluate performance
4. Compute feature importance and SHAP
5. Generate visualizations
6. Create LaTeX report

Usage:
    python -m pipeline.run_pipeline                    # Full pipeline
    python -m pipeline.run_pipeline --equation dual_exponential
    python -m pipeline.run_pipeline --skip-shap        # Skip SHAP (faster)
    python -m pipeline.run_pipeline --no-plots         # Skip plotting
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import config
from pipeline.data_loader import load_and_prepare_data
from pipeline.train import train_all_models
from pipeline.evaluate import evaluate_all_models, save_metrics
from pipeline.explain import compute_all_explanations, save_explanations
from pipeline.visualize import (
    plot_all_roc_curves,
    plot_all_confusion_matrices,
    plot_all_feature_importances,
    create_summary_figure
)
from pipeline.report import generate_full_report


def run_full_pipeline(
    equation_name: str = "dual_exponential",
    skip_shap: bool = False,
    no_plots: bool = False,
    no_report: bool = False
) -> dict:
    """
    Run the complete prediction models pipeline.

    Parameters:
    -----------
    equation_name : str
        Name of the equation sheet to use
    skip_shap : bool
        Skip SHAP computation (faster)
    no_plots : bool
        Skip plot generation
    no_report : bool
        Skip LaTeX report generation

    Returns:
    --------
    dict
        Dictionary containing all pipeline outputs
    """
    start_time = datetime.now()

    print("\n" + "="*80)
    print("PREDICTION MODELS PIPELINE")
    print("="*80)
    print(f"Equation: {equation_name}")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Validate paths
    print("\nValidating paths...")
    config.validate_paths()
    print("  All paths validated successfully")

    # Step 1: Load and prepare data
    print("\n" + "-"*60)
    print("STEP 1: LOADING DATA")
    print("-"*60)
    df_raw, features_df, targets = load_and_prepare_data(equation_name)

    # Step 2: Train models
    print("\n" + "-"*60)
    print("STEP 2: TRAINING MODELS")
    print("-"*60)
    results = train_all_models(features_df, targets, save_models=True)

    # Step 3: Evaluate models
    print("\n" + "-"*60)
    print("STEP 3: EVALUATING MODELS")
    print("-"*60)
    evaluations = evaluate_all_models(results)
    save_metrics(evaluations)

    # Step 4: Compute explanations
    print("\n" + "-"*60)
    print("STEP 4: COMPUTING EXPLANATIONS")
    print("-"*60)
    if skip_shap:
        print("  Skipping SHAP computation (--skip-shap)")
        # Just compute feature importances without SHAP
        from pipeline.explain import (
            get_tree_feature_importance,
            compute_permutation_importance
        )
        explanations = {}
        if 'arrhythmia' in results:
            explanations['arrhythmia'] = {
                'feature_importances': get_tree_feature_importance(
                    results['arrhythmia']['final_model'],
                    features_df.columns.tolist(), 'xgb'
                )
            }
        if 'heart_damage' in results:
            explanations['heart_damage'] = {
                'feature_importances': compute_permutation_importance(
                    results['heart_damage']['final_model'],
                    features_df, targets['heart_damage']
                )
            }
        if 'concern' in results:
            explanations['concern'] = {
                'feature_importances': get_tree_feature_importance(
                    results['concern']['final_model'],
                    features_df.columns.tolist(), 'rf'
                )
            }
    else:
        explanations = compute_all_explanations(results, features_df, targets)

    save_explanations(explanations)

    # Step 5: Generate plots
    if not no_plots:
        print("\n" + "-"*60)
        print("STEP 5: GENERATING PLOTS")
        print("-"*60)

        # ROC curves
        plot_all_roc_curves(results)

        # Confusion matrices
        plot_all_confusion_matrices(evaluations)

        # Feature importances
        plot_all_feature_importances(explanations)

        # Summary figure
        summary_path = config.PLOTS_OUTPUT_DIR / "summary_roc.png"
        create_summary_figure(results, evaluations, summary_path)
    else:
        print("\n  Skipping plots (--no-plots)")

    # Step 6: Generate LaTeX report
    if not no_report:
        print("\n" + "-"*60)
        print("STEP 6: GENERATING LATEX REPORT")
        print("-"*60)
        report_path = generate_full_report(
            results, evaluations, explanations,
            equation_name=equation_name
        )
    else:
        print("\n  Skipping LaTeX report (--no-report)")
        report_path = None

    # Summary
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "="*80)
    print("PIPELINE COMPLETE")
    print("="*80)
    print(f"Duration: {duration}")
    print(f"\nOutput files:")
    print(f"  Models: {config.MODEL_OUTPUT_DIR}")
    print(f"  Metrics: {config.METRICS_OUTPUT_DIR}")
    print(f"  Plots: {config.PLOTS_OUTPUT_DIR}")
    print(f"  SHAP: {config.SHAP_OUTPUT_DIR}")
    if report_path:
        print(f"  LaTeX: {report_path}")

    print("\nModel Performance Summary:")
    for model_name in ['arrhythmia', 'heart_damage', 'concern']:
        if model_name in evaluations:
            metrics = evaluations[model_name]['metrics']
            if 'auc' in metrics:
                print(f"  {model_name}: AUC = {metrics['auc']:.4f}, Accuracy = {metrics['accuracy']:.4f}")
            else:
                print(f"  {model_name}: Mean AUC = {metrics.get('mean_auc', 'N/A'):.4f}, Accuracy = {metrics['accuracy']:.4f}")

    print("="*80)

    return {
        'df_raw': df_raw,
        'features_df': features_df,
        'targets': targets,
        'results': results,
        'evaluations': evaluations,
        'explanations': explanations,
        'report_path': report_path
    }


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Prediction Models Pipeline for Cardiac RODEO',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python -m pipeline.run_pipeline
    python -m pipeline.run_pipeline --equation pkpd_elimination
    python -m pipeline.run_pipeline --skip-shap --no-report
        '''
    )

    parser.add_argument(
        '--equation', '-e',
        type=str,
        default='dual_exponential',
        help='Equation sheet name (default: dual_exponential)'
    )

    parser.add_argument(
        '--skip-shap',
        action='store_true',
        help='Skip SHAP computation (faster)'
    )

    parser.add_argument(
        '--no-plots',
        action='store_true',
        help='Skip plot generation'
    )

    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip LaTeX report generation'
    )

    args = parser.parse_args()

    try:
        run_full_pipeline(
            equation_name=args.equation,
            skip_shap=args.skip_shap,
            no_plots=args.no_plots,
            no_report=args.no_report
        )
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
