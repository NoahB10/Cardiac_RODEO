"""
Quick example demonstrating the Jupyter Notebook Editor skill utilities.

Usage:
    python quick_example.py path/to/notebook.ipynb
"""

import sys
from pathlib import Path
from notebook_utils import load_notebook, save_notebook, print_cell_summary
from cell_editor import edit_cell, insert_cell, add_cell_header
from execute_cells import execute_range, print_execution_summary


def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_example.py <notebook.ipynb>")
        sys.exit(1)

    notebook_path = Path(sys.argv[1])

    if not notebook_path.exists():
        print(f"Error: Notebook not found: {notebook_path}")
        sys.exit(1)

    print(f"Loading notebook: {notebook_path}")
    nb = load_notebook(notebook_path)

    # Print summary
    print("\n" + "="*60)
    print_cell_summary(nb)
    print("="*60 + "\n")

    # Example 1: Add a header to cell 0
    print("Example 1: Adding dependency header to cell 0...")
    if len(nb.cells) > 0:
        cell = nb.cells[0]
        header = add_cell_header(0, dependencies=None)
        if not cell.source.startswith('# Cell #'):
            cell.source = header + cell.source
            print("  ✓ Added header")

    # Example 2: Insert a new markdown cell
    print("\nExample 2: Inserting new markdown cell...")
    insert_cell(
        nb,
        index=1,
        source="## Auto-generated section\n\nThis cell was added programmatically.",
        cell_type='markdown'
    )
    print("  ✓ Inserted markdown cell at position 1")

    # Example 3: Edit a cell (if there are enough cells)
    if len(nb.cells) > 2:
        print("\nExample 3: Editing cell 2 with dependencies...")
        original_source = nb.cells[2].source
        edit_cell(
            nb,
            index=2,
            new_source=original_source,  # Keep same content but add header
            dependencies=[0, 1],
            preserve_outputs=True
        )
        print("  ✓ Updated cell 2")

    # Example 4: Execute cells (optional - can be slow)
    execute = input("\nExecute cells 0-2? (y/n): ").lower() == 'y'
    if execute:
        print("\nExecuting cells...")
        results = execute_range(nb, 0, min(2, len(nb.cells) - 1), stop_on_error=True)
        print_execution_summary(results)

    # Save the modified notebook
    backup_path = notebook_path.with_suffix('.ipynb.backup')
    print(f"\nSaving backup to: {backup_path}")
    save_notebook(nb, backup_path)

    save_original = input("Overwrite original notebook? (y/n): ").lower() == 'y'
    if save_original:
        save_notebook(nb, notebook_path)
        print(f"  ✓ Saved to: {notebook_path}")
    else:
        print("  Skipped saving original")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
