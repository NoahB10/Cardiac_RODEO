"""
Analyze raw QC data from all log files.
Extracts SNR, O2, and file path for all measurements from files that started within 96 hours
of any of the 3 plate start times.
"""

import pandas as pd
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta
import re

# Path discovery convention
current_dir = Path.cwd()

if current_dir.name == 'Prediction_Models':
    PROJECT_ROOT = current_dir.parent
elif (current_dir / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir
elif (current_dir.parent / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir.parent
else:
    PROJECT_ROOT = current_dir

# Three plate start times (user provided)
PLATE_START_TIMES = [
    datetime(2025, 5, 11, 20, 45, 7),   # P1: 5/11/2025 8:45:07 PM
    datetime(2025, 5, 29, 13, 29, 0),   # P2: 5/29/2025 1:29:00 PM
    datetime(2020, 1, 19, 20, 14, 13),  # P3: 1/19/2020 8:14:13 PM
]


def parse_file_start_time(filepath):
    """
    Parse the header of a log file to extract start datetime.

    Header format (line 2):
    DD.MM.YYYY    HH:MM:SS  (with tabs/spaces between)

    Returns:
        datetime object or None
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Check first 10 lines for datetime pattern
        for line in lines[:10]:
            # Look for DD.MM.YYYY HH:MM:SS pattern
            match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})', line)
            if match:
                day, month, year, hour, minute, second = match.groups()
                return datetime(
                    int(year), int(month), int(day),
                    int(hour), int(minute), int(second)
                )
    except:
        pass

    return None


def is_within_96h_of_any_plate(file_start):
    """
    Check if the file's start time is within 96 hours of any plate start.

    Returns:
        True if within 96h of any plate, False otherwise
    """
    if file_start is None:
        return False

    for plate_start in PLATE_START_TIMES:
        # Calculate 96 hour window from plate start
        cutoff = plate_start + timedelta(hours=96)

        # File should have started between plate_start and cutoff
        if plate_start <= file_start <= cutoff:
            return True

    return False


def process_log_file_p1p2(filepath):
    """
    Process a Plate 1 or 2 (.log) file and extract SNR and O2.

    Returns:
        DataFrame with columns: snr, oxygen_pct_air, file_path
        or None if parsing fails
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Find the header line with column names
        header_line_idx = None
        for idx, line in enumerate(lines):
            if 'time / s' in line.lower() or 'time/s' in line.lower():
                header_line_idx = idx
                break

        if header_line_idx is None:
            return None

        # Read the CSV starting from the header line
        df = pd.read_csv(filepath, skiprows=header_line_idx, sep='\t', on_bad_lines='skip')

        # Clean column names
        df.columns = df.columns.str.strip()

        # Find O2 and SNR columns
        o2_col = None
        snr_col = None

        for col in df.columns:
            if 'o2' in col.lower() and 'air' in col.lower():
                o2_col = col
            elif 'probe signal' in col.lower() or 'snr' in col.lower():
                snr_col = col

        if o2_col is None or snr_col is None:
            return None

        # Extract only the columns we need
        result = pd.DataFrame({
            'snr': pd.to_numeric(df[snr_col], errors='coerce'),
            'oxygen_pct_air': pd.to_numeric(df[o2_col], errors='coerce'),
            'file_path': str(filepath)
        })

        # Drop rows with NaN values
        result = result.dropna()

        return result if len(result) > 0 else None

    except Exception as e:
        return None


def process_log_file_p3(filepath):
    """
    Process a Plate 3 (.txt) file and extract SNR and O2.

    P3 format differences:
    - Column 12 is "probe signal : background" (SNR)
    - Uses .txt extension

    Returns:
        DataFrame with columns: snr, oxygen_pct_air, file_path
        or None if parsing fails
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Find data start marker
        data_start_idx = None
        for i, line in enumerate(lines):
            if 'time / s' in line and 'O2 content / % air' in line:
                data_start_idx = i + 1
                break

        if data_start_idx is None:
            return None

        # Parse data rows
        data_rows = []
        for line in lines[data_start_idx:]:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split('\t')
                if len(parts) >= 12:  # Need at least 12 columns for SNR
                    try:
                        o2_value = float(parts[1])   # Column 2: O2 content / % air
                        snr_value = float(parts[11]) # Column 12: probe signal : background
                        data_rows.append({
                            'snr': snr_value,
                            'oxygen_pct_air': o2_value,
                            'file_path': str(filepath)
                        })
                    except (ValueError, IndexError):
                        continue

        if not data_rows:
            return None

        return pd.DataFrame(data_rows)

    except Exception as e:
        return None


def main():
    """Process all log files from the three plates."""

    # Define plate directories using PROJECT_ROOT
    plate_dirs = [
        ("P1", PROJECT_ROOT / "LogFiles" / "P1OxygenLogs", ".log"),
        ("P2", PROJECT_ROOT / "LogFiles" / "P2OxygenLogs", ".log"),
        ("P3", PROJECT_ROOT / "LogFiles" / "P3OxygenLogs", ".txt"),
    ]

    # Collect all log files
    all_files = []
    for plate_name, plate_dir, ext in plate_dirs:
        if plate_dir.exists():
            files = list(plate_dir.glob(f"*{ext}"))
            all_files.extend([(plate_name, f) for f in files])

    print(f"Found {len(all_files)} total log files:")
    for plate_name, plate_dir, ext in plate_dirs:
        if plate_dir.exists():
            count = len(list(plate_dir.glob(f"*{ext}")))
            print(f"  {plate_name}: {count} files")

    # Print plate start times and 96-hour cutoffs
    print("\nPlate start times and 96-hour cutoffs:")
    for i, start_time in enumerate(PLATE_START_TIMES, 1):
        cutoff = start_time + timedelta(hours=96)
        print(f"  Plate {i}:")
        print(f"    Start:  {start_time}")
        print(f"    Cutoff: {cutoff}")

    # Process all files
    print("\nProcessing files...")

    all_results = []
    files_processed = 0
    files_skipped_no_time = 0
    files_skipped_outside_window = 0
    files_skipped_parse_error = 0

    total_files = len(all_files)
    for i, (plate_name, filepath) in enumerate(all_files):
        if (i + 1) % 500 == 0 or i == 0:
            print(f"  Processing file {i + 1}/{total_files}...")
        # Extract file start time from header
        file_start = parse_file_start_time(filepath)

        if file_start is None:
            files_skipped_no_time += 1
            continue

        # Check if within 96 hours of any plate start
        if not is_within_96h_of_any_plate(file_start):
            files_skipped_outside_window += 1
            continue

        # Process the file based on plate type
        if plate_name == "P3":
            result = process_log_file_p3(filepath)
        else:
            result = process_log_file_p1p2(filepath)

        if result is not None and len(result) > 0:
            all_results.append(result)
            files_processed += 1
        else:
            files_skipped_parse_error += 1

    # Report
    print(f"\nFiles processed: {files_processed}")
    print(f"Files skipped (no timestamp): {files_skipped_no_time}")
    print(f"Files skipped (outside 96h): {files_skipped_outside_window}")
    print(f"Files skipped (parse error): {files_skipped_parse_error}")

    if not all_results:
        print("ERROR: No data collected!")
        return

    # Combine all results
    print("\nCombining all data...")
    final_df = pd.concat(all_results, ignore_index=True)

    print(f"\nFinal Statistics:")
    print(f"  Total rows: {len(final_df):,}")
    print(f"  SNR range: {final_df['snr'].min():.2f} to {final_df['snr'].max():.2f}")
    print(f"  O2 range: {final_df['oxygen_pct_air'].min():.1f}% to {final_df['oxygen_pct_air'].max():.1f}%")

    # SNR distribution
    print(f"\n  SNR distribution:")
    print(f"    SNR < 0.4:        {(final_df['snr'] < 0.4).sum():,} rows")
    print(f"    0.4 <= SNR < 1.4: {((final_df['snr'] >= 0.4) & (final_df['snr'] < 1.4)).sum():,} rows")
    print(f"    1.4 <= SNR < 2.0: {((final_df['snr'] >= 1.4) & (final_df['snr'] < 2.0)).sum():,} rows")
    print(f"    SNR >= 2.0:       {(final_df['snr'] >= 2.0).sum():,} rows")

    # O2 distribution
    print(f"\n  O2 distribution:")
    print(f"    O2 < 0%:         {(final_df['oxygen_pct_air'] < 0).sum():,} rows")
    print(f"    0% <= O2 <= 80%: {((final_df['oxygen_pct_air'] >= 0) & (final_df['oxygen_pct_air'] <= 80)).sum():,} rows")
    print(f"    O2 > 80%:        {(final_df['oxygen_pct_air'] > 80).sum():,} rows")

    # Create output directories if needed
    cleaned_data_dir = PROJECT_ROOT / "Cleaned_Data"
    cleaned_data_dir.mkdir(parents=True, exist_ok=True)

    # Save to CSV in Cleaned_Data/ (Excel has 1M row limit, data exceeds that)
    csv_file = cleaned_data_dir / "Raw_QC_Analysis_96h.csv"
    print(f"\nSaving to {csv_file}...")
    final_df.to_csv(csv_file, index=False)
    print(f"Done! Saved {len(final_df):,} rows to {csv_file}")

    # Save summary statistics to Output/
    output_dir = PROJECT_ROOT / "Output" / "QC_Analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_file = output_dir / "Raw_QC_Summary_96h.txt"
    with open(summary_file, 'w') as f:
        f.write("RAW QC ANALYSIS SUMMARY (96h Window)\n")
        f.write("=" * 50 + "\n\n")

        f.write("Plate Start Times and 96-Hour Cutoffs:\n")
        for i, start_time in enumerate(PLATE_START_TIMES, 1):
            cutoff = start_time + timedelta(hours=96)
            f.write(f"  Plate {i}:\n")
            f.write(f"    Start:  {start_time}\n")
            f.write(f"    Cutoff: {cutoff}\n")

        f.write(f"\nFile Processing Summary:\n")
        f.write(f"  Files processed: {files_processed}\n")
        f.write(f"  Files skipped (no timestamp): {files_skipped_no_time}\n")
        f.write(f"  Files skipped (outside 96h): {files_skipped_outside_window}\n")
        f.write(f"  Files skipped (parse error): {files_skipped_parse_error}\n")

        f.write(f"\nFinal Statistics:\n")
        f.write(f"  Total rows: {len(final_df):,}\n")
        f.write(f"  SNR range: {final_df['snr'].min():.2f} to {final_df['snr'].max():.2f}\n")
        f.write(f"  O2 range: {final_df['oxygen_pct_air'].min():.1f}% to {final_df['oxygen_pct_air'].max():.1f}%\n")

        f.write(f"\n  SNR distribution:\n")
        f.write(f"    SNR < 0.4:        {(final_df['snr'] < 0.4).sum():,} rows\n")
        f.write(f"    0.4 <= SNR < 1.4: {((final_df['snr'] >= 0.4) & (final_df['snr'] < 1.4)).sum():,} rows\n")
        f.write(f"    1.4 <= SNR < 2.0: {((final_df['snr'] >= 1.4) & (final_df['snr'] < 2.0)).sum():,} rows\n")
        f.write(f"    SNR >= 2.0:       {(final_df['snr'] >= 2.0).sum():,} rows\n")

        f.write(f"\n  O2 distribution:\n")
        f.write(f"    O2 < 0%:         {(final_df['oxygen_pct_air'] < 0).sum():,} rows\n")
        f.write(f"    0% <= O2 <= 80%: {((final_df['oxygen_pct_air'] >= 0) & (final_df['oxygen_pct_air'] <= 80)).sum():,} rows\n")
        f.write(f"    O2 > 80%:        {(final_df['oxygen_pct_air'] > 80).sum():,} rows\n")

    print(f"Summary statistics saved to {summary_file}")


if __name__ == "__main__":
    main()
