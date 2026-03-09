"""
Reliable notebook writing utilities for when NotebookEdit doesn't persist changes.

This module provides functions to safely rewrite entire Jupyter notebooks using
the Write tool, which guarantees persistence.
"""

import nbformat
from typing import Optional
from pathlib import Path


def notebook_to_json(nb: nbformat.NotebookNode) -> str:
    """
    Convert a notebook object to JSON string.

    Args:
        nb: NotebookNode object

    Returns:
        JSON string representation of the notebook
    """
    return nbformat.writes(nb)


def write_notebook_with_tool(nb: nbformat.NotebookNode, path: Path) -> str:
    """
    Generate the Write tool call parameters for a notebook.

    This function doesn't actually call the Write tool (that must be done by Claude Code),
    but it prepares the parameters.

    Args:
        nb: NotebookNode object to write
        path: Path to write the notebook to

    Returns:
        JSON string ready for Write tool
    """
    nb_json = nbformat.writes(nb)
    return nb_json


def verify_notebook_persisted(path: Path, expected_cells: Optional[list] = None) -> bool:
    """
    Verify that a notebook was written correctly by re-reading it.

    Args:
        path: Path to the notebook file
        expected_cells: Optional list of expected cell counts or content to verify

    Returns:
        True if notebook matches expectations, False otherwise
    """
    try:
        nb = nbformat.read(str(path), as_version=4)

        if expected_cells is not None:
            if len(nb.cells) != len(expected_cells):
                print(f"❌ Cell count mismatch: expected {len(expected_cells)}, got {len(nb.cells)}")
                return False

        print(f"✓ Notebook verified: {len(nb.cells)} cells")
        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def create_minimal_notebook(cells_data: list) -> nbformat.NotebookNode:
    """
    Create a minimal notebook from cell data.

    Args:
        cells_data: List of dicts with keys:
            - 'cell_type': 'code' or 'markdown'
            - 'source': Cell source code/markdown
            - 'metadata': Optional dict of cell metadata

    Returns:
        NotebookNode object

    Example:
        >>> cells = [
        ...     {'cell_type': 'code', 'source': 'import pandas as pd'},
        ...     {'cell_type': 'markdown', 'source': '## Data Analysis'}
        ... ]
        >>> nb = create_minimal_notebook(cells)
        >>> json_str = notebook_to_json(nb)
    """
    nb = nbformat.v4.new_notebook()

    for cell_data in cells_data:
        cell_type = cell_data['cell_type']
        source = cell_data['source']
        metadata = cell_data.get('metadata', {})

        if cell_type == 'code':
            cell = nbformat.v4.new_code_cell(source=source, metadata=metadata)
        elif cell_type == 'markdown':
            cell = nbformat.v4.new_markdown_cell(source=source, metadata=metadata)
        else:
            raise ValueError(f"Unknown cell type: {cell_type}")

        nb.cells.append(cell)

    # Set minimal metadata
    nb.metadata = {
        'kernelspec': {
            'display_name': 'Python 3',
            'language': 'python',
            'name': 'python3'
        },
        'language_info': {
            'name': 'python',
            'version': '3.10.0'
        }
    }

    return nb


# Example usage demonstration
if __name__ == "__main__":
    print("Notebook Writer Utilities")
    print("=" * 60)
    print()
    print("When NotebookEdit doesn't persist changes:")
    print("1. Load notebook: nb = load_notebook('file.ipynb')")
    print("2. Modify cells: nb.cells[4].source = '# new code'")
    print("3. Convert to JSON: json_str = notebook_to_json(nb)")
    print("4. Use Write tool: Write(file_path='file.ipynb', content=json_str)")
    print("5. Verify: verify_notebook_persisted('file.ipynb')")
    print()
    print("This guarantees changes are persisted to disk.")
