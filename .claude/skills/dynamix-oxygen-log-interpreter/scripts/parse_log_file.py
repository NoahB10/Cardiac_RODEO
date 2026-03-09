"""
Parse Dynamix oxygen log files (.log or .txt) and extract key measurements.

This script handles both Plate 1-2 format (.log) and Plate 3 format (.txt).
Returns standardized data with intuitive variable names.

Usage:
    from parse_log_file import parse_single_log, parse_batch_logs
    
    # Single file
    data = parse_single_log('path/to/A01.log')
    
    # Batch processing
    results = parse_batch_logs('path/to/logs/directory', well_id='A01')
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import numpy as np


def extract_well_id_from_filename(filepath: Union[str, Path]) -> Optional[str]:
    """Extract well ID from filename (e.g., 'A01', 'B12').
    
    Args:
        filepath: Path to log file
        
    Returns:
        Well ID string or None if not found
    """
    filename = Path(filepath).stem
    # Pattern: Letter followed by 1-2 digits (A01, B12, etc.)
    match = re.search(r'([A-H])(\d{1,2})', filename, re.IGNORECASE)
    if match:
        letter = match.group(1).upper()
        number = match.group(2).zfill(2)
        return f"{letter}{number}"
    return None


def extract_start_datetime(lines: List[str]) -> Tuple[Optional[pd.Timestamp], Optional[str]]:
    """Extract start datetime from log file header.
    
    Supports multiple formats:
    - Plate 3: "24.1.2024 9:45:01" (DD.MM.YYYY HH:MM:SS)
    - Other formats may be added as needed
    
    Args:
        lines: First 20 lines of the log file
        
    Returns:
        Tuple of (pandas Timestamp, date string)
    """
    for line in lines[:20]:
        # Plate 3 format: DD.MM.YYYY HH:MM:SS
        match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})', line)
        if match:
            day, month, year, hour, minute, second = match.groups()
            datetime_str = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute}:{second}"
            timestamp = pd.to_datetime(datetime_str, format='%Y-%m-%d %H:%M:%S', errors='coerce')
            if pd.notna(timestamp):
                date_str = timestamp.strftime('%Y-%m-%d')
                return timestamp, date_str
    
    return None, None


def parse_single_log(
    filepath: Union[str, Path],
    min_oxygen: float = 0.0,
    max_oxygen: float = 80.0,
    min_snr: float = 0.0,
    apply_filters: bool = False
) -> Dict:
    """Parse a single Dynamix log file and extract measurements.
    
    Args:
        filepath: Path to .log or .txt file
        min_oxygen: Minimum valid oxygen percentage (for filtering)
        max_oxygen: Maximum valid oxygen percentage (for filtering)
        min_snr: Minimum valid SNR (for filtering)
        apply_filters: If True, filter rows based on O2 and SNR thresholds
        
    Returns:
        Dictionary with keys:
        - 'dataframe': pandas DataFrame with all measurements
        - 'well_id': Well identifier (e.g., 'A01')
        - 'start_datetime': pandas Timestamp of measurement start
        - 'start_date': Date string (YYYY-MM-DD)
        - 'measurement_time': Series of absolute timestamps
        - 'oxygen_pct_air': Series of oxygen percentages
        - 'snr': Series of signal-to-noise ratios
        - 'amp0_vpp': Series of amplitude 0 values
        - 'amp1_vpp': Series of amplitude 1 values
        - 'file_path': Original file path
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Log file not found: {filepath}")
    
    # Read file
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Find data start marker
    data_start_idx = None
    for i, line in enumerate(lines):
        if 'time / s' in line and 'O2 content / % air' in line:
            data_start_idx = i + 1
            break
    
    if data_start_idx is None:
        raise ValueError(f"No data section found in {filepath}")
    
    # Parse data rows
    data_lines = []
    for line in lines[data_start_idx:]:
        line = line.strip()
        if line and not line.startswith('#'):
            parts = line.split('\t')
            if len(parts) >= 8:
                data_lines.append(parts)
    
    if not data_lines:
        raise ValueError(f"No data rows found in {filepath}")
    
    # Create DataFrame
    df = pd.DataFrame(data_lines)
    expected_cols = [
        'time_s', 'oxygen_pct_air', 'tau_us', 'temp_c',
        'oxygen_pct_vol', 'phase1_deg', 'phase2_deg',
        'amp0_vpp', 'amp1_vpp', 'amp2_vpp', 'amp3_vpp',
        'snr'
    ]
    
    available_cols = expected_cols[:min(len(expected_cols), df.shape[1])]
    df.columns = available_cols + [f'extra_{i}' for i in range(len(available_cols), df.shape[1])]
    
    # Convert to numeric
    numeric_cols = ['time_s', 'oxygen_pct_air', 'snr', 'amp0_vpp', 'amp1_vpp']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Extract metadata
    start_datetime, start_date = extract_start_datetime(lines)
    well_id = extract_well_id_from_filename(filepath)
    
    # Add metadata columns
    df['file_path'] = str(filepath)
    df['well_id'] = well_id
    if start_datetime is not None:
        df['start_datetime'] = start_datetime
        df['measurement_time'] = start_datetime + pd.to_timedelta(df['time_s'], unit='s')
    else:
        df['start_datetime'] = pd.NaT
        df['measurement_time'] = pd.NaT
    
    # Apply filters if requested
    if apply_filters:
        valid_o2 = (df['oxygen_pct_air'] >= min_oxygen) & (df['oxygen_pct_air'] <= max_oxygen)
        valid_snr = df['snr'] >= min_snr
        df = df[valid_o2 & valid_snr].copy()
    
    # Build result dictionary
    result = {
        'dataframe': df,
        'well_id': well_id,
        'start_datetime': start_datetime,
        'start_date': start_date,
        'measurement_time': df['measurement_time'],
        'oxygen_pct_air': df['oxygen_pct_air'],
        'snr': df['snr'],
        'amp0_vpp': df.get('amp0_vpp', pd.Series(dtype=float)),
        'amp1_vpp': df.get('amp1_vpp', pd.Series(dtype=float)),
        'file_path': str(filepath)
    }
    
    return result


def parse_batch_logs(
    directory: Union[str, Path],
    well_id: Optional[str] = None,
    file_pattern: str = "*.log",
    min_oxygen: float = 0.0,
    max_oxygen: float = 80.0,
    min_snr: float = 0.0,
    apply_filters: bool = False
) -> Dict:
    """Parse multiple log files from a directory (batch processing).
    
    Args:
        directory: Directory containing log files
        well_id: Optional well ID to filter files (e.g., 'A01')
        file_pattern: File pattern to match (default: "*.log", also supports "*.txt")
        min_oxygen: Minimum valid oxygen percentage
        max_oxygen: Maximum valid oxygen percentage
        min_snr: Minimum valid SNR
        apply_filters: If True, filter rows based on thresholds
        
    Returns:
        Dictionary with keys:
        - 'dataframes': List of DataFrames (one per file)
        - 'combined_dataframe': Single DataFrame with all files combined
        - 'well_ids': List of well IDs found
        - 'file_paths': List of file paths processed
        - 'summary': Dictionary with counts and statistics
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    # Find log files
    log_files = []
    for pattern in [file_pattern, "*.txt"] if file_pattern == "*.log" else [file_pattern]:
        found = list(directory.glob(pattern))
        log_files.extend(found)
    
    # Filter by well_id if provided
    if well_id:
        log_files = [f for f in log_files if well_id.upper() in f.name.upper()]
    
    if not log_files:
        raise ValueError(f"No log files found in {directory} matching pattern {file_pattern}")
    
    # Parse each file
    dataframes = []
    well_ids = []
    file_paths = []
    
    for filepath in sorted(log_files):
        try:
            result = parse_single_log(
                filepath,
                min_oxygen=min_oxygen,
                max_oxygen=max_oxygen,
                min_snr=min_snr,
                apply_filters=apply_filters
            )
            dataframes.append(result['dataframe'])
            if result['well_id']:
                well_ids.append(result['well_id'])
            file_paths.append(result['file_path'])
        except Exception as e:
            print(f"Warning: Failed to parse {filepath}: {e}")
            continue
    
    if not dataframes:
        raise ValueError("No files were successfully parsed")
    
    # Combine all DataFrames
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Build summary
    summary = {
        'total_files': len(file_paths),
        'total_rows': len(combined_df),
        'unique_wells': len(set(well_ids)) if well_ids else 0,
        'well_ids': list(set(well_ids)) if well_ids else [],
        'date_range': (
            combined_df['measurement_time'].min(),
            combined_df['measurement_time'].max()
        ) if 'measurement_time' in combined_df.columns and combined_df['measurement_time'].notna().any() else (None, None)
    }
    
    return {
        'dataframes': dataframes,
        'combined_dataframe': combined_df,
        'well_ids': well_ids,
        'file_paths': file_paths,
        'summary': summary
    }


def to_dict(data: Union[pd.DataFrame, Dict]) -> Dict:
    """Convert DataFrame or parse result to dictionary format.
    
    Args:
        data: DataFrame or result dictionary from parse functions
        
    Returns:
        Dictionary with data as lists/values
    """
    if isinstance(data, pd.DataFrame):
        return data.to_dict('list')
    elif isinstance(data, dict) and 'dataframe' in data:
        return data['dataframe'].to_dict('list')
    else:
        return data


def to_csv(data: Union[pd.DataFrame, Dict], output_path: Union[str, Path]) -> None:
    """Save DataFrame or parse result to CSV file.
    
    Args:
        data: DataFrame or result dictionary from parse functions
        output_path: Path to output CSV file
    """
    if isinstance(data, pd.DataFrame):
        df = data
    elif isinstance(data, dict) and 'dataframe' in data:
        df = data['dataframe']
    elif isinstance(data, dict) and 'combined_dataframe' in data:
        df = data['combined_dataframe']
    else:
        raise ValueError("Cannot convert data to CSV")
    
    df.to_csv(output_path, index=False)


if __name__ == '__main__':
    # Example usage
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        result = parse_single_log(filepath)
        print(f"Parsed {len(result['dataframe'])} rows from {filepath}")
        print(f"Well ID: {result['well_id']}")
        print(f"Start datetime: {result['start_datetime']}")

