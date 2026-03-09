"""
Cell manipulation utilities for Jupyter notebooks.
"""

import nbformat
from typing import Optional, List


def add_cell_header(cell_index: int, dependencies: Optional[List[int]] = None) -> str:
    """
    Generate a cell header comment with index and dependencies.

    Args:
        cell_index: Index of the cell (0-based)
        dependencies: List of cell indices this cell depends on

    Returns:
        Formatted header string

    Example:
        >>> header = add_cell_header(3, dependencies=[0, 2])
        >>> print(header)
        # Cell #3
        # Depends on: 0, 2
    """
    header_lines = [f"# Cell #{cell_index}"]

    if dependencies:
        deps_str = ", ".join(map(str, dependencies))
        header_lines.append(f"# Depends on: {deps_str}")
    else:
        header_lines.append("# Depends on: None")

    return "\n".join(header_lines) + "\n"


def insert_cell(nb: nbformat.NotebookNode, index: int, source: str,
                cell_type: str = 'code', dependencies: Optional[List[int]] = None) -> None:
    """
    Insert a new cell at the specified index.

    Args:
        nb: NotebookNode object
        index: Position to insert (0-based)
        source: Cell source code/text
        cell_type: 'code' or 'markdown'
        dependencies: List of cell indices this cell depends on

    Example:
        >>> insert_cell(nb, 3, "print('hello')", dependencies=[0])
    """
    # Add header for code cells
    if cell_type == 'code' and not source.startswith('# Cell #'):
        header = add_cell_header(index, dependencies)
        source = header + source

    # Create new cell
    if cell_type == 'code':
        new_cell = nbformat.v4.new_code_cell(source=source)
    elif cell_type == 'markdown':
        new_cell = nbformat.v4.new_markdown_cell(source=source)
    else:
        raise ValueError(f"Invalid cell_type: {cell_type}. Must be 'code' or 'markdown'")

    # Insert into notebook
    nb.cells.insert(index, new_cell)


def edit_cell(nb: nbformat.NotebookNode, index: int, new_source: str,
              dependencies: Optional[List[int]] = None, preserve_outputs: bool = True) -> None:
    """
    Edit an existing cell's source code.

    Args:
        nb: NotebookNode object
        index: Cell index to edit (0-based)
        new_source: New source code/text
        dependencies: List of cell indices this cell depends on
        preserve_outputs: Keep existing outputs (if False, clears them)

    Example:
        >>> edit_cell(nb, 5, "df = pd.read_csv('new_data.csv')", dependencies=[0, 1])
    """
    if index < 0 or index >= len(nb.cells):
        raise IndexError(f"Cell index {index} out of range (0-{len(nb.cells)-1})")

    cell = nb.cells[index]

    # Add header for code cells if not present
    if cell.cell_type == 'code' and not new_source.startswith('# Cell #'):
        header = add_cell_header(index, dependencies)
        new_source = header + new_source

    cell.source = new_source

    # Clear outputs if requested
    if not preserve_outputs and cell.cell_type == 'code':
        cell.outputs = []
        cell.execution_count = None


def delete_cell(nb: nbformat.NotebookNode, index: int) -> None:
    """
    Delete a cell from the notebook.

    Args:
        nb: NotebookNode object
        index: Cell index to delete (0-based)

    Example:
        >>> delete_cell(nb, 7)
    """
    if index < 0 or index >= len(nb.cells):
        raise IndexError(f"Cell index {index} out of range (0-{len(nb.cells)-1})")

    del nb.cells[index]


def move_cell(nb: nbformat.NotebookNode, from_index: int, to_index: int) -> None:
    """
    Move a cell from one position to another.

    Args:
        nb: NotebookNode object
        from_index: Current cell index (0-based)
        to_index: Destination index (0-based)

    Example:
        >>> move_cell(nb, 5, 2)  # Move cell 5 to position 2
    """
    if from_index < 0 or from_index >= len(nb.cells):
        raise IndexError(f"Source index {from_index} out of range")
    if to_index < 0 or to_index > len(nb.cells):
        raise IndexError(f"Destination index {to_index} out of range")

    cell = nb.cells.pop(from_index)
    nb.cells.insert(to_index, cell)


def clear_outputs(nb: nbformat.NotebookNode, cell_indices: Optional[List[int]] = None) -> None:
    """
    Clear outputs from code cells.

    Args:
        nb: NotebookNode object
        cell_indices: Specific cells to clear (None = all cells)

    Example:
        >>> clear_outputs(nb, [3, 5, 7])  # Clear specific cells
        >>> clear_outputs(nb)  # Clear all cells
    """
    if cell_indices is None:
        cell_indices = range(len(nb.cells))

    for idx in cell_indices:
        if idx < 0 or idx >= len(nb.cells):
            continue

        cell = nb.cells[idx]
        if cell.cell_type == 'code':
            cell.outputs = []
            cell.execution_count = None


def find_cells_with_text(nb: nbformat.NotebookNode, search_text: str,
                         case_sensitive: bool = False) -> List[int]:
    """
    Find all cells containing specific text.

    Args:
        nb: NotebookNode object
        search_text: Text to search for
        case_sensitive: Whether search is case-sensitive

    Returns:
        List of cell indices containing the search text

    Example:
        >>> indices = find_cells_with_text(nb, "import pandas")
        >>> print(f"Found in cells: {indices}")
    """
    matching_indices = []

    for i, cell in enumerate(nb.cells):
        source = cell.source if case_sensitive else cell.source.lower()
        search = search_text if case_sensitive else search_text.lower()

        if search in source:
            matching_indices.append(i)

    return matching_indices
