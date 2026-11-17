"""Phase 3 — analytical functions. Pure pandas/scipy; no Streamlit imports.

Terminology used everywhere in this project
    accidents         number of records (one record = one accident)
    fatal accidents   accidents whose severity is 'fatal'
    fatality rate     fatal accidents / accidents in the same group  (a %)
    casualties        persons affected as recorded in `casualties`
                      (killed + injured; the dataset does NOT separate deaths)
    fatalities        NOT AVAILABLE — the dataset has no deaths count, so this
                      project never reports a number of people killed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src import config

SEV = config.SEVERITY_ORDER


# --------------------------------------------------------------------------- #
# Basic metrics
# --------------------------------------------------------------------------- #
def kpis(df: pd.DataFrame) -> dict:
    n = len(df)
    sev = df["accident_severity"]
    fatal, major, minor = (int((sev == s).sum()) for s in SEV)
    return {
        "accidents": n,
        "casualties": int(df["casualties"].sum()) if n else 0,
        "fatal": fatal, "major": major, "minor": minor,
        "fatal_pct": fatal / n * 100 if n else np.nan,
        "avg_casualties": df["casualties"].mean() if n else np.nan,
        "avg_vehicles": df["vehicles_involved"].mean() if n else np.nan,
        "avg_risk": df["risk_score"].mean() if n else np.nan,
        "casualties_in_fatal": int(df.loc[sev == "fatal", "casualties"].sum()) if n else 0,
        "days": int(df["date"].dt.normalize().nunique()) if n else 0,
    }


def wilson_ci(k, n, alpha: float = config.ALPHA):
    """Wilson score interval for a proportion, returned in percent."""
    k, n = np.asarray(k, float), np.asarray(n, float)
    z = stats.norm.ppf(1 - alpha / 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = k / n
        denom = 1 + z ** 2 / n
        centre = (p + z ** 2 / (2 * n)) / denom
        half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (centre - half) * 100, (centre + half) * 100


def group_summary(df: pd.DataFrame, col: str, order: list | None = None) -> pd.DataFrame:
    """Accident, fatality, casualty and risk metrics per category of `col`."""
    if df.empty:
        return pd.DataFrame(columns=[col, "accidents", "share_pct", "fatal", "fatal_rate"])
    g = df.groupby(col, observed=True, dropna=False)
    out = pd.DataFrame({
        "accidents": g.size(),
        "fatal": g["accident_severity"].apply(lambda s: (s == "fatal").sum()),
        "major": g["accident_severity"].apply(lambda s: (s == "major").sum()),
        "minor": g["accident_severity"].apply(lambda s: (s == "minor").sum()),
        "casualties": g["casualties"].sum(),
        "avg_casualties": g["casualties"].mean(),
        "avg_vehicles": g["vehicles_involved"].mean(),
        "avg_risk": g["risk_score"].mean(),
        "avg_condition_risk": g["condition_risk"].mean(),
    })
    out["share_pct"] = out["accidents"] / len(df) * 100
    out["casualty_share_pct"] = out["casualties"] / max(df["casualties"].sum(), 1) * 100
    out["fatal_rate"] = out["fatal"] / out["accidents"] * 100
    out["ci_low"], out["ci_high"] = wilson_ci(out["fatal"], out["accidents"])
    out["reliable"] = out["accidents"] >= config.MIN_GROUP_N
    out = out.reset_index()
    if order:
        out[col] = pd.Categorical(out[col], categories=[o for o in order if o in set(out[col])], ordered=True)
        out = out.sort_values(col)
        out[col] = out[col].astype(str)
    return out


def severity_mix(df: pd.DataFrame, col: str, order: list | None = None) -> pd.DataFrame:
    """Long table: count and % of each severity within each group of `col`."""
    if df.empty:
        return pd.DataFrame(columns=[col, "accident_severity", "count", "pct"])
    ct = pd.crosstab(df[col], df["accident_severity"]).reindex(columns=SEV, fill_value=0)
    if order:
        ct = ct.reindex([o for o in order if o in ct.index])
    pct = ct.div(ct.sum(axis=1), axis=0) * 100
    long = ct.stack().rename("count").to_frame().join(pct.stack().rename("pct")).reset_index()
    long.columns = [col, "accident_severity", "count", "pct"]
    long["group_total"] = long[col].map(ct.sum(axis=1))
    return long


# --------------------------------------------------------------------------- #
# Temporal
# --------------------------------------------------------------------------- #
def coverage(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    dmin, dmax = df["date"].min(), df["date"].max()
    return {"start": dmin, "end": dmax,
            "partial_last_month": dmax.day < dmax.days_in_month,
            "last_month": str(dmax.to_period("M"))}


def yearly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Per-year totals plus a *rate* (accidents per observed day) so a partial
    year (2025 ends 15 Apr) is not mistaken for a decline."""
    if df.empty:
        return pd.DataFrame(columns=["year", "accidents"])
    g = df.groupby("year")
    out = pd.DataFrame({
        "accidents": g.size(),
        "fatal": g["accident_severity"].apply(lambda s: (s == "fatal").sum()),
        "casualties": g["casualties"].sum(),
        "first_date": g["date"].min(), "last_date": g["date"].max(),
    }).reset_index()
    # days in the observation window of each year (calendar days, not just days with records)
    full_min, full_max = df["date"].min(), df["date"].max()
    def window_days(y):
        a = max(pd.Timestamp(int(y), 1, 1), full_min)
        b = min(pd.Timestamp(int(y), 12, 31), full_max)
        return (b - a).days + 1
    out["days_observed"] = out["year"].map(window_days)
    out["accidents_per_day"] = out["accidents"] / out["days_observed"]
    out["fatal_rate"] = out["fatal"] / out["accidents"] * 100
    out["is_partial"] = out["days_observed"] < out["year"].map(
        lambda y: 366 if pd.Timestamp(int(y), 12, 31).day_of_year == 366 else 365)
    out["change_in_daily_rate_pct"] = out["accidents_per_day"].pct_change() * 100
    return out


def same_period_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare every year over the same calendar window as the latest year
    (e.g. 1 Jan – 15 Apr) — the only fair like-for-like YoY comparison."""
    if df.empty:
        return pd.DataFrame()
    end = df["date"].max()
    cutoff = (end.month, end.day)
    md = list(zip(df["date"].dt.month, df["date"].dt.day))
    mask = pd.Series([m <= cutoff for m in md], index=df.index)
    sub = df[mask]
    out = sub.groupby("year").agg(accidents=("accident_id", "size"),
                                  fatal=("is_fatal", "sum")).reset_index()
    out["fatal_rate"] = out["fatal"] / out["accidents"] * 100
    out["window"] = f"1 Jan – {end.strftime('%d %b')}"
    out["change_pct"] = out["accidents"].pct_change() * 100
    return out


def monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["year_month", "accidents"])
    g = df.groupby("year_month")
    out = pd.DataFrame({
        "accidents": g.size(),
        "fatal": g["is_fatal"].sum(),
        "casualties": g["casualties"].sum(),
        "days_with_data": g["date"].nunique(),
    }).reset_index()
    out["month_start"] = pd.to_datetime(out["year_month"] + "-01")
    out["days_in_month"] = out["month_start"].dt.days_in_month
    out["accidents_per_day"] = out["accidents"] / out["days_with_data"]
    out["partial"] = out["days_with_data"] < out["days_in_month"]
    out["fatal_rate"] = out["fatal"] / out["accidents"] * 100
    return out


def per_slot_rate(df: pd.DataFrame) -> pd.DataFrame:
    """Accidents per clock-hour for each time-of-day bucket. Buckets span
    different numbers of hours (Night 8h, Morning 7h, Afternoon 5h, Evening 4h),
    so raw counts favour longer buckets; this normalises by hours covered."""
    hours = {"Morning": 7, "Afternoon": 5, "Evening": 4, "Night": 8}
    s = group_summary(df, "time_of_day", config.TIME_OF_DAY_ORDER)
    if s.empty:
        return s
    s["hours_in_bucket"] = s["time_of_day"].map(hours)
    s["accidents_per_hour"] = s["accidents"] / s["hours_in_bucket"]
    return s


def weekday_weekend(df: pd.DataFrame) -> pd.DataFrame:
    """Accidents per calendar day for weekdays vs weekends (5 vs 2 days a week)."""
    if df.empty:
        return pd.DataFrame()
    s = group_summary(df, "day_type", ["Weekday", "Weekend"])
    days = df.assign(d=df["date"].dt.normalize()).groupby("day_type")["d"].nunique()
    # calendar days in window (independent of whether records exist)
    rng = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    cal = pd.Series(np.where(rng.day_of_week >= 5, "Weekend", "Weekday")).value_counts()
    s["calendar_days"] = s["day_type"].map(cal)
    s["days_with_records"] = s["day_type"].map(days)
    s["accidents_per_day"] = s["accidents"] / s["calendar_days"]
    return s


def hour_dow_matrix(df: pd.DataFrame, value: str = "count") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    if value == "fatal_rate":
        m = df.pivot_table(index="day_of_week", columns="hour", values="is_fatal",
                           aggfunc="mean") * 100
    else:
        m = pd.crosstab(df["day_of_week"], df["hour"])
    return m.reindex(index=[d for d in config.DAY_ORDER if d in m.index],
                     columns=range(24)).astype(float)


# --------------------------------------------------------------------------- #
# Statistical tests
# --------------------------------------------------------------------------- #
def chi2_independence(df: pd.DataFrame, a: str, b: str) -> dict:
    ct = pd.crosstab(df[a], df[b])
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return {"test": f"χ² independence: {a} × {b}", "statistic": np.nan, "dof": np.nan, "p_value": np.nan,
                "effect_size": np.nan, "effect_name": "Cramér's V", "n": int(ct.values.sum()), "valid": False,
                "reason": "fewer than two categories on one side"}
    chi2, p, dof, exp = stats.chi2_contingency(ct)
    n = ct.values.sum()
    v = np.sqrt(chi2 / (n * (min(ct.shape) - 1)))
    ok = (exp >= 5).mean() >= 0.8 and exp.min() >= 1
    return {"test": f"χ² independence: {a} × {b}", "statistic": chi2, "dof": dof, "p_value": p,
            "effect_size": v, "effect_name": "Cramér's V", "n": int(n), "valid": bool(ok),
            "reason": "" if ok else "expected counts too small (<5 in >20% of cells)"}


def fatal_rate_test(df: pd.DataFrame, col: str) -> dict:
    r = chi2_independence(df, col, "is_fatal")
    r["test"] = f"Fatality rate differs by {col} (χ²)"
    return r


def two_proportion_z(k1, n1, k2, n2) -> dict:
    if min(n1, n2) == 0:
        return {"valid": False}
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se else 0.0
    return {"statistic": z, "p_value": 2 * stats.norm.sf(abs(z)), "diff_pp": (p1 - p2) * 100,
            "valid": bool(min(k1, n1 - k1, k2, n2 - k2) >= 5)}


def kruskal(df: pd.DataFrame, value: str, group: str) -> dict:
    groups = [g[value].dropna().values for _, g in df.groupby(group) if len(g) > 0]
    if len(groups) < 2:
        return {"test": f"Kruskal–Wallis {value} ~ {group}", "valid": False}
    h, p = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    eps2 = (h - len(groups) + 1) / (n - len(groups)) if n > len(groups) else np.nan
    return {"test": f"Kruskal–Wallis: {value} by {group}", "statistic": h, "dof": len(groups) - 1,
            "p_value": p, "effect_size": max(eps2, 0), "effect_name": "ε²", "n": n, "valid": True,
            "reason": "rank-based: no normality assumption"}


def mann_whitney(df: pd.DataFrame, value: str, flag: str) -> dict:
    a = df.loc[df[flag] == 1, value].dropna()
    b = df.loc[df[flag] == 0, value].dropna()
    if len(a) < 2 or len(b) < 2:
        return {"test": f"Mann–Whitney {value} by {flag}", "valid": False}
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    rbc = 1 - 2 * u / (len(a) * len(b))
    return {"test": f"Mann–Whitney U: {value} by {flag}", "statistic": u, "p_value": p,
            "effect_size": abs(rbc), "effect_name": "rank-biserial r", "n": len(a) + len(b),
            "valid": True, "reason": "rank-based: no normality assumption"}


def benjamini_hochberg(p: pd.Series) -> pd.Series:
    p = p.astype(float)
    m = p.notna().sum()
    if m == 0:
        return p
    order = p.dropna().sort_values()
    ranks = np.arange(1, len(order) + 1)
    adj = (order * m / ranks)[::-1].cummin()[::-1].clip(upper=1)
    return adj.reindex(p.index)


def test_battery(df: pd.DataFrame) -> pd.DataFrame:
    """Hypothesis tests whose assumptions we check. p-values are adjusted for
    multiple comparisons (Benjamini–Hochberg FDR)."""
    if len(df) < config.MIN_GROUP_N:
        return pd.DataFrame()
    rows = []
    for col in ["city", "state", "cause", "weather", "visibility", "road_type", "traffic_density",
                "time_of_day", "day_type", "peak_label", "signal_label", "lanes", "season", "year",
                "festival_name", "vehicles_involved"]:
        if df[col].nunique() > 1:
            rows.append(fatal_rate_test(df, col))
    for a, b in [("cause", "accident_severity"), ("weather", "accident_severity"),
                 ("road_type", "accident_severity"), ("traffic_density", "hour")]:
        if df[a].nunique() > 1 and df[b].nunique() > 1:
            rows.append(chi2_independence(df, a, b))
    for value, group in [("casualties", "accident_severity"), ("casualties", "cause"),
                         ("casualties", "weather"), ("casualties", "road_type"),
                         ("risk_score", "cause"), ("risk_score", "city")]:
        if df[group].nunique() > 1:
            rows.append(kruskal(df, value, group))
    for flag in ["is_weekend", "is_peak_hour", "traffic_signal"]:
        if df[flag].nunique() > 1:
            rows.append(mann_whitney(df, "casualties", flag))
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    t["p_adjusted"] = benjamini_hochberg(t["p_value"])
    t["significant"] = (t["p_adjusted"] < config.ALPHA) & t["valid"].fillna(False)
    t["interpretation"] = np.where(
        ~t["valid"].fillna(False), "assumptions not met — not interpreted",
        np.where(t["significant"],
                 np.where(t["effect_size"] < 0.1, "significant but negligible effect",
                          "significant association (not causal)"),
                 "no evidence of a difference"))
    return t


def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["casualties", "vehicles_involved", "temperature", "lanes", "hour", "risk_score",
            "condition_risk", "casualties_per_vehicle", "km_from_city_centre"]
    d = df[cols].astype(float).describe().T
    d["skew"] = df[cols].astype(float).skew()
    d["kurtosis"] = df[cols].astype(float).kurt()
    return d


CORR_COLUMNS = ["severity_rank", "casualties", "vehicles_involved", "risk_score", "condition_risk",
                "temperature", "lanes", "hour", "is_weekend", "is_peak_hour", "traffic_signal",
                "festival_flag"]


def correlation_matrix(df: pd.DataFrame, method: str = "spearman") -> pd.DataFrame:
    x = df[CORR_COLUMNS].astype(float)
    x = x.loc[:, x.nunique() > 1]
    return x.corr(method=method)


def outlier_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ["casualties", "vehicles_involved", "temperature", "km_from_city_centre", "risk_score"]:
        x = df[col].astype(float).dropna()
        if x.empty:
            continue
        q1, q3 = x.quantile([.25, .75])
        iqr = q3 - q1
        z = np.abs(stats.zscore(x)) if x.std() > 0 else np.zeros(len(x))
        rows.append({"variable": col, "q1": q1, "q3": q3, "lower_fence": q1 - 1.5 * iqr,
                     "upper_fence": q3 + 1.5 * iqr,
                     "iqr_outliers": int(((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)).sum()),
                     "z_gt_3": int((z > 3).sum()), "min": x.min(), "max": x.max()})
    return pd.DataFrame(rows)


def risk_profiles(df: pd.DataFrame, dims: list[str], min_n: int = config.MIN_GROUP_N,
                  sort_by: str = "fatal_rate", top: int = 15) -> pd.DataFrame:
    """Observed condition combinations ranked by fatality rate (or casualties).
    Only combinations with at least `min_n` accidents are ranked, and each is
    given a 95% Wilson interval — small cells are not allowed to top the list."""
    if df.empty or not dims:
        return pd.DataFrame()
    g = df.groupby(dims, observed=True)
    out = pd.DataFrame({"accidents": g.size(), "fatal": g["is_fatal"].sum(),
                        "avg_casualties": g["casualties"].mean(),
                        "avg_risk": g["risk_score"].mean()}).reset_index()
    out = out[out["accidents"] >= min_n].copy()
    if out.empty:
        return out
    out["fatal_rate"] = out["fatal"] / out["accidents"] * 100
    out["ci_low"], out["ci_high"] = wilson_ci(out["fatal"], out["accidents"])
    overall = df["is_fatal"].mean() * 100
    out["vs_overall_pp"] = out["fatal_rate"] - overall
    out["ci_excludes_overall"] = (out["ci_low"] > overall) | (out["ci_high"] < overall)
    # exact binomial test of each cell vs the overall rate, FDR-corrected across
    # *all* eligible combinations (not just the top ones shown)
    p0 = overall / 100
    out["p_value"] = [stats.binomtest(int(k), int(n), p0).pvalue if 0 < p0 < 1 else np.nan
                      for k, n in zip(out["fatal"], out["accidents"])]
    out["p_adjusted"] = benjamini_hochberg(out["p_value"])
    out["significant_after_correction"] = out["p_adjusted"] < config.ALPHA
    out["combinations_tested"] = len(out)
    return out.sort_values([sort_by, "accidents"], ascending=False).head(top)


def temperature_bands(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    bins = [-50, 19, 24, 29, 34, 60]
    labels = ["≤19 °C", "20–24 °C", "25–29 °C", "30–34 °C", "≥35 °C"]
    tmp = df.assign(temp_band=pd.cut(df["temperature"].astype(float), bins=bins, labels=labels).astype(str))
    return group_summary(tmp, "temp_band", labels)
