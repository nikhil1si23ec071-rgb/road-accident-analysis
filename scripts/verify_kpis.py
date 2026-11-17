"""Independent verification of every dashboard KPI and key aggregate.

Expected values are computed here with plain pandas straight from the RAW CSV
(no project code), then compared with what src.analysis returns from the
CLEANED data — i.e. what the dashboard shows. A third column checks against
aggregates embedded in the original Kaggle notebook's outputs.

    python scripts/verify_kpis.py        # writes reports/kpi_verification.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import analysis as A  # noqa: E402
from src.data_loader import ensure_clean_data  # noqa: E402

# Values read from the plot/table outputs embedded in the original notebook
# (notebooks/original_kaggle_eda.ipynb), used as a third, external reference.
NOTEBOOK = {
    "accidents": 20000, "fatal": 2987, "major": 5988, "minor": 11025,
    "city:Chandigarh": 2577, "city:Hyderabad": 2409, "state:Maharashtra": 5009,
    "casualties city:Chennai": 4567, "cause:distraction": 4026, "weather:fog": 6633,
    "fatal_rate road:urban": 15.404002965159377, "fatal_rate cause:poor road": 15.68,
    "festival:Holi": 38, "peak accidents": 4948, "avg_casualties fatal": 3.0016739203213927,
}


def expected_from_raw(raw: pd.DataFrame) -> dict:
    sev = raw["accident_severity"]
    e = {
        "accidents": len(raw),
        "casualties": int(raw["casualties"].sum()),
        "fatal": int((sev == "fatal").sum()),
        "major": int((sev == "major").sum()),
        "minor": int((sev == "minor").sum()),
        "fatal_pct": (sev == "fatal").mean() * 100,
        "avg_casualties": raw["casualties"].mean(),
        "avg_vehicles": raw["vehicles_involved"].mean(),
        "avg_risk": raw["risk_score"].mean(),
    }
    for c, n in raw["city"].value_counts().items():
        e[f"city:{c}"] = int(n)
    for c, n in raw["state"].value_counts().items():
        e[f"state:{c}"] = int(n)
    for c, n in raw.groupby("city")["casualties"].sum().items():
        e[f"casualties city:{c}"] = int(n)
    for c, n in raw["cause"].value_counts().items():
        e[f"cause:{c}"] = int(n)
    for c, n in raw["weather"].value_counts().items():
        e[f"weather:{c}"] = int(n)
    for c, r in raw.groupby("road_type")["accident_severity"].apply(lambda s: (s == "fatal").mean() * 100).items():
        e[f"fatal_rate road:{c}"] = r
    for c, r in raw.groupby("cause")["accident_severity"].apply(lambda s: (s == "fatal").mean() * 100).items():
        e[f"fatal_rate cause:{c}"] = r
    for c, n in raw["festival"].value_counts().items():
        e[f"festival:{c}"] = int(n)
    e["peak accidents"] = int(raw["is_peak_hour"].sum())
    e["avg_casualties fatal"] = raw.loc[sev == "fatal", "casualties"].mean()
    d = pd.to_datetime(raw["date"])
    for y, n in d.dt.year.value_counts().items():
        e[f"year:{y}"] = int(n)
    e["weekend accidents"] = int(raw["is_weekend"].sum())
    # Pune + fatal, used in the UI tests
    e["Pune fatal"] = int(((raw["city"] == "Pune") & (sev == "fatal")).sum())
    return e


def actual_from_dashboard(df: pd.DataFrame) -> dict:
    k = A.kpis(df)
    a = {key: k[key] for key in ["accidents", "casualties", "fatal", "major", "minor", "fatal_pct",
                                 "avg_casualties", "avg_vehicles", "avg_risk"]}
    for col, prefix in [("city", "city"), ("state", "state"), ("cause", "cause"), ("weather", "weather"),
                        ("festival_name", "festival")]:
        for _, r in A.group_summary(df, col).iterrows():
            if r[col] != "No Festival":
                a[f"{prefix}:{r[col]}"] = int(r["accidents"])
    for _, r in A.group_summary(df, "city").iterrows():
        a[f"casualties city:{r['city']}"] = int(r["casualties"])
    for _, r in A.group_summary(df, "road_type").iterrows():
        a[f"fatal_rate road:{r['road_type']}"] = r["fatal_rate"]
    for _, r in A.group_summary(df, "cause").iterrows():
        a[f"fatal_rate cause:{r['cause']}"] = r["fatal_rate"]
    a["peak accidents"] = int(A.group_summary(df, "peak_label").set_index("peak_label").loc["Peak hour", "accidents"])
    a["avg_casualties fatal"] = A.group_summary(df, "accident_severity").set_index("accident_severity").loc["fatal", "avg_casualties"]
    for _, r in A.yearly_trend(df).iterrows():
        a[f"year:{int(r['year'])}"] = int(r["accidents"])
    a["weekend accidents"] = int(A.weekday_weekend(df).set_index("day_type").loc["Weekend", "accidents"])
    a["Pune fatal"] = A.kpis(df[df["city"] == "Pune"])["fatal"]
    return a


def verify() -> tuple[pd.DataFrame, bool]:
    raw = pd.read_csv(ROOT / "data" / "raw" / "indian_roads_dataset.csv")
    df = ensure_clean_data()
    exp, act = expected_from_raw(raw), actual_from_dashboard(df)
    rows = []
    for key in exp:
        e, a = exp[key], act.get(key, np.nan)
        nb = NOTEBOOK.get(key)
        ok = bool(np.isclose(float(e), float(a), rtol=0, atol=1e-9))
        nb_ok = None if nb is None else bool(np.isclose(float(nb), float(a), atol=0.01))
        rows.append({"metric": key, "independent_pandas_on_raw": e, "dashboard": a, "match": ok,
                     "notebook_value": nb, "matches_notebook": nb_ok})
    t = pd.DataFrame(rows)
    return t, bool(t["match"].all() and t["matches_notebook"].dropna().all())


def main():
    t, ok = verify()
    out = ROOT / "reports" / "kpi_verification.md"
    out.parent.mkdir(exist_ok=True)
    fmt = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else (f"{v:,.6g}" if isinstance(v, float) else f"{v:,}" if isinstance(v, (int, np.integer)) else str(v))  # noqa: E731
    lines = ["# KPI Verification\n",
             "Expected values are recomputed with plain pandas from the **raw** CSV (no project code) and compared "
             "with the dashboard's functions on the **cleaned** data. Notebook values were read from the outputs "
             "embedded in the original notebook.\n",
             f"**Result: {'ALL ' + str(len(t)) + ' CHECKS PASS' if ok else 'MISMATCHES FOUND'}** "
             f"({int(t['match'].sum())}/{len(t)} vs raw; {int(t['matches_notebook'].dropna().sum())}/"
             f"{int(t['matches_notebook'].notna().sum())} vs notebook)\n",
             "| Metric | Independent (raw) | Dashboard | Match | Notebook | Matches notebook |",
             "|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        nbm = "" if r["matches_notebook"] is None or pd.isna(r["matches_notebook"]) else ("✅" if r["matches_notebook"] else "❌")
        lines.append(f"| {r['metric']} | {fmt(r['independent_pandas_on_raw'])} | {fmt(r['dashboard'])} | "
                     f"{'✅' if r['match'] else '❌'} | {fmt(r['notebook_value'])} | {nbm} |")
    out.write_text("\n".join(lines) + "\n")
    print(f"{int(t['match'].sum())}/{len(t)} metrics match the independent calculation; "
          f"{int(t['matches_notebook'].dropna().sum())}/{int(t['matches_notebook'].notna().sum())} match the notebook. → {out}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
