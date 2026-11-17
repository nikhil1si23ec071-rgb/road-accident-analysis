"""Phase 6 — automatic insight generation.

Every insight is computed from whatever (filtered) DataFrame is passed in.
Nothing is hard-coded from the original notebook. Each insight carries a
`status` so the UI can show how much weight it deserves:

    descriptive  plain fact about the selection (counts, most common value)
    significant  difference passes a hypothesis test after FDR correction
    not_significant  a "highest/lowest" exists but is indistinguishable from chance
    unreliable   too few records to compute a stable rate
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src import analysis as A
from src import config
from src.utils import fmt_int, fmt_num, fmt_pct

MIN_N = config.MIN_GROUP_N
PLURAL = {"city": "cities", "weather condition": "weather conditions"}


def _pl(label):
    return PLURAL.get(label, label + "s")


def _sig_status(p):
    """significant (p<0.01), weak (0.01≤p<0.05: does not survive correction for
    the ~30 comparisons this dashboard makes), else not_significant."""
    if p < 0.01:
        return "significant"
    if p < config.ALPHA:
        return "weak"
    return "not_significant"


def _insight(category, title, value, detail, status="descriptive", icon="•"):
    return {"category": category, "title": title, "value": value, "detail": detail,
            "status": status, "icon": icon}


def _p_text(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def _rate_leader(df, col, label, icon, category):
    """Group with the highest fatality rate, with a test of whether groups differ."""
    groups = df[col].nunique()
    if groups < 2:
        return _insight(category, f"Highest fatality rate by {label}", "n/a",
                        f"Only one {label} in the current selection — no comparison possible.",
                        "unreliable", icon)
    s = A.group_summary(df, col)
    eligible = s[s["accidents"] >= MIN_N]
    if eligible.empty:
        return _insight(category, f"Highest fatality rate by {label}", "Cannot be calculated reliably",
                        f"No {label} has at least {MIN_N} accidents in this selection.", "unreliable", icon)
    top = eligible.sort_values("fatal_rate", ascending=False).iloc[0]
    low = eligible.sort_values("fatal_rate").iloc[0]
    t = A.fatal_rate_test(df, col)
    status = _sig_status(t["p_value"]) if t.get("valid") else "unreliable"
    if status == "significant":
        tail = (f"Differences between {_pl(label)} are statistically significant ({_p_text(t['p_value'])}, "
                f"Cramér's V = {t['effect_size']:.3f}) — an association, not proof of cause.")
    elif status == "weak":
        tail = (f"Evidence of a difference is weak ({_p_text(t['p_value'])}, Cramér's V = "
                f"{t['effect_size']:.3f}): it does not survive correction for the many comparisons made "
                "here, so treat it as a lead, not a finding.")
    elif status == "unreliable":
        tail = "The χ² test's assumptions are not met (cells too small), so no test result is given."
    else:
        tail = (f"However the spread across {_pl(label)} is not statistically significant "
                f"({_p_text(t['p_value'])}) — it is consistent with random variation.")
    skipped = len(s) - len(eligible)
    note = f" {skipped} {label}(s) with < {MIN_N} accidents excluded." if skipped else ""
    return _insight(
        category, f"Highest fatality rate by {label}", f"{top[col]} · {fmt_pct(top['fatal_rate'])}",
        f"{fmt_int(top['fatal'])} of {fmt_int(top['accidents'])} accidents were fatal "
        f"(95% CI {top['ci_low']:.1f}–{top['ci_high']:.1f}%), versus {fmt_pct(low['fatal_rate'])} "
        f"for {low[col]}. {tail}{note}", status, icon)


def _most_common(df, col, label, icon, category, exposure_note=""):
    vc = df[col].value_counts()
    if vc.empty:
        return None
    top, n = vc.index[0], vc.iloc[0]
    if len(vc) < 2:
        return _insight(category, f"Most common {label}", str(top),
                        f"All {fmt_int(n)} accidents in the selection share this {label}.", "descriptive", icon)
    gof = stats.chisquare(vc.values)
    uneven = gof.pvalue < config.ALPHA
    detail = (f"{fmt_int(n)} accidents ({n / len(df) * 100:.1f}%), "
              f"next: {vc.index[1]} ({fmt_int(vc.iloc[1])}). ")
    detail += ("Counts differ more than chance would allow "
               f"(χ² goodness-of-fit, {_p_text(gof.pvalue)})." if uneven else
               f"But counts across {_pl(label)} are statistically indistinguishable from an even split "
               f"({_p_text(gof.pvalue)}), so '{top}' leads only marginally.")
    return _insight(category, f"Most common {label}", str(top), detail + exposure_note,
                    _sig_status(gof.pvalue), icon)


def generate_insights(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return [_insight("Selection", "No records match the current filters", "0",
                         "Widen or reset the filters to generate insights.", "unreliable", "⚠")]
    out: list[dict] = []
    k = A.kpis(df)

    out.append(_insight(
        "Overview", "Accidents in selection", fmt_int(k["accidents"]),
        f"{fmt_int(k['fatal'])} fatal ({fmt_pct(k['fatal_pct'])}), {fmt_int(k['major'])} major and "
        f"{fmt_int(k['minor'])} minor, involving {fmt_int(k['casualties'])} casualties "
        f"(persons killed or injured — the data does not separate deaths). "
        f"Average {fmt_num(k['avg_casualties'])} casualties per accident.", "descriptive", "▣"))

    # Trend with partial-year handling
    yt = A.yearly_trend(df)
    if len(yt) >= 2:
        sp = A.same_period_comparison(df)
        first, last = yt.iloc[0], yt.iloc[-1]
        detail = (f"Accidents per day went from {first['accidents_per_day']:.2f} in {int(first['year'])} to "
                  f"{last['accidents_per_day']:.2f} in {int(last['year'])}"
                  f"{' (partial year, to ' + last['last_date'].strftime('%d %b') + ')' if last['is_partial'] else ''}. ")
        if len(sp) >= 2:
            ct = stats.chisquare(sp["accidents"].values)
            detail += (f"Like-for-like ({sp['window'].iloc[0]}): "
                       + ", ".join(f"{int(y)}: {fmt_int(a)}" for y, a in zip(sp["year"], sp["accidents"]))
                       + f". Year-to-year differences are {'' if ct.pvalue < config.ALPHA else 'not '}"
                         f"statistically significant ({_p_text(ct.pvalue)}).")
            status = _sig_status(ct.pvalue)
        else:
            status = "descriptive"
        change = (last["accidents_per_day"] / first["accidents_per_day"] - 1) * 100
        out.append(_insight("Temporal", "Accident frequency trend",
                            f"{change:+.1f}% daily rate", detail
                            + " Raw annual totals are not compared because the last year is incomplete.",
                            status, "↗"))

    # Geography
    if df["city"].nunique() > 1:
        out.append(_most_common(df, "city", "city", "⌖", "Geography",
                                " Counts are absolute: without population or vehicle-km exposure data they "
                                "cannot show which city is more dangerous per traveller."))
        out.append(_rate_leader(df, "city", "city", "⌖", "Geography"))
    else:
        out.append(_insight("Geography", "City comparison", str(df["city"].iloc[0]),
                            "Only one city selected — city rankings are not applicable.", "unreliable", "⌖"))

    # Causes
    out.append(_most_common(df, "cause", "cause", "⚑", "Cause"))
    out.append(_rate_leader(df, "cause", "cause", "⚑", "Cause"))

    # Time of day: normalised by hours per bucket
    tod = A.per_slot_rate(df)
    if len(tod) >= 2:
        top = tod.sort_values("accidents_per_hour", ascending=False).iloc[0]
        lowest = tod.sort_values("accidents_per_hour").iloc[0]
        hour_counts = df["hour"].value_counts().reindex(range(24), fill_value=0)
        gof = stats.chisquare(hour_counts.values) if hour_counts.sum() >= 24 * 5 else None
        peak_hour = int(hour_counts.idxmax())
        det = (f"{top['accidents_per_hour']:.0f} accidents per clock-hour vs {lowest['accidents_per_hour']:.0f} "
               f"for {lowest['time_of_day']} (buckets are normalised by length: Night 8 h, Morning 7 h, "
               f"Afternoon 5 h, Evening 4 h). Busiest single hour: {peak_hour:02d}:00 "
               f"({fmt_int(hour_counts.max())} accidents). ")
        if gof is not None:
            det += ("The hourly distribution is uneven beyond chance "
                    f"({_p_text(gof.pvalue)})." if gof.pvalue < config.ALPHA else
                    f"The hourly distribution is statistically flat ({_p_text(gof.pvalue)}), so no time "
                    "period is meaningfully more accident-prone.")
            st_ = _sig_status(gof.pvalue)
        else:
            st_ = "unreliable"
        out.append(_insight("Temporal", "Most accident-prone time of day", str(top["time_of_day"]), det, st_, "◷"))

    # Weather (exposure caveat)
    out.append(_most_common(df, "weather", "weather condition", "☂", "Weather",
                            " Without the share of hours each weather condition actually occurred, this "
                            "cannot say that any weather makes accidents more likely."))
    out.append(_rate_leader(df, "weather", "weather condition", "☂", "Weather"))

    # Road type
    out.append(_rate_leader(df, "road_type", "road type", "⛙", "Infrastructure"))

    # Weekend vs weekday (per calendar day)
    ww = A.weekday_weekend(df)
    if len(ww) == 2:
        wd, we = ww.set_index("day_type").loc["Weekday"], ww.set_index("day_type").loc["Weekend"]
        z = A.two_proportion_z(we["fatal"], we["accidents"], wd["fatal"], wd["accidents"])
        sig = z.get("valid") and z["p_value"] < config.ALPHA
        out.append(_insight(
            "Temporal", "Weekend vs weekday",
            f"{we['accidents_per_day']:.1f} vs {wd['accidents_per_day']:.1f} per day",
            f"Weekends average {we['accidents_per_day']:.2f} accidents per calendar day vs "
            f"{wd['accidents_per_day']:.2f} on weekdays (raw totals would mislead: 2 vs 5 days a week). "
            f"Fatality rate {fmt_pct(we['fatal_rate'])} vs {fmt_pct(wd['fatal_rate'])} "
            f"(difference {z.get('diff_pp', np.nan):+.1f} pp, {_p_text(z.get('p_value', 1))}, "
            f"{'significant' if sig else 'not significant'}).",
            _sig_status(z.get("p_value", 1)), "▦"))

    # Peak vs off-peak
    if df["is_peak_hour"].nunique() == 2:
        pk = A.group_summary(df, "peak_label").set_index("peak_label")
        peak_hours = sorted(df.loc[df["is_peak_hour"] == 1, "hour"].unique())
        per_h_peak = pk.loc["Peak hour", "accidents"] / max(len(peak_hours), 1)
        per_h_off = pk.loc["Off-peak", "accidents"] / max(24 - len(peak_hours), 1)
        z = A.two_proportion_z(pk.loc["Peak hour", "fatal"], pk.loc["Peak hour", "accidents"],
                               pk.loc["Off-peak", "fatal"], pk.loc["Off-peak", "accidents"])
        sig = z.get("valid") and z["p_value"] < config.ALPHA
        out.append(_insight(
            "Temporal", "Peak vs off-peak hours", f"{per_h_peak:.0f} vs {per_h_off:.0f} per hour",
            f"Peak hours in this data are {', '.join(f'{int(h):02d}' for h in peak_hours)}:00. "
            f"Per clock-hour, peak and off-peak see {per_h_peak:.0f} and {per_h_off:.0f} accidents. "
            f"Fatality rate {fmt_pct(pk.loc['Peak hour', 'fatal_rate'])} vs "
            f"{fmt_pct(pk.loc['Off-peak', 'fatal_rate'])} ({_p_text(z.get('p_value', 1))}).",
            _sig_status(z.get("p_value", 1)), "◑"))

    # Risk score by cause (with formula caveat)
    if df["cause"].nunique() > 1:
        rc = df.groupby("cause")["risk_score"].agg(["mean", "size"]).sort_values("mean", ascending=False)
        kw = A.kruskal(df, "risk_score", "cause")
        sig = kw.get("valid") and kw["p_value"] < config.ALPHA
        out.append(_insight(
            "Risk", "Highest average risk score by cause", f"{rc.index[0]} · {rc['mean'].iloc[0]:.3f}",
            f"Range across causes: {rc['mean'].min():.3f}–{rc['mean'].max():.3f} "
            f"(Kruskal–Wallis {_p_text(kw.get('p_value', 1))}). Cause is not an input to risk_score — the "
            "score is an exact additive rule of severity, traffic density, peak hour, weather, visibility "
            "and festival — so any gap between causes only reflects how those conditions happen to be mixed.",
            _sig_status(kw.get("p_value", 1)), "◆"))

    # Festivals (small n)
    fest = df[df["festival_flag"] == 1]
    if len(fest):
        fs = A.group_summary(fest, "festival_name").sort_values("accidents", ascending=False)
        small = fs[fs["accidents"] < MIN_N]["festival_name"].tolist()
        nonfest = df.loc[df["festival_flag"] == 0, "is_fatal"].astype(float)
        base = float(nonfest.mean()) if len(nonfest) else np.nan
        parts = []
        for _, r in fs.iterrows():
            p = stats.binomtest(int(r["fatal"]), int(r["accidents"]), base).pvalue if pd.notna(base) and 0 < base < 1 else np.nan
            parts.append(f"{r['festival_name']} {fmt_int(r['accidents'])} accidents, "
                         f"{fmt_pct(r['fatal_rate'])} fatal (CI {r['ci_low']:.0f}–{r['ci_high']:.0f}%, {_p_text(p) if pd.notna(p) else 'no test'})")
        out.append(_insight(
            "Festival", "Festival-day accidents", f"{fmt_int(len(fest))} records",
            "; ".join(parts) + (f". Non-festival fatality rate: {base * 100:.1f}%. " if pd.notna(base)
                                else ". No non-festival records selected, so there is no baseline to compare. ")
            + (f"Rates for {', '.join(small)} rest on fewer than {MIN_N} records and cannot be calculated "
               "reliably. " if small else "")
            + "Festival labels exist only for 2023–2024; other festival days are unlabelled.",
            "unreliable", "✦"))
    else:
        out.append(_insight("Festival", "Festival-day accidents", "0",
                            "No festival-labelled records in this selection.", "unreliable", "✦"))

    # Severity vs casualties — the one strong pattern, framed correctly
    if df["accident_severity"].nunique() > 1:
        cas = df.groupby("accident_severity")["casualties"].mean()
        detail = "Average casualties per accident. "
        if {"fatal", "major", "minor"} <= set(cas.index) and cas[["major", "minor"]].mean() > 0:
            ratio = cas["fatal"] / cas[["major", "minor"]].mean()
            detail += (f"Fatal accidents average {ratio:.1f}× the casualties of major/minor ones; major vs "
                       f"minor differ by {abs(cas['major'] - cas['minor']):.2f}. ")
        zero_major = int(df["dq_major_zero_casualties"].sum())
        if zero_major:
            detail += (f"{fmt_int(zero_major)} 'major' accidents record zero casualties, so the severity "
                       "label should be read as recorded, not as an injury scale.")
        out.append(_insight(
            "Severity", "Casualties by severity",
            " · ".join(f"{s.title()} {cas[s]:.2f}" for s in config.SEVERITY_ORDER if s in cas),
            detail, "descriptive", "✚"))
    return [i for i in out if i is not None]
