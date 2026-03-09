# Jupyter Notebook Editor Skill

Programmatically edit, execute, and manage Jupyter notebooks (.ipynb files) using Python.

## Features

- **Load/Save notebooks** with validation
- **Inspect cells** with formatted summaries
- **Edit cells** with dependency tracking
- **Insert/Delete/Move cells** while preserving structure
- **Execute cells** individually or in ranges
- **Capture errors** with detailed tracebacks
- **Clear outputs** for version control
- **Search cells** by content

## Quick Start

### Load and Inspect

```python
from scripts import load_notebook, print_cell_summary

nb = load_notebook("analysis.ipynb")
print_cell_summary(nb)
```

### Edit a Cell (Use Write Tool, NOT NotebookEdit)

```python
import nbformat

# 1. Load notebook
nb = nbformat.read("analysis.ipynb", as_version=4)

# 2. Edit cell 5
nb.cells[5].source = """# Cell #5
# Depends on: 0, 2
df = pd.read_csv('data.csv')
"""

# 3. Convert to JSON
nb_json = nbformat.writes(nb)

# 4. Write back using Write tool (guarantees persistence)
# Write(file_path="analysis.ipynb", content=nb_json)
```

### Execute Cells

```python
from scripts import execute_range, print_execution_summary

# Execute cells 0-10
results = execute_range(nb, 0, 10, stop_on_error=True)
print_execution_summary(results)
```

## Installation

This skill requires:
- `nbformat >= 5.9`
- `nbclient >= 0.10`
- `python >= 3.8`

Install dependencies:

```bash
pip install nbformat nbclient
```

## Skill Structure

```
jupyter-notebook-editor/
├── skill.md                 # Skill definition for Claude
├── README.md               # This file
├── scripts/                # Python utilities
│   ├── __init__.py        # Package exports
│   ├── notebook_utils.py  # Load, save, inspect
│   ├── cell_editor.py     # Edit, insert, move, delete
│   ├── execute_cells.py   # Execute and error handling
│   └── quick_example.py   # Interactive example
└── references/             # Documentation
    └── examples.md        # Detailed usage examples
```

## Usage Patterns

### 1. Add Dependency Headers

Automatically add tracking headers to code cells:

```python
# Cell #5
# Depends on: 0, 2
df = pd.read_csv('data.csv')
```

### 2. Execute After Editing

After modifying a cell, re-run downstream cells:

```python
# Edit cell 5
edit_cell(nb, 5, new_source="...")

# Re-execute from cell 5 onward
execute_from_cell(nb, start_index=5)
```

### 3. Clear Outputs for Git

Before committing, strip outputs:

```python
from scripts import clear_outputs

clear_outputs(nb)  # All cells
save_notebook(nb, "notebook.ipynb")
```

### 4. Find and Fix Errors

Execute all cells, identify errors, fix them:

```python
results = execute_range(nb, 0, len(nb.cells) - 1)

for i, result in enumerate(results):
    if result['error']:
        print(f"Cell {i} error: {result['error_info']}")
```

## When to Use This Skill

Claude should invoke this skill whenever:
- User mentions `.ipynb` files or Jupyter notebooks
- Task involves editing, running, or inspecting notebook cells
- Need to add/remove/reorganize cells
- Debugging notebook execution errors
- Preparing notebooks for version control

## Examples

See [`references/examples.md`](references/examples.md) for detailed examples including:
- Cell inspection and summaries
- Adding dependency headers
- Inserting setup cells
- Executing and error handling
- Reorganizing cells
- Batch processing notebooks

## Integration with Claude Code

This skill provides reliable notebook editing by using the Write tool instead of NotebookEdit:
- **Guaranteed persistence** - Write tool directly overwrites files (NotebookEdit doesn't work reliably)
- **Dependency tracking** - Track which cells depend on others
- **Execution** - Run cells and capture outputs/errors
- **Validation** - Ensure notebook structure is correct
- **Batch operations** - Process multiple cells/notebooks
- **Programmatic access** - Use in scripts and automation

### Core Editing Method: Read → Modify → Write

**DO NOT use NotebookEdit tool** - it reports success but doesn't persist changes.

**ALWAYS use this workflow:**
1. Use `Read` tool to load the current notebook
2. Modify cells in memory with nbformat
3. Use `Write` tool to save the entire notebook JSON
4. Verify by re-reading the file

See `references/best_practices.md` and `references/examples.md` for complete details.

## Contributing

To extend this skill:

1. Add new functions to appropriate module:
   - `notebook_utils.py` - Core notebook operations
   - `cell_editor.py` - Cell manipulation
   - `execute_cells.py` - Execution features

2. Update `__init__.py` exports

3. Add examples to `references/examples.md`

4. Update this README

## License

This skill is part of the Cardiac RODEO project.
