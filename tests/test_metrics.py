"""Tests for metrics module."""

import os
import pytest
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_participant_oi, load_participant_vol
from src.metrics import (
    compute_oi_snapshot,
    compute_oi_differences,
    compute_pcr,
)


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@pytest.fixture
def oi_data():
    return load_participant_oi(DATA_DIR)


def _vol_files_exist():
    from glob import glob
    from pathlib import Path
    return len(glob(str(Path(DATA_DIR) / "fao_participant_vol*.csv"))) > 0


@pytest.fixture
def vol_data():
    if not _vol_files_exist():
        pytest.skip("No volume files in data dir")
    return load_participant_vol(DATA_DIR)


class TestComputeOISnapshot:
    """Tests for compute_oi_snapshot()."""

    def test_returns_dataframe(self, oi_data):
        result = compute_oi_snapshot(oi_data)
        assert isinstance(result, pd.DataFrame)

    def test_has_net_columns(self, oi_data):
        result = compute_oi_snapshot(oi_data)
        expected_cols = ['Future Index Net', 'Future Stock Net',
                         'Option Index Net', 'Option Stock Net']
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_has_market_view_columns(self, oi_data):
        result = compute_oi_snapshot(oi_data)
        mv_cols = ['Future Index Market View', 'Future Stock Market View',
                   'Option Index Market View', 'Option Stock Market View']
        for col in mv_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_market_view_values(self, oi_data):
        """Market view columns should only contain 'Bullish' or 'Bearish'."""
        result = compute_oi_snapshot(oi_data)
        mv_cols = [c for c in result.columns if 'Market View' in c]
        for col in mv_cols:
            unique_vals = set(result[col].dropna().unique())
            assert unique_vals.issubset({'Bullish', 'Bearish'}), \
                f"Unexpected values in {col}: {unique_vals}"

    def test_active_party_columns_exist(self, oi_data):
        result = compute_oi_snapshot(oi_data)
        for prefix in ['FUTIDX', 'FUTSTK', 'OPTIDX', 'OPTSTK']:
            col = f'{prefix} Active Party'
            assert col in result.columns, f"Missing column: {col}"

    def test_helper_columns_removed(self, oi_data):
        """Helper columns (Active Party1/2) should be dropped."""
        result = compute_oi_snapshot(oi_data)
        for prefix in ['FUTIDX', 'FUTSTK', 'OPTIDX', 'OPTSTK']:
            assert f'{prefix} Active Party1' not in result.columns
            assert f'{prefix} Active Party2' not in result.columns


class TestComputeOIDifferences:
    """Tests for compute_oi_differences()."""

    def test_returns_dataframe(self, oi_data, vol_data):
        result = compute_oi_differences(oi_data, vol_data)
        assert isinstance(result, pd.DataFrame)

    def test_has_volume_ratio_columns(self, oi_data, vol_data):
        result = compute_oi_differences(oi_data, vol_data)
        vr_cols = [c for c in result.columns if c.startswith('VR ')]
        assert len(vr_cols) > 0, "No volume ratio columns found"

    def test_has_market_view(self, oi_data, vol_data):
        result = compute_oi_differences(oi_data, vol_data)
        mv_cols = [c for c in result.columns if 'Market View' in c]
        assert len(mv_cols) >= 4


class TestComputePCR:
    """Tests for compute_pcr()."""

    def test_returns_dataframe(self, oi_data):
        result = compute_pcr(oi_data)
        assert isinstance(result, pd.DataFrame)

    def test_has_pcr_columns(self, oi_data):
        result = compute_pcr(oi_data)
        for col in ['PCR Index OI', 'PCR Stock OI', 'PCR Combined']:
            assert col in result.columns, f"Missing column: {col}"

    def test_pcr_positive(self, oi_data):
        """PCR values should be positive (or NaN)."""
        result = compute_pcr(oi_data)
        for col in result.columns:
            valid = result[col].dropna()
            assert (valid >= 0).all(), f"Negative PCR value in {col}"
