"""
Cell execution utilities for Jupyter notebooks.
"""

import nbformat
from nbclient import NotebookClient
from typing import Optional, List, Dict, Any


def execute_cell(nb: nbformat.NotebookNode, cell_index: int,
                 timeout: int = 600, kernel_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a single cell in the notebook.

    Args:
        nb: NotebookNode object
        cell_index: Index of cell to execute (0-based)
        timeout: Maximum execution time in seconds
        kernel_name: Kernel to use (None = use notebook's kernel)

    Returns:
        Dictionary with execution results and any errors

    Example:
        >>> result = execute_cell(nb, 3)
        >>> if result['error']:
        ...     print(f"Error: {result['error_message']}")
    """
    if cell_index < 0 or cell_index >= len(nb.cells):
        raise IndexError(f"Cell index {cell_index} out of range")

    cell = nb.cells[cell_index]

    # Only execute code cells
    if cell.cell_type != 'code':
        return {'executed': False, 'reason': 'Not a code cell', 'error': False}

    # Get kernel name
    if kernel_name is None:
        kernel_name = nb.metadata.get('kernelspec', {}).get('name', 'python3')

    # Create client and execute
    client = NotebookClient(nb, timeout=timeout, kernel_name=kernel_name)

    try:
        client.execute_cell(cell, cell_index, execution_count=cell_index + 1)

        # Check for errors in outputs
        error_info = capture_errors(cell)

        return {
            'executed': True,
            'error': error_info is not None,
            'error_info': error_info,
            'execution_count': cell.execution_count
        }

    except Exception as e:
        return {
            'executed': False,
            'error': True,
            'error_message': str(e),
            'exception': e
        }


def execute_range(nb: nbformat.NotebookNode, start_index: int, end_index: Optional[int] = None,
                  timeout: int = 600, kernel_name: Optional[str] = None,
                  stop_on_error: bool = False) -> List[Dict[str, Any]]:
    """
    Execute a range of cells.

    Args:
        nb: NotebookNode object
        start_index: First cell to execute (0-based, inclusive)
        end_index: Last cell to execute (0-based, inclusive). None = end of notebook
        timeout: Maximum execution time per cell in seconds
        kernel_name: Kernel to use (None = use notebook's kernel)
        stop_on_error: Whether to stop execution on first error

    Returns:
        List of execution results for each cell

    Example:
        >>> results = execute_range(nb, 0, 10, stop_on_error=True)
        >>> errors = [r for r in results if r['error']]
        >>> print(f"Found {len(errors)} errors")
    """
    if end_index is None:
        end_index = len(nb.cells) - 1

    if start_index < 0 or start_index >= len(nb.cells):
        raise IndexError(f"Start index {start_index} out of range")
    if end_index < start_index or end_index >= len(nb.cells):
        raise IndexError(f"End index {end_index} out of range")

    results = []

    for idx in range(start_index, end_index + 1):
        result = execute_cell(nb, idx, timeout=timeout, kernel_name=kernel_name)
        results.append(result)

        if stop_on_error and result['error']:
            break

    return results


def execute_from_cell(nb: nbformat.NotebookNode, start_index: int,
                      timeout: int = 600, kernel_name: Optional[str] = None,
                      stop_on_error: bool = False) -> List[Dict[str, Any]]:
    """
    Execute all cells from a starting index to the end.

    Useful for re-running downstream cells after editing an upstream cell.

    Args:
        nb: NotebookNode object
        start_index: First cell to execute (0-based)
        timeout: Maximum execution time per cell in seconds
        kernel_name: Kernel to use (None = use notebook's kernel)
        stop_on_error: Whether to stop execution on first error

    Returns:
        List of execution results

    Example:
        >>> # After editing cell 5, rerun everything from cell 5 onward
        >>> results = execute_from_cell(nb, 5)
    """
    return execute_range(nb, start_index, None, timeout, kernel_name, stop_on_error)


def capture_errors(cell: nbformat.NotebookNode) -> Optional[Dict[str, Any]]:
    """
    Extract error information from a cell's outputs.

    Args:
        cell: Cell to check for errors

    Returns:
        Dictionary with error details, or None if no errors

    Example:
        >>> error = capture_errors(nb.cells[5])
        >>> if error:
        ...     print(f"{error['ename']}: {error['evalue']}")
    """
    if cell.cell_type != 'code':
        return None

    for output in cell.get('outputs', []):
        if output.get('output_type') == 'error':
            return {
                'ename': output.get('ename', 'UnknownError'),
                'evalue': output.get('evalue', ''),
                'traceback': output.get('traceback', [])
            }

    return None


def print_execution_summary(results: List[Dict[str, Any]]) -> None:
    """
    Print a formatted summary of execution results.

    Args:
        results: List of execution results from execute_range()

    Example:
        >>> results = execute_range(nb, 0, 10)
        >>> print_execution_summary(results)
    """
    total = len(results)
    executed = sum(1 for r in results if r.get('executed', False))
    errors = sum(1 for r in results if r.get('error', False))

    print(f"Execution Summary:")
    print(f"  Total cells: {total}")
    print(f"  Executed: {executed}")
    print(f"  Errors: {errors}")

    if errors > 0:
        print(f"\nCells with errors:")
        for i, result in enumerate(results):
            if result.get('error', False):
                error_info = result.get('error_info', {})
                if error_info:
                    print(f"  Cell {i}: {error_info.get('ename', 'Error')} - {error_info.get('evalue', '')}")
                else:
                    print(f"  Cell {i}: {result.get('error_message', 'Unknown error')}")


def execute_with_retry(nb: nbformat.NotebookNode, cell_index: int,
                       max_retries: int = 3, timeout: int = 600) -> Dict[str, Any]:
    """
    Execute a cell with automatic retry on failure.

    Args:
        nb: NotebookNode object
        cell_index: Cell to execute
        max_retries: Maximum number of retry attempts
        timeout: Timeout per attempt

    Returns:
        Execution result dictionary

    Example:
        >>> result = execute_with_retry(nb, 8, max_retries=3)
    """
    for attempt in range(max_retries):
        result = execute_cell(nb, cell_index, timeout=timeout)

        if not result['error']:
            return result

        if attempt < max_retries - 1:
            print(f"Cell {cell_index} failed (attempt {attempt + 1}/{max_retries}), retrying...")

    return result
