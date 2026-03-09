"""
Notebook loading, saving, and inspection utilities.
"""

import nbformat
from pathlib import Path
from typing import Optional, List, Dict, Any


def load_notebook(notebook_path: str | Path) -> nbformat.NotebookNode:
    """
    Load a Jupyter notebook from file.

    Args:
        notebook_path: Path to .ipynb file

    Returns:
        NotebookNode object

    Example:
        >>> nb = load_notebook("analysis.ipynb")
        >>> print(f"Loaded {len(nb.cells)} cells")
    """
    path = Path(notebook_path)
    if not path.exists():
        raise FileNotFoundError(f"Notebook not found: {path}")

    return nbformat.read(path, as_version=4)


def save_notebook(nb: nbformat.NotebookNode, notebook_path: str | Path,
                  validate: bool = True) -> None:
    """
    Save a notebook to file.

    Args:
        nb: NotebookNode object
        notebook_path: Path to save .ipynb file
        validate: Whether to validate notebook structure before saving

    Example:
        >>> save_notebook(nb, "analysis.ipynb")
    """
    if validate:
        validate_notebook(nb)

    path = Path(notebook_path)
    nbformat.write(nb, path)


def inspect_cells(nb: nbformat.NotebookNode, max_lines: int = 3) -> List[Dict[str, Any]]:
    """
    Get summary information about all cells in a notebook.

    Args:
        nb: NotebookNode object
        max_lines: Maximum number of source lines to show per cell

    Returns:
        List of cell info dictionaries

    Example:
        >>> cells_info = inspect_cells(nb)
        >>> for info in cells_info:
        ...     print(f"Cell {info['index']}: {info['type']}")
    """
    cells_info = []

    for i, cell in enumerate(nb.cells):
        source_lines = cell.source.splitlines()
        preview = source_lines[:max_lines]

        info = {
            'index': i,
            'type': cell.cell_type,
            'source_preview': preview,
            'num_lines': len(source_lines),
            'has_outputs': len(cell.get('outputs', [])) > 0 if cell.cell_type == 'code' else False,
            'execution_count': cell.get('execution_count', None) if cell.cell_type == 'code' else None
        }

        cells_info.append(info)

    return cells_info


def validate_notebook(nb: nbformat.NotebookNode) -> None:
    """
    Validate notebook structure against nbformat schema.

    Args:
        nb: NotebookNode object

    Raises:
        nbformat.ValidationError: If notebook structure is invalid

    Example:
        >>> validate_notebook(nb)
    """
    nbformat.validate(nb)


def print_cell_summary(nb: nbformat.NotebookNode) -> None:
    """
    Print a formatted summary of notebook cells.

    Args:
        nb: NotebookNode object

    Example:
        >>> print_cell_summary(nb)
        Cell 0 [code]: import pandas as pd
        Cell 1 [markdown]: # Data Analysis
        Cell 2 [code]: df = pd.read_csv('data.csv')
    """
    cells_info = inspect_cells(nb, max_lines=1)

    print(f"Notebook contains {len(nb.cells)} cells:")
    print("-" * 60)

    for info in cells_info:
        preview = info['source_preview'][0] if info['source_preview'] else '(empty)'
        cell_type = info['type']
        exec_info = f" [exec: {info['execution_count']}]" if info['execution_count'] else ""

        print(f"Cell {info['index']:2d} [{cell_type:8s}]{exec_info}: {preview[:60]}")
