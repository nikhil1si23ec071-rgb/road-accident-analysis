"""Phase 2 — cleaning and feature engineering.

Run as a script to (re)build everything derived from the raw CSV:

    python -m src.preprocessing

Outputs
    data/processed/cleaned_road_accidents.csv   cleaned + engineered dataset
    data/processed/data_profile.json            machine-readable raw profile
    data/processed/cleaning_log.json            every cleaning action
    reports/data_profile.md                     human-readable raw profile
    reports/cleaning_report.md                  human-readable cleaning log

The raw CSV is opened read-only; its SHA-256 is checked before and after.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src import config
from src.data_loader import load_raw
from src.profiling import profile_dataset, profile_to_markdown, reconstruct_risk_score
from src.utils import haversine_km, norm_key, to_jsonable


@dataclass
class LogEntry:
    step: str
    column: str
    action: str
    rows_affected: int
    rationale: str


class CleaningLog(list):
    def add(self, step, column, action, rows, rationale):
        self.append(LogEntry(step, column, action, int(rows), rationale))


# --------------------------------------------------------------------------- #
# Cleaning steps
# --------------------------------------------------------------------------- #
def _ensure_schema(df, log):
    for col in config.EXPECTED_COLUMNS:
        if col not in df:
            df[col] = np.nan
            log.add("schema", col, "added empty column", len(df),
                    "Expected column absent from the file; created as missing so downstream "
                    "code degrades gracefully instead of crashing.")
    extra = [c for c in df.columns if c not in config.EXPECTED_COLUMNS]
    for c in extra:
        log.add("schema", c, "kept unexpected column", 0,
                "Not part of the documented schema; retained untouched (never silently dropped).")
    return df


def _strip_text(df, log):
    for col in df.select_dtypes(include=["object", "string"]).columns:
        s = df[col]
        stripped = s.where(s.isna(), s.astype(str).str.strip())
        changed = int(((stripped != s) & s.notna()).sum())
        empty = stripped.isin(["", "nan", "NaN", "None", "null", "NULL", "NA", "N/A"]) & s.notna()
        stripped = stripped.mask(empty)
        df[col] = stripped
        if changed or empty.sum():
            log.add("whitespace", col, "trimmed whitespace / blank tokens → missing",
                    changed + int(empty.sum()),
                    "Leading/trailing spaces and textual null tokens create false categories.")
    return df


def _standardise_categories(df, log):
    def apply(col, aliases, case):
        before = df[col].copy()
        keys = df[col].map(norm_key)
        out = keys.map(lambda k: aliases.get(k, k) if k is not None else None)
        if case == "title":
            out = out.map(lambda v: v if v is None or v in aliases.values() else v.title())
        df[col] = out.astype("object").where(out.notna(), None)
        changed = int((before.astype("string") != df[col].astype("string")).fillna(False).sum())
        if changed:
            log.add("standardise", col, f"normalised case/spelling ({case})", changed,
                    "Merge spelling variants (e.g. 'Bengaluru'→'Bangalore', 'Over-speeding'→"
                    "'overspeeding') into one canonical label.")

    apply("city", config.CITY_ALIASES, "title")
    apply("state", config.STATE_ALIASES, "title")
    apply("cause", config.CAUSE_ALIASES, "lower")
    apply("accident_severity", config.SEVERITY_ALIASES, "lower")
    apply("weather", config.WEATHER_ALIASES, "lower")
    for col in ("road_type", "visibility", "traffic_density"):
        apply(col, {}, "lower")
    apply("day_of_week", {}, "title")
    if df["festival"].notna().any():
        df["festival"] = df["festival"].map(lambda v: v if pd.isna(v) else str(v).strip().title()
                                            .replace("New year", "New Year"))
    unknown_sev = ~df["accident_severity"].isin(config.SEVERITY_ORDER) & df["accident_severity"].notna()
    if unknown_sev.any():
        log.add("standardise", "accident_severity", "unrecognised severity → missing",
                unknown_sev.sum(), "Only fatal / major / minor are defined.")
        df.loc[unknown_sev, "accident_severity"] = None
    return df


def _numeric_types(df, log):
    for col in config.NUMERIC_COLUMNS + config.BINARY_COLUMNS + ["accident_id"]:
        before_na = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        new_na = df[col].isna().sum() - before_na
        if new_na:
            log.add("types", col, "non-numeric text → missing", new_na,
                    "Values that cannot be parsed as numbers are kept as missing, not guessed.")
    for col, (lo, hi) in config.VALID_RANGES.items():
        bad = df[col].notna() & ~df[col].between(lo, hi)
        if bad.any():
            log.add("validity", col, f"outside plausible range [{lo}, {hi}] → missing", bad.sum(),
                    "Physically impossible values are nulled (the record is kept).")
            df.loc[bad, col] = np.nan
    for col in config.BINARY_COLUMNS:
        bad = df[col].notna() & ~df[col].isin([0, 1])
        if bad.any():
            log.add("validity", col, "non-binary value → missing", bad.sum(), "Flag must be 0 or 1.")
            df.loc[bad, col] = np.nan
    for col in ("hour", "lanes", "temperature", "vehicles_involved", "casualties") + tuple(config.BINARY_COLUMNS):
        df[col] = df[col].round().astype("Int64")
    return df


def _duplicates(df, log):
    n = len(df)
    df = df.drop_duplicates().copy()
    if n - len(df):
        log.add("duplicates", "<all>", "dropped exact duplicate rows", n - len(df),
                "Identical rows (including accident_id) are double-counted records.")
    dup_id = df["accident_id"].duplicated(keep=False) & df["accident_id"].notna()
    df["dq_duplicate_id"] = dup_id.astype(int)
    if dup_id.any():
        log.add("duplicates", "accident_id", "flagged (kept) rows sharing an id with different content",
                dup_id.sum(), "Content differs, so neither copy can be assumed wrong; flagged for review.")
    else:
        log.add("duplicates", "accident_id", "verified unique", 0, "No duplicate ids found.")
    return df


def _dates_times(df, log):
    raw_date = df["date"]
    df["date"] = pd.to_datetime(raw_date, errors="coerce", format="mixed")
    bad = df["date"].isna() & raw_date.notna()
    if bad.any():
        log.add("dates", "date", "unparseable date → missing", bad.sum(), "Kept record; date unknown.")
    t = df["time"].astype("string").str.strip().str.extract(r"^(\d{1,2}):(\d{2})")
    hour_from_time = pd.to_numeric(t[0], errors="coerce")
    hour_from_time = hour_from_time.where(hour_from_time.between(0, 23))
    df["time"] = hour_from_time.map(lambda h: f"{int(h):02d}:00" if pd.notna(h) else None)
    mism = df["hour"].notna() & hour_from_time.notna() & (df["hour"] != hour_from_time)
    if mism.any():
        log.add("dates", "hour", "hour disagrees with time → time value used", mism.sum(),
                "The time string is the primary record; hour is derived from it.")
        df.loc[mism, "hour"] = hour_from_time[mism]
    fill = df["hour"].isna() & hour_from_time.notna()
    if fill.any():
        df.loc[fill, "hour"] = hour_from_time[fill]
        log.add("dates", "hour", "missing hour recovered from time", fill.sum(), "Lossless recovery.")
    log.add("dates", "time", "normalised 'H:MM' → 'HH:00'", int(df["time"].notna().sum()),
            "Raw mixes '5:00' and '13:00'; all times are on the hour, so a zero-padded form is used.")

    derived_day = df["date"].dt.day_name()
    mism = derived_day.notna() & df["day_of_week"].notna() & (derived_day != df["day_of_week"])
    if mism.any():
        log.add("dates", "day_of_week", "disagreed with date → recomputed from date", mism.sum(),
                "The calendar date is authoritative.")
    df["day_of_week"] = derived_day.where(derived_day.notna(), df["day_of_week"])
    we = df["date"].dt.day_of_week.isin([5, 6]).astype("Int64").where(df["date"].notna())
    mism = we.notna() & df["is_weekend"].notna() & (we != df["is_weekend"])
    if mism.any():
        log.add("dates", "is_weekend", "disagreed with date → recomputed", mism.sum(), "Saturday/Sunday = weekend.")
    df["is_weekend"] = we.fillna(df["is_weekend"]).astype("Int64")
    return df


def _coordinates(df, log):
    lat, lon = df["latitude"], df["longitude"]
    valid = lat.between(*config.INDIA_LAT) & lon.between(*config.INDIA_LON) & ~((lat == 0) & (lon == 0))
    centre = df[valid].groupby("city")[["latitude", "longitude"]].median()
    dist = pd.Series(haversine_km(lat, lon, df["city"].map(centre["latitude"]),
                                  df["city"].map(centre["longitude"])), index=df.index)
    far = valid & (dist > config.MAX_KM_FROM_CITY_CENTRE)
    df["coord_valid"] = (valid & ~far).astype(int)
    df["km_from_city_centre"] = dist.where(valid).round(2)
    invalid = (~valid).sum()
    log.add("coordinates", "latitude/longitude",
            "validated against India bounding box and city centre (>75 km flagged)",
            int(invalid + far.sum()),
            "Invalid coordinates are excluded from maps via coord_valid=0; they are not "
            "imputed or relocated, so no location is fabricated.")
    return df


def _features(df, log):
    d = df["date"]
    df["year"] = d.dt.year.astype("Int64")
    df["month"] = d.dt.month.astype("Int64")
    df["month_name"] = d.dt.strftime("%b")
    df["quarter"] = d.dt.quarter.astype("Int64")
    df["year_month"] = d.dt.to_period("M").astype("string")
    df["year_quarter"] = d.dt.year.astype("string") + "-Q" + d.dt.quarter.astype("string")
    df["week_of_year"] = d.dt.isocalendar().week.astype("Int64")
    df["day_type"] = df["is_weekend"].map({1: "Weekend", 0: "Weekday"})
    df["time_of_day"] = df["hour"].map(lambda h: config.time_of_day(h) if pd.notna(h) else None)
    df["peak_label"] = df["is_peak_hour"].map({1: "Peak hour", 0: "Off-peak"})
    df["season"] = df["month"].map(config.SEASON_BY_MONTH)

    df["festival_flag"] = df["festival"].notna().astype(int)
    df["festival_name"] = df["festival"].fillna("No Festival")
    log.add("missing", "festival", "missing → 'No Festival' (in festival_name); raw column kept",
            int(df["festival"].isna().sum()),
            "Missing here is structural (no festival that day), not unknown. Note: labels exist "
            "only for 2023–2024 festival dates; see the profile.")

    df["severity_category"] = df["accident_severity"].map(str.title, na_action="ignore")
    df["severity_rank"] = df["accident_severity"].map(config.SEVERITY_RANK).astype("Int64")
    df["is_fatal"] = (df["accident_severity"] == "fatal").astype("Int64").where(df["accident_severity"].notna())
    df["casualties_per_vehicle"] = (df["casualties"] / df["vehicles_involved"]).astype(float).round(3)
    df["has_casualties"] = (df["casualties"] > 0).astype("Int64").where(df["casualties"].notna())
    veh = df["vehicles_involved"].astype("Float64")
    df["collision_type"] = pd.Series(np.where(veh.eq(1).fillna(False), "Single-vehicle", "Multi-vehicle"),
                                     index=df.index).where(veh.notna())
    df["signal_label"] = df["traffic_signal"].map({1: "Signalised", 0: "No signal"})
    bands = pd.cut(df["risk_score"], bins=[b[0] for b in config.RISK_BANDS] + [config.RISK_BANDS[-1][1]],
                   labels=[b[2] for b in config.RISK_BANDS], right=False)
    df["risk_band"] = bands.astype("string")

    # Condition-only risk: the published risk score minus its severity term.
    # This removes the circularity of "risk score by severity".
    tmp = df.copy()
    tmp["accident_severity"] = "minor"
    df["condition_risk"] = reconstruct_risk_score(tmp).round(2).where(df["risk_score"].notna())
    log.add("features", "condition_risk", "risk_score recomputed without its severity term", len(df),
            "risk_score is an exact additive rule that includes severity; condition_risk lets "
            "severity be compared against conditions without circular reasoning.")

    log.add("features", "<derived>",
            "added year, month, month_name, quarter, year_month, year_quarter, week_of_year, day_type, "
            "time_of_day, peak_label, season, festival_flag, festival_name, severity_category, "
            "severity_rank, is_fatal, casualties_per_vehicle, has_casualties, collision_type, "
            "signal_label, risk_band, condition_risk, coord_valid, km_from_city_centre",
            len(df), "Analytical features; raw columns are retained alongside.")
    return df


def _quality_flags(df, log):
    zero_major = ((df["accident_severity"] == "major") & df["casualties"].eq(0)).fillna(False).astype(bool)
    df["dq_major_zero_casualties"] = zero_major.astype(int)
    log.add("quality", "accident_severity/casualties",
            "flagged 'major' accidents with zero casualties (kept)", zero_major.sum(),
            "Logically inconsistent, but there is no basis to say which field is wrong; "
            "flagged so users can exclude them.")
    for col in ("casualties", "vehicles_involved", "temperature", "km_from_city_centre"):
        x = df[col].astype(float)
        q1, q3 = x.quantile([0.25, 0.75])
        iqr = q3 - q1
        out = (x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)
        df[f"outlier_{col}"] = out.astype(int)
        log.add("outliers", col, f"IQR rule (1.5×IQR, fences {q1 - 1.5*iqr:.2f}–{q3 + 1.5*iqr:.2f}) — flagged, not removed",
                out.sum(), "Outliers are flagged so analysis can test sensitivity; none are deleted.")
    missing = df[config.EXPECTED_COLUMNS].isna().sum()
    for col, n in missing.items():
        if n and col != "festival":
            log.add("missing", col, "left as missing (no imputation)", n,
                    "Imputing accident attributes would fabricate data; metrics use available values.")
    return df


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningLog]:
    log = CleaningLog()
    df = raw.copy()
    log.add("load", "<all>", "loaded raw records", len(df), "Full dataset — no sampling.")
    for step in (_ensure_schema, _strip_text, _standardise_categories, _numeric_types,
                 _duplicates, _dates_times, _coordinates, _features, _quality_flags):
        df = step(df, log)
    df = df.sort_values(["date", "hour", "accident_id"], na_position="last").reset_index(drop=True)
    log.add("output", "<all>", "records in cleaned dataset", len(df),
            f"{len(raw) - len(df)} rows removed in total (exact duplicates only).")
    return df, log


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
def cleaning_log_markdown(log: CleaningLog, raw_shape, clean_shape) -> str:
    lines = ["# Cleaning Report\n",
             "_Generated by `python -m src.preprocessing`._\n",
             f"Raw: **{raw_shape[0]:,} rows × {raw_shape[1]} columns** → "
             f"Cleaned: **{clean_shape[0]:,} rows × {clean_shape[1]} columns**\n",
             "| # | Step | Column | Action | Rows | Rationale |", "|---|---|---|---|---|---|"]
    for i, e in enumerate(log, 1):
        lines.append(f"| {i} | {e.step} | {e.column} | {e.action} | {e.rows_affected:,} | {e.rationale} |")
    return "\n".join(lines) + "\n"


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pipeline(verbose: bool = True) -> pd.DataFrame:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    digest_before = _sha256(config.RAW_FILE) if config.RAW_FILE.exists() else None

    raw = load_raw()
    profile = profile_dataset(raw)
    config.PROFILE_JSON.write_text(json.dumps(to_jsonable(profile), indent=2, default=str))
    (config.REPORTS_DIR / "data_profile.md").write_text(profile_to_markdown(profile))

    df, log = clean(raw)
    df.to_csv(config.CLEAN_FILE, index=False)
    config.CLEANING_LOG_JSON.write_text(json.dumps([asdict(e) for e in log], indent=2, default=str))
    (config.REPORTS_DIR / "cleaning_report.md").write_text(
        cleaning_log_markdown(log, raw.shape, df.shape))

    assert digest_before == _sha256(config.RAW_FILE), "Raw CSV was modified — aborting."
    if verbose:
        print(f"Raw      : {raw.shape[0]:,} rows × {raw.shape[1]} cols  (sha256 {digest_before[:12]}… unchanged)")
        print(f"Cleaned  : {df.shape[0]:,} rows × {df.shape[1]} cols  → {config.CLEAN_FILE}")
        print(f"Profile  : {config.REPORTS_DIR / 'data_profile.md'}")
        print(f"Cleaning : {config.REPORTS_DIR / 'cleaning_report.md'}  ({len(log)} logged actions)")
        print(f"Verdict  : {profile['provenance']['verdict']}")
    return df


if __name__ == "__main__":
    run_pipeline()
