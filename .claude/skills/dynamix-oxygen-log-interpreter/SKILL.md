---
name: dynamix-oxygen-log-interpreter
description: Extract and process data from Dynamix oxygen log files (.log and .txt formats). Use this skill when working with Dynamix oxygen sensor log files to extract measurements including oxygen percentage, SNR, amplitude values, timestamps, well IDs, contractility, and heart rate. Supports both single file and batch processing, with optional filtering by O2 range and SNR thresholds. Includes signal processing for contractility and heart rate extraction using bandpass filtering, harmonic doubling detection, and half-power bandwidth analysis. Returns data as pandas DataFrames, CSV files, or dictionaries with intuitive variable names (oxygen_pct_air, snr, amp0_vpp, amp1_vpp, start_datetime, measurement_time, well_id, contractility, heart_rate_bpm). Always use this skill when extracting data from Dynamix log files in any context.
---

# Dynamix Oxygen Log Interpreter

Extract and process data from Dynamix oxygen log files with standardized variable names and flexible output formats.

## When to Use This Skill

Use this skill whenever you need to:
- Extract data from Dynamix oxygen log files (.log or .txt)
- Parse single log files or batch process multiple files
- Access oxygen measurements, SNR, amplitude, timestamps, or well IDs
- Convert log files to DataFrames, CSV files, or dictionaries
- Filter data by O2 range or SNR thresholds

**Always reference this skill when working with Dynamix log files**, even when integrating with other skills or workflows.

## Quick Start

When this skill loads, you'll see the base directory path. Use it to access bundled resources:
- Scripts: `{base_directory}/scripts/parse_log_file.py`
- References: `{base_directory}/references/log_file_format.md`

### Single File Processing

```python
# Import from the scripts directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from parse_log_file import parse_single_log

# Parse a single log file
result = parse_single_log('path/to/A01.log')

# Access data
df = result['dataframe']
well_id = result['well_id']
oxygen = result['oxygen_pct_air']
snr = result['snr']
timestamps = result['measurement_time']
```

### Batch Processing

```python
# Import from the scripts directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from parse_log_file import parse_batch_logs

# Process all log files in a directory
results = parse_batch_logs('path/to/logs/', well_id='A01')

# Access combined data
combined_df = results['combined_dataframe']
summary = results['summary']
```

## Key Variables

The skill extracts these standardized variables:

- **oxygen_pct_air**: Oxygen content as percentage of air (0-100%)
- **snr**: Signal-to-noise ratio
- **amp0_vpp**: Amplitude 0 (Volts peak-to-peak)
- **amp1_vpp**: Amplitude 1 (Volts peak-to-peak)
- **start_datetime**: pandas Timestamp of measurement start
- **start_date**: Date string (YYYY-MM-DD)
- **measurement_time**: Series of absolute timestamps
- **well_id**: Well identifier (e.g., 'A01', 'B12')
- **contractility**: Standard deviation of the dominant frequency (extracted via signal processing)
- **heart_rate_bpm**: Heart rate in beats per minute (dominant frequency × 60)

## Contractility and Heart Rate Extraction

This skill includes advanced signal processing methods to extract **contractility** and **heart rate** from amplitude data (amp1_vpp).

### Methodology Overview

The extraction process uses frequency-domain analysis with the following pipeline:

1. **Extract Measurement Interval**: Parse file header (line 4) to get true sampling rate
2. **Data Cleaning**: Remove initial erroneous measurements (typically first 5 rows)
3. **Wide Bandpass Filtering**: Apply 0.5-2.0 Hz filter to isolate cardiac frequency range
4. **Dominant Frequency Detection**: Use Welch's method with extracted sampling rate
5. **Harmonic Doubling Check**: Detect and correct frequency doubling artifacts
6. **Half-Power Bandwidth**: Calculate adaptive bandwidth around dominant frequency
7. **Narrow Bandpass Filtering**: Apply tight filter for clean signal extraction
8. **Contractility Calculation**: Compute standard deviation of dominant frequency

### Critical: Measurement Interval Extraction

**IMPORTANT:** Always extract the measurement interval from the file header (line 4), not from time differences in the data!

File header line 4 format:
```
time interval / ms = 100	measurement time / ms = 100
```

This tells you:
- **Time interval**: 100 ms between measurements
- **Sampling rate**: 1000 / 100 = 10 Hz

**Why this matters:**
- Files with 1000ms intervals → 1 Hz sampling → insufficient for heart rate analysis
- Files with 100ms intervals → 10 Hz sampling → suitable for cardiac frequency analysis (0.5-2.0 Hz range)
- Computing sampling rate from time differences can be inaccurate due to irregular timing

**Implementation:**
```python
import re

def extract_measurement_interval(log_path):
    """Extract measurement interval from file header."""
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # Line 4 (index 3) contains measurement interval
    line4 = lines[3]
    match = re.search(r'time interval / ms = (\d+)', line4)

    if match:
        interval_ms = int(match.group(1))
        sampling_rate_hz = 1000.0 / interval_ms
        return interval_ms, sampling_rate_hz

    return None, None
```

### Data Quality Requirements

For valid heart rate analysis, require:
- **Minimum measurements**: 20 (after skipping first 5 and last 1)
- **Minimum sampling rate**: 2 Hz (500ms interval or less)
- **Recommended**: 10 Hz (100ms interval) for cardiac frequencies

Files with insufficient data should be flagged as `INSUFFICIENT_DATA` rather than returning invalid results.

### Signal Processing Functions

#### 1. Bandpass Filtering (Wide: 0.5-2.0 Hz)

Uses FFT to filter amplitude signal and remove low-frequency drift and high-frequency noise:

```python
from scipy.fft import fft, ifft, fftfreq
import numpy as np

def bandpass_filter_signal(time_s, signal, freq_band=(0.5, 2.0)):
    """
    Apply bandpass filter in frequency domain via FFT.

    Args:
        time_s: Time array in seconds
        signal: Amplitude signal (amp1_vpp)
        freq_band: (low_freq, high_freq) in Hz

    Returns:
        Filtered signal in time domain
    """
    # Detrend signal
    signal_detrended = signal - np.nanmean(signal)

    # Sort by time
    order = np.argsort(time_s)
    time_sorted = time_s[order]
    signal_sorted = signal_detrended[order]

    # Compute sampling rate from median time difference
    dt = np.median(np.diff(time_sorted))

    # FFT
    signal_fft = fft(signal_sorted)
    freqs = fftfreq(len(signal_sorted), dt)

    # Create bandpass mask
    freq_mask = (np.abs(freqs) >= freq_band[0]) & (np.abs(freqs) <= freq_band[1])

    # Zero out frequencies outside band
    signal_fft_filtered = signal_fft.copy()
    signal_fft_filtered[~freq_mask] = 0

    # Inverse FFT to get cleaned signal
    signal_cleaned = np.real(ifft(signal_fft_filtered))

    return signal_cleaned
```

#### 2. Dominant Frequency Detection

Uses Welch's method for robust power spectral density (PSD) estimation with extracted sampling rate:

```python
from scipy.signal import welch

def compute_dominant_frequency(time_s, signal, sampling_rate_hz, freq_band=(0.5, 2.0)):
    """
    Compute dominant frequency using Welch's method.

    Args:
        time_s: Time array
        signal: Amplitude signal
        sampling_rate_hz: Sampling rate in Hz (from file header)
        freq_band: Frequency search range

    Returns:
        dominant_freq: Peak frequency in Hz
        freqs: Frequency array from Welch
        power: Power spectral density
    """
    # Detrend and sort
    signal_detrended = signal - np.nanmean(signal)
    order = np.argsort(time_s)
    signal_sorted = signal_detrended[order]

    # Use extracted sampling rate (NOT computed from time differences!)
    fs = sampling_rate_hz

    # Welch's PSD
    freqs, power = welch(signal_sorted, fs=fs, nperseg=min(256, len(signal_sorted)))

    # Find peak in frequency band
    band_mask = (freqs >= freq_band[0]) & (freqs <= freq_band[1])
    band_freqs = freqs[band_mask]
    band_power = power[band_mask]

    dominant_freq = band_freqs[np.argmax(band_power)]

    return dominant_freq, freqs, power
```

#### 3. Harmonic Doubling Detection

Checks if detected frequency is a doubled harmonic and corrects if needed:

```python
def detect_harmonic_doubling(time_s, signal, detected_freq, freq_band=(0.5, 2.0)):
    """
    Check if detected frequency is a harmonic double.

    Returns:
        corrected_freq: Frequency after doubling check
        was_corrected: Boolean indicating if correction was applied
    """
    # Get power spectrum
    signal_detrended = signal - np.nanmean(signal)
    order = np.argsort(time_s)
    signal_sorted = signal_detrended[order]
    time_sorted = time_s[order]

    dt = np.median(np.diff(time_sorted))
    freqs, power = welch(signal_sorted, fs=1.0/dt, nperseg=min(256, len(signal_sorted)))

    # Find power at detected frequency
    peak_mask = (freqs >= detected_freq - 0.05) & (freqs <= detected_freq + 0.05)
    peak_power = np.max(power[peak_mask])

    # Check half-frequency power
    half_freq = detected_freq / 2.0
    if half_freq >= freq_band[0]:
        half_mask = (freqs >= half_freq - 0.05) & (freqs <= half_freq + 0.05)
        half_power = np.max(power[half_mask])

        # If half-frequency has >70% of peak power, it's the true fundamental
        if half_power / peak_power > 0.7:
            return half_freq, True

    return detected_freq, False
```

#### 4. Half-Power Bandwidth Calculation

Calculates adaptive bandwidth around dominant frequency:

```python
def get_half_power_bandwidth(time_s, signal, peak_freq, freq_band=(0.5, 2.0)):
    """
    Calculate bandwidth based on half-power (-3dB) points.

    Returns:
        bandwidth: Half-power bandwidth in Hz (clamped to 0.05-1.0 Hz)
    """
    signal_detrended = signal - np.nanmean(signal)
    order = np.argsort(time_s)
    signal_sorted = signal_detrended[order]
    time_sorted = time_s[order]

    dt = np.median(np.diff(time_sorted))
    freqs, power = welch(signal_sorted, fs=1.0/dt, nperseg=min(256, len(signal_sorted)))

    # Find peak power
    peak_mask = (freqs >= peak_freq - 0.1) & (freqs <= peak_freq + 0.1)
    peak_power = np.max(power[peak_mask])
    half_power = peak_power / 2.0

    # Find frequencies at half-power
    half_power_mask = (freqs >= freq_band[0]) & (freqs <= freq_band[1]) & (power >= half_power)
    freqs_at_half_power = freqs[half_power_mask]

    # Bandwidth is half the span (radius from center)
    bandwidth = (np.max(freqs_at_half_power) - np.min(freqs_at_half_power)) / 2.0

    # Clamp to reasonable range
    bandwidth = np.clip(bandwidth, 0.05, 1.0)

    return bandwidth
```

#### 5. Narrow Bandpass Filtering

Applies tight FFT mask around dominant frequency:

```python
def narrow_bandpass_around_peak(time_s, signal, peak_freq, bandwidth=0.2):
    """
    Apply narrow bandpass centered on dominant frequency.

    Args:
        time_s: Time array
        signal: Amplitude signal
        peak_freq: Center frequency
        bandwidth: ±bandwidth around center

    Returns:
        Narrowly filtered signal
    """
    signal_detrended = signal - np.nanmean(signal)
    order = np.argsort(time_s)
    signal_sorted = signal_detrended[order]
    time_sorted = time_s[order]

    dt = np.median(np.diff(time_sorted))

    signal_fft = fft(signal_sorted)
    freqs = fftfreq(len(signal_sorted), dt)

    # Tight frequency mask
    freq_mask = (np.abs(freqs) >= peak_freq - bandwidth) & (np.abs(freqs) <= peak_freq + bandwidth)

    signal_fft_filtered = signal_fft.copy()
    signal_fft_filtered[~freq_mask] = 0

    signal_cleaned = np.real(ifft(signal_fft_filtered))

    return signal_cleaned
```

### Complete Extraction Pipeline

To extract contractility and heart rate from a log file:

```python
# 1. Extract measurement interval from file header
interval_ms, sampling_rate_hz = extract_measurement_interval('A01.log')

if sampling_rate_hz is None:
    print("ERROR: Could not extract sampling rate from header")
    return

# 2. Parse log file
result = parse_single_log('A01.log')
df = result['dataframe']

# 3. Remove initial bad measurements (first 5 rows)
df_cleaned = df.iloc[5:-1].reset_index(drop=True)  # Skip first 5 and last 1

# 4. Check data quality
if len(df_cleaned) < 20:
    print(f"INSUFFICIENT_DATA: Only {len(df_cleaned)} measurements (need 20+)")
    return

# 5. Extract time and amplitude
time_s = df_cleaned['time_s'].values
signal = df_cleaned['amp1_vpp'].values

# 6. Apply wide bandpass filter (0.5-2.0 Hz)
signal_filtered = bandpass_filter_signal(time_s, signal, freq_band=(0.5, 2.0))

# 7. Detect dominant frequency using extracted sampling rate
dom_freq, freqs, power = compute_dominant_frequency(
    time_s, signal_filtered, sampling_rate_hz, freq_band=(0.5, 2.0)
)

# 8. Check for harmonic doubling
dom_freq_corrected, was_corrected = detect_harmonic_doubling(
    time_s, signal, dom_freq, sampling_rate_hz, freq_band=(0.5, 2.0)
)

# 9. Calculate half-power bandwidth
bandwidth = get_half_power_bandwidth(
    time_s, signal, dom_freq_corrected, sampling_rate_hz, freq_band=(0.5, 2.0)
)

# 10. Apply narrow bandpass filter
signal_narrow = narrow_bandpass_around_peak(time_s, signal, dom_freq_corrected, bandwidth)

# 11. Calculate outputs
heart_rate_bpm = dom_freq_corrected * 60  # Convert Hz to BPM
contractility = np.std(signal_narrow)  # Standard deviation of filtered signal
amplitude = np.max(signal_narrow) - np.min(signal_narrow)  # Peak-to-peak amplitude

print(f"Sampling rate: {sampling_rate_hz} Hz (interval: {interval_ms} ms)")
print(f"Heart rate: {heart_rate_bpm:.2f} BPM")
print(f"Contractility: {contractility:.6f}")
print(f"Harmonic corrected: {was_corrected}")
```

### Quality Control Recommendations

**Data Cleaning:**
- Remove first 5 measurements (startup artifacts)
- Remove last 1 measurement (ending artifacts)
- Filter out NaN/Inf values in time_s and amp1_vpp

**Frequency Band:**
- Typical cardiac range: 0.5-2.0 Hz (30-120 BPM)
- Extended range: 0.5-2.5 Hz (30-150 BPM)
- Minimum: 0.1-2.5 Hz (6-150 BPM) for very slow beating

**Signal Quality:**
- Require minimum 4 data points for FFT analysis
- Check for valid sampling rate (dt > 0)
- Verify dominant frequency is within expected range

**Harmonic Doubling:**
- Threshold: 70% power ratio (half-frequency / peak-frequency)
- Guards against doubled fundamental frequency artifacts
- Most common in low-amplitude or noisy signals

**Half-Power Bandwidth:**
- Adaptive bandwidth around dominant frequency
- Clamped to 0.05-1.0 Hz for stability
- Provides tight filter for clean signal extraction

### Usage Notes

- **Always use filtered signal** for downstream analysis
- **Contractility** reflects beat-to-beat variability (higher = more variable)
- **Heart rate** is the dominant frequency converted to BPM
- **Amplitude** (optional) provides contraction strength metric
- For batch processing, track both raw and corrected frequencies to identify harmonic doubling prevalence

## File Format Support

### Plate 1-2 Format (.log)
- Standard `.log` files
- Well ID extracted from filename
- Timestamp from file header

### Plate 3 Format (.txt)
- `.txt` files
- Supports multiple filename patterns
- Date format: `DD.MM.YYYY HH:MM:SS`

See `references/log_file_format.md` for detailed format specifications.

## Filtering Options

Apply quality filters when parsing:

```python
# Filter by O2 range and SNR
result = parse_single_log(
    'A01.log',
    min_oxygen=2.0,
    max_oxygen=80.0,
    min_snr=2.0,
    apply_filters=True
)
```

**Recommended thresholds:**
- O2 range: 0-80% (exclude -100 error values)
- SNR: ≥ 2.0 for good quality, ≥ 1.4 for marginal

## Output Formats

### Pandas DataFrame
```python
df = result['dataframe']
# or for batch:
df = results['combined_dataframe']
```

### CSV File
```python
from scripts.parse_log_file import to_csv

to_csv(result, 'output.csv')
```

### Dictionary
```python
from scripts.parse_log_file import to_dict

data_dict = to_dict(result)
```

## Integration with Other Skills

This skill works alongside other analysis skills:

- **Stage 1 Filtering**: Use parsed data with `cdap/stage1_filter.py` for advanced filtering
- **Data Analysis**: Use DataFrames with pandas for statistical analysis
- **Visualization**: Use extracted variables for plotting

When combining with other workflows, always use this skill to extract log file data first, then pass the DataFrames to other processing steps.

## Batch vs Single File

The skill automatically detects whether to use batch or single file processing:

- **Single file**: Use `parse_single_log()` when you have one specific file
- **Batch processing**: Use `parse_batch_logs()` when processing multiple files or a directory

For batch processing, you can:
- Filter by well_id
- Process all files in a directory
- Combine results into a single DataFrame
- Get summary statistics

## Error Handling

The skill handles:
- Missing files (raises FileNotFoundError)
- Invalid file formats (raises ValueError with details)
- Missing data sections (raises ValueError)
- Corrupted files (prints warning, continues with batch)

Always check for empty DataFrames after parsing:
```python
if df.empty:
    print("No data extracted")
```

## Examples

### Extract O2 measurements for a well
```python
result = parse_single_log('LogFiles/P1OxygenLogs/A01.log')
o2_data = result['oxygen_pct_air']
timestamps = result['measurement_time']
```

### Batch process with filtering
```python
results = parse_batch_logs(
    'LogFiles/P1OxygenLogs/',
    well_id='A01',
    min_oxygen=2.0,
    max_oxygen=80.0,
    min_snr=2.0,
    apply_filters=True
)
df = results['combined_dataframe']
```

### Save to CSV
```python
result = parse_single_log('A01.log')
to_csv(result, 'A01_parsed.csv')
```

### Convert to dictionary
```python
result = parse_single_log('A01.log')
data_dict = to_dict(result)
# Access as: data_dict['oxygen_pct_air'], data_dict['snr'], etc.
```

## Bundled Resources

### Scripts

**`scripts/parse_log_file.py`**: Main parsing functions for single and batch processing.

Key functions:
- `parse_single_log(filepath, ...)`: Parse a single log file
- `parse_batch_logs(directory, ...)`: Batch process multiple files
- `to_csv(data, output_path)`: Save results to CSV
- `to_dict(data)`: Convert to dictionary format
- `extract_well_id_from_filename(filepath)`: Extract well ID from filename
- `extract_start_datetime(lines)`: Extract timestamp from file header

When using the script, import it from the scripts directory:
```python
import sys
from pathlib import Path
base_dir = Path(__file__).parent  # or use the base directory provided when skill loads
sys.path.insert(0, str(base_dir / 'scripts'))
from parse_log_file import parse_single_log, parse_batch_logs
```

### References

**`references/log_file_format.md`**: Complete documentation of the Dynamix log file format.

Read this file when you need:
- Detailed file structure and column specifications
- Well ID extraction patterns and examples
- Timestamp calculation methods
- Data quality considerations and filtering recommendations
- File naming conventions for different plate formats

Access the reference file:
```python
from pathlib import Path
base_dir = Path(__file__).parent  # or use the base directory provided when skill loads
format_docs = base_dir / 'references' / 'log_file_format.md'
# Read the file to understand format details
```

