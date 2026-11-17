"""Loading utilities for the raw and the cleaned dataset.

The raw CSV is only ever *read*; it is never written to.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src import config


class DatasetMissingError(FileNotFoundError):
    """Raised when the raw CSV has not been placed in data/raw/."""


def load_raw(path: Path | str = config.RAW_FILE) -> pd.DataFrame:
    """Read the raw CSV exactly as stored (no type coercion beyond pandas defaults)."""
    path = Path(path)
    if not path.exists():
        raise DatasetMissingError(
            f"Raw dataset not found at '{path}'. Place 'indian_roads_dataset.csv' "
            "in data/raw/ (download it from Kaggle: "
            "sehaj1104/indian-road-accident-dataset-20222025)."
        )
    return pd.read_csv(path, low_memory=False)


CLEAN_DTYPES = {
    "city": "string", "state": "string", "road_type": "string",
    "weather": "string", "visibility": "string", "traffic_density": "string",
    "cause": "string", "accident_severity": "string", "festival_name": "string",
}


def load_clean(path: Path | str = config.CLEAN_FILE) -> pd.DataFrame:
    """Read the cleaned CSV produced by ``src.preprocessing`` with proper types."""
    df = pd.read_csv(path, low_memory=False, parse_dates=["date"])
    for col in ("is_weekend", "traffic_signal", "is_peak_hour", "festival_flag",
                "is_fatal", "coord_valid"):
        if col in df:
            df[col] = df[col].astype("Int64")
    return df


def ensure_clean_data(force: bool = False) -> pd.DataFrame:
    """Return the cleaned dataset, (re)building it when missing or stale."""
    raw, clean = config.RAW_FILE, config.CLEAN_FILE
    stale = (
        not clean.exists()
        or (raw.exists() and raw.stat().st_mtime > clean.stat().st_mtime)
    )
    if force or stale:
        from src.preprocessing import run_pipeline  # local import avoids cycle
        run_pipeline()
    return load_clean(clean)
