# Heart Rate Analysis Notes

## Files

| File | Purpose |
|------|---------|
| `heart_rate_analysis.ipynb` | Main notebook (interactive) |
| `heart_rate_analysis_script.py.py` | Standalone script version |
| `.claude/skills/dynamix-oxygen-log-interpreter/` | Skill for parsing Dynamix logs & extracting HR |
| `Output/HeartRate_Analysis/` | CSV tables + 20+ PNG plots |

## Data Source
- Raw CSV files from `Cleaned_Data/Stage1_Raw_Relaxed/` (extracted from `Raw_Tables.zip`)
- Structure: `{Drug}/{Concentration_mM}/{WellID}_{Hour}h_timestamp.csv`
- Columns: `time_s`, `amp1_vpp` (amplitude in volts peak-to-peak)
- The amplitude signal (`amp1_vpp`) is what heart rate is extracted from

## 6 Drugs Analyzed

| Drug | Baseline | Compare | Category |
|------|----------|---------|----------|
| Sotalol | 0h & 3h | 24h | high_rate |
| Chlorpromazine | 0h & 3h | 24h | high_rate |
| Amiodarone | 3h | 48h | low_rate |
| Ibrutinib | 0h | 48h | low_rate |
| Vandetanib | 0h | 24h | special |
| Bortezomib | 0h | 24h | special |

## Signal Processing Pipeline (8 steps)
1. Parse sampling rate from file header (e.g. 100ms interval → 10 Hz)
2. Clean data — skip first 5 rows (startup artifacts), last 1 row
3. Wide bandpass filter (0.5–2.0 Hz = 30–120 BPM) via FFT
4. Welch's PSD to find dominant frequency (nperseg=min(256, len))
5. Harmonic doubling check — if half-frequency has ≥70% of peak power, halve the detected freq
6. Half-power bandwidth — adaptive -3dB bandwidth (0.05–1.0 Hz)
7. Narrow bandpass around dominant freq ± bandwidth for clean extraction
8. Contractility = std(filtered signal), BPM = freq × 60

## Key Decisions & Parameters

| Decision | Choice | Rationale |
|----------|--------|-----------|
| QC trimming | Skip first 5 rows, last 1 row | Startup transients / shutdown artifacts |
| Wide band | 0.5–2.0 Hz | Typical cardiac range (30–120 BPM) |
| Extended band | 0.1–2.5 Hz | Abnormal beating (6–150 BPM) |
| Frequency method | Welch's PSD (`scipy.signal.welch`) | Robust spectral estimation |
| Welch segment length | min(256, N) | Balance resolution vs noise |
| Baseline hour | Drug-dependent (0h or 3h) | Some drugs need stabilization time (e.g. Amiodarone uses 3h) |
| Comparison hour | 24h or 48h depending on drug | Matches expected drug onset |
| Harmonic doubling threshold | 70% power ratio | Prevents frequency doubling errors |
| Harmonic correction | If half-freq has comparable power, use half | Corrects doubling artifact |
| Contractility metric | std of narrow-filtered signal | Captures beat-to-beat variability |
| Filtering | Two-tier: wideband [0.5–2.0 Hz] Butterworth + narrow adaptive FFT-based bandpass using half-power (-3dB) bandwidth | General noise removal + detailed analysis |
| File selection | Prefer files starting at time_s ≈ 0, tie-break by file size | Ensures complete recordings |

## Key Algorithms

### 1. Dominant Frequency Detection
- Welch's PSD → peak in [0.1, 2.5] Hz → ×60 = BPM
- nperseg = min(256, len(signal))

### 2. Harmonic Doubling Detection & Correction
- If detected freq > 1.5 Hz, check if half-frequency has comparable power
- If yes: `freq_corrected = freq_detected / 2`
- Both raw and corrected BPM values are reported

### 3. Half-Power Bandwidth
- Find -3dB points around peak frequency
- Clamped to [0.05, 1.0] Hz range
- Used as adaptive bandpass width for narrow filtering

### 4. Narrow Bandpass Filter
- FFT-based filter centered on dominant frequency
- Uses computed half-power bandwidth
- Zero-phase filtering

## 18 Analysis Functions
| Function | Purpose |
|----------|---------|
| `discover_concentrations()` | Auto-discover concentration folders within drug directories |
| `extract_hour_from_filename()` | Parse hour value from filename pattern `_(\d+)h_` |
| `get_well_name()` | Extract well ID (A-P, 01-24) from filename |
| `load_relaxed_log()` | Load CSV, skip initial/final rows, validate columns |
| `compute_dominant_frequency()` | Welch's method → peak frequency in [0.1, 2.5] Hz |
| `bandpass_filter_signal()` | Butterworth filter [0.5, 2.0] Hz |
| `plot_waveform_and_fft()` | Generate waveform + FFT subplots |
| `parse_concentration_uM()` | Convert concentration string to µM float |
| `bpm_for_hour()` | Wrapper: find files + compute dominant freq + convert to BPM |
| `is_below_cmax()` | Check if concentration exceeds Cmax threshold |
| `detect_harmonic_doubling()` | Check for 2x frequency doubling, correct if present |
| `narrow_bandpass_around_peak()` | FFT-based filter centered on detected frequency |
| `get_half_power_bandwidth()` | Calculate -3dB bandwidth around dominant frequency |
| `select_best_file()` | Choose CSV by preferring files starting at time_s ≈ 0 |
| `find_files_for_concentration()` | Locate all CSV files at target hour (±tolerance) |
| `collect_bpm_timepoints_filtered()` | Gather BPM across all timepoints for a well |
| `export_each_csv_to_sheet()` | Write individual CSV datasets to Excel sheets |

## Outputs
- `all_drugs_comprehensive_table_all_wells.csv` — BPM at 0h, 3h, 4h, 6h, 12h, 24h + baseline change + % change (99 rows)
- `focused_outcomes_with_harmonic_doubling.csv` — Per-well frequency analysis with raw vs corrected BPM (68 rows)
- 20 PNG plots — Multi-panel waveform + FFT visualizations, including half-power filtered variants

## Well Selection (per drug)
- Sotalol: [O20]
- Amiodarone: [K13, H13, G14]
- Custom per-drug well and timepoint selection in Cell 6 of notebook

## Pipeline Sections (11 cells)
1. Setup & configuration, path init, output dir creation
2. Helper functions (file I/O, signal loading, QC)
3. Plotting functions (waveform + FFT multi-panel)
4. Concentration parsing & filtering
5. Configuration overrides
6. Focused outcomes analysis with harmonic doubling
7. Harmonic doubling function definition
8. Half-power & narrow bandpass functions
9. Excel export utility
10. Comprehensive table generation (all drugs × all concentrations × all wells)
11. Visualization generation (multi-panel plots + half-power filtered variants)
