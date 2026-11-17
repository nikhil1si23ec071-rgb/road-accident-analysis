"""Every KPI/aggregate equals an independent pandas computation on the raw CSV."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_kpis import verify  # noqa: E402


def test_all_kpis_match_independent_calculation():
    table, ok = verify()
    bad = table[~table["match"] | (table["matches_notebook"] == False)]  # noqa: E712
    assert ok, bad.to_string()
