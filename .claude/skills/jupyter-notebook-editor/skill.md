---
name: jupyter-notebook-editor
description: Edit Jupyter notebooks (.ipynb) using nbformat. Read, modify, add, move cells; execute with full kernel state; capture and fix errors. Cross-platform (Windows/Linux/Mac). Use whenever notebooks or cells are mentioned.
dependencies: python>=3.8, nbformat>=5.9, nbclient>=0.10
---

# Jupyter Notebook Editor

**Platform**: Cross-platform (Windows, Linux, macOS)
**Execution**: Full Jupyter kernel with state preservation
**Approach**: Read → nbformat → Write workflow

Use this skill for ANY Jupyter notebook operations. This approach is more robust than MCP-based tools because it:
- Preserves kernel state across cell executions
- Works on all platforms (especially important for Windows)
- Uses actual Jupyter kernels (not isolated subprocess execution)
- Handles complex notebooks with dependencies between cells

## When to Use

**ALWAYS use this skill when:**
- Any request mentions notebooks, .ipynb files, or cells
- Editing or adding cells (code or markdown)
- Running specific cells and inspecting outputs/errors
- Refactoring, cleaning, or reorganizing notebook structure
- Converting between StratifiedKFold and LOOCV
- Fixing variable names or result dictionary keys
- Updating training loops or plotting cells

## Core Workflow: Read → Modify → Write

**CRITICAL RULE:** NEVER use NotebookEdit tool - it doesn't persist changes reliably.

### Standard Pattern

```python
# 1. Read notebook with Read tool
# (Read tool already executed by Claude)

# 2. Load with nbformat
import json
import nbformat

# Option A: If you already used Read tool
nb = nbformat.reads(json.dumps(notebook_data), as_version=4)

# Option B: Direct file read
nb = nbformat.read("notebook.ipynb", as_version=4)

# 3. Inspect cells
for i, cell in enumerate(nb.cells):
    print(f"Cell {i} ({cell.cell_type}): {cell.source[:50]}")

# 4. Modify cells directly
cell_idx = 13
nb.cells[cell_idx].source = '''# Cell #13: Train XGBoost for Arrhythmia (LOOCV)
# Depends on: 0-12

from sklearn.model_selection import LeaveOneOut
# ... rest of cell code
'''

# 5. Convert to JSON string
nb_json = nbformat.writes(nb)

# 6. Write back (GUARANTEES PERSISTENCE)
# Use Write tool with nb_json content
```

**Why this works:**
- ✓ Read tool loads current state
- ✓ nbformat modifies in memory
- ✓ Write tool overwrites file directly
- ✓ Changes persist immediately
- ✓ Works on all platforms

## Executing Cells with Kernel State

For cells that depend on previous executions:

```python
from nbclient import NotebookClient

# Create client with notebook's kernel
client = NotebookClient(
    nb,
    timeout=600,
    kernel_name=nb.metadata.kernelspec.name
)

# Execute single cell
client.execute_cell(nb.cells[cell_idx], cell_idx, execution_count=cell_idx+1)

# Execute range of cells (preserves state)
for idx in range(start_idx, end_idx):
    client.execute_cell(nb.cells[idx], idx, execution_count=idx+1)

# Check for errors
for cell in nb.cells:
    if cell.outputs:
        for output in cell.outputs:
            if output.get('output_type') == 'error':
                print(f"Error in cell: {output['ename']}: {output['evalue']}")
```

## Cell Annotations

For every edited or new cell, add dependency headers:

```python
# Cell #13: Train XGBoost for Arrhythmia (LOOCV)
# Depends on: 0-12

# ... actual code follows
```

This helps track:
- Cell execution order
- Dependencies between cells
- What needs to be rerun when changes are made

## Common Operations

### Find and Replace Variable Names

```python
import json

with open('notebook.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Fix all cells with old variable names
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        src = ''.join(cell['source'])

        # Replace old variable names
        src = src.replace('model_concern_rf', 'model_concern')
        src = src.replace('results_concern_rf', 'results_concern')

        cell['source'] = src

# Save back
with open('notebook.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
```

### Update Multiple Training Cells

When converting from StratifiedKFold to LOOCV:

```python
# Template for LOOCV cell
LOOCV_CELL = '''# Cell #13: Train XGBoost (LOOCV)
from sklearn.model_selection import LeaveOneOut

loo = LeaveOneOut()
y_true_all = []
y_pred_all = []

for train_idx, test_idx in loo.split(features_df):
    # ... training logic
    y_true_all.append(y_test[0])
    y_pred_all.append(y_pred[0])

# Aggregate metrics
y_true = np.array(y_true_all)
y_pred = np.array(y_pred_all)
'''

# Find and replace training cells
for idx, cell in enumerate(nb.cells):
    src = ''.join(cell['source'])
    if 'TRAINING XGBOOST' in src and 'StratifiedKFold' in src:
        nb.cells[idx].source = LOOCV_CELL
        nb.cells[idx].outputs = []
        nb.cells[idx].execution_count = None
```

### Clear Outputs and Reset Execution Counts

```python
for cell in nb.cells:
    if cell.cell_type == 'code':
        cell.outputs = []
        cell.execution_count = None
```

### Add New Cell at Specific Position

```python
new_cell = nbformat.v4.new_code_cell('''# Cell #22: ROC Curves
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 5, figsize=(25, 5))
# ... plotting code
''')

nb.cells.insert(22, new_cell)
```

## Error Handling

When cells fail during execution:

```python
for idx, cell in enumerate(nb.cells):
    if cell.outputs:
        for output in cell.outputs:
            if output.get('output_type') == 'error':
                print(f"\nCell {idx} ERROR:")
                print(f"  Type: {output['ename']}")
                print(f"  Message: {output['evalue']}")
                print(f"  Traceback: {output['traceback']}")
```

**Fix strategy:**
1. Identify failing cell and error type
2. Check cell dependencies
3. Fix code in failing cell
4. Rerun from earliest dependency
5. Verify outputs are correct

## Comparison: MCP vs nbformat Approach

| Feature | MCP jupyter-notebooks | nbformat jupyter-notebook-editor |
|---------|----------------------|----------------------------------|
| Platform | Linux (/opt/venv) | Windows/Linux/Mac |
| Execution | Subprocess (isolated) | Full Jupyter kernel |
| State | No state preservation | Full state preservation |
| Complexity | Simple operations | Complex notebooks |
| Dependencies | Requires MCP server | Pure Python |
| Best for | Simple automation | Research/ML workflows |

**On Windows, ALWAYS use jupyter-notebook-editor (this skill).**

## Preservation and Safety

- ✓ Preserve notebook metadata (`kernelspec`, `language_info`)
- ✓ Preserve cell metadata
- ✓ Keep outputs unless explicitly asked to clear
- ✓ Maintain execution counts when running cells
- ✓ Validate schema with `nbformat.validate(nb)` after changes

## Best Practices

1. **Always Read First**: Use Read tool before any modifications
2. **Test Changes**: Run cells after modifications to verify
3. **Clear Before Commit**: Clear sensitive outputs before version control
4. **Document Dependencies**: Add `# Depends on:` headers
5. **Incremental Execution**: Run from earliest changed cell forward
6. **Verify Outputs**: Check for errors in cell outputs
7. **Use Write Tool**: NEVER use NotebookEdit - always Write

## Example: Complete Workflow

```python
# 1. Read notebook
import json
import nbformat
from nbclient import NotebookClient

# Load
with open('Prediction_Models_AR_HD_Concern.ipynb', 'r', encoding='utf-8') as f:
    nb_data = json.load(f)
nb = nbformat.reads(json.dumps(nb_data), as_version=4)

# 2. Find and update cells
for idx, cell in enumerate(nb.cells):
    if cell.cell_type == 'code':
        src = ''.join(cell.source)

        # Replace old patterns
        if 'StratifiedKFold' in src:
            # Update to LOOCV
            new_src = src.replace('StratifiedKFold', 'LeaveOneOut')
            # ... more replacements
            cell.source = new_src
            cell.outputs = []

# 3. Execute changed cells
client = NotebookClient(nb, timeout=600, kernel_name='python3')
for idx in range(13, 18):  # Training cells
    client.execute_cell(nb.cells[idx], idx, execution_count=idx+1)

# 4. Check for errors
errors_found = []
for idx, cell in enumerate(nb.cells):
    if cell.outputs:
        for output in cell.outputs:
            if output.get('output_type') == 'error':
                errors_found.append((idx, output['ename'], output['evalue']))

if errors_found:
    print("Errors found:")
    for idx, ename, evalue in errors_found:
        print(f"  Cell {idx}: {ename}: {evalue}")
else:
    # 5. Save if no errors
    nb_json = nbformat.writes(nb)
    with open('Prediction_Models_AR_HD_Concern.ipynb', 'w', encoding='utf-8') as f:
        f.write(nb_json)
    print("Notebook updated successfully")
```

## Troubleshooting

### Kernel Not Starting
- Check Python environment has ipykernel installed
- Verify kernel name in metadata matches installed kernels
- Use `jupyter kernelspec list` to see available kernels

### Import Errors
- Activate correct environment before running
- Install missing packages in kernel's Python environment
- Check kernel is using correct Python interpreter

### Execution Hangs
- Check for infinite loops
- Verify external resources are available
- Increase timeout parameter in NotebookClient

### Changes Not Persisting
- NEVER use NotebookEdit tool
- ALWAYS use Read → nbformat → Write workflow
- Verify Write tool completes successfully
