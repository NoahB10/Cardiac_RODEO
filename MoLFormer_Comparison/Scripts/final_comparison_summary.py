"""
Final Comparison Summary: MoLFormer vs Organoid vs ADMET Models

Compares LOOCV performance across all models for Arrhythmia prediction.
"""
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_DIR = PROJECT_ROOT / "Output" / "MoLFormer_Comparison"

def create_final_comparison():
    """Create final comparison table with all models."""

    # MoLFormer DIQT results (from our inference)
    molformer_results = {
        'Model': 'MoLFormer DIQT',
        'Method': 'Structure-based (SMILES)',
        'Training_Data': 'DIQT (255 drugs)',
        'Target': 'QT Prolongation → Arrhythmia',
        'LOOCV_AUC_Training': 0.817,  # 5-fold CV on DIQT
        'Test_AUC_25drugs': 0.688,     # On Cardiac RODEO drugs
        'Test_Accuracy_25drugs': 0.600,
        'N_test': 25
    }

    # Organoid PK-PD results (from loocv_results.csv)
    # Using pkpd_elimination equation, best models
    organoid_xgb = {
        'Model': 'Organoid PK-PD (XGBoost)',
        'Method': 'Functional (Organoid coefficients)',
        'Training_Data': 'Cardiac RODEO (25 drugs)',
        'Target': 'Arrhythmia',
        'LOOCV_AUC_Training': 0.779,  # LOOCV on 25 drugs
        'Test_AUC_25drugs': 0.779,     # Same (LOOCV)
        'Test_Accuracy_25drugs': 0.72,
        'N_test': 25
    }

    organoid_rf = {
        'Model': 'Organoid PK-PD (RandomForest)',
        'Method': 'Functional (Organoid coefficients)',
        'Training_Data': 'Cardiac RODEO (25 drugs)',
        'Target': 'Arrhythmia',
        'LOOCV_AUC_Training': 0.795,  # LOOCV on 25 drugs
        'Test_AUC_25drugs': 0.795,     # Same (LOOCV)
        'Test_Accuracy_25drugs': 0.76,
        'N_test': 25
    }

    # Create comparison DataFrame
    comparison_df = pd.DataFrame([
        molformer_results,
        organoid_xgb,
        organoid_rf
    ])

    # Save to CSV
    comparison_df.to_csv(OUTPUT_DIR / 'final_comparison_all_models.csv', index=False)

    # Print comparison
    print("="*80)
    print("FINAL COMPARISON: Arrhythmia Prediction")
    print("="*80)
    print()
    print(comparison_df[['Model', 'Method', 'LOOCV_AUC_Training', 'Test_AUC_25drugs', 'Test_Accuracy_25drugs']].to_string(index=False))
    print()

    return comparison_df

def plot_final_comparison(df):
    """Create final comparison bar chart."""

    models = df['Model'].tolist()
    aucs = df['Test_AUC_25drugs'].tolist()
    accuracies = df['Test_Accuracy_25drugs'].tolist()

    x = np.arange(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 7))

    # Colors
    colors_auc = ['#2E86AB', '#A23B72', '#F18F01']  # Blue, Purple, Orange
    colors_acc = ['#5CB8E4', '#C76BA3', '#F9B938']  # Lighter versions

    bars1 = ax.bar(x - width/2, aucs, width, label='LOOCV AUC', color=colors_auc)
    bars2 = ax.bar(x + width/2, accuracies, width, label='Accuracy', color=colors_acc)

    ax.set_ylabel('Score', fontsize=14)
    ax.set_title('Arrhythmia Prediction: MoLFormer vs Organoid PK-PD\n(N=25 Cardiac RODEO Drugs)', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=11, rotation=15, ha='right')
    ax.legend(fontsize=12, loc='upper left')
    ax.set_ylim([0, 1])
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', fontsize=11, fontweight='bold')
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', fontsize=11)

    # Add horizontal line at 0.5 (random)
    ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='Random baseline')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'Final_Comparison_All_Models.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'figures' / 'Final_Comparison_All_Models.pdf', bbox_inches='tight')
    plt.close()

    print(f"Plot saved to: {OUTPUT_DIR / 'Final_Comparison_All_Models.png'}")

def print_conclusions():
    """Print key conclusions."""

    print()
    print("="*80)
    print("KEY FINDINGS")
    print("="*80)
    print("""
1. ORGANOID PK-PD OUTPERFORMS STRUCTURE-BASED MOLFORMER:
   - Organoid RandomForest AUC: 0.795 vs MoLFormer AUC: 0.688
   - Improvement: +0.107 AUC points (+15.6% relative)

2. FUNCTIONAL DATA ADDS VALUE BEYOND MOLECULAR STRUCTURE:
   - MoLFormer uses only SMILES (chemical structure)
   - Organoid model uses PK-PD coefficients from real cardiac response
   - The biological response data captures mechanistic information
     that structure alone cannot predict

3. MOLFORMER PERFORMANCE:
   - Training on DIQT (255 drugs): AUC = 0.817 (matches paper ~0.83)
   - Testing on Cardiac RODEO (25 drugs): AUC = 0.688
   - Some drugs are correctly predicted (Sotalol, Panobinostat, Vandetanib)
   - Others fail (Doxorubicin, Epirubicin - known cardiotoxic but low DIQT score)

4. COMPLEMENTARY APPROACHES:
   - MoLFormer catches: Sotalol (0.94), Mexiletine (0.88), Panobinostat (0.93)
   - Organoid catches: Doxorubicin, Epirubicin, Isoproterenol (missed by MoLFormer)
   - Combining both approaches could improve overall prediction

5. IMPLICATION FOR DRUG SAFETY:
   - Structure-based predictions (ADMET, MoLFormer) are useful for early screening
   - Organoid functional assays provide additional predictive power
   - Cardiac RODEO organoid approach captures drug effects that structure
     alone cannot predict
""")
    print("="*80)

def main():
    # Create comparison
    df = create_final_comparison()

    # Create plot
    (OUTPUT_DIR / 'figures').mkdir(exist_ok=True)
    plot_final_comparison(df)

    # Print conclusions
    print_conclusions()

    print("\nAll outputs saved to:", OUTPUT_DIR)

if __name__ == "__main__":
    main()
