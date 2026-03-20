"""Reporter module — exports analysis results to Excel files."""

import os
import pandas as pd


def export_to_excel(data_dict, output_dir):
    """Export a dictionary of DataFrames to separate Excel files.

    Args:
        data_dict: dict mapping filename (e.g. 'main.xlsx') to a DataFrame.
        output_dir: Directory where files will be written.
    """
    os.makedirs(output_dir, exist_ok=True)

    for filename, df in data_dict.items():
        filepath = os.path.join(output_dir, filename)
        df.to_excel(filepath, merge_cells=False)
        print(f"  [OK] Exported {filepath}")
