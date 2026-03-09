# CDAP Data Structures Reference

This document describes the data structures used throughout the CDAP pipeline.

## Stage 1 Data Structures

### SegmentRecord

Represents a single log file after Stage 1 filtering.

```python
@dataclass
class SegmentRecord:
    segment_key: str          # Unique identifier (e.g., "0-3h", "3-7h")
    source_file: str          # Original log file path
    completeness: float       # Fraction of valid rows (0.0-1.0)
    data: pd.DataFrame        # Filtered data
```

**DataFrame columns**:
- `time_s`: Time in seconds (original from log file)
- `oxygen_pct_air`: Oxygen percentage (0-100%)
- `snr`: Signal-to-noise ratio
- `amp1_vpp`: Amplitude 1 (Volts peak-to-peak)
- `amp2_vpp`: Amplitude 2 (Volts peak-to-peak)
- `abs_time`: Absolute timestamp (pandas Timestamp)
- `duration_hours`: Hours since experiment start
- `timeline_hour`: Hour label (0, 3, 7, 18, 24, 48, 72, 96...)

### WellResult

All Stage 1 segments for a single well.

```python
@dataclass
class WellResult:
    well_id: str                              # e.g., "A01", "B12"
    segments: Dict[str, SegmentRecord]        # Keyed by segment_key
```

### ConcentrationResult

All wells at the same drug concentration.

```python
@dataclass
class ConcentrationResult:
    concentration_mM: float                   # Concentration in mM
    level_index: int                          # Index in concentration series
    wells: Dict[str, WellResult]              # Keyed by well_id
```

### PlateResult

All concentrations from a single plate.

```python
@dataclass
class PlateResult:
    plate_name: str                           # e.g., "Plate1", "Plate2"
    concentrations: Dict[float, ConcentrationResult]  # Keyed by concentration_mM
```

### DrugStage1Result

Complete Stage 1 results for a single drug (may span multiple plates).

```python
@dataclass
class DrugStage1Result:
    drug_name: str                            # e.g., "Amiodarone", "Verapamil"
    plates: Dict[str, PlateResult]            # Keyed by plate_name
    has_baseline: bool                        # True if timeline hour 0 is baseline
```

### Stage1Result

Top-level container returned by `run_stage1()`.

```python
@dataclass
class Stage1Result:
    drugs: Dict[str, DrugStage1Result]        # Keyed by drug_name

    def iter_segments(self):
        """Yield (drug_name, plate_name, concentration, well_id, seg_key, segment) tuples."""
        ...
```

## Configuration Objects

### Stage1Config

Runtime options for Stage 1 filtering.

```python
@dataclass
class Stage1Config:
    # Data sources
    plate_roots: Tuple[Path, ...]            # List of plate directories

    # Filtering thresholds
    min_oxygen_pct: float = 2.0              # Min oxygen %
    max_oxygen_pct: float = 80.0             # Max oxygen %
    min_snr: float = 2.0                     # Min signal-to-noise ratio
    min_segment_completeness: float = 0.50   # Min fraction valid rows

    # Alternative SNR thresholds
    snr_critical_threshold: float = 1.4      # SNR below this is critical
    snr_low_threshold: float = 2.0           # SNR between critical and this is low
    process_snr_low: bool = True             # Enable SNR low rescue

    # Duration handling
    maximum_duration_hours: float = 96.0     # Max experiment duration
    duration_grace_hours: float = 1.0        # Grace period beyond max
    duration_slot_hours: float = 3.0         # Hour slot size
    align_baseline_by_drug: bool = True      # Use single baseline per drug

    # Output toggles
    debug: bool = False                      # Enable debug outputs
    save_raw: bool = True                    # Export filtered CSVs
    write_timeline_csv: bool = True          # Write timeline tables

    # Output locations
    output_root: Path                        # Reserved for Stage 2/3
    debug_root: Path                         # Debug outputs
    raw_export_root: Path                    # Filtered CSV exports
    timeline_root: Path                      # Timeline CSV exports
```

### Stage2Config

Runtime options for Stage 2 aggregation.

```python
@dataclass
class Stage2Config:
    output_root: Path = Path("Stage2_Tables")
    interpolate_limit: int = 1               # Max gap hours to interpolate
    apply_diameter_normalization: bool = False
    diameter_sources: Dict[str, Path] = None # Plate name → diameter file path
```

### Stage3Config

Runtime options for Stage 3 Prism loading.

```python
@dataclass
class Stage3Config:
    stage2_root: Path = Path("Stage2_Tables")
    min_fill_percent: float = 60.0           # Sparse column threshold
    create_backups: bool = True              # Backup .pzfx files
    prism_files: Dict[str, str] = None       # Custom file mapping
```

## Drug Assignment Structure

Used internally for drug discovery.

```python
@dataclass
class DrugAssignment:
    drug: str                                # Drug name
    concentration_mM: float                  # Concentration in mM
    level_index: int                         # Index in series
    plate_name: str                          # Plate identifier
    plate_logs_dir: Path                     # Log files directory
    wells: List[str]                         # Well IDs (e.g., ["A01", "A02"])
```

## Stage 2 Output Format

Stage 2 generates CSV tables with this structure:

### Table Structure
```
Hour,     0.0mM_1, 0.0mM_2, 0.01mM_1, 0.01mM_2, ...
0,        15.2,    15.8,    14.9,     15.1,     ...
3,        14.8,    15.3,    13.2,     12.9,     ...
7,        14.5,    15.1,    11.8,     11.2,     ...
18,       14.2,    14.9,    10.5,     9.8,      ...
...
```

**Column format**: `{concentration}mM_{replicate}`
- First row: Timeline hour labels
- Subsequent rows: Metric values (mean, std, frequency, etc.)

### Metric Files
- `O2_mean.csv`: Average oxygen percentage
- `O2_std.csv`: Oxygen standard deviation
- `O2_dom_freq.csv`: Dominant frequency (Hz) from FFT
- `Amp_std.csv`: Amplitude standard deviation
- `Amp_dom_freq.csv`: Beating frequency (Hz)

## Timeline Structure

Timeline CSVs map timestamps to hour labels.

```csv
Hour,A01,A02,B01,B02,...
0,2024-01-15 10:00:00,2024-01-15 10:01:23,2024-01-15 10:00:45,...
3,2024-01-15 13:02:15,2024-01-15 13:03:01,2024-01-15 13:01:52,...
7,2024-01-15 17:05:33,2024-01-15 17:06:12,2024-01-15 17:04:58,...
...
```

## Usage Examples

### Access Stage 1 Data

```python
from cdap import run_stage1, Stage1Config
from pathlib import Path

config = Stage1Config()
result = run_stage1(config, single_drug="Amiodarone")

# Access specific drug
drug_result = result.drugs["Amiodarone"]

# Access specific plate
plate_result = drug_result.plates["Plate1"]

# Access specific concentration
conc_result = plate_result.concentrations[0.01]  # 0.01 mM

# Access specific well
well_result = conc_result.wells["A01"]

# Access specific segment
segment = well_result.segments["0-3h"]

# Get DataFrame
df = segment.data
print(df.head())
```

### Iterate All Segments

```python
result = run_stage1(config)

for drug, plate, conc, well, seg_key, segment in result.iter_segments():
    print(f"{drug} | {plate} | {conc}mM | {well} | {seg_key}")
    print(f"  Completeness: {segment.completeness:.1%}")
    print(f"  Rows: {len(segment.data)}")
```

### Extract Time Series

```python
# Get oxygen time series for a well
well_result = result.drugs["Amiodarone"].plates["Plate1"].concentrations[0.01].wells["A01"]

all_oxygen = []
all_timestamps = []

for seg_key, segment in well_result.segments.items():
    all_oxygen.extend(segment.data["oxygen_pct_air"].values)
    all_timestamps.extend(segment.data["abs_time"].values)

# Plot
import matplotlib.pyplot as plt
plt.plot(all_timestamps, all_oxygen)
plt.xlabel("Time")
plt.ylabel("O2 (%)")
plt.title("Amiodarone 0.01mM - Well A01")
plt.show()
```

### Access Stage 2 Tables

```python
import pandas as pd

# Load O2 mean table
df = pd.read_csv("Stage2_Tables/Amiodarone/O2_mean.csv")

# First column is 'Hour'
hours = df["Hour"].values

# Other columns are wells at different concentrations
well_columns = [col for col in df.columns if col != "Hour"]

# Get data for a specific concentration/replicate
conc_0p01_rep1 = df["0.01mM_1"].values
```

## Data Flow Diagram

```
Raw Log Files (.log, .txt)
    ↓
[Stage 1: run_stage1()]
    ↓
Stage1Result
    ├── drugs: Dict[str, DrugStage1Result]
    │   └── plates: Dict[str, PlateResult]
    │       └── concentrations: Dict[float, ConcentrationResult]
    │           └── wells: Dict[str, WellResult]
    │               └── segments: Dict[str, SegmentRecord]
    │                   └── data: pd.DataFrame
    ↓
[Stage 2: generate_stage2_tables()]
    ↓
CSV Tables (Stage2_Tables/)
    ├── O2_mean.csv
    ├── O2_std.csv
    ├── O2_dom_freq.csv
    ├── Amp_std.csv
    └── Amp_dom_freq.csv
    ↓
[Stage 3: load_stage2_to_prism()]
    ↓
Prism Files (.pzfx)
    ├── Average_Oxygen.pzfx
    ├── Dominant_frequency_Oxygen.pzfx
    └── ...
```
