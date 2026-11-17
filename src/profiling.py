"""Phase 1 — dataset inspection and profiling of the *raw* CSV.

`profile_dataset()` returns a nested dict that is saved as JSON and rendered
to Markdown (reports/data_profile.md). Nothing here modifies the data.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats

from src import config
from src.utils import haversine_km, norm_key


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #
def _column_overview(df: pd.DataFrame) -> list[dict]:
    rows = []
    for col in df.columns:
        s = df[col]
        kind = ("numeric" if col in config.NUMERIC_COLUMNS
                else "binary" if col in config.BINARY_COLUMNS
                else "identifier" if col == "accident_id"
                else "date/time" if col in ("date", "time")
                else "categorical")
        rows.append({
            "column": col,
            "dtype": str(s.dtype),
            "role": kind,
            "missing": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean() * 100), 3),
            "unique": int(s.nunique(dropna=True)),
            "examples": [str(v) for v in s.dropna().unique()[:5]],
        })
    return rows


def _numeric_summary(df: pd.DataFrame) -> dict:
    out = {}
    for col in config.NUMERIC_COLUMNS + config.BINARY_COLUMNS:
        if col not in df:
            continue
        x = pd.to_numeric(df[col], errors="coerce")
        non_numeric = int(x.isna().sum() - df[col].isna().sum())
        q1, q3 = x.quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        entry = {
            "count": int(x.notna().sum()), "mean": x.mean(), "std": x.std(),
            "min": x.min(), "q1": q1, "median": x.median(), "q3": q3,
            "max": x.max(), "skew": x.skew(),
            "non_numeric_values": non_numeric,
            "iqr_outliers": (None if col in config.BINARY_COLUMNS
                             else int(((x < lo) | (x > hi)).sum())),
            "zscore_outliers_gt3": (None if col in config.BINARY_COLUMNS
                                    else int((np.abs(stats.zscore(x, nan_policy="omit")) > 3).sum())),
            "distinct_values": int(x.nunique()),
        }
        if col in config.VALID_RANGES:
            vmin, vmax = config.VALID_RANGES[col]
            entry["valid_range"] = [vmin, vmax]
            entry["impossible_values"] = int(((x < vmin) | (x > vmax)).sum())
        if col in config.BINARY_COLUMNS:
            entry["non_binary_values"] = int((~x.isin([0, 1]) & x.notna()).sum())
        out[col] = entry
    return out


def _categorical_summary(df: pd.DataFrame) -> dict:
    out = {}
    for col in config.CATEGORICAL_COLUMNS:
        if col not in df:
            continue
        s = df[col]
        vc = s.value_counts(dropna=False)
        # spelling variants: distinct raw strings that collapse to one key
        groups = defaultdict(set)
        for raw in s.dropna().unique():
            groups[norm_key(raw)].add(str(raw))
        variants = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
        out[col] = {
            "n_unique": int(s.nunique(dropna=True)),
            "value_counts": {("<missing>" if pd.isna(k) else str(k)): int(v)
                             for k, v in vc.head(30).items()},
            "spelling_variants": variants,
            "leading_trailing_spaces": int(s.dropna().astype(str)
                                           .ne(s.dropna().astype(str).str.strip()).sum()),
        }
    return out


def _duplicates(df: pd.DataFrame) -> dict:
    res = {
        "exact_duplicate_rows": int(df.duplicated().sum()),
    }
    if "accident_id" in df:
        ids = df["accident_id"]
        res["accident_id_unique"] = bool(ids.is_unique)
        res["duplicate_accident_ids"] = int(ids.duplicated().sum())
        res["missing_accident_ids"] = int(ids.isna().sum())
        num = pd.to_numeric(ids, errors="coerce")
        if num.notna().all() and len(num):
            res["accident_id_is_sequential_0_to_n_minus_1"] = bool(
                (np.sort(num.values) == np.arange(len(num))).all())
        rest = [c for c in df.columns if c != "accident_id"]
        res["duplicate_rows_ignoring_id"] = int(df.duplicated(subset=rest).sum())
    return res


def _dates_and_times(df: pd.DataFrame) -> dict:
    res = {}
    if "date" in df:
        raw = df["date"].astype("string")
        iso = raw.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
        parsed = pd.to_datetime(df["date"], errors="coerce", format="mixed")
        res["date"] = {
            "iso_yyyy_mm_dd_share_pct": round(float(iso.mean() * 100), 3),
            "unparseable": int(parsed.isna().sum() - df["date"].isna().sum()),
            "missing": int(df["date"].isna().sum()),
            "min": parsed.min(), "max": parsed.max(),
            "distinct_days": int(parsed.dt.normalize().nunique()),
            "records_per_year": {int(k): int(v) for k, v in
                                 parsed.dt.year.value_counts().sort_index().items()},
        }
        if parsed.notna().any():
            last = parsed.max()
            res["date"]["last_month_days_covered"] = int(
                parsed[parsed.dt.to_period("M") == last.to_period("M")].dt.day.max())
            res["date"]["last_month_days_in_month"] = int(last.days_in_month)
            per_year_months = parsed.dt.to_period("M").groupby(parsed.dt.year).nunique()
            res["date"]["months_covered_per_year"] = {int(k): int(v) for k, v in per_year_months.items()}
        if "day_of_week" in df:
            derived = parsed.dt.day_name()
            ok = parsed.notna() & df["day_of_week"].notna()
            res["day_of_week_matches_date_pct"] = round(float(
                (derived[ok].str.lower() == df.loc[ok, "day_of_week"].astype(str).str.strip().str.lower()).mean() * 100), 3)
        if "is_weekend" in df:
            derived_we = parsed.dt.day_of_week.isin([5, 6]).astype(int)
            ok = parsed.notna() & df["is_weekend"].notna()
            res["is_weekend_matches_date_pct"] = round(float(
                (derived_we[ok] == pd.to_numeric(df.loc[ok, "is_weekend"], errors="coerce")).mean() * 100), 3)
    if "time" in df:
        t = df["time"].astype("string").str.strip()
        pattern = t.str.replace(r"\d", "9", regex=True)
        m = t.str.extract(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")
        hh, mm = pd.to_numeric(m[0], errors="coerce"), pd.to_numeric(m[1], errors="coerce")
        res["time"] = {
            "format_patterns": {str(k): int(v) for k, v in pattern.value_counts().head(10).items()},
            "unparseable": int(hh.isna().sum() - df["time"].isna().sum()),
            "share_on_the_hour_pct": round(float((mm == 0).mean() * 100), 3),
        }
        if "hour" in df:
            h = pd.to_numeric(df["hour"], errors="coerce")
            ok = hh.notna() & h.notna()
            res["time"]["hour_matches_time_pct"] = round(float((hh[ok] == h[ok]).mean() * 100), 3)
    return res


def _peak_hour_rule(df: pd.DataFrame) -> dict:
    if not {"hour", "is_peak_hour"} <= set(df.columns):
        return {}
    h = pd.to_numeric(df["hour"], errors="coerce")
    p = pd.to_numeric(df["is_peak_hour"], errors="coerce")
    share = p.groupby(h).mean()
    peak_hours = sorted(int(x) for x in share[share > 0.5].index)
    implied = h.isin(peak_hours).astype(int)
    ok = h.notna() & p.notna()
    return {
        "inferred_peak_hours": peak_hours,
        "is_peak_hour_matches_rule_pct": round(float((implied[ok] == p[ok]).mean() * 100), 3),
    }


def _coordinates(df: pd.DataFrame) -> dict:
    if not {"latitude", "longitude"} <= set(df.columns):
        return {"available": False}
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    in_india = lat.between(*config.INDIA_LAT) & lon.between(*config.INDIA_LON)
    res = {
        "available": True,
        "missing": int((lat.isna() | lon.isna()).sum()),
        "outside_india_bbox": int((~in_india & lat.notna() & lon.notna()).sum()),
        "zero_zero": int(((lat == 0) & (lon == 0)).sum()),
        "decimal_places_typical": int(df["latitude"].astype(str).str.split(".").str[-1].str.len().median()),
    }
    if "city" in df:
        city = df["city"].map(norm_key)
        cen = pd.DataFrame({"lat": lat.where(in_india), "lon": lon.where(in_india), "city": city}) \
            .groupby("city")[["lat", "lon"]].median()
        d = haversine_km(lat, lon, city.map(cen["lat"]), city.map(cen["lon"]))
        d = pd.Series(d, index=df.index)
        res["km_from_city_median"] = {
            "median": float(np.nanmedian(d)), "p95": float(np.nanpercentile(d, 95)),
            "max": float(np.nanmax(d)),
            f"beyond_{config.MAX_KM_FROM_CITY_CENTRE}km": int((d > config.MAX_KM_FROM_CITY_CENTRE).sum()),
        }
        spread = pd.DataFrame({"lat": lat, "lon": lon, "city": city}).groupby("city").agg(
            lat_min=("lat", "min"), lat_max=("lat", "max"),
            lon_min=("lon", "min"), lon_max=("lon", "max"))
        res["per_city_extent_deg"] = {
            k: {"lat_range": round(r.lat_max - r.lat_min, 3), "lon_range": round(r.lon_max - r.lon_min, 3)}
            for k, r in spread.iterrows()}
        if "state" in df:
            pairs = df.groupby(city)["state"].nunique()
            res["cities_mapped_to_multiple_states"] = [str(c) for c in pairs[pairs > 1].index]
    return res


def _logical_consistency(df: pd.DataFrame) -> dict:
    res = {}
    if {"accident_severity", "casualties"} <= set(df.columns):
        sev = df["accident_severity"].map(norm_key)
        cas = pd.to_numeric(df["casualties"], errors="coerce")
        res["fatal_with_zero_casualties"] = int(((sev == "fatal") & (cas == 0)).sum())
        res["major_with_zero_casualties"] = int(((sev == "major") & (cas == 0)).sum())
        res["casualties_by_severity_mean"] = {str(k): float(v) for k, v in cas.groupby(sev).mean().items()}
        res["zero_casualty_records"] = int((cas == 0).sum())
    if {"vehicles_involved", "casualties"} <= set(df.columns):
        v = pd.to_numeric(df["vehicles_involved"], errors="coerce")
        c = pd.to_numeric(df["casualties"], errors="coerce")
        res["casualties_equal_vehicles_pct"] = round(float((v == c).mean() * 100), 3)
        res["casualties_exceed_vehicles_pct"] = round(float((c > v).mean() * 100), 3)
        if "accident_severity" in df:
            sev = df["accident_severity"].map(norm_key)
            res["fatal_casualties_equal_vehicles_pct"] = round(float((c[sev == "fatal"] == v[sev == "fatal"]).mean() * 100), 3)
    if {"weather", "visibility"} <= set(df.columns):
        ct = pd.crosstab(df["weather"].map(norm_key), df["visibility"].map(norm_key))
        res["weather_vs_visibility"] = {str(i): {str(k): int(v) for k, v in row.items()}
                                        for i, row in ct.iterrows()}
        res["visibility_determined_by_weather_pct"] = round(float(ct.max(axis=1).sum() / ct.values.sum() * 100), 3)
    return res


RISK_FORMULA_TEXT = ("risk_score = min(1, 0.10 + 0.20·[severity = fatal] + 0.20·[traffic_density = high] "
                     "+ 0.15·[is_peak_hour] + 0.15·[weather ∈ {fog, rain}] + 0.20·[visibility = low] "
                     "+ 0.10·[festival recorded])")


def reconstruct_risk_score(df: pd.DataFrame) -> pd.Series:
    """Additive rule reverse-engineered from the data (least squares, then
    rounded to the obvious coefficients). Used only to *audit* risk_score."""
    sev = df["accident_severity"].map(norm_key)
    dens = df["traffic_density"].map(norm_key)
    wea = df["weather"].map(norm_key)
    vis = df["visibility"].map(norm_key)
    peak = pd.to_numeric(df["is_peak_hour"], errors="coerce").fillna(0)
    fest_col = "festival" if "festival" in df else "festival_name"
    fest = df[fest_col].notna() & (df[fest_col].astype(str) != "No Festival")
    r = (0.10 + 0.20 * (sev == "fatal") + 0.20 * (dens == "high") + 0.15 * peak
         + 0.15 * wea.isin(["fog", "rain"]) + 0.20 * (vis == "low") + 0.10 * fest)
    return r.clip(upper=1.0)


def risk_formula_check(df: pd.DataFrame) -> dict:
    need = {"accident_severity", "traffic_density", "weather", "visibility", "is_peak_hour", "risk_score"}
    if not need <= set(df.columns):
        return {}
    pred = reconstruct_risk_score(df)
    actual = pd.to_numeric(df["risk_score"], errors="coerce")
    diff = (pred - actual).abs()
    return {"formula": RISK_FORMULA_TEXT,
            "exact_match_pct": round(float((diff < 1e-6).mean() * 100), 3),
            "max_abs_difference": float(diff.max())}


def _risk_score_audit(df: pd.DataFrame) -> dict:
    if "risk_score" not in df:
        return {}
    r = pd.to_numeric(df["risk_score"], errors="coerce")
    vals = np.sort(r.dropna().unique())
    steps = np.round(np.diff(vals), 6) if len(vals) > 1 else np.array([])
    res = {
        "distinct_values": int(len(vals)),
        "values": [float(v) for v in vals[:40]],
        "smallest_step": float(steps.min()) if len(steps) else None,
    }
    # association of risk score with each candidate input (eta-squared / Spearman)
    assoc = {}
    for col in ["accident_severity", "cause", "weather", "visibility", "road_type",
                "traffic_density", "city", "festival", "time", "day_of_week"]:
        if col not in df:
            continue
        g = df[col].map(norm_key).fillna("<missing>")
        grand = r.mean()
        ss_between = (r.groupby(g).count() * (r.groupby(g).mean() - grand) ** 2).sum()
        ss_total = ((r - grand) ** 2).sum()
        assoc[col] = round(float(ss_between / ss_total), 4) if ss_total else None
    for col in ["hour", "lanes", "temperature", "vehicles_involved", "casualties",
                "is_weekend", "traffic_signal", "is_peak_hour"]:
        if col in df:
            x = pd.to_numeric(df[col], errors="coerce")
            ok = x.notna() & r.notna()
            if ok.sum() > 2 and x[ok].nunique() > 1:
                assoc[col] = round(float(stats.spearmanr(x[ok], r[ok]).statistic ** 2), 4)
    res["formula_check"] = risk_formula_check(df)
    res["share_of_variance_explained_by_column"] = dict(sorted(assoc.items(), key=lambda kv: -(kv[1] or 0)))
    if "accident_severity" in df:
        res["mean_by_severity"] = {str(k): float(v) for k, v in
                                   r.groupby(df["accident_severity"].map(norm_key)).mean().items()}
    return res


def _uniformity_tests(df: pd.DataFrame) -> dict:
    """Chi-square goodness-of-fit against a uniform distribution. Real crash
    data is strongly non-uniform across hour, weekday, city and cause; a
    dataset where *every* marginal is uniform is a fingerprint of simulation."""
    res = {}
    candidates = {"city": df.get("city"), "hour": df.get("hour"),
                  "day_of_week": df.get("day_of_week"), "cause": df.get("cause"),
                  "weather": df.get("weather"), "road_type": df.get("road_type"),
                  "lanes": df.get("lanes"), "traffic_density": df.get("traffic_density")}
    if "date" in df:
        d = pd.to_datetime(df["date"], errors="coerce")
        full = d[d.dt.to_period("M") != d.max().to_period("M")] if d.notna().any() else d
        candidates["month (complete months)"] = full.dt.to_period("M").astype(str).where(full.notna())
    for name, s in candidates.items():
        if s is None:
            continue
        counts = s.dropna().map(lambda v: norm_key(v) if isinstance(v, str) else v).value_counts()
        if len(counts) < 2:
            continue
        r = stats.chisquare(counts.values)
        res[name] = {"categories": int(len(counts)), "chi2": float(r.statistic),
                     "p_value": float(r.pvalue),
                     "max_to_min_ratio": float(counts.max() / counts.min()),
                     "consistent_with_uniform": bool(r.pvalue > config.ALPHA)}
    return res


def _festival_audit(df: pd.DataFrame) -> dict:
    if not {"festival", "date"} <= set(df.columns):
        return {}
    d = pd.to_datetime(df["date"], errors="coerce")
    f = df["festival"]
    res = {"records_with_festival": int(f.notna().sum()), "labels": {}}
    for label, grp in d[f.notna()].groupby(f[f.notna()].astype(str).str.strip()):
        key = next((k for k in config.FESTIVAL_CALENDAR if k.lower() == label.lower()), None)
        entry = {"records": int(len(grp)), "distinct_dates": int(grp.dt.normalize().nunique()),
                 "months_seen": sorted({int(m) for m in grp.dt.month.dropna()})}
        if key:
            ref = pd.to_datetime(config.FESTIVAL_CALENDAR[key])
            near = grp.apply(lambda x: bool(pd.notna(x) and (abs(ref - x) <= pd.Timedelta(days=1)).any()))
            entry["on_actual_festival_date_pct"] = round(float(near.mean() * 100), 2)
        entry["dates"] = sorted(str(x.date()) for x in grp.dt.normalize().unique())
        res["labels"][label] = entry
    # coverage: real festival dates inside the data window, labelled or not
    lo, hi = d.min(), d.max()
    cov = []
    for name, dates in config.FESTIVAL_CALENDAR.items():
        for ds in dates:
            day = pd.Timestamp(ds)
            if not (lo <= day <= hi):
                continue
            window = (d - day).abs() <= pd.Timedelta(days=1)
            same = d.dt.normalize() == day
            if not window.any():
                continue
            cov.append({"festival": name, "reference_date": ds,
                        "records_on_date": int(same.sum()),
                        "labelled_within_1_day": int((window & f.notna()).sum())})
    res["calendar_coverage"] = cov
    res["festival_dates_never_labelled"] = [f"{c['festival']} {c['reference_date']}" for c in cov
                                            if c["labelled_within_1_day"] == 0 and c["records_on_date"] > 0]
    return res


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def profile_dataset(df: pd.DataFrame) -> dict:
    expected, actual = set(config.EXPECTED_COLUMNS), set(df.columns)
    profile = {
        "shape": {"rows": int(len(df)), "columns": int(df.shape[1])},
        "schema": {
            "missing_expected_columns": sorted(expected - actual),
            "unexpected_columns": sorted(actual - expected),
        },
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1e6, 2),
        "columns": _column_overview(df),
        "numeric": _numeric_summary(df),
        "categorical": _categorical_summary(df),
        "duplicates": _duplicates(df),
        "dates_times": _dates_and_times(df),
        "peak_hour": _peak_hour_rule(df),
        "coordinates": _coordinates(df),
        "consistency": _logical_consistency(df),
        "risk_score": _risk_score_audit(df),
        "uniformity": _uniformity_tests(df),
        "festival": _festival_audit(df),
    }
    profile["derived_columns"] = _derived_column_verdicts(profile)
    profile["provenance"] = _provenance_verdict(profile)
    return profile


def _derived_column_verdicts(p: dict) -> list[dict]:
    out = []
    dt = p["dates_times"]
    if "hour_matches_time_pct" in dt.get("time", {}):
        out.append({"column": "hour", "derived_from": "time",
                    "agreement_pct": dt["time"]["hour_matches_time_pct"]})
    if "day_of_week_matches_date_pct" in dt:
        out.append({"column": "day_of_week", "derived_from": "date",
                    "agreement_pct": dt["day_of_week_matches_date_pct"]})
    if "is_weekend_matches_date_pct" in dt:
        out.append({"column": "is_weekend", "derived_from": "date",
                    "agreement_pct": dt["is_weekend_matches_date_pct"]})
    if p["peak_hour"]:
        out.append({"column": "is_peak_hour",
                    "derived_from": f"hour ∈ {p['peak_hour']['inferred_peak_hours']}",
                    "agreement_pct": p["peak_hour"]["is_peak_hour_matches_rule_pct"]})
    c = p["consistency"]
    if "visibility_determined_by_weather_pct" in c:
        out.append({"column": "visibility", "derived_from": "weather (modal mapping)",
                    "agreement_pct": c["visibility_determined_by_weather_pct"]})
    rs = p["risk_score"].get("share_of_variance_explained_by_column", {})
    if rs:
        top = next(iter(rs.items()))
        out.append({"column": "risk_score",
                    "derived_from": f"composite; strongest single input = {top[0]} "
                                    f"({top[1]*100:.1f}% of variance)",
                    "agreement_pct": None})
    return out


def _provenance_verdict(p: dict) -> dict:
    signals = []
    uni = p["uniformity"]
    n_uniform = sum(v["consistent_with_uniform"] for v in uni.values())
    if uni:
        signals.append(f"{n_uniform} of {len(uni)} categorical/temporal marginals are statistically "
                       f"indistinguishable from a uniform distribution (chi-square, α={config.ALPHA}).")
    t = p["dates_times"].get("time", {})
    if t.get("share_on_the_hour_pct", 0) > 99:
        signals.append("Every timestamp is exactly on the hour (minutes = 00).")
    fest = p["festival"].get("labels", {})
    off = [k for k, v in fest.items() if v.get("on_actual_festival_date_pct", 100) < 50]
    if off:
        signals.append("Festival labels do not align with the real festival dates for: "
                       + ", ".join(off) + ".")
    rs = p["risk_score"]
    if rs.get("distinct_values") and rs["distinct_values"] <= 25:
        signals.append(f"risk_score takes only {rs['distinct_values']} discrete values "
                       f"(step {rs.get('smallest_step')}).")
    fc = p["risk_score"].get("formula_check", {})
    if fc.get("exact_match_pct", 0) > 99:
        signals.append(f"risk_score is reproduced exactly ({fc['exact_match_pct']}% of rows) by a simple additive "
                       f"rule: {fc['formula']}.")
    if p["consistency"].get("fatal_casualties_equal_vehicles_pct", 0) > 99:
        signals.append("For every fatal accident, casualties == vehicles_involved exactly; casualties never exceed "
                       "vehicles in any record — a generation rule, not an observed pattern.")
    if p["consistency"].get("major_with_zero_casualties", 0) > 0:
        signals.append(f"{p['consistency']['major_with_zero_casualties']:,} 'major' accidents record zero casualties "
                       "(logically inconsistent with a major-injury classification).")
    if p["festival"].get("festival_dates_never_labelled"):
        signals.append("Festival labels cover only some years; real festival days with records but no label: "
                       + ", ".join(p["festival"]["festival_dates_never_labelled"]) + ".")
    if p["consistency"].get("fatal_with_zero_casualties", 0) > 0:
        signals.append(f"{p['consistency']['fatal_with_zero_casualties']} 'fatal' accidents record zero casualties.")
    if p["duplicates"].get("accident_id_is_sequential_0_to_n_minus_1"):
        signals.append("accident_id is a plain 0…n-1 row index rather than an official FIR / iRAD reference.")
    likely_synthetic = len(signals) >= 3
    return {
        "source": "Kaggle dataset 'Indian Road Accident Dataset 2022–2025' uploaded by user "
                  "sehaj1104. No collecting agency, methodology or licence linking it to MoRTH, "
                  "NCRB or iRAD records is documented.",
        "signals": signals,
        "verdict": ("Likely SIMULATED / SYNTHETIC. Treat all findings as properties of this "
                    "dataset, not of Indian road safety.") if likely_synthetic else
                   ("Provenance unverified. Treat as reported, unofficial data."),
        "likely_synthetic": likely_synthetic,
    }


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #
def _md_table(rows: list[dict], cols: list[str] | None = None) -> str:
    if not rows:
        return "_none_\n"
    cols = cols or list(rows[0].keys())
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                v = f"{v:,.4g}"
            elif isinstance(v, list):
                v = ", ".join(map(str, v))
            cells.append(str(v).replace("|", "/"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def profile_to_markdown(p: dict) -> str:
    s = []
    s.append("# Dataset Profile — raw `indian_roads_dataset.csv`\n")
    s.append("_Generated automatically by `python -m src.preprocessing`. The raw file is never modified._\n")
    s.append(f"**Records:** {p['shape']['rows']:,} · **Columns:** {p['shape']['columns']} · "
             f"**Memory:** {p['memory_mb']} MB\n")
    sch = p["schema"]
    s.append(f"Missing expected columns: {sch['missing_expected_columns'] or 'none'} · "
             f"Unexpected columns: {sch['unexpected_columns'] or 'none'}\n")

    s.append("\n## 1. Provenance assessment\n")
    pv = p["provenance"]
    s.append(f"**Source.** {pv['source']}\n\n**Verdict: {pv['verdict']}**\n")
    for sig in pv["signals"]:
        s.append(f"- {sig}")
    s.append("")

    s.append("\n## 2. Columns\n")
    s.append(_md_table(p["columns"], ["column", "dtype", "role", "missing", "missing_pct", "unique", "examples"]))

    s.append("\n## 3. Numerical columns\n")
    rows = [{"column": k, **{kk: v.get(kk) for kk in ["count", "mean", "std", "min", "median", "max",
                                                      "iqr_outliers", "impossible_values", "distinct_values"]}}
            for k, v in p["numeric"].items()]
    s.append(_md_table(rows))

    s.append("\n## 4. Categorical columns\n")
    for col, info in p["categorical"].items():
        vc = ", ".join(f"{k} ({v:,})" for k, v in list(info["value_counts"].items())[:12])
        s.append(f"- **{col}** — {info['n_unique']} unique: {vc}")
        if info["spelling_variants"]:
            s.append(f"  - spelling variants: {info['spelling_variants']}")
        if info["leading_trailing_spaces"]:
            s.append(f"  - values with stray whitespace: {info['leading_trailing_spaces']}")
    s.append("")

    s.append("\n## 5. Duplicates and identifiers\n")
    for k, v in p["duplicates"].items():
        s.append(f"- {k.replace('_', ' ')}: **{v}**")

    s.append("\n## 6. Dates and times\n")
    dt = p["dates_times"]
    for k, v in dt.get("date", {}).items():
        s.append(f"- date · {k.replace('_', ' ')}: {v}")
    for k, v in dt.get("time", {}).items():
        s.append(f"- time · {k.replace('_', ' ')}: {v}")
    for k in ("day_of_week_matches_date_pct", "is_weekend_matches_date_pct"):
        if k in dt:
            s.append(f"- {k.replace('_', ' ')}: {dt[k]}%")
    if p["peak_hour"]:
        s.append(f"- inferred peak hours: {p['peak_hour']['inferred_peak_hours']} "
                 f"(rule agreement {p['peak_hour']['is_peak_hour_matches_rule_pct']}%)")

    s.append("\n## 7. Coordinates\n")
    for k, v in p["coordinates"].items():
        if k != "per_city_extent_deg":
            s.append(f"- {k.replace('_', ' ')}: {v}")

    s.append("\n## 8. Logical consistency\n")
    for k, v in p["consistency"].items():
        s.append(f"- {k.replace('_', ' ')}: {v}")

    s.append("\n## 9. Derived / leakage-prone columns\n")
    s.append(_md_table(p["derived_columns"]))
    rs = p["risk_score"]
    if rs.get("formula_check"):
        fc = rs["formula_check"]
        s.append(f"\n**risk_score reconstruction:** `{fc['formula']}` → exact match on "
                 f"**{fc['exact_match_pct']}%** of rows (max |Δ| = {fc['max_abs_difference']:.2g}). "
                 "Because severity is an input, risk_score must not be used to explain or predict severity.\n")
    if rs:
        s.append(f"\n`risk_score`: {rs['distinct_values']} distinct values; mean by severity "
                 f"{ {k: round(v, 3) for k, v in rs.get('mean_by_severity', {}).items()} }.\n")
        s.append("Share of risk_score variance explained by each column (η² or Spearman ρ²):\n")
        s.append(_md_table([{"column": k, "variance_explained": v}
                            for k, v in rs["share_of_variance_explained_by_column"].items()]))

    s.append("\n## 10. Uniformity tests (synthetic-data fingerprint)\n")
    s.append(_md_table([{"variable": k, **v} for k, v in p["uniformity"].items()]))

    s.append("\n## 11. Festival label audit\n")
    fest = p["festival"]
    if fest:
        s.append(f"Records with a festival label: {fest['records_with_festival']}\n")
        s.append(_md_table([{"festival": k, **v} for k, v in fest["labels"].items()]))
        s.append("\nCoverage of real festival dates inside the data window:\n")
        s.append(_md_table(fest.get("calendar_coverage", [])))
    return "\n".join(s) + "\n"
