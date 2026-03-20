"""Tests for data_loader module."""

import os
import pytest
import pandas as pd

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_participant_oi, load_participant_vol


# Use the project's actual data directory for integration-style tests
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class TestLoadParticipantOI:
    """Tests for load_participant_oi()."""

    def test_returns_dataframe(self):
        """Should return a pandas DataFrame."""
        result = load_participant_oi(DATA_DIR)
        assert isinstance(result, pd.DataFrame)

    def test_has_date_column(self):
        """Result should have a 'Date' column."""
        result = load_participant_oi(DATA_DIR)
        assert 'Date' in result.columns

    def test_has_client_type_column(self):
        """Result should have a 'Client Type' column."""
        result = load_participant_oi(DATA_DIR)
        assert 'Client Type' in result.columns

    def test_four_participants_per_date(self):
        """Each date should have exactly 4 rows (Client, DII, FII, Pro)."""
        result = load_participant_oi(DATA_DIR)
        counts = result.groupby('Date').size()
        assert (counts == 4).all(), f"Dates with != 4 rows: {counts[counts != 4]}"

    def test_date_column_is_datetime(self):
        """Date column should be datetime type."""
        result = load_participant_oi(DATA_DIR)
        assert pd.api.types.is_datetime64_any_dtype(result['Date'])

    def test_raises_on_missing_dir(self):
        """Should raise FileNotFoundError for non-existent directory."""
        with pytest.raises(FileNotFoundError):
            load_participant_oi("nonexistent_dir_12345")


def _vol_files_exist():
    """Check if volume data files exist."""
    from glob import glob
    from pathlib import Path
    return len(glob(str(Path(DATA_DIR) / "fao_participant_vol*.csv"))) > 0


class TestLoadParticipantVol:
    """Tests for load_participant_vol()."""

    @pytest.mark.skipif(not _vol_files_exist(), reason="No volume files in data dir")
    def test_returns_dataframe(self):
        result = load_participant_vol(DATA_DIR)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.skipif(not _vol_files_exist(), reason="No volume files in data dir")
    def test_has_date_column(self):
        result = load_participant_vol(DATA_DIR)
        assert 'Date' in result.columns

    def test_raises_on_missing_dir(self):
        with pytest.raises(FileNotFoundError):
            load_participant_vol("nonexistent_dir_12345")
