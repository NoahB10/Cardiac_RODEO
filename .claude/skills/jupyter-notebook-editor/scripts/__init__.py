"""
Jupyter Notebook Editor Skill - Helper Scripts

This package provides utilities for programmatically editing and executing
Jupyter notebooks (.ipynb files).

Modules:
    notebook_utils: Core notebook loading, saving, and inspection
    cell_editor: Cell manipulation (add, edit, move, delete)
    execute_cells: Cell execution and error handling
    notebook_writer: Reliable notebook writing when NotebookEdit fails
"""

from .notebook_utils import (
    load_notebook,
    save_notebook,
    inspect_cells,
    validate_notebook
)

from .cell_editor import (
    add_cell_header,
    insert_cell,
    edit_cell,
    delete_cell,
    move_cell,
    clear_outputs
)

from .execute_cells import (
    execute_cell,
    execute_range,
    execute_from_cell,
    capture_errors
)

from .notebook_writer import (
    notebook_to_json,
    write_notebook_with_tool,
    verify_notebook_persisted,
    create_minimal_notebook
)

__all__ = [
    # notebook_utils
    'load_notebook',
    'save_notebook',
    'inspect_cells',
    'validate_notebook',
    # cell_editor
    'add_cell_header',
    'insert_cell',
    'edit_cell',
    'delete_cell',
    'move_cell',
    'clear_outputs',
    # execute_cells
    'execute_cell',
    'execute_range',
    'execute_from_cell',
    'capture_errors',
    # notebook_writer (reliable persistence)
    'notebook_to_json',
    'write_notebook_with_tool',
    'verify_notebook_persisted',
    'create_minimal_notebook',
]
