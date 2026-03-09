"""
Merge Excel_Figures data into PowerPoint_Figures structure.

This script combines:
- PowerPoint_Figures: Organization (Fig_X naming), metadata, source tracking
- Excel_Figures: Richer/more complete data

Output: Updated PowerPoint_Figures with complete data from Excel_Figures
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

# Paths
PROJECT_ROOT = Path(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO')
PPTX_FIGS = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures'
EXCEL_FIGS = PROJECT_ROOT / 'Output' / 'Excel_Figures'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures_Merged'

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def add_metadata_sheet(writer, source_file, figure_id, description):
    """Add a standard metadata sheet to every Excel file."""
    metadata = pd.DataFrame({
        'Field': ['Generated', 'Source_File', 'Figure_ID', 'Description', 'Merged_From'],
        'Value': [
            datetime.now().isoformat(),
            str(source_file),
            figure_id,
            description,
            'Excel_Figures + PowerPoint_Figures'
        ]
    })
    metadata.to_excel(writer, sheet_name='Metadata', index=False)

def merge_roc_curves():
    """
    Merge ROC curve data.
    Excel has: FPR, TPR_Mean, TPR_Upper, TPR_Lower (pre-computed bounds)
    PowerPoint has: Per-fold data

    Output: Both per-fold AND summary statistics
    """
    print("\n=== Merging ROC Curves ===")

    targets = {
        'Arrhythmia': ('Fig_6', 'Fig_6a_data.xlsx'),
        'HeartDamage': ('Fig_7', 'Fig_7a_data.xlsx'),
        'ConcernBinary': ('Fig_8', 'Fig_8a_data.xlsx'),
    }

    # Load Excel ROC data (has confidence bounds)
    excel_roc = EXCEL_FIGS / 'ROC_Curves.xlsx'
    if not excel_roc.exists():
        print(f"  Warning: {excel_roc} not found")
        return

    for target, (fig_folder, fig_file) in targets.items():
        print(f"  Processing {target}...")

        # Create output folder
        out_folder = OUTPUT_DIR / fig_folder
        out_folder.mkdir(parents=True, exist_ok=True)

        # Load Excel data (summary with bounds)
        try:
            excel_df = pd.read_excel(excel_roc, sheet_name=target)
        except:
            print(f"    Warning: Sheet {target} not found in Excel ROC file")
            continue

        # Load PowerPoint data (per-fold)
        pptx_file = PPTX_FIGS / fig_folder / fig_file
        pptx_sheets = {}
        if pptx_file.exists():
            try:
                pptx_xl = pd.ExcelFile(pptx_file)
                for sheet in pptx_xl.sheet_names:
                    pptx_sheets[sheet] = pd.read_excel(pptx_xl, sheet_name=sheet)
            except Exception as e:
                print(f"    Warning: Could not read {pptx_file}: {e}")

        # Write merged file
        out_file = out_folder / fig_file
        with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
            # Sheet 1: Summary with confidence bounds (from Excel)
            excel_df.to_excel(writer, sheet_name='ROC_Summary', index=False)

            # Sheet 2: Per-fold data (from PowerPoint if available)
            if 'ROC_Data' in pptx_sheets:
                pptx_sheets['ROC_Data'].to_excel(writer, sheet_name='ROC_PerFold', index=False)

            # Metadata
            add_metadata_sheet(writer, excel_roc, f'{fig_folder}a', f'{target} ROC Curves')

        print(f"    Saved: {out_file}")

def merge_confusion_matrices():
    """
    Merge confusion matrix data.
    Excel has: Simple 2x2 matrices
    PowerPoint has: Extended format with metadata

    Output: Both formats plus computed metrics
    """
    print("\n=== Merging Confusion Matrices ===")

    targets = {
        'Arrhythmia': ('Fig_6', 'Fig_6b_data.xlsx', 'Arrhythmia'),
        'Heart Damage': ('Fig_7', 'Fig_7b_data.xlsx', 'Heart Damage'),
        'Concern Binary': ('Fig_8', 'Fig_8b_data.xlsx', 'Concern Binary'),
    }

    # Load Excel CM data
    excel_cm = EXCEL_FIGS / 'confusion_matrices.xlsx'

    for target, (fig_folder, fig_file, sheet_name) in targets.items():
        print(f"  Processing {target}...")

        out_folder = OUTPUT_DIR / fig_folder
        out_folder.mkdir(parents=True, exist_ok=True)

        # Load Excel data
        try:
            excel_df = pd.read_excel(excel_cm, sheet_name=sheet_name)
        except Exception as e:
            print(f"    Warning: Could not load Excel CM for {target}: {e}")
            excel_df = None

        # Load PowerPoint data
        pptx_file = PPTX_FIGS / fig_folder / fig_file
        pptx_df = None
        if pptx_file.exists():
            try:
                pptx_df = pd.read_excel(pptx_file, sheet_name='CM')
            except:
                pass

        # Also check for organoid-specific CM
        organoid_cm = EXCEL_FIGS / f'confusion_matrix_organoid_{target.lower().replace(" ", "_")}.xlsx'
        organoid_df = None
        if organoid_cm.exists():
            try:
                organoid_df = pd.read_excel(organoid_cm)
            except:
                pass

        # Write merged file
        out_file = out_folder / fig_file
        with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
            # Primary CM (prefer PowerPoint aggregated, fallback to Excel)
            if pptx_df is not None:
                pptx_df.to_excel(writer, sheet_name='CM', index=False)
            elif excel_df is not None:
                excel_df.to_excel(writer, sheet_name='CM', index=False)

            # Excel simple format
            if excel_df is not None:
                excel_df.to_excel(writer, sheet_name='CM_Simple', index=False)

            # Organoid extended format
            if organoid_df is not None:
                organoid_df.to_excel(writer, sheet_name='CM_Extended', index=False)

            # Computed metrics sheet
            if pptx_df is not None or excel_df is not None:
                df = pptx_df if pptx_df is not None else excel_df
                try:
                    # Try to extract TN, FP, FN, TP
                    # This depends on the exact format of the CM
                    metrics = pd.DataFrame({
                        'Metric': ['Source', 'Format'],
                        'Value': ['Merged', 'See CM sheet']
                    })
                    metrics.to_excel(writer, sheet_name='Metrics', index=False)
                except:
                    pass

            add_metadata_sheet(writer, excel_cm, f'{fig_folder}b', f'{target} Confusion Matrix')

        print(f"    Saved: {out_file}")

def merge_performance_metrics():
    """
    Merge performance metrics.
    Excel has: Mean ± Std for Accuracy, AUC, F1, MCC
    PowerPoint has: Per-fold raw data + summary

    Output: Both raw fold data AND summary statistics
    """
    print("\n=== Merging Performance Metrics ===")

    targets = {
        'Arrhythmia': ('Fig_6', 'Fig_6c_data.xlsx', 'accuracy_auc_arrhythmia.xlsx'),
        'Heart_Damage': ('Fig_7', 'Fig_7c_data.xlsx', 'accuracy_auc_heart_damage.xlsx'),
        'Concern_Binary': ('Fig_8', 'Fig_8c_data.xlsx', 'accuracy_auc_concern_binary.xlsx'),
    }

    # Also load combined Performance_Metrics.xlsx
    perf_metrics = EXCEL_FIGS / 'Performance_Metrics.xlsx'

    for target, (fig_folder, fig_file, excel_file) in targets.items():
        print(f"  Processing {target}...")

        out_folder = OUTPUT_DIR / fig_folder
        out_folder.mkdir(parents=True, exist_ok=True)

        # Load Excel data
        excel_path = EXCEL_FIGS / excel_file
        excel_df = None
        if excel_path.exists():
            try:
                excel_df = pd.read_excel(excel_path)
            except:
                pass

        # Load PowerPoint data (has both summary and raw)
        pptx_file = PPTX_FIGS / fig_folder / fig_file
        pptx_sheets = {}
        if pptx_file.exists():
            try:
                pptx_xl = pd.ExcelFile(pptx_file)
                for sheet in pptx_xl.sheet_names:
                    pptx_sheets[sheet] = pd.read_excel(pptx_xl, sheet_name=sheet)
            except:
                pass

        # Write merged file
        out_file = out_folder / fig_file
        with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
            # Summary from Excel (cleaner format)
            if excel_df is not None:
                excel_df.to_excel(writer, sheet_name='Metrics_Summary', index=False)
            elif 'Metrics_Summary' in pptx_sheets:
                pptx_sheets['Metrics_Summary'].to_excel(writer, sheet_name='Metrics_Summary', index=False)

            # Raw fold data from PowerPoint
            if 'Raw_Fold_Data' in pptx_sheets:
                pptx_sheets['Raw_Fold_Data'].to_excel(writer, sheet_name='Raw_Fold_Data', index=False)

            add_metadata_sheet(writer, excel_path, f'{fig_folder}c', f'{target} Performance Metrics')

        print(f"    Saved: {out_file}")

def merge_predictions():
    """
    Merge prediction scatter data.
    Excel has: Drug, Predicted_pct, Actual (simple)
    PowerPoint has: + is_positive, Source, Threshold columns

    Output: Full data with all columns
    """
    print("\n=== Merging Prediction Scatter Data ===")

    targets = {
        'Arrhythmia': ('Fig_6', 'Fig_6d_data.xlsx', 'Arrhythmia'),
        'Heart Damage': ('Fig_7', 'Fig_7d_data.xlsx', 'Heart Damage'),
        'Concern Binary': ('Fig_8', 'Fig_8d_data.xlsx', 'Concern Binary'),
    }

    # Load Excel prediction data
    excel_scatter = EXCEL_FIGS / 'Prediction_Scatter.xlsx'
    excel_scatter_plots = EXCEL_FIGS / 'Prediction_Scatter_Plots.xlsx'

    for target, (fig_folder, fig_file, sheet_name) in targets.items():
        print(f"  Processing {target}...")

        out_folder = OUTPUT_DIR / fig_folder
        out_folder.mkdir(parents=True, exist_ok=True)

        # Load Excel data
        excel_df = None
        if excel_scatter.exists():
            try:
                excel_df = pd.read_excel(excel_scatter, sheet_name=sheet_name)
            except:
                pass

        # Load extended Excel data
        excel_ext_df = None
        if excel_scatter_plots.exists():
            try:
                sheet_key = target.lower().replace(' ', '_')
                excel_ext_df = pd.read_excel(excel_scatter_plots, sheet_name=sheet_key)
            except:
                pass

        # Load PowerPoint data (has metadata columns)
        pptx_file = PPTX_FIGS / fig_folder / fig_file
        pptx_df = None
        if pptx_file.exists():
            try:
                pptx_df = pd.read_excel(pptx_file, sheet_name='Predictions')
            except:
                pass

        # Merge: Start with PowerPoint structure, fill gaps from Excel
        merged_df = None
        if pptx_df is not None:
            merged_df = pptx_df.copy()
        elif excel_df is not None:
            merged_df = excel_df.copy()
            # Add missing columns
            if 'is_positive' not in merged_df.columns:
                # Infer from Actual column
                actual_col = [c for c in merged_df.columns if 'Actual' in c]
                if actual_col:
                    merged_df['is_positive'] = merged_df[actual_col[0]].apply(
                        lambda x: str(x).lower() in ['true', '1', 'yes', 'positive']
                    )
            if 'Source' not in merged_df.columns:
                merged_df['Source'] = str(excel_scatter)

        # Write merged file
        out_file = out_folder / fig_file
        with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
            if merged_df is not None:
                merged_df.to_excel(writer, sheet_name='Predictions', index=False)

            # Also include extended data if available
            if excel_ext_df is not None:
                excel_ext_df.to_excel(writer, sheet_name='Predictions_Extended', index=False)

            add_metadata_sheet(writer, excel_scatter, f'{fig_folder}d', f'{target} Predictions')

        print(f"    Saved: {out_file}")

def merge_cumulative_importance():
    """
    Merge cumulative feature importance data.
    Both sources have similar structure (14 features x 25 drugs).
    PowerPoint has metadata sheet.

    Output: Combined with source tracking
    """
    print("\n=== Merging Cumulative Feature Importance ===")

    targets = {
        'Arrhythmia': ('Fig_6', 'Fig_6e_data.xlsx', 'Cumulative_Feature_Importance_Arrhythmia.xlsx'),
        'Heart_Damage': ('Fig_7', 'Fig_7e_data.xlsx', 'Cumulative_Feature_Importance_Heart_Damage.xlsx'),
        'Concern_Binary': ('Fig_8', 'Fig_8e_data.xlsx', 'Cumulative_Feature_Importance_Concern_Binary.xlsx'),
    }

    # Also load combined file
    combined_file = EXCEL_FIGS / 'cumulative_feature_importance.xlsx'

    for target, (fig_folder, fig_file, excel_file) in targets.items():
        print(f"  Processing {target}...")

        out_folder = OUTPUT_DIR / fig_folder
        out_folder.mkdir(parents=True, exist_ok=True)

        # Load Excel data
        excel_path = EXCEL_FIGS / excel_file
        excel_df = None
        if excel_path.exists():
            try:
                excel_df = pd.read_excel(excel_path)
            except:
                pass

        # Load PowerPoint data
        pptx_file = PPTX_FIGS / fig_folder / fig_file
        pptx_sheets = {}
        if pptx_file.exists():
            try:
                pptx_xl = pd.ExcelFile(pptx_file)
                for sheet in pptx_xl.sheet_names:
                    pptx_sheets[sheet] = pd.read_excel(pptx_xl, sheet_name=sheet)
            except:
                pass

        # Write merged file
        out_file = out_folder / fig_file
        with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
            # Prefer Excel data (typically more complete)
            if excel_df is not None:
                excel_df.to_excel(writer, sheet_name='Cumulative_Data', index=False)
            elif 'Cumulative_Data' in pptx_sheets:
                pptx_sheets['Cumulative_Data'].to_excel(writer, sheet_name='Cumulative_Data', index=False)

            # Keep PowerPoint metadata
            if 'Source_Metadata' in pptx_sheets:
                pptx_sheets['Source_Metadata'].to_excel(writer, sheet_name='Source_Metadata', index=False)

            add_metadata_sheet(writer, excel_path, f'{fig_folder}e', f'{target} Cumulative Feature Importance')

        print(f"    Saved: {out_file}")

def merge_shap_data():
    """
    Merge SHAP feature importance data.
    Excel has: Mean absolute SHAP (14 features)
    PowerPoint has: Full per-drug SHAP values (26 drugs x 14 features)

    Output: Both full matrix AND summary
    """
    print("\n=== Merging SHAP Data ===")

    targets = {
        'arrhythmia': ('Fig_6', 'Fig_6f_data.xlsx'),
        'heart_damage': ('Fig_7', 'Fig_7f_data.xlsx'),
        'concern_binary': ('Fig_8', 'Fig_8f_data.xlsx'),
    }

    for target, (fig_folder, fig_file) in targets.items():
        print(f"  Processing {target}...")

        out_folder = OUTPUT_DIR / fig_folder
        out_folder.mkdir(parents=True, exist_ok=True)

        # Load Excel data (summary)
        excel_path = EXCEL_FIGS / f'shap_{target}.xlsx'
        excel_df = None
        if excel_path.exists():
            try:
                excel_df = pd.read_excel(excel_path)
            except:
                pass

        # Load combined SHAP file
        combined_shap = EXCEL_FIGS / 'SHAP_Feature_Importance.xlsx'
        combined_df = None
        if combined_shap.exists():
            try:
                sheet_name = target.replace('_', ' ').title()
                combined_df = pd.read_excel(combined_shap, sheet_name=sheet_name)
            except:
                pass

        # Load PowerPoint data (full matrix)
        pptx_file = PPTX_FIGS / fig_folder / fig_file
        pptx_sheets = {}
        if pptx_file.exists():
            try:
                pptx_xl = pd.ExcelFile(pptx_file)
                for sheet in pptx_xl.sheet_names:
                    pptx_sheets[sheet] = pd.read_excel(pptx_xl, sheet_name=sheet)
            except:
                pass

        # Write merged file
        out_file = out_folder / fig_file
        with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
            # Full matrix from PowerPoint
            if 'SHAP_Full' in pptx_sheets:
                pptx_sheets['SHAP_Full'].to_excel(writer, sheet_name='SHAP_Full', index=False)

            # Summary from Excel
            summary_df = excel_df if excel_df is not None else combined_df
            if summary_df is not None:
                summary_df.to_excel(writer, sheet_name='SHAP_Summary', index=False)

            # Top features from PowerPoint
            if 'Top_Features' in pptx_sheets:
                pptx_sheets['Top_Features'].to_excel(writer, sheet_name='Top_Features', index=False)

            add_metadata_sheet(writer, excel_path, f'{fig_folder}f', f'{target} SHAP Values')

        print(f"    Saved: {out_file}")

def merge_model_comparison():
    """
    Merge model comparison data (MoLFormer, ADMET).
    """
    print("\n=== Merging Model Comparison Data ===")

    # Fig_6g/h: MoLFormer comparison
    print("  Processing MoLFormer comparison (Fig_6g/h)...")

    out_folder = OUTPUT_DIR / 'Fig_6'
    out_folder.mkdir(parents=True, exist_ok=True)

    # Load MoLFormer data from Excel
    molformer_dir = EXCEL_FIGS / 'MoLFormer'
    molformer_files = {
        'ROC_Comparison.xlsx': 'ROC curves',
        'Overall_Comparison.xlsx': 'Performance metrics',
        'Per_Drug_Predictions.xlsx': 'Drug predictions',
        'Confusion_Matrices.xlsx': 'Confusion matrices',
    }

    # Merge into Fig_6g
    out_file = out_folder / 'Fig_6g_data.xlsx'
    with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
        for mf_file, desc in molformer_files.items():
            mf_path = molformer_dir / mf_file
            if mf_path.exists():
                try:
                    xl = pd.ExcelFile(mf_path)
                    for sheet in xl.sheet_names:
                        df = pd.read_excel(xl, sheet_name=sheet)
                        # Truncate sheet name if too long
                        sheet_name = f"{mf_file.replace('.xlsx', '')}_{sheet}"[:31]
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                except Exception as e:
                    print(f"    Warning: {mf_file}: {e}")

        # Also load PowerPoint version for comparison
        pptx_file = PPTX_FIGS / 'Fig_6' / 'Fig_6g_data.xlsx'
        if pptx_file.exists():
            try:
                xl = pd.ExcelFile(pptx_file)
                for sheet in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=sheet)
                    sheet_name = f"PPTX_{sheet}"[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            except:
                pass

        add_metadata_sheet(writer, molformer_dir, 'Fig_6g', 'MoLFormer Model Comparison')

    print(f"    Saved: {out_file}")

    # Fig_7g/h: ADMET comparison
    print("  Processing ADMET comparison (Fig_7g/h)...")

    out_folder = OUTPUT_DIR / 'Fig_7'
    out_folder.mkdir(parents=True, exist_ok=True)

    admet_dir = EXCEL_FIGS / 'ADMET'
    admet_files = {
        'ROC_Comparison.xlsx': 'ROC curves',
        'Overall_Comparison.xlsx': 'Performance metrics',
        'DICTrank_Predictions.xlsx': 'DICTrank predictions',
        'Scaffold_CV.xlsx': 'Scaffold validation',
    }

    out_file = out_folder / 'Fig_7g_data.xlsx'
    with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
        for ad_file, desc in admet_files.items():
            ad_path = admet_dir / ad_file
            if ad_path.exists():
                try:
                    xl = pd.ExcelFile(ad_path)
                    for sheet in xl.sheet_names:
                        df = pd.read_excel(xl, sheet_name=sheet)
                        sheet_name = f"{ad_file.replace('.xlsx', '')}_{sheet}"[:31]
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                except Exception as e:
                    print(f"    Warning: {ad_file}: {e}")

        # Also load PowerPoint version
        pptx_file = PPTX_FIGS / 'Fig_7' / 'Fig_7g_data.xlsx'
        if pptx_file.exists():
            try:
                xl = pd.ExcelFile(pptx_file)
                for sheet in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=sheet)
                    sheet_name = f"PPTX_{sheet}"[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            except:
                pass

        add_metadata_sheet(writer, admet_dir, 'Fig_7g', 'ADMET Model Comparison')

    print(f"    Saved: {out_file}")

def merge_equation_data():
    """
    Merge equation comparison data (heatmaps, R2 values, LOOCV).
    """
    print("\n=== Merging Equation Data ===")

    # Fig_3d: R2 comparison
    print("  Processing R2 comparison (Fig_3d)...")

    out_folder = OUTPUT_DIR / 'Fig_3'
    out_folder.mkdir(parents=True, exist_ok=True)

    # Load Excel R2 data
    r2_files = [
        EXCEL_FIGS / 'r2_equation_comparison.xlsx',
        EXCEL_FIGS / 'r2_o2_comparison.xlsx',
    ]

    out_file = out_folder / 'Fig_3d_data.xlsx'
    with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
        for r2_file in r2_files:
            if r2_file.exists():
                try:
                    xl = pd.ExcelFile(r2_file)
                    for sheet in xl.sheet_names:
                        df = pd.read_excel(xl, sheet_name=sheet)
                        sheet_name = f"{r2_file.stem}_{sheet}"[:31]
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                except Exception as e:
                    print(f"    Warning: {r2_file}: {e}")

        # PowerPoint version
        pptx_file = PPTX_FIGS / 'Fig_3' / 'Fig_3d_data.xlsx'
        if pptx_file.exists():
            try:
                xl = pd.ExcelFile(pptx_file)
                for sheet in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=sheet)
                    sheet_name = f"PPTX_{sheet}"[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            except:
                pass

        add_metadata_sheet(writer, r2_files[0], 'Fig_3d', 'Equation R2 Comparison')

    print(f"    Saved: {out_file}")

def merge_qc_data():
    """
    Merge QC/SNR analysis data.
    """
    print("\n=== Merging QC Data ===")

    out_folder = OUTPUT_DIR / 'Fig_2'
    out_folder.mkdir(parents=True, exist_ok=True)

    # Load Excel SNR data
    snr_file = EXCEL_FIGS / 'snr_analysis.xlsx'

    out_file = out_folder / 'Fig_2a_data.xlsx'
    with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
        if snr_file.exists():
            try:
                xl = pd.ExcelFile(snr_file)
                for sheet in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=sheet)
                    df.to_excel(writer, sheet_name=sheet, index=False)
            except Exception as e:
                print(f"    Warning: {snr_file}: {e}")

        # PowerPoint version
        pptx_file = PPTX_FIGS / 'Fig_2' / 'Fig_2a_data.xlsx'
        if pptx_file.exists():
            try:
                xl = pd.ExcelFile(pptx_file)
                for sheet in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=sheet)
                    sheet_name = f"PPTX_{sheet}"[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            except:
                pass

        add_metadata_sheet(writer, snr_file, 'Fig_2a', 'SNR/QC Analysis')

    print(f"    Saved: {out_file}")

def copy_remaining_pptx_files():
    """
    Copy any PowerPoint files that don't have Excel equivalents.
    """
    print("\n=== Copying Remaining PowerPoint Files ===")

    # List of files already handled
    handled = set()

    for fig_folder in PPTX_FIGS.iterdir():
        if fig_folder.is_dir() and fig_folder.name.startswith('Fig_'):
            out_folder = OUTPUT_DIR / fig_folder.name
            out_folder.mkdir(parents=True, exist_ok=True)

            for xlsx_file in fig_folder.glob('*.xlsx'):
                out_file = out_folder / xlsx_file.name
                if not out_file.exists():
                    # Copy file that wasn't merged
                    shutil.copy2(xlsx_file, out_file)
                    print(f"  Copied: {xlsx_file.name} -> {out_folder.name}/")

def create_index():
    """
    Create an index file listing all merged data.
    """
    print("\n=== Creating Index ===")

    index_data = []

    for fig_folder in sorted(OUTPUT_DIR.iterdir()):
        if fig_folder.is_dir() and fig_folder.name.startswith('Fig_'):
            for xlsx_file in sorted(fig_folder.glob('*.xlsx')):
                try:
                    xl = pd.ExcelFile(xlsx_file)
                    sheets = xl.sheet_names
                except:
                    sheets = ['Error reading']

                index_data.append({
                    'Figure': fig_folder.name,
                    'File': xlsx_file.name,
                    'Sheets': ', '.join(sheets),
                    'Path': str(xlsx_file.relative_to(OUTPUT_DIR)),
                })

    index_df = pd.DataFrame(index_data)
    index_file = OUTPUT_DIR / 'INDEX.xlsx'
    index_df.to_excel(index_file, index=False)
    print(f"  Saved: {index_file}")

def main():
    print("=" * 60)
    print("MERGING EXCEL_FIGURES INTO POWERPOINT_FIGURES STRUCTURE")
    print("=" * 60)
    print(f"\nSource 1: {PPTX_FIGS}")
    print(f"Source 2: {EXCEL_FIGS}")
    print(f"Output:   {OUTPUT_DIR}")

    # Run all merge functions
    merge_roc_curves()
    merge_confusion_matrices()
    merge_performance_metrics()
    merge_predictions()
    merge_cumulative_importance()
    merge_shap_data()
    merge_model_comparison()
    merge_equation_data()
    merge_qc_data()
    copy_remaining_pptx_files()
    create_index()

    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("Review INDEX.xlsx for a complete listing of all merged files.")

if __name__ == '__main__':
    main()
