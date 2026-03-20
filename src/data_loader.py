"""Data loading module for Futures_Main project.

Provides functions to load participant OI data, volume data, and
contract-level F&O data from the data directory.
"""

import re
import zipfile
import io
from glob import glob
from pathlib import Path

import pandas as pd


def load_participant_oi(data_dir):
    """Load all participant-wise Open Interest CSV files.

    Reads files matching ``data_dir/fao_participant_oi_*.csv``, extracts
    the date from the filename, and concatenates into a single DataFrame.

    Returns:
        pd.DataFrame with columns from the CSV plus 'Date'.
    """
    pattern = str(Path(data_dir) / "fao_participant_oi_*.csv")
    all_files = sorted(glob(pattern))
    if not all_files:
        raise FileNotFoundError(f"No OI files found matching {pattern}")

    frames = []
    for filename in all_files:
        df = pd.read_csv(filename, skiprows=1, nrows=4)
        df.columns = df.columns.str.strip()
        date_str = re.search(r'\d{8}', Path(filename).stem).group()
        df['Date'] = pd.to_datetime(date_str, format='%d%m%Y')
        frames.append(df)

    result = pd.concat(frames, axis=0, ignore_index=True)
    return result


def load_participant_vol(data_dir):
    """Load all participant-wise Volume CSV files.

    Reads files matching ``data_dir/fao_participant_vol*.csv``.

    Returns:
        pd.DataFrame with columns from the CSV plus 'Date'.
    """
    pattern = str(Path(data_dir) / "fao_participant_vol*.csv")
    all_files = sorted(glob(pattern))
    if not all_files:
        raise FileNotFoundError(f"No volume files found matching {pattern}")

    frames = []
    for filename in all_files:
        df = pd.read_csv(filename, skiprows=1, nrows=4)
        df.columns = df.columns.str.strip()
        date_str = re.search(r'\d{8}', Path(filename).stem).group()
        df['Date'] = pd.to_datetime(date_str, format='%d%m%Y')
        frames.append(df)

    return pd.concat(frames, axis=0, ignore_index=True)


def load_fo_contracts(data_dir):
    """Load contract-level F&O data from ZIP files.

    Reads files matching ``data_dir/fo*.zip``, extracts the CSV inside
    each ZIP, cleans up summary rows, and standardizes column names.

    Returns:
        pd.DataFrame with contract-level data.
    """
    pattern = str(Path(data_dir) / "fo*.zip")
    all_files = sorted(glob(pattern))
    if not all_files:
        raise FileNotFoundError(f"No F&O zip files found matching {pattern}")

    frames = []
    for zip_path in all_files:
        # Extract date from zip filename (e.g., fo07072020.zip)
        zip_stem = Path(zip_path).stem
        date_match = re.search(r'\d{8}', zip_stem)
        if date_match:
            file_date = pd.to_datetime(date_match.group(), format='%d%m%Y')
        else:
            file_date = pd.NaT

        with zipfile.ZipFile(zip_path, 'r') as z:
            csv_names = [n for n in z.namelist() if n.lower().endswith('.csv')]
            for csv_name in csv_names:
                with z.open(csv_name) as csv_file:
                    df = pd.read_csv(io.TextIOWrapper(csv_file))
                    df.columns = df.columns.str.strip()

                    # Filter to rows that have a valid INSTRUMENT value
                    valid_instruments = ['FUTIDX', 'FUTSTK', 'OPTIDX', 'OPTSTK']
                    if 'INSTRUMENT' in df.columns:
                        df = df[df['INSTRUMENT'].isin(valid_instruments)].copy()

                    # Add timestamp from filename
                    df['TIMESTAMP'] = file_date
                    frames.append(df)

    if not frames:
        raise FileNotFoundError("No CSV data found inside ZIP files")

    result = pd.concat(frames, axis=0, ignore_index=True)

    # Standardize column names to match expected format
    col_rename = {
        'EXP_DATE': 'EXPIRY_DT',
        'CLOSE_PRICE': 'CLOSE',
        'OPEN_INT*': 'OPEN_INT',
        'NO_OF_CONT': 'CONTRACTS',
        'STR_PRICE': 'STRIKE_PR',
        'OPT_TYPE': 'OPTION_TYP',
    }
    result.rename(columns=col_rename, inplace=True)

    # Parse date columns
    for col in ('TIMESTAMP', 'EXPIRY_DT'):
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], dayfirst=True, errors='coerce')

    # Compute CHG_IN_OI where possible (between dates for same contract)
    result.sort_values(by=['INSTRUMENT', 'SYMBOL', 'EXPIRY_DT', 'TIMESTAMP'], inplace=True)
    if 'OPEN_INT' in result.columns:
        result['CHG_IN_OI'] = result.groupby(
            ['INSTRUMENT', 'SYMBOL', 'EXPIRY_DT']
        )['OPEN_INT'].diff().fillna(0)

    result.reset_index(drop=True, inplace=True)
    return result
