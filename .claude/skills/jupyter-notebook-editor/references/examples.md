# Jupyter Notebook Editor - Examples

Practical examples for common notebook editing tasks.

## Example 1: Basic Cell Inspection

```python
from scripts import load_notebook, print_cell_summary

# Load and inspect
nb = load_notebook("analysis.ipynb")
print_cell_summary(nb)
```

Output:
```
Notebook contains 8 cells:
------------------------------------------------------------
Cell  0 [code    ] [exec: 1]: import pandas as pd
Cell  1 [code    ] [exec: 2]: df = pd.read_csv('data.csv')
Cell  2 [markdown]:           ## Data Cleaning
Cell  3 [code    ] [exec: 3]: df.dropna(inplace=True)
...
```

## Example 2: Add Dependency Headers to All Code Cells

```python
from scripts import load_notebook, save_notebook, add_cell_header

nb = load_notebook("notebook.ipynb")

# Track dependencies manually or with static analysis
cell_dependencies = {
    0: None,           # Imports - no dependencies
    1: [0],            # Uses imports from cell 0
    2: [0, 1],         # Uses both
    3: [1],            # Only needs cell 1
}

for idx, deps in cell_dependencies.items():
    cell = nb.cells[idx]
    if cell.cell_type == 'code':
        header = add_cell_header(idx, dependencies=deps)
        if not cell.source.startswith('# Cell #'):
            cell.source = header + cell.source

save_notebook(nb, "notebook.ipynb")
```

## Example 3: Insert Setup Cell at Beginning

```python
from scripts import load_notebook, save_notebook, insert_cell

nb = load_notebook("analysis.ipynb")

# Insert setup cell at position 0
setup_code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
"""

insert_cell(nb, index=0, source=setup_code, cell_type='code', dependencies=None)

save_notebook(nb, "analysis.ipynb")
```

## Example 4: Execute Modified Cells and Downstream Dependencies

```python
from scripts import (
    load_notebook, save_notebook, edit_cell,
    execute_from_cell, print_execution_summary
)

nb = load_notebook("model.ipynb")

# Modify cell 5
new_code = """
# Updated hyperparameters
learning_rate = 0.001  # Changed from 0.01
batch_size = 64
epochs = 100
"""

edit_cell(nb, index=5, new_source=new_code, dependencies=[0, 1], preserve_outputs=False)

# Re-execute from cell 5 onward (to update downstream results)
print("Re-executing cells 5 through end...")
results = execute_from_cell(nb, start_index=5, stop_on_error=True)

print_execution_summary(results)
save_notebook(nb, "model.ipynb")
```

## Example 5: Find and Fix Errors

```python
from scripts import (
    load_notebook, execute_range,
    capture_errors, edit_cell, save_notebook
)

nb = load_notebook("buggy.ipynb")

# Execute all cells to find errors
results = execute_range(nb, 0, len(nb.cells) - 1, stop_on_error=False)

# Find cells with errors
error_cells = [i for i, r in enumerate(results) if r['error']]

for idx in error_cells:
    cell = nb.cells[idx]
    error_info = capture_errors(cell)

    print(f"\nCell {idx} error:")
    print(f"  {error_info['ename']}: {error_info['evalue']}")
    print(f"  Source preview: {cell.source[:100]}")

    # Manual fix based on error
    # (In practice, you'd analyze the error and apply appropriate fix)

save_notebook(nb, "buggy_fixed.ipynb")
```

## Example 6: Clear All Outputs Before Committing

```python
from scripts import load_notebook, save_notebook, clear_outputs

nb = load_notebook("analysis.ipynb")

# Clear all outputs to reduce file size and avoid git conflicts
clear_outputs(nb)

save_notebook(nb, "analysis.ipynb")
print("✓ All outputs cleared")
```

## Example 7: Reorganize Cells

```python
from scripts import load_notebook, save_notebook, move_cell

nb = load_notebook("messy.ipynb")

# Move imports (currently at cell 5) to the beginning
move_cell(nb, from_index=5, to_index=0)

# Move conclusion (cell 3) to the end
move_cell(nb, from_index=3, to_index=len(nb.cells) - 1)

save_notebook(nb, "organized.ipynb")
```

## Example 8: Search and Replace in Cells

```python
from scripts import load_notebook, save_notebook, find_cells_with_text

nb = load_notebook("notebook.ipynb")

# Find all cells using old variable name
cells_to_update = find_cells_with_text(nb, "old_variable_name")

print(f"Found {len(cells_to_update)} cells to update: {cells_to_update}")

# Replace in each cell
for idx in cells_to_update:
    cell = nb.cells[idx]
    cell.source = cell.source.replace('old_variable_name', 'new_variable_name')

save_notebook(nb, "notebook.ipynb")
```

## Example 9: Batch Processing Multiple Notebooks

```python
from pathlib import Path
from scripts import load_notebook, save_notebook, clear_outputs

notebooks = Path('.').glob('*.ipynb')

for nb_path in notebooks:
    print(f"Processing {nb_path}...")

    nb = load_notebook(nb_path)

    # Clear outputs
    clear_outputs(nb)

    # Save
    save_notebook(nb, nb_path)

print("✓ All notebooks processed")
```

## Example 10: Validate Notebook Structure

```python
from scripts import load_notebook, validate_notebook
import nbformat

try:
    nb = load_notebook("notebook.ipynb")
    validate_notebook(nb)
    print("✓ Notebook structure is valid")
except nbformat.ValidationError as e:
    print(f"❌ Validation failed: {e}")
```

## Example 11: Editing Cells (PRIMARY METHOD - Always Use This)

**DO NOT use NotebookEdit** - always use this Read → Modify → Write workflow:

```python
from scripts import load_notebook
import nbformat

# 1. Read current notebook
nb = load_notebook("notebook.ipynb")

# 2. Modify cells in memory
# Fix cell 4 - correct column indices
nb.cells[4].source = """# Cell #4
# Depends on: 1, 2
# Purpose: Load data with correct indices

# CORRECT indices
time_points = df_sheet.iloc[1, 2:].values  # Row 1, cols 2+
concentrations = df_sheet.iloc[2:, 1].values  # Rows 2+, col 1
o2_matrix = df_sheet.iloc[2:, 2:].values  # Rows 2+, cols 2+
"""

# Fix cell 5 - use dictionary check instead of .empty
nb.cells[5].source = """# Cell #5
# Depends on: 4

def get_drug_data(drug_name, data_dict):
    if drug_name in data_dict:
        return data_dict[drug_name]
    return None

drug_info = get_drug_data('Sunitinib', df_o2_raw)
if drug_info is None:
    print('No data found')
"""

# 3. Write back using Claude Code Write tool or nbformat
# Method A: Using Write tool (recommended for Claude Code)
notebook_json = nbformat.writes(nb)
# Then call Write(file_path="notebook.ipynb", content=notebook_json)

# Method B: Direct write with nbformat
with open("notebook.ipynb", 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("✓ Notebook rewritten successfully")
```

**Why always use this method:**
- Write tool directly overwrites the file (guaranteed persistence)
- NotebookEdit is unreliable and fails silently
- Full control over all cells and metadata
- Can fix multiple cells at once
- Verifiable - read the file back to confirm changes

## Best Practices

1. **Always backup before modifying**:
   ```python
   save_notebook(nb, notebook_path.with_suffix('.ipynb.backup'))
   ```

2. **Add dependency headers when editing**:
   - Helps track execution order
   - Makes debugging easier
   - Documents cell relationships

3. **Clear outputs before version control**:
   - Reduces file size
   - Avoids merge conflicts
   - Keeps diffs clean

4. **Execute downstream cells after editing**:
   - Use `execute_from_cell()` after modifying a cell
   - Ensures consistency across notebook

5. **Validate after structural changes**:
   - Run `validate_notebook()` before saving
   - Catches schema errors early

6. **ALWAYS use Write tool for edits (NOT NotebookEdit)**:
   - Read → modify in memory → Write entire notebook
   - Verify changes by re-reading the file
   - Write tool guarantees persistence, NotebookEdit doesn't
