"""
Equation Fitting Pipeline - Main Entry Point

This script runs the complete equation fitting pipeline:
1. Fits all 11 equations to Contractility and O2 data
2. Consolidates coefficient files
3. Creates the all_equations_coefficients.xlsx workbook
4. Generates LaTeX report with figures
5. Creates Overleaf-ready zip file

Usage:
    python run_pipeline.py           # Run full pipeline
    python run_pipeline.py --fit     # Only fit equations
    python run_pipeline.py --excel   # Only create Excel
    python run_pipeline.py --report  # Only generate report
"""
import sys
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import validate_paths, COEFF_DIR, OUTPUT_DIR, FINAL_EXCEL

def run_fitting():
    """Run equation fitting for all equations."""
    print("\n" + "="*80)
    print("STEP 1: FITTING ALL EQUATIONS")
    print("="*80)

    from fit_all_equations import run_all_fits
    contract_results, o2_results = run_all_fits()

    return contract_results, o2_results


def run_consolidation():
    """Run consolidation of coefficient files."""
    print("\n" + "="*80)
    print("STEP 2: CONSOLIDATING COEFFICIENT FILES")
    print("="*80)

    from consolidate import consolidate_all_equations
    consolidated_files = consolidate_all_equations()

    return consolidated_files


def run_excel_creation():
    """Create the final Excel workbook."""
    print("\n" + "="*80)
    print("STEP 3: CREATING EXCEL WORKBOOK")
    print("="*80)

    from create_excel import create_all_equations_excel
    excel_path = create_all_equations_excel()

    return excel_path


def run_report_generation():
    """Generate LaTeX report and Overleaf zip."""
    print("\n" + "="*80)
    print("STEP 4: GENERATING LATEX REPORT")
    print("="*80)

    from generate_report import generate_full_report
    tex_path, zip_path = generate_full_report()

    return tex_path, zip_path


def run_full_pipeline():
    """Run the complete pipeline."""
    print("\n" + "="*80)
    print("EQUATION FITTING PIPELINE")
    print("="*80)
    print("\nThis pipeline will:")
    print("  1. Fit all 11 equations to Contractility and O2 data")
    print("  2. Consolidate coefficient files")
    print("  3. Create all_equations_coefficients.xlsx")
    print("  4. Generate LaTeX report with figures")
    print("  5. Create Overleaf-ready zip file")

    # Validate input files
    print("\nValidating input files...")
    if not validate_paths():
        print("\nERROR: Missing required input files. Aborting.")
        return

    # Step 1: Fit equations
    contract_results, o2_results = run_fitting()

    # Step 2: Consolidate
    consolidated_files = run_consolidation()

    # Step 3: Create Excel
    excel_path = run_excel_creation()

    # Step 4: Generate report
    tex_path, zip_path = run_report_generation()

    # Summary
    print("\n" + "="*80)
    print("PIPELINE COMPLETE!")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  Coefficient CSVs: {COEFF_DIR}")
    print(f"  Excel workbook: {excel_path}")
    if tex_path:
        print(f"  LaTeX report: {tex_path}")
    if zip_path:
        print(f"  Overleaf zip: {zip_path}")

    print(f"\nContractility: {len(contract_results)} equations fitted")
    print(f"O2: {len(o2_results)} equations fitted")

    if excel_path and excel_path.exists():
        print(f"\nExcel file ready at: {excel_path}")

    if zip_path and zip_path.exists():
        print(f"\nTo upload to Overleaf:")
        print(f"  1. Go to https://www.overleaf.com")
        print(f"  2. Click 'New Project' -> 'Upload Project'")
        print(f"  3. Upload: {zip_path}")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Equation Fitting Pipeline for Cardiac RODEO',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python run_pipeline.py           # Run full pipeline
    python run_pipeline.py --fit     # Only fit equations
    python run_pipeline.py --excel   # Only create Excel
    python run_pipeline.py --report  # Only generate report
        '''
    )

    parser.add_argument('--fit', action='store_true',
                       help='Only run equation fitting')
    parser.add_argument('--consolidate', action='store_true',
                       help='Only consolidate coefficient files')
    parser.add_argument('--excel', action='store_true',
                       help='Only create Excel workbook')
    parser.add_argument('--report', action='store_true',
                       help='Only generate LaTeX report')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip input file validation')

    args = parser.parse_args()

    # If no specific step requested, run full pipeline
    if not any([args.fit, args.consolidate, args.excel, args.report]):
        run_full_pipeline()
        return

    # Validate unless skipped
    if not args.no_validate:
        print("Validating input files...")
        if not validate_paths():
            print("\nWARNING: Missing required input files.")
            if not args.excel and not args.report:
                print("Use --no-validate to skip this check.")
                return

    # Run specific steps
    if args.fit:
        run_fitting()

    if args.consolidate:
        run_consolidation()

    if args.excel:
        run_excel_creation()

    if args.report:
        run_report_generation()


if __name__ == "__main__":
    main()
