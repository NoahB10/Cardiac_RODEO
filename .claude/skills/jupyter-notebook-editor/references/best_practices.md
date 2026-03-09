# Best Practices for Jupyter Notebook Editing

## Dependency Management

### Always Track Dependencies

When editing cells, document dependencies:

```python
# Cell #5
# Depends on: 0, 1, 2
# Uses: pd from cell 0, data_path from cell 1, config from cell 2

df = pd.read_csv(data_path, **config)
```

### Topological Execution Order

Maintain dependency order:
1. Imports (Cell 0)
2. Configuration (Cell 1)
3. Data loading (depends on 0, 1)
4. Processing (depends on 3)
5. Analysis (depends on 4)
6. Visualization (depends on 5)

### Rerun Downstream After Editing

```python
# After editing cell 5, rerun all dependent cells
execute_from_cell(nb, start_index=5)
```

## Version Control

### Clear Outputs Before Committing

```python
# Before git commit
clear_outputs(nb)
save_notebook(nb, "notebook.ipynb")
```

### Use Pre-commit Hooks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Strip notebook outputs before commit

for notebook in $(git diff --cached --name-only --diff-filter=ACM | grep '\.ipynb$'); do
    python -c "
import nbformat
nb = nbformat.read('$notebook', as_version=4)
for cell in nb.cells:
    if cell.cell_type == 'code':
        cell.outputs = []
        cell.execution_count = None
nbformat.write(nb, '$notebook')
"
    git add "$notebook"
done
```

### Keep Notebooks Small

- **Separate concerns**: One notebook per analysis stage
- **Extract utilities**: Move reusable code to `.py` modules
- **Link notebooks**: Use `%run notebook.ipynb` or imports

## Code Organization

### Standard Notebook Structure

```
Cell 0: # Imports and Setup
Cell 1: ## Configuration
Cell 2: ## Load Data
Cell 3: ## Data Cleaning
Cell 4: ## Exploratory Analysis
Cell 5: ## Modeling
Cell 6: ## Results
Cell 7: ## Conclusions
```

### Use Markdown Headers

```python
insert_cell(nb, 0, "# Project Title\n\n**Goal:** ...", cell_type='markdown')
insert_cell(nb, 3, "## Data Processing", cell_type='markdown')
```

### Extract Repeated Code

❌ **Bad** - Repeated code:
```python
# Cell 5
df = pd.read_csv('data.csv')
df.dropna(inplace=True)
df['date'] = pd.to_datetime(df['date'])

# Cell 8
df = pd.read_csv('data.csv')
df.dropna(inplace=True)
df['date'] = pd.to_datetime(df['date'])
```

✅ **Good** - Shared function:
```python
# Cell 1
def load_data(path):
    df = pd.read_csv(path)
    df.dropna(inplace=True)
    df['date'] = pd.to_datetime(df['date'])
    return df

# Cell 5
# Depends on: 1
df = load_data('data.csv')

# Cell 8
# Depends on: 1
df = load_data('data.csv')
```

## Error Handling

### Capture and Log Errors

```python
results = execute_range(nb, 0, len(nb.cells) - 1, stop_on_error=False)

# Log errors to file
with open('errors.log', 'w') as f:
    for i, result in enumerate(results):
        if result['error']:
            error_info = result.get('error_info', {})
            f.write(f"Cell {i}: {error_info.get('ename')}\n")
            f.write(f"  {error_info.get('evalue')}\n")
            f.write(f"  {''.join(error_info.get('traceback', []))}\n\n")
```

### Fix Errors Systematically

1. **Identify error** - Run all cells, capture errors
2. **Find dependencies** - Check which cells the error cell depends on
3. **Fix source** - Update error cell and its dependencies
4. **Rerun from earliest change** - Execute from first modified cell onward

### Use Try-Except in Notebooks

```python
# Cell #5
# Depends on: 0, 1

try:
    df = pd.read_csv(data_path)
except FileNotFoundError:
    print(f"⚠ File not found: {data_path}")
    print("  Using sample data instead")
    df = pd.DataFrame({'A': [1, 2, 3]})
```

## Performance

### Don't Execute Expensive Cells Repeatedly

```python
# Cell #10 - Long-running computation
# Cache results to avoid re-running

import pickle
from pathlib import Path

cache_file = Path('model_cache.pkl')

if cache_file.exists():
    with open(cache_file, 'rb') as f:
        model = pickle.load(f)
    print("✓ Loaded cached model")
else:
    # Train model (expensive)
    model = train_expensive_model(data)

    with open(cache_file, 'wb') as f:
        pickle.dump(model, f)
    print("✓ Trained and cached model")
```

### Use Cell Magic for Timing

```python
%%time
# Expensive operation
result = long_computation()
```

## Documentation

### Add Cell Purpose Headers

```python
# Cell #8: Feature Engineering
# Depends on: 0, 5, 7
# Purpose: Create interaction features for modeling

df['feature_product'] = df['A'] * df['B']
df['feature_ratio'] = df['A'] / (df['B'] + 1e-8)
```

### Include TOC in First Markdown Cell

```markdown
# Analysis Title

**Table of Contents:**
1. Setup (Cells 0-1)
2. Data Loading (Cells 2-3)
3. Exploratory Analysis (Cells 4-6)
4. Modeling (Cells 7-10)
5. Results (Cells 11-12)
```

### Document Assumptions

```python
# Cell #5: Load Training Data
# Depends on: 0, 1
# Assumptions:
#   - data.csv exists in project root
#   - CSV has columns: id, feature1, feature2, target
#   - No missing values in target column

df = pd.read_csv('data.csv')
assert set(['id', 'feature1', 'feature2', 'target']).issubset(df.columns)
assert df['target'].notna().all()
```

## Editing Notebooks: Always Use Write Tool

### PRIMARY METHOD: Read → Modify → Write

**DO NOT use NotebookEdit tool** - it doesn't reliably persist changes.

**ALWAYS use this workflow:**

### Step-by-Step Workflow

```python
# Step 1: Read the notebook file with Read tool
# Read(file_path="notebook.ipynb")

# Step 2: Load into nbformat
import nbformat
nb = nbformat.read('notebook.ipynb', as_version=4)

# Step 3: Modify cells as needed
nb.cells[4].source = """# Cell #4
# Depends on: 1, 2
# Purpose: Load data with correct indices

time_points = df_sheet.iloc[1, 2:].values
concentrations = df_sheet.iloc[2:, 1].values
o2_matrix = df_sheet.iloc[2:, 2:].values
"""

nb.cells[5].source = """# Cell #5
# Depends on: 4

def get_drug_data(drug_name, data_dict):
    if drug_name in data_dict:
        return data_dict[drug_name]
    return None
"""

# Step 4: Convert to JSON string
nb_json = nbformat.writes(nb)

# Step 5: Write back using Write tool (GUARANTEED PERSISTENCE)
# Write(file_path="notebook.ipynb", content=nb_json)

# Step 6: Verify changes persisted
nb_verify = nbformat.read('notebook.ipynb', as_version=4)
print(f"✓ Cell 4 starts with: {nb_verify.cells[4].source[:50]}")
```

### Why This Method Works

- **Read tool**: Ensures you have the latest file state
- **nbformat in memory**: Full control over all cells and metadata
- **Write tool**: Direct file overwrite guarantees persistence
- **No NotebookEdit**: Avoids the unreliable built-in tool

### Verification After Write

```python
# Always verify changes persisted
nb_check = nbformat.read('notebook.ipynb', as_version=4)
for i, cell in enumerate(nb_check.cells):
    if cell.cell_type == 'code':
        print(f"Cell {i}: {cell.source[:60]}...")
```

## Safety

### Always Backup Before Modifying

```python
from shutil import copy

# Backup original
copy('notebook.ipynb', 'notebook.ipynb.backup')

# Then modify
nb = load_notebook('notebook.ipynb')
# ... edits ...
save_notebook(nb, 'notebook.ipynb')
```

### Validate After Changes

```python
from nbformat import validate, ValidationError

try:
    validate(nb)
    print("✓ Notebook structure is valid")
except ValidationError as e:
    print(f"❌ Validation error: {e}")
    # Restore from backup
```

### Use Read-Only Mode for Inspection

```python
# When just inspecting, don't save changes
nb = load_notebook('notebook.ipynb')
print_cell_summary(nb)
# Don't call save_notebook()
```

## Testing Notebooks

### Create Test Notebooks

```
project/
├── analysis.ipynb          # Main analysis
├── test_analysis.ipynb     # Test with sample data
└── notebooks/
    ├── exploratory.ipynb
    └── test_exploratory.ipynb
```

### Automated Testing

```python
# test_notebooks.py
import nbformat
from nbclient import NotebookClient

def test_notebook(path):
    """Execute notebook and check for errors."""
    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(nb, timeout=600)

    try:
        client.execute()
        print(f"✓ {path} executed successfully")
        return True
    except Exception as e:
        print(f"❌ {path} failed: {e}")
        return False

# Run tests
test_notebook('analysis.ipynb')
test_notebook('exploratory.ipynb')
```

## Summary Checklist

Before committing a notebook:

- [ ] All cells execute without errors
- [ ] Dependency headers added to edited cells
- [ ] Outputs cleared (or selectively kept for documentation)
- [ ] Markdown headers for major sections
- [ ] No hardcoded paths (use config or environment variables)
- [ ] Long computations cached
- [ ] Code extracted to modules where appropriate
- [ ] TOC updated in first cell
- [ ] Notebook validated with `nbformat.validate()`
- [ ] Backup created before major changes
