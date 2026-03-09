---
name: cdap-pipeline
description: Complete Data Analysis Pipeline (CDAP) for cardiac organoid oxygen and contractility analysis. Use this skill to run the 3-stage analysis pipeline - Stage 1 (filtering), Stage 2 (metrics aggregation), Stage 3 (Prism export). Processes Dynamix oxygen log files through quality filtering, time-series aggregation, frequency analysis, and GraphPad Prism integration. Supports all plate formats (P1/P2 .log files, P3 .txt files). Always use this skill when analyzing cardiac organoid data or running the complete pipeline.
---

# CDAP Pipeline - Cardiac Organoid Data Analysis

Complete 3-stage pipeline for processing cardiac organoid oxygen and contractility measurements from raw sensor logs to publication-ready Prism visualizations.

## When to Use This Skill

Use this skill whenever you need to:
- Run the complete 3-stage data analysis pipeline
- Process cardiac organoid oxygen sensor data
- Filter and quality-check Dynamix log files (Stage 1)
- Generate time-series metrics and aggregations (Stage 2)
- Load data into GraphPad Prism files (Stage 3)
- Analyze drug effects on cardiac organoids
- Calculate oxygen/contractility metrics (mean, std, dominant frequency)
- Apply diameter normalization to organoid measurements

**Always reference this skill when working with the CDAP pipeline**, whether running individual stages or the complete workflow.

## Quick Start

When this skill loads, you'll see the base directory path. Use it to access bundled resources:
- Scripts: `{base_directory}/scripts/`
- References: `{base_directory}/references/`

### Run Complete Pipeline

```python
# Import the pipeline modules
from cdap import (
    Stage1Config, run_stage1,
    Stage2Config, generate_stage2_tables,
    Stage3Config, load_stage2_to_prism
)
from pathlib import Path

# Stage 1: Filter raw data
s1_config = Stage1Config(
    plate_roots=[Path("LogFiles/P1OxygenLogs")],
    save_raw=True
)
s1_result = run_stage1(s1_config, single_drug="Amiodarone")

# Stage 2: Generate metrics tables
s2_config = Stage2Config(output_root=Path("Stage2_Tables"))
generate_stage2_tables(stage1_result=s1_result, single_drug="Amiodarone")

# Stage 3: Load to Prism
s3_config = Stage3Config(min_fill_percent=60.0)
s3_result = load_stage2_to_prism(s3_config)

print(f"✓ Complete! Processed {s3_result.total_tables_processed} tables")
```

### Run Individual Stages

```python
# Stage 1 only
from cdap import Stage1Config, run_stage1
config = Stage1Config(save_raw=True)
result = run_stage1(config, single_drug="Amiodarone")

# Stage 2 only
from cdap import Stage2Config, generate_stage2_tables
config = Stage2Config()
generate_stage2_tables(config=config, single_drug="Amiodarone")

# Stage 3 only
from cdap import Stage3Config, load_stage2_to_prism
config = Stage3Config(min_fill_percent=60.0)
result = load_stage2_to_prism(config)
```

## Pipeline Overview

```
Raw Log Files → Stage 1 (Filter) → Stage 2 (Aggregate) → Stage 3 (Load to Prism)
```

### Stage 1: Quality Filtering & Segmentation

**Purpose**: Filter raw oxygen sensor logs and remove low-quality data

**Key Operations**:
- Oxygen range filtering (0-80% air saturation)
- SNR filtering (signal-to-noise ratio ≥ 2.0)
- Amplitude outlier removal (±2σ filtering)
- Segment completeness check (≥50% valid rows)
- Timeline construction with hour labels
- Duration truncation (default: 96 hours)

**Input**: Raw `.log` or `.txt` files from oxygen sensors
**Output**:
- `Stage1_Raw/[Drug]/[Concentration]/` - Filtered segment CSV files
- `[drug]_timeline.csv` - Experiment timeline
- `[drug]_stage1_notes.txt` - Processing summary

**Configuration**:
```python
Stage1Config(
    plate_roots: List[Path],              # Plate directories
    min_oxygen_pct: float = 2.0,          # Min oxygen %
    max_oxygen_pct: float = 80.0,         # Max oxygen %
    min_snr: float = 2.0,                 # SNR threshold
    min_segment_completeness: float = 0.5, # Min valid rows
    maximum_duration_hours: float = 96.0, # Max experiment duration
    save_raw: bool = True,                # Export filtered CSVs
    debug: bool = False                   # Enable debug outputs
)
```

### Stage 2: Aggregation & Metrics

**Purpose**: Calculate time-series metrics and aggregate across wells

**Key Metrics**:
- **Oxygen**: Mean, standard deviation, dominant frequency
- **Contractility**: Amplitude standard deviation, dominant frequency
- **Timeline interpolation**: Fills small gaps (≤1 hour)
- **Diameter normalization** (optional): Normalizes by organoid size

**Input**: Stage 1 filtered segments
**Output**: CSV tables in `Stage2_Tables/[Drug]/`
- `O2_mean.csv` - Average oxygen over time
- `O2_std.csv` - Oxygen variability
- `O2_dom_freq.csv` - Oxygen oscillation frequency
- `Amp_std.csv` - Contractility variability
- `Amp_dom_freq.csv` - Beating frequency

**Table Structure**:
- **Rows**: Timeline hours (0, 3, 7, 18, 24, 48, 72, 96...)
- **Columns**: Wells/replicates at each concentration
- **First row**: Concentration values (mM)

**Configuration**:
```python
Stage2Config(
    output_root: Path = Path("Stage2_Tables"),
    interpolate_limit: int = 1,               # Max gap hours
    apply_diameter_normalization: bool = False,
    diameter_sources: Dict[str, Path] = None  # Diameter files
)
```

### Stage 3: Prism Integration & Cleanup

**Purpose**: Load data into GraphPad Prism and remove sparse columns

**Key Operations**:
1. Load CSV data into existing Prism `.pzfx` files
2. Update tables by matching drug names
3. Clean column names (removes `.1`, `.2`, `.3` suffixes)
4. Remove sparse columns (< 60% data by default)
5. Create backups before modification

**Input**: Stage 2 CSV tables
**Output**: Updated Prism files
- `Average_Oxygen.pzfx`
- `Dominant_frequency_Oxygen.pzfx`
- `Standard_Deviation_Oxygen.pzfx`
- `Standard_Deviation_Contractility.pzfx`
- `Dominant_frequency_Contractility.pzfx`

**Prism File Mapping**:
```
Average_Oxygen.pzfx                    ← O2_mean.csv
Dominant_frequency_Oxygen.pzfx         ← O2_dom_freq.csv
Standard_Deviation_Oxygen.pzfx         ← O2_std.csv
Standard_Deviation_Contractility.pzfx  ← Amp_std.csv
Dominant_frequency_Contractility.pzfx  ← Amp_dom_freq.csv
```

**Configuration**:
```python
Stage3Config(
    stage2_root: Path = Path("Stage2_Tables"),
    min_fill_percent: float = 60.0,    # Sparse threshold
    create_backups: bool = True,       # Backup .pzfx files
    prism_files: Dict[str, str] = None # Custom mapping
)
```

## Data Formats

### Plate 1 & 2 Format (.log files)
- **Extension**: `.log`
- **Columns**: `time_s`, `oxygen_pct_air`, `snr`, `amp1_vpp`, `amp2_vpp`
- **Drug Maps**: `P1DrugMap.csv`, `P2DrugMap.csv`
- **Layout**: 8 drugs × 8 concentrations × 4 replicates

### Plate 3 Format (.txt files)
- **Extension**: `.txt`
- **Timestamp**: `DD.MM.YYYY HH:MM:SS`
- **Columns**: Same as P1/P2, but SNR in column 12
- **Drug Map**: `P3DrugMap.csv` (format: "DrugName ConcentrationµM")
- **Drugs**: Ibuprofen, Vioxx, Troglitazone, Rosiglitazone
- **Wells**: 48 per drug (2 rows × 24 columns)

## Key Variables and Data Structures

### Stage 1 Result Structure
```python
Stage1Result
├── drugs: Dict[str, DrugStage1Result]
    └── DrugStage1Result
        ├── drug_name: str
        ├── plates: Dict[str, PlateResult]
        │   └── PlateResult
        │       └── concentrations: Dict[float, ConcentrationResult]
        │           └── ConcentrationResult
        │               └── wells: Dict[str, WellResult]
        │                   └── WellResult
        │                       └── segments: Dict[str, SegmentRecord]
        │                           └── SegmentRecord
        │                               ├── segment_key: str
        │                               ├── source_file: str
        │                               ├── completeness: float
        │                               └── data: pd.DataFrame
        └── has_baseline: bool
```

### DataFrame Columns (Stage 1 Output)
- **time_s**: Time in seconds (original)
- **oxygen_pct_air**: Oxygen percentage (0-100%)
- **snr**: Signal-to-noise ratio
- **amp1_vpp**: Amplitude 1 (Volts peak-to-peak)
- **amp2_vpp**: Amplitude 2 (Volts peak-to-peak)
- **abs_time**: Absolute timestamp
- **duration_hours**: Hours since experiment start
- **timeline_hour**: Hour label (0, 3, 7, 18, 24, 48, 72, 96...)

## Common Workflows

### Process Single Drug

```python
from pathlib import Path
from cdap import Stage1Config, run_stage1, Stage2Config, generate_stage2_tables

# Stage 1: Filter
config = Stage1Config(
    plate_roots=[Path("LogFiles/P1OxygenLogs")],
    save_raw=True
)
result = run_stage1(config, single_drug="Amiodarone")

# Stage 2: Aggregate
s2_config = Stage2Config()
generate_stage2_tables(stage1_result=result, single_drug="Amiodarone")
```

### Process All Drugs

```python
from pathlib import Path
from cdap import Stage1Config, run_stage1, generate_stage2_tables

# Process all plates
config = Stage1Config(
    plate_roots=[
        Path("LogFiles/P1OxygenLogs"),
        Path("LogFiles/P2OxygenLogs"),
        Path("LogFiles/P3OxygenLogs")
    ],
    save_raw=True
)

# Run for all drugs (don't specify single_drug)
result = run_stage1(config)
generate_stage2_tables(stage1_result=result)
```

### Apply Diameter Normalization

```python
from pathlib import Path
from cdap import Stage2Config, generate_stage2_tables

config = Stage2Config(
    apply_diameter_normalization=True,
    diameter_sources={
        "Plate1": Path("Diameters/organoids_only_results_plate1.csv"),
        "Plate2": Path("Diameters/organoids_only_results_plate2.csv")
    }
)
generate_stage2_tables(config=config, single_drug="Amiodarone")
```

### Custom Sparse Threshold

```python
from cdap import Stage3Config, load_stage2_to_prism

# Remove columns with < 70% data (more aggressive)
config = Stage3Config(min_fill_percent=70.0)
result = load_stage2_to_prism(config)
print(f"Removed {result.total_columns_removed} sparse columns")
```

## Command Line Usage

### Run Complete Pipeline
```bash
# Single drug
python run_complete_pipeline.py --drug Amiodarone --plates P1

# All drugs
python run_complete_pipeline.py --all

# Specific plates only
python run_complete_pipeline.py --all --plates P1 P2
```

### Individual Stages
```bash
# Stage 1 only
python -m cdap.stage1_filter --single-drug Amiodarone

# Stage 2 only
python -m cdap.stage2_tables --drug Amiodarone

# Stage 3 only
python -m cdap.stage3_prism --min-fill 60
```

## Integration with Other Skills

This skill integrates with:

- **dynamix-oxygen-log-interpreter**: Use for low-level log file parsing before Stage 1
- **Data visualization**: Use Stage 2 CSV outputs for custom plotting
- **Statistical analysis**: Use filtered DataFrames for advanced statistics
- **Timeline analysis**: Use timeline CSVs for temporal analysis

When combining workflows:
1. Use `dynamix-oxygen-log-interpreter` for raw log file exploration
2. Use `cdap-pipeline` for the main analysis workflow
3. Use Stage 1 or Stage 2 outputs for custom analysis

## Error Handling

### Common Issues and Solutions

**"No drug map found"**
- Ensure `P1DrugMap.csv`, `P2DrugMap.csv`, `P3DrugMap.csv` exist in LogFiles folder
- Check file names match exactly (case-sensitive)

**"All wells rejected in Stage 1"**
- Check SNR values in raw data (should be ≥ 2.0)
- For Plate 3: SNR is in column 12 ("probe signal : background")
- Try lowering SNR threshold if data is marginal:
  ```python
  config = Stage1Config(min_snr=1.4)  # More permissive
  ```

**"Stage 2 tables empty"**
- Verify Stage 1 completed successfully (check `Stage1_Raw/` folder)
- Ensure timeline CSV was generated
- Check processing notes in `[drug]_stage1_notes.txt`

**"No Stage 2 data found for drug" in Stage 3**
- Drug names must match between Prism file and `Stage2_Tables/` folder
- Drug name matching is case-insensitive and fuzzy
- Check that Stage 2 tables exist: `ls Stage2_Tables/[DrugName]/`

**"Permission denied" when saving Prism files**
- Close GraphPad Prism before running Stage 3
- Stage 3 will create timestamped fallback files if needed
- Check file permissions on `.pzfx` files

## Quality Filters and Thresholds

### Stage 1 Default Filters
```python
min_oxygen_pct = 2.0          # Exclude sensor errors
max_oxygen_pct = 80.0         # Exclude unrealistic values
min_snr = 2.0                 # Signal-to-noise threshold
min_segment_completeness = 0.5 # 50% valid rows minimum
```

### Alternative SNR Modes
```python
# Relaxed mode (SNR Low Rescue disabled)
config = Stage1Config(
    snr_critical_threshold=1.4,  # Below this is rejected
    snr_low_threshold=2.0,       # Between 1.4-2.0 is "low"
    process_snr_low=False        # Skip SNR low rescue
)

# Standard mode (SNR Low Rescue enabled)
config = Stage1Config(
    process_snr_low=True  # Apply special processing to 1.4-2.0 range
)
```

### Stage 2 Interpolation
```python
interpolate_limit = 1  # Fill gaps ≤ 1 hour
```

### Stage 3 Sparse Removal
```python
min_fill_percent = 60.0  # Remove columns with < 60% data
```

## Advanced Features

### Custom Timeline Hours
The pipeline uses predefined timeline hours:
```python
timeline_hours = [0, 3, 7, 18, 24, 48, 72, 96]
```

To modify, edit `cdap/config.py` or use custom processing.

### Frequency Analysis (FFT)
Stage 2 calculates dominant frequencies using FFT:
```python
from cdap.fft_tools import FFTConfig, dominant_frequency

# Configure FFT parameters
fft_config = FFTConfig(
    sample_rate_hz=1.0,     # 1 sample per second
    min_freq_hz=0.01,       # Min frequency of interest
    max_freq_hz=0.5         # Max frequency of interest
)

# Calculate dominant frequency
freq = dominant_frequency(signal_array, fft_config)
```

### Parallel Processing

```python
import concurrent.futures
from cdap import Stage1Config, run_stage1

drugs = ["Amiodarone", "Verapamil", "Dofetilide"]
config = Stage1Config()

with concurrent.futures.ProcessPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(run_stage1, config, drug) for drug in drugs]
    results = [f.result() for f in futures]
```

## Bundled Resources

### Scripts

**`scripts/run_pipeline.py`**: Helper script to run the complete pipeline

**`scripts/analyze_qc.py`**: Quality control analysis utilities

**`scripts/batch_process.py`**: Batch processing for multiple drugs

### References

**`references/pipeline_architecture.md`**: Complete pipeline architecture documentation

**`references/data_structures.md`**: Detailed data structure specifications

**`references/quality_control.md`**: Quality control guidelines and thresholds

**`references/troubleshooting.md`**: Comprehensive troubleshooting guide

## Performance Tips

- **Process specific drugs**: Much faster than `--all`
- **Skip Stage 1 if filtered**: Re-use existing filtered data with `--skip-stage1`
- **Disable backups**: Use `create_backups=False` in Stage 3 for speed
- **Parallel processing**: Run multiple drugs in parallel (see Advanced Features)

## Directory Structure

```
complete data analysis program/
├── cdap/                          # Main package
│   ├── stage1_filter.py          # Stage 1
│   ├── stage2_tables.py          # Stage 2
│   ├── stage3_prism.py           # Stage 3
│   ├── config.py                 # Configuration
│   ├── io_utils.py               # I/O utilities
│   ├── fft_tools.py              # FFT analysis
│   └── models.py                 # Data structures
├── LogFiles/                      # Raw data
│   ├── P1OxygenLogs/
│   ├── P2OxygenLogs/
│   ├── P3OxygenLogs/
│   ├── P1DrugMap.csv
│   ├── P2DrugMap.csv
│   └── P3DrugMap.csv
├── Stage1_Raw/                    # Stage 1 output
├── Stage2_Tables/                 # Stage 2 output
└── *.pzfx                         # Prism files (Stage 3)
```

## Examples

### Example 1: Single Drug, Complete Pipeline

```python
from pathlib import Path
from cdap import (
    Stage1Config, run_stage1,
    Stage2Config, generate_stage2_tables,
    Stage3Config, load_stage2_to_prism
)

# Complete pipeline for Amiodarone
drug = "Amiodarone"

# Stage 1
s1_config = Stage1Config(
    plate_roots=[Path("LogFiles/P1OxygenLogs")],
    save_raw=True
)
s1_result = run_stage1(s1_config, single_drug=drug)
print(f"Stage 1: Filtered {len(s1_result.drugs)} drugs")

# Stage 2
s2_config = Stage2Config()
generate_stage2_tables(stage1_result=s1_result, single_drug=drug)
print("Stage 2: Generated metrics tables")

# Stage 3
s3_config = Stage3Config(min_fill_percent=60.0)
s3_result = load_stage2_to_prism(s3_config)
print(f"Stage 3: Loaded {s3_result.total_tables_processed} tables to Prism")
```

### Example 2: Re-run Stage 2 with Different Settings

```python
from cdap import Stage2Config, generate_stage2_tables, stage1_filter

# Load existing Stage 1 result
s1_result = stage1_filter.LAST_STAGE1_RESULT

# Generate tables with diameter normalization
config = Stage2Config(
    apply_diameter_normalization=True,
    diameter_sources={
        "Plate1": Path("Diameters/organoids_only_results_plate1.csv")
    }
)
generate_stage2_tables(stage1_result=s1_result, config=config, single_drug="Amiodarone")
```

### Example 3: Batch Process All Drugs

```python
from pathlib import Path
from cdap import Stage1Config, run_stage1, generate_stage2_tables

# Process all plates and drugs
config = Stage1Config(
    plate_roots=[
        Path("LogFiles/P1OxygenLogs"),
        Path("LogFiles/P2OxygenLogs"),
        Path("LogFiles/P3OxygenLogs")
    ],
    save_raw=True,
    debug=False
)

# Run complete Stage 1 + 2
result = run_stage1(config)
generate_stage2_tables(stage1_result=result)
print("Batch processing complete!")
```

### Example 4: Custom Quality Control

```python
from cdap import Stage1Config, run_stage1

# Stricter filtering for high-quality data
config = Stage1Config(
    min_oxygen_pct=5.0,           # Tighter range
    max_oxygen_pct=75.0,
    min_snr=2.5,                  # Higher SNR
    min_segment_completeness=0.75, # 75% valid rows
    save_raw=True,
    debug=True                    # Enable debug outputs
)

result = run_stage1(config, single_drug="Amiodarone")
```

## Version History

- **v3.0** (2025): Complete Plate 3 integration
- **v2.0** (2024): Stage 3 Prism integration
- **v1.0** (2024): Initial Stage 1 & 2 pipeline

## Additional Documentation

- **Full Pipeline Guide**: `README_PIPELINE.md` in project root
- **Quick Reference**: `QUICK_REFERENCE.md` in project root
- **Prism Loading Guide**: `LOAD_PRISM_GUIDE.md` in project root
