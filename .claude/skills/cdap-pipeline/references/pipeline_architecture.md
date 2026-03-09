# CDAP Pipeline Architecture

Complete technical documentation of the CDAP pipeline architecture.

## Overview

The Complete Data Analysis Pipeline (CDAP) is a 3-stage processing system for cardiac organoid oxygen and contractility data.

```
Stage 1: Filtering & QC     → Stage 2: Metrics         → Stage 3: Visualization
(cdap/stage1_filter.py)       (cdap/stage2_tables.py)    (cdap/stage3_prism.py)

Raw Logs (.log/.txt)     →   Filtered Segments     →   CSV Tables        →   Prism Files (.pzfx)
                             Stage1Result              Stage2_Tables/         *.pzfx
```

## Module Structure

```
cdap/
├── __init__.py                 # Package exports
├── config.py                   # Configuration dataclasses
├── stage1_filter.py            # Stage 1: Filtering
├── stage2_tables.py            # Stage 2: Aggregation
├── stage3_prism.py             # Stage 3: Prism loading
├── io_utils.py                 # I/O utilities
├── io_utils_logfiles.py        # Plate 3 log file loader
├── fft_tools.py                # FFT analysis
├── models.py                   # Data structures
├── debug_outputs.py            # Debug visualization
├── pipeline.py                 # CLI entry point
├── Save_Excel.py               # Excel export utilities
├── export_o2_heatmaps.py       # O2 heatmap generation
├── export_qc_rejections.py     # QC rejection tracking
├── add_excel_heatmap.py        # Excel heatmap integration
├── plot_stage2_heatmap.py      # Stage 2 visualization
├── model_smoothed_surfaces.py  # 3D surface modeling
└── show_smoothed_preview.py    # Surface preview tool
```

## Stage 1: Quality Filtering

**Module**: `cdap/stage1_filter.py`

**Purpose**: Filter raw oxygen sensor logs and remove low-quality data

### Key Functions

```python
def run_stage1(config: Stage1Config, single_drug: str = None) -> Stage1Result:
    """Main Stage 1 entry point."""
    ...

def _compute_duration_columns(...) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Convert timestamps to duration labels."""
    ...

def _filter_oxygen_and_snr(df: pd.DataFrame, config: Stage1Config) -> pd.DataFrame:
    """Apply oxygen and SNR filters."""
    ...

def _filter_amplitude_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Remove amplitude outliers (±2σ)."""
    ...
```

### Processing Flow

1. **Discover drug assignments** from plate maps
2. **Load raw log files** per well
3. **Apply filters**:
   - Oxygen range (2-80% air)
   - SNR threshold (≥ 2.0)
   - Amplitude outliers (±2σ)
4. **Check segment completeness** (≥ 50% valid rows)
5. **Build timeline** with hour labels
6. **Truncate duration** (default: 96 hours)
7. **Export outputs**:
   - Filtered CSVs (Stage1_Raw/)
   - Timeline CSV
   - Processing notes

### Data Flow

```
Raw Logs → load_well_dataframe() → pd.DataFrame
    ↓
_filter_oxygen_and_snr() → Filtered DataFrame
    ↓
_filter_amplitude_outliers() → Cleaned DataFrame
    ↓
_compute_duration_columns() → Add timeline columns
    ↓
Check completeness → SegmentRecord
    ↓
Build hierarchical structure → Stage1Result
```

## Stage 2: Metrics Aggregation

**Module**: `cdap/stage2_tables.py`

**Purpose**: Calculate time-series metrics and aggregate across wells

### Key Functions

```python
def generate_stage2_tables(
    stage1_result: Stage1Result = None,
    config: Stage2Config = None,
    single_drug: str = None
) -> None:
    """Main Stage 2 entry point."""
    ...

def _calculate_diameter_normalization_factors(diameter_sources: Dict[str, Path]) -> Dict[str, float]:
    """Calculate diameter normalization factors."""
    ...

def _should_apply_normalization(...) -> Tuple[bool, Dict[str, int]]:
    """Determine if normalization should be applied."""
    ...
```

### Processing Flow

1. **Load Stage 1 result** (or use cached LAST_STAGE1_RESULT)
2. **Extract metrics** per segment:
   - O2 mean, std, dominant frequency
   - Amplitude std, dominant frequency
3. **Aggregate by timeline hour**
4. **Apply interpolation** (fill gaps ≤ 1 hour)
5. **Apply diameter normalization** (optional)
6. **Export CSV tables** to Stage2_Tables/

### Metrics Calculation

```python
# O2 mean
o2_mean = segment_df["oxygen_pct_air"].mean()

# O2 std
o2_std = segment_df["oxygen_pct_air"].std()

# Dominant frequency (FFT)
from cdap.fft_tools import dominant_frequency, FFTConfig
fft_config = FFTConfig(sample_rate_hz=1.0)
dom_freq = dominant_frequency(signal_array, fft_config)
```

### Table Structure

```
Hour | 0.0mM_1 | 0.0mM_2 | 0.01mM_1 | 0.01mM_2 | ...
-----|---------|---------|----------|----------|----
0    | 15.2    | 15.8    | 14.9     | 15.1     | ...
3    | 14.8    | 15.3    | 13.2     | 12.9     | ...
7    | 14.5    | 15.1    | 11.8     | 11.2     | ...
```

## Stage 3: Prism Integration

**Module**: `cdap/stage3_prism.py`

**Purpose**: Load Stage 2 data into GraphPad Prism files

### Key Functions

```python
def load_stage2_to_prism(config: Stage3Config) -> Stage3Result:
    """Main Stage 3 entry point."""
    ...

def find_stage2_csv_path(table_name: str, metric_filename: str, stage2_root: Path) -> Optional[str]:
    """Find corresponding Stage 2 CSV."""
    ...

def extract_drug_name_from_table_title(title: str) -> str:
    """Extract clean drug name from Prism table title."""
    ...

def remove_sparse_columns(root: ET.Element, min_fill_percent: float) -> int:
    """Remove columns with < min_fill_percent data."""
    ...
```

### Processing Flow

1. **Parse Prism XML files** (.pzfx)
2. **Find Stage 2 CSV files** by drug name matching
3. **Load CSV data** into Prism tables
4. **Clean column names** (remove .1, .2, .3 suffixes)
5. **Remove sparse columns** (< 60% data by default)
6. **Create backups**
7. **Save updated Prism files**

### Prism File Mapping

```python
METRIC_MAPPING = {
    'Average_Oxygen.pzfx': 'O2_mean.csv',
    'Dominant_frequency_Oxygen.pzfx': 'O2_dom_freq.csv',
    'Standard_Deviation_Oxygen.pzfx': 'O2_std.csv',
    'Standard_Deviation_Contractility.pzfx': 'Amp_std.csv',
    'Dominant_frequency_Contractility.pzfx': 'Amp_dom_freq.csv',
}
```

## I/O Utilities

**Module**: `cdap/io_utils.py`

### Key Functions

```python
def load_well_dataframe(plate_logs_dir: Path, well_id: str) -> pd.DataFrame:
    """Load and stitch all log files for a well."""
    ...

def discover_drug_assignments(plate_roots) -> List[DrugAssignment]:
    """Discover drug assignments from plate maps."""
    ...

def build_timestamp_series(df: pd.DataFrame) -> pd.Series:
    """Build absolute timestamp series."""
    ...
```

### Plate Format Detection

```python
# Check if Plate 3 (.txt files)
txt_files = list(plate_logs_dir.glob(f"{well_id}*.txt"))

if txt_files:
    # Use Plate 3 loader
    df = load_well_dataframe_plate3(plate_logs_dir, well_id)
else:
    # Use legacy loader for Plates 1-2
    df = collect_well_for_plate(plate_logs_dir, well_id)
```

## FFT Analysis

**Module**: `cdap/fft_tools.py`

### FFTConfig

```python
@dataclass
class FFTConfig:
    sample_rate_hz: float = 1.0
    min_freq_hz: float = 0.01
    max_freq_hz: float = 0.5
```

### Dominant Frequency Calculation

```python
def dominant_frequency(signal: np.ndarray, config: FFTConfig) -> float:
    """Calculate dominant frequency using FFT."""
    # Apply window function
    # Compute FFT
    # Find peak in frequency range
    # Return dominant frequency
    ...
```

## Configuration System

**Module**: `cdap/config.py`

### Global Constants

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
```

### Default Paths

```python
def _default_plate_roots() -> tuple[Path, ...]:
    roots = [
        PROJECT_ROOT / "LogFiles" / "P1OxygenLogs",
        PROJECT_ROOT / "LogFiles" / "P2OxygenLogs",
    ]
    if (PROJECT_ROOT / "LogFiles" / "P3OxygenLogs").exists():
        roots.append(PROJECT_ROOT / "LogFiles" / "P3OxygenLogs")
    return tuple(roots)
```

## Data Models

**Module**: `cdap/models.py`

Provides hierarchical data structures for Stage 1 results. See `references/data_structures.md` for details.

## Debug Utilities

**Module**: `cdap/debug_outputs.py`

Generates Excel files and plots for quality control during Stage 1.

## Export Utilities

- **`export_o2_heatmaps.py`**: Generate O2 heatmap visualizations
- **`export_qc_rejections.py`**: Track QC rejection statistics
- **`add_excel_heatmap.py`**: Add heatmaps to Excel files
- **`plot_stage2_heatmap.py`**: Visualize Stage 2 tables

## Advanced Features

### 3D Surface Modeling

**Module**: `cdap/model_smoothed_surfaces.py`

Experimental 3D surface fitting for dose-response visualization.

### Timeline Analysis

**Output**: `timeline_analysis_output/`

Per-drug tables mapping timeline hours to actual timestamps for each well.

## Performance Considerations

- **Memory usage**: Stage 1 loads all wells into memory
- **Parallelization**: Not implemented (sequential processing)
- **Caching**: Stage 1 result cached in LAST_STAGE1_RESULT
- **File I/O**: Main bottleneck for large datasets

## Extension Points

1. **Custom filters**: Modify `_filter_oxygen_and_snr()`, `_filter_amplitude_outliers()`
2. **New metrics**: Add to Stage 2 aggregation
3. **Export formats**: Extend Stage 3 for different visualization tools
4. **Plate formats**: Add new loaders in `io_utils.py`
5. **Timeline algorithms**: Customize `_compute_duration_columns()`

## Testing Strategy

1. **Unit tests**: Individual functions (filters, metrics)
2. **Integration tests**: Complete pipeline runs
3. **Validation**: Known datasets with expected outputs
4. **QC checks**: Automated validation after each stage
