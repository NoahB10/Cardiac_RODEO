# CDAP Usage Examples

Practical examples for working with log files using the CDAP modules.

## Table of Contents

1. [Basic Log File Loading](#basic-log-file-loading)
2. [Stage 1: Filtering](#stage-1-filtering)
3. [Stage 2: Metrics Calculation](#stage-2-metrics-calculation)
4. [Custom Analysis](#custom-analysis)
5. [Working with DataFrames](#working-with-dataframes)
6. [Quality Control](#quality-control)

## Basic Log File Loading

### Load a Single Well

```python
from cdap.io_utils import load_well_dataframe
from pathlib import Path

# Automatically detects Plate 1/2 (.log) or Plate 3 (.txt)
plate_dir = Path("LogFiles/P1OxygenLogs")
well_id = "A01"

df = load_well_dataframe(plate_dir, well_id)

print(f"Loaded {len(df)} rows for well {well_id}")
print(df.head())
```

### Discover Drug Assignments

```python
from cdap.io_utils import discover_drug_assignments
from pathlib import Path

# Discover all drugs across plates
plate_roots = [
    Path("LogFiles/P1OxygenLogs"),
    Path("LogFiles/P2OxygenLogs")
]

assignments = discover_drug_assignments(plate_roots)

for assignment in assignments:
    print(f"{assignment.drug} @ {assignment.concentration_mM}mM")
    print(f"  Plate: {assignment.plate_name}")
    print(f"  Wells: {assignment.wells}")
```

### Build Timestamp Series

```python
from cdap.io_utils import load_well_dataframe, build_timestamp_series
from pathlib import Path

df = load_well_dataframe(Path("LogFiles/P1OxygenLogs"), "A01")

# Extract absolute timestamps
timestamps = build_timestamp_series(df)

print(f"First measurement: {timestamps.iloc[0]}")
print(f"Last measurement: {timestamps.iloc[-1]}")
print(f"Duration: {timestamps.iloc[-1] - timestamps.iloc[0]}")
```

## Stage 1: Filtering

### Run Stage 1 for a Single Drug

```python
from cdap import Stage1Config, run_stage1
from pathlib import Path

config = Stage1Config(
    plate_roots=(Path("LogFiles/P1OxygenLogs"),),
    min_oxygen_pct=2.0,
    max_oxygen_pct=80.0,
    min_snr=2.0,
    save_raw=True
)

result = run_stage1(config, single_drug="Amiodarone")

# Access filtered data
drug_data = result.drugs["Amiodarone"]
print(f"Plates: {list(drug_data.plates.keys())}")
print(f"Has baseline: {drug_data.has_baseline}")
```

### Custom Filtering Thresholds

```python
from cdap import Stage1Config, run_stage1
from pathlib import Path

# Stricter filtering for high-quality data
config = Stage1Config(
    plate_roots=(Path("LogFiles/P1OxygenLogs"),),
    min_oxygen_pct=5.0,          # Tighter range
    max_oxygen_pct=75.0,
    min_snr=2.5,                 # Higher SNR
    min_segment_completeness=0.75 # 75% valid rows required
)

result = run_stage1(config, single_drug="Amiodarone")
```

### Access Filtered Segments

```python
from cdap import Stage1Config, run_stage1

config = Stage1Config()
result = run_stage1(config, single_drug="Amiodarone")

# Navigate to a specific well
drug = result.drugs["Amiodarone"]
plate = drug.plates["Plate1"]
conc = plate.concentrations[0.01]  # 0.01 mM
well = conc.wells["A01"]

# Iterate segments
for seg_key, segment in well.segments.items():
    print(f"Segment: {seg_key}")
    print(f"  Source: {segment.source_file}")
    print(f"  Completeness: {segment.completeness:.1%}")
    print(f"  Rows: {len(segment.data)}")
    print(f"  O2 range: {segment.data['oxygen_pct_air'].min():.1f} - {segment.data['oxygen_pct_air'].max():.1f}%")
```

### Iterate All Segments

```python
from cdap import run_stage1, Stage1Config

config = Stage1Config()
result = run_stage1(config)

# Iterate all segments across all drugs/plates/wells
for drug, plate, conc, well_id, seg_key, segment in result.iter_segments():
    df = segment.data
    mean_o2 = df["oxygen_pct_air"].mean()
    mean_snr = df["snr"].mean()

    print(f"{drug} | {well_id} | {seg_key}")
    print(f"  Mean O2: {mean_o2:.2f}%")
    print(f"  Mean SNR: {mean_snr:.2f}")
```

## Stage 2: Metrics Calculation

### Generate Metrics Tables

```python
from cdap import Stage1Config, run_stage1, Stage2Config, generate_stage2_tables
from pathlib import Path

# Run Stage 1
s1_config = Stage1Config()
s1_result = run_stage1(s1_config, single_drug="Amiodarone")

# Generate Stage 2 tables
s2_config = Stage2Config(output_root=Path("Stage2_Tables"))
generate_stage2_tables(stage1_result=s1_result, single_drug="Amiodarone")

# Tables will be in: Stage2_Tables/Amiodarone/
#   - O2_mean.csv
#   - O2_std.csv
#   - O2_dom_freq.csv
#   - Amp_std.csv
#   - Amp_dom_freq.csv
```

### Apply Diameter Normalization

```python
from cdap import Stage2Config, generate_stage2_tables
from pathlib import Path

config = Stage2Config(
    apply_diameter_normalization=True,
    diameter_sources={
        "Plate1": Path("Diameters/organoids_only_results_plate1.csv"),
        "Plate2": Path("Diameters/organoids_only_results_plate2.csv")
    }
)

# Requires Stage 1 result
from cdap import stage1_filter
s1_result = stage1_filter.LAST_STAGE1_RESULT

generate_stage2_tables(stage1_result=s1_result, config=config, single_drug="Amiodarone")
```

### Read Stage 2 Tables

```python
import pandas as pd
import numpy as np

# Load O2 mean table
df = pd.read_csv("Stage2_Tables/Amiodarone/O2_mean.csv")

# Get timeline hours
hours = df["Hour"].values

# Get all concentration/replicate columns
data_columns = [col for col in df.columns if col != "Hour"]

# Extract concentration from column name (e.g., "0.01mM_1" → 0.01)
concentrations = []
for col in data_columns:
    conc_str = col.split("mM")[0]
    concentrations.append(float(conc_str))

unique_concentrations = sorted(set(concentrations))
print(f"Concentrations: {unique_concentrations}")

# Get data for a specific concentration
conc_0p01_cols = [col for col in data_columns if col.startswith("0.01mM")]
conc_0p01_data = df[conc_0p01_cols].values

print(f"0.01mM data shape: {conc_0p01_data.shape}")  # (time_points, replicates)
```

## Custom Analysis

### Calculate Custom Metrics

```python
from cdap import Stage1Config, run_stage1
import numpy as np

config = Stage1Config()
result = run_stage1(config, single_drug="Amiodarone")

# Calculate custom metric: O2 coefficient of variation
for drug, plate, conc, well_id, seg_key, segment in result.iter_segments():
    df = segment.data
    o2_mean = df["oxygen_pct_air"].mean()
    o2_std = df["oxygen_pct_air"].std()
    o2_cv = (o2_std / o2_mean) * 100 if o2_mean > 0 else np.nan

    print(f"{drug} | {well_id} | {seg_key}")
    print(f"  O2 CV: {o2_cv:.2f}%")
```

### Extract Time Series for Plotting

```python
from cdap import Stage1Config, run_stage1
import matplotlib.pyplot as plt

config = Stage1Config()
result = run_stage1(config, single_drug="Amiodarone")

# Get all segments for a specific well
drug = result.drugs["Amiodarone"]
plate = drug.plates["Plate1"]
conc = plate.concentrations[0.01]
well = conc.wells["A01"]

# Combine all segments
all_times = []
all_o2 = []

for seg_key, segment in sorted(well.segments.items()):
    df = segment.data
    all_times.extend(df["abs_time"].values)
    all_o2.extend(df["oxygen_pct_air"].values)

# Plot
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(all_times, all_o2, linewidth=0.5)
ax.set_xlabel("Time")
ax.set_ylabel("O2 (% air)")
ax.set_title(f"Amiodarone 0.01mM - Well A01")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("amiodarone_timeseries.png", dpi=300)
```

### Calculate Dominant Frequency Manually

```python
from cdap.fft_tools import FFTConfig, dominant_frequency
import numpy as np

# Get oxygen time series
o2_values = np.array(all_o2)

# Configure FFT
fft_config = FFTConfig(
    sample_rate_hz=1.0,      # 1 sample per second
    min_freq_hz=0.01,        # 0.01 Hz = 1 cycle per 100 seconds
    max_freq_hz=0.5          # 0.5 Hz = 1 cycle per 2 seconds
)

# Calculate dominant frequency
dom_freq = dominant_frequency(o2_values, fft_config)

print(f"Dominant frequency: {dom_freq:.4f} Hz")
print(f"Period: {1/dom_freq:.1f} seconds" if dom_freq > 0 else "No dominant frequency")
```

### Compare Concentrations

```python
from cdap import Stage1Config, run_stage1
import numpy as np
import matplotlib.pyplot as plt

config = Stage1Config()
result = run_stage1(config, single_drug="Amiodarone")

drug = result.drugs["Amiodarone"]
plate = drug.plates["Plate1"]

# Calculate mean O2 for each concentration
concentration_means = {}

for conc_val, conc_result in plate.concentrations.items():
    all_o2 = []

    for well_id, well in conc_result.wells.items():
        for seg_key, segment in well.segments.items():
            all_o2.extend(segment.data["oxygen_pct_air"].values)

    if all_o2:
        concentration_means[conc_val] = np.mean(all_o2)

# Plot dose-response
concentrations = sorted(concentration_means.keys())
means = [concentration_means[c] for c in concentrations]

plt.figure(figsize=(10, 6))
plt.plot(concentrations, means, marker='o', linewidth=2, markersize=8)
plt.xscale('log')
plt.xlabel("Concentration (mM)")
plt.ylabel("Mean O2 (% air)")
plt.title("Amiodarone Dose-Response")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("dose_response.png", dpi=300)
```

## Working with DataFrames

### Filter by Timeline Hour

```python
from cdap import Stage1Config, run_stage1

config = Stage1Config()
result = run_stage1(config, single_drug="Amiodarone")

# Get data for a specific timeline hour
for drug, plate, conc, well_id, seg_key, segment in result.iter_segments():
    df = segment.data

    # Filter to hour 24
    hour_24 = df[df["timeline_hour"] == 24]

    if not hour_24.empty:
        mean_o2 = hour_24["oxygen_pct_air"].mean()
        print(f"{well_id} @ hour 24: {mean_o2:.2f}% O2")
```

### Calculate Statistics per Segment

```python
from cdap import Stage1Config, run_stage1
import pandas as pd

config = Stage1Config()
result = run_stage1(config, single_drug="Amiodarone")

stats_list = []

for drug, plate, conc, well_id, seg_key, segment in result.iter_segments():
    df = segment.data

    stats = {
        "drug": drug,
        "plate": plate,
        "concentration": conc,
        "well": well_id,
        "segment": seg_key,
        "n_rows": len(df),
        "completeness": segment.completeness,
        "o2_mean": df["oxygen_pct_air"].mean(),
        "o2_std": df["oxygen_pct_air"].std(),
        "o2_min": df["oxygen_pct_air"].min(),
        "o2_max": df["oxygen_pct_air"].max(),
        "snr_mean": df["snr"].mean(),
        "snr_min": df["snr"].min()
    }

    stats_list.append(stats)

# Create summary DataFrame
summary_df = pd.DataFrame(stats_list)
summary_df.to_csv("segment_statistics.csv", index=False)

print(summary_df.describe())
```

## Quality Control

### Check Data Quality

```python
from cdap import Stage1Config, run_stage1

config = Stage1Config()
result = run_stage1(config, single_drug="Amiodarone")

print("Quality Control Report")
print("=" * 60)

for drug, plate, conc, well_id, seg_key, segment in result.iter_segments():
    df = segment.data

    # Check completeness
    if segment.completeness < 0.6:
        print(f"⚠ Low completeness: {well_id} {seg_key} ({segment.completeness:.1%})")

    # Check SNR
    low_snr_pct = (df["snr"] < 2.0).sum() / len(df)
    if low_snr_pct > 0.2:
        print(f"⚠ High low-SNR fraction: {well_id} {seg_key} ({low_snr_pct:.1%})")

    # Check oxygen range
    if df["oxygen_pct_air"].max() > 90:
        print(f"⚠ Unrealistic O2: {well_id} {seg_key} (max={df['oxygen_pct_air'].max():.1f}%)")
```

### Count Valid Data Points

```python
from cdap import Stage1Config, run_stage1

config = Stage1Config()
result = run_stage1(config)

total_rows = 0
valid_rows = 0

for drug, plate, conc, well_id, seg_key, segment in result.iter_segments():
    # Each segment already has filtered data
    segment_rows = len(segment.data)

    # Estimate original rows based on completeness
    original_rows = segment_rows / segment.completeness if segment.completeness > 0 else 0

    total_rows += original_rows
    valid_rows += segment_rows

print(f"Total rows (estimated): {total_rows:,.0f}")
print(f"Valid rows after filtering: {valid_rows:,.0f}")
print(f"Rejection rate: {(1 - valid_rows/total_rows)*100:.1f}%")
```

### Identify Problematic Wells

```python
from cdap import Stage1Config, run_stage1

config = Stage1Config()
result = run_stage1(config)

# Track completeness by well
well_completeness = {}

for drug, plate, conc, well_id, seg_key, segment in result.iter_segments():
    key = f"{drug}_{plate}_{well_id}"

    if key not in well_completeness:
        well_completeness[key] = []

    well_completeness[key].append(segment.completeness)

# Calculate average completeness
print("Wells with low completeness:")
print("-" * 60)

for key, completeness_list in sorted(well_completeness.items()):
    avg_completeness = sum(completeness_list) / len(completeness_list)

    if avg_completeness < 0.7:
        print(f"{key}: {avg_completeness:.1%} (n={len(completeness_list)} segments)")
```

## Tips and Best Practices

1. **Always check data quality** after Stage 1 filtering
2. **Use debug mode** when developing: `Stage1Config(debug=True)`
3. **Save raw files** for inspection: `Stage1Config(save_raw=True)`
4. **Iterate segments** efficiently using `result.iter_segments()`
5. **Check completeness** before analyzing segments
6. **Use pandas** for advanced DataFrame operations
7. **Combine segments** carefully when analyzing time series
8. **Validate timestamps** are continuous across segments
