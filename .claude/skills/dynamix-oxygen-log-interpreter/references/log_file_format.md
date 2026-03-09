# Dynamix Oxygen Log File Format

## Overview

Dynamix oxygen log files contain time-series measurements from oxygen sensors. The files come in two formats:
- **Plate 1-2 format**: `.log` files
- **Plate 3 format**: `.txt` files (Wells A-H)

## File Structure

### Header Section
- Contains metadata including start datetime
- Plate 3 format: `DD.MM.YYYY HH:MM:SS` (e.g., "24.1.2024 9:45:01")
- May contain other metadata lines

### Data Section
Starts with a header line containing column names:
```
time / s	O2 content / % air	tau / µs	temp / °C	O2 content / % vol	phase1 / °	phase2 / °	amp0 / Vpp	amp1 / Vpp	amp2 / Vpp	amp3 / Vpp	probe signal : background
```

### Data Columns

1. **time_s**: Time in seconds (relative to start_datetime)
2. **oxygen_pct_air**: Oxygen content as percentage of air (0-100%)
3. **tau_us**: Lifetime in microseconds
4. **temp_c**: Temperature in Celsius
5. **oxygen_pct_vol**: Oxygen content as percentage by volume
6. **phase1_deg**: Phase 1 in degrees
7. **phase2_deg**: Phase 2 in degrees
8. **amp0_vpp**: Amplitude 0 (Volts peak-to-peak)
9. **amp1_vpp**: Amplitude 1 (Volts peak-to-peak)
10. **amp2_vpp**: Amplitude 2 (Volts peak-to-peak)
11. **amp3_vpp**: Amplitude 3 (Volts peak-to-peak)
12. **snr**: Signal-to-noise ratio (probe signal : background)

## Well Position to Well ID Mapping

**384-Well Plate Format (16 rows × 24 columns):**

Position numbers (1-384) map to well IDs using this formula:
- Row = A-P (calculated as: (position-1) // 24)
- Column = 1-24 (calculated as: ((position-1) % 24) + 1)

**Mapping Examples:**
- Position 1-24 → A1-A24 (Row A)
- Position 25-48 → B1-B24 (Row B)
- Position 49-72 → C1-C24 (Row C)
- ...
- Position 361-384 → P1-P24 (Row P)

**Specific Examples:**
- Position 1 → A1
- Position 24 → A24
- Position 25 → B1
- Position 48 → B24
- Position 384 → P24

## Well ID Extraction from Filenames

Well IDs can also be extracted from filenames using pattern matching:
- Pattern: `[A-P][1-24]` (e.g., A01, B12, P24)
- Examples:
  - `A01.log` → well_id: "A01"
  - `logfile_B12.txt` → well_id: "B12"
  - `A01_20240124.log` → well_id: "A01"

## Timestamp Calculation

Absolute timestamps are calculated as:
```
measurement_time = start_datetime + time_s (as timedelta)
```

Where `start_datetime` is extracted from the file header.

## Data Quality Considerations

### Valid Oxygen Range
- Typical valid range: 0-80% air
- Error value: -100 (should be filtered out)
- Out-of-range values may indicate sensor issues

### SNR Thresholds
- Typical valid SNR: ≥ 2.0
- Low SNR (< 2.0): Marginal quality, may need filtering
- Critical SNR (< 1.4): Poor quality, should be filtered

### Filtering Recommendations
- Filter oxygen: `0.0 <= oxygen_pct_air <= 80.0` and `oxygen_pct_air != -100.0`
- Filter SNR: `snr >= 2.0` (or custom threshold)
- Apply both filters for high-quality data

## File Naming Conventions

### Plate 1-2
- Format: `{well_id}*.log`
- Example: `A01.log`, `B12_20240124.log`

### Plate 3
- Format: `{well_id}*.txt` or `*{well_id}*.txt`
- Example: `A01.txt`, `logfile_A01.txt`, `A01_measurement.txt`

## Batch Processing

When processing multiple files:
- Files are sorted alphabetically
- DataFrames are concatenated with `ignore_index=True`
- Well IDs are extracted from each filename
- Combined DataFrame includes all measurements with metadata columns

