"""Pipeline tests: (a) robustness on a dirty fixture written to a temporary
data root, (b) the real cleaned file keeps every record and column."""
import hashlib
import importlib
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REAL_RAW = ROOT / "data" / "raw" / "indian_roads_dataset.csv"
sys.path.insert(0, str(ROOT / "tests"))
from make_fixture import build_dirty_fixture  # noqa: E402


@pytest.fixture(scope="module")
def cleaned_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("raa")
    (root / "raw").mkdir()
    raw = build_dirty_fixture(REAL_RAW)
    raw.to_csv(root / "raw" / "indian_roads_dataset.csv", index=False)
    os.environ["RAA_DATA_DIR"] = str(root)
    os.environ["RAA_REPORTS_DIR"] = str(root / "reports")
    import src.config, src.data_loader, src.profiling, src.preprocessing  # noqa: E401
    for m in (src.config, src.data_loader, src.profiling, src.preprocessing):
        importlib.reload(m)
    before = hashlib.sha256((root / "raw" / "indian_roads_dataset.csv").read_bytes()).hexdigest()
    df = src.preprocessing.run_pipeline(verbose=False)
    after = hashlib.sha256((root / "raw" / "indian_roads_dataset.csv").read_bytes()).hexdigest()
    yield raw, df, before == after, root
    del os.environ["RAA_DATA_DIR"], os.environ["RAA_REPORTS_DIR"]
    for m in (src.config, src.data_loader, src.profiling, src.preprocessing):
        importlib.reload(m)


def test_raw_file_untouched(cleaned_fixture):
    assert cleaned_fixture[2]


def test_only_exact_duplicates_removed(cleaned_fixture):
    raw, df, _, _ = cleaned_fixture
    assert len(df) == len(raw) - 3
    assert df["dq_duplicate_id"].sum() == 2          # id clash kept + flagged


def test_categories_standardised(cleaned_fixture):
    _, df, _, _ = cleaned_fixture
    assert {"Bangalore", "Mumbai"} <= set(df["city"])
    assert not any(c.strip() != c for c in df["city"].dropna())
    assert set(df["cause"].dropna()) <= {"overspeeding", "drunk driving", "distraction", "weather", "poor road"}
    assert set(df["accident_severity"].dropna()) <= {"fatal", "major", "minor"}
    assert "fog" in set(df["weather"]) and "Foggy" not in set(df["weather"])
    assert "Tamil Nadu" in set(df["state"])


def test_impossible_values_nulled_not_dropped(cleaned_fixture):
    _, df, _, _ = cleaned_fixture
    assert df["casualties"].min() >= 0
    assert df["risk_score"].max() <= 1
    assert df["hour"].dropna().between(0, 23).all()
    assert df["temperature"].max() <= 55
    assert (df["vehicles_involved"].dropna() >= 1).all()


def test_coordinates_flagged_not_moved(cleaned_fixture):
    _, df, _, _ = cleaned_fixture
    assert (df["coord_valid"] == 0).sum() >= 2
    assert ((df["latitude"] == 0) & (df["coord_valid"] == 1)).sum() == 0


def test_time_is_authoritative_and_day_recomputed(cleaned_fixture):
    _, df, _, _ = cleaned_fixture
    ok = df["date"].notna()
    assert (df.loc[ok, "day_of_week"] == df.loc[ok, "date"].dt.day_name()).all()
    t = df["time"].dropna().str.slice(0, 2).astype(int)
    assert (t == df.loc[t.index, "hour"]).all()


def test_reports_written(cleaned_fixture):
    root = cleaned_fixture[3]
    for f in ["processed/cleaned_road_accidents.csv", "processed/data_profile.json",
              "processed/cleaning_log.json", "reports/data_profile.md", "reports/cleaning_report.md"]:
        assert (root / f).exists(), f


def test_real_cleaned_file_complete():
    from src.data_loader import load_clean, load_raw
    raw, clean = load_raw(REAL_RAW), load_clean(ROOT / "data" / "processed" / "cleaned_road_accidents.csv")
    assert len(clean) == len(raw) == 20000
    assert set(raw.columns) <= set(clean.columns)          # no column silently dropped
    assert clean["accident_id"].is_unique
    m = raw.set_index("accident_id").join(clean.set_index("accident_id").add_suffix("_c"))
    for col in ["casualties", "vehicles_involved", "risk_score", "lanes", "temperature", "latitude"]:
        assert np.allclose(m[col].astype(float), m[col + "_c"].astype(float)), col
    for col in ["city", "cause", "accident_severity", "weather", "road_type"]:
        assert (m[col].str.strip().str.lower() == m[col + "_c"].str.lower()).all(), col
    assert (pd.to_datetime(m["date"]) == m["date_c"]).all()
