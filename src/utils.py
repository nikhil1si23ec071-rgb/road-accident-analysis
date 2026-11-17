"""Small shared helpers."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd


def norm_key(value) -> str | None:
    """Normalise a categorical string for comparison: lower-case, '_'/'-' to
    space, collapsed whitespace. Returns None for missing values."""
    if value is None or (isinstance(value, float) and np.isnan(value)) or value is pd.NA:
        return None
    s = str(value).strip().lower()
    s = re.sub(r"[_\-]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s or None


def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorised great-circle distance in km."""
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(x, dtype=float))
                              for x in (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def to_jsonable(obj):
    """Recursively convert numpy / pandas scalars so json.dump works."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if obj is pd.NA or obj is pd.NaT:
        return None
    if isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


def fmt_int(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{int(round(x)):,}"


def fmt_pct(x, digits: int = 1) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.{digits}f}%"


def fmt_num(x, digits: int = 2) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:,.{digits}f}"
