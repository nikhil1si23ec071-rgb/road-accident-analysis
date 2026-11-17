"""Page 3 — Temporal Analytics."""
import pandas as pd
import streamlit as st

from src import analysis as A
from src import config, ui
from src import visualizations as V

fdf = ui.filtered()
ui.page_header("Temporal Analytics",
               "When accidents happen — by month, year, weekday, hour and season — using rates per day or per "
               "hour wherever periods have unequal length.", fdf)
ui.guard(fdf)

cov = A.coverage(fdf)
ui.note(f"Coverage: <b>{cov['start']:%d %b %Y} – {cov['end']:%d %b %Y}</b>. "
        + (f"The last month ({cov['last_month']}) is partial, so it is plotted as accidents per day and flagged. "
           if cov["partial_last_month"] else "") +
        "2025 contains only 1 Jan – 15 Apr; yearly comparisons therefore use daily rates or the same calendar window.",
        "warn")

# ---- Monthly trend ------------------------------------------------------------
ms = A.monthly_series(fdf)
with st.container(border=True):
    a, b = st.columns([2, 1])
    with a:
        ui.card_title("Monthly accident trend", "Each point is one calendar month.")
    with b:
        m = st.segmented_control("Metric", ["Accidents", "Per day", "Fatality rate"], default="Per day",
                                 key="tm_month_metric", label_visibility="collapsed") or "Per day"
    col = {"Accidents": "accidents", "Per day": "accidents_per_day", "Fatality rate": "fatal_rate"}[m]
    ms["label"] = ms["month_start"].dt.strftime("%b %Y") + ms["partial"].map({True: " (partial)", False: ""})
    fig = V.lines(ms, "month_start", col, y_title={"accidents": "Accidents", "accidents_per_day": "Accidents per day",
                                                   "fatal_rate": "Fatality rate (%)"}[col],
                  value_fmt=",.0f" if col == "accidents" else ".1f", height=320,
                  hover_extra={"accidents": ("Accidents", ",.0f"), "days_with_data": ("Days with data", ",.0f"),
                               "fatal": ("Fatal", ",.0f")})
    part = ms[ms["partial"]]
    if len(part):
        fig.add_scatter(x=part["month_start"], y=part[col], mode="markers", name="Partial month",
                        marker=dict(size=12, color="rgba(0,0,0,0)", line=dict(color=V.TEXT, width=2)),
                        hoverinfo="skip", showlegend=True)
        fig.update_layout(showlegend=True)
    ui.chart(fig)

# ---- YoY ----------------------------------------------------------------------
c1, c2 = st.columns([1.5, 1], gap="medium")
with c1:
    yoy = fdf.groupby(["year", "month"]).size().rename("accidents").reset_index()
    yoy["month_name"] = yoy["month"].map(lambda x: config.MONTH_ORDER[x - 1])
    years = sorted(yoy["year"].unique())
    fig = V.lines(yoy.sort_values(["year", "month"]), "month_name", "accidents", group="year",
                  colors={str(y): V.CATEGORICAL[i] for i, y in enumerate(years)}, y_title="Accidents", height=330)
    fig.update_xaxes(categoryorder="array", categoryarray=config.MONTH_ORDER)
    ui.chart_card("Year-over-year comparison by month", fig,
                  "Monthly counts overlaid by year (April 2025 holds only 15 days).")
with c2:
    sp = A.same_period_comparison(fdf)
    if not sp.empty:
        sp["year"] = sp["year"].astype(str)
        ui.chart_card(f"Like-for-like: {sp['window'].iloc[0]}",
                      V.bar(sp, "year", "accidents", val_title="Accidents",
                            hover_extra={"fatal_rate": ("Fatality rate %", ".1f"), "change_pct": ("Change vs prior %", "+.1f")},
                            height=330),
                      "Same calendar window in every year — the only fair YoY comparison with a partial 2025.")

# ---- Day of week & hour --------------------------------------------------------------------
c1, c2 = st.columns(2, gap="medium")
with c1:
    dw = A.group_summary(fdf, "day_of_week", config.DAY_ORDER)
    rng = pd.date_range(fdf["date"].min(), fdf["date"].max(), freq="D")
    cal = pd.Series(rng.day_name()).value_counts()
    dw["calendar_days"] = dw["day_of_week"].map(cal)
    dw["per_day"] = dw["accidents"] / dw["calendar_days"]
    colors = [V.ACCENT if d in ("Saturday", "Sunday") else V.CATEGORICAL[0] for d in dw["day_of_week"]]
    ui.chart_card("Day-of-week analysis",
                  V.bar(dw, "day_of_week", "per_day", color=colors, value_fmt=".2f", val_title="Accidents per calendar day",
                        hover_extra={"accidents": ("Total accidents", ",.0f"), "calendar_days": ("Calendar days", ",.0f"),
                                     "fatal_rate": ("Fatality rate %", ".1f")}, height=320),
                  "Average accidents on each weekday (orange = weekend).")
with c2:
    hr = A.group_summary(fdf, "hour")
    hr["hour"] = hr["hour"].astype(int)
    peak = set(fdf.loc[fdf["is_peak_hour"] == 1, "hour"].unique())
    hr["label"] = hr["hour"].map(lambda h: f"{h:02d}")
    fig = V.bar(hr, "label", "accidents", color=[V.ACCENT if h in peak else V.CATEGORICAL[0] for h in hr["hour"]],
                val_title="Accidents", text=False, hover_extra={"fatal": ("Fatal", ",.0f"),
                                                                "fatal_rate": ("Fatality rate %", ".1f")}, height=320)
    fig.update_xaxes(title_text="Hour of day")
    ui.chart_card("Hour-wise accident distribution", fig,
                  f"Orange = dataset's peak hours ({', '.join(f'{h:02d}' for h in sorted(peak))}:00).")

# ---- Heatmap --------------------------------------------------------------------
with st.container(border=True):
    a, b = st.columns([2, 1])
    with a:
        ui.card_title("Day × hour heatmap", "Darker → brighter = more accidents (or higher fatality rate).")
    with b:
        hv = st.segmented_control("Value", ["Accidents", "Fatality rate"], default="Accidents",
                                  key="tm_heat", label_visibility="collapsed") or "Accidents"
    mat = A.hour_dow_matrix(fdf, "fatal_rate" if hv == "Fatality rate" else "count")
    mat.columns = [f"{c:02d}" for c in mat.columns]
    ui.chart(V.heatmap(mat, height=330, x_title="Hour of day", z_label="Fatality %" if hv != "Accidents" else "Accidents",
                       value_fmt=".1f" if hv != "Accidents" else ",.0f",
                       zmin=0 if hv == "Accidents" else None))
    if hv == "Accidents":
        st.caption("Colour scale starts at zero so that near-equal cells look near-equal.")
    if hv == "Fatality rate":
        st.caption(f"Each cell holds ~{len(fdf) / 168:.0f} accidents on average; cell-level rates are noisy.")

# ---- Weekend / peak ---------------------------------------------------------------
ww = A.weekday_weekend(fdf)
pk = A.group_summary(fdf, "peak_label", ["Peak hour", "Off-peak"])
c1, c2 = st.columns(2, gap="medium")
with c1, st.container(border=True):
    ui.card_title("Weekend vs weekday", "Normalised per calendar day (5 weekdays vs 2 weekend days).")
    if len(ww) == 2:
        w = ww.set_index("day_type")
        z = A.two_proportion_z(w.loc["Weekend", "fatal"], w.loc["Weekend", "accidents"],
                               w.loc["Weekday", "fatal"], w.loc["Weekday", "accidents"])
        mw = A.mann_whitney(fdf, "casualties", "is_weekend")
        ui.kpi_cards([
            {"label": "Weekday / day", "value": f"{w.loc['Weekday', 'accidents_per_day']:.2f}",
             "sub": f"{w.loc['Weekday', 'accidents']:,} accidents"},
            {"label": "Weekend / day", "value": f"{w.loc['Weekend', 'accidents_per_day']:.2f}",
             "sub": f"{w.loc['Weekend', 'accidents']:,} accidents", "tone": "accent"},
            {"label": "Fatality rate", "value": f"{w.loc['Weekend', 'fatal_rate']:.1f}% vs {w.loc['Weekday', 'fatal_rate']:.1f}%",
             "sub": f"weekend vs weekday · p = {z['p_value']:.3f}", "tone": "fatal"},
            {"label": "Avg casualties", "value": f"{w.loc['Weekend', 'avg_casualties']:.2f} vs {w.loc['Weekday', 'avg_casualties']:.2f}",
             "sub": f"Mann–Whitney p = {mw.get('p_value', float('nan')):.3f}"},
        ], cols=2)
    else:
        st.caption("Only one day type in the current selection.")
with c2, st.container(border=True):
    ui.card_title("Peak vs off-peak", "Per clock-hour: peak hours are 6 of the 24.")
    if len(pk) == 2:
        p = pk.set_index("peak_label")
        n_peak = fdf.loc[fdf["is_peak_hour"] == 1, "hour"].nunique()
        z = A.two_proportion_z(p.loc["Peak hour", "fatal"], p.loc["Peak hour", "accidents"],
                               p.loc["Off-peak", "fatal"], p.loc["Off-peak", "accidents"])
        ui.kpi_cards([
            {"label": "Peak / hour", "value": f"{p.loc['Peak hour', 'accidents'] / max(n_peak, 1):,.0f}",
             "sub": f"{p.loc['Peak hour', 'accidents']:,} accidents", "tone": "accent"},
            {"label": "Off-peak / hour", "value": f"{p.loc['Off-peak', 'accidents'] / max(24 - n_peak, 1):,.0f}",
             "sub": f"{p.loc['Off-peak', 'accidents']:,} accidents"},
            {"label": "Fatality rate", "value": f"{p.loc['Peak hour', 'fatal_rate']:.1f}% vs {p.loc['Off-peak', 'fatal_rate']:.1f}%",
             "sub": f"peak vs off-peak · p = {z['p_value']:.3f}", "tone": "fatal"},
            {"label": "Avg risk score", "value": f"{p.loc['Peak hour', 'avg_risk']:.2f} vs {p.loc['Off-peak', 'avg_risk']:.2f}",
             "sub": "peak hour adds +0.15 by formula"},
        ], cols=2)
    else:
        st.caption("Only one period in the current selection.")

# ---- Time of day severity + seasons -----------------------------------------------------
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Time-of-day accident severity",
                  V.severity_stack(A.severity_mix(fdf, "time_of_day", config.TIME_OF_DAY_ORDER), "time_of_day", height=330),
                  "Severity share within each time-of-day bucket.")
with c2:
    se = A.group_summary(fdf, "season", config.SEASON_ORDER)
    rng = pd.date_range(fdf["date"].min(), fdf["date"].max(), freq="D")
    days = pd.Series(pd.Series(rng.month).map(config.SEASON_BY_MONTH)).value_counts()
    se["calendar_days"] = se["season"].map(days)
    se["per_day"] = se["accidents"] / se["calendar_days"]
    ui.chart_card("Seasonal pattern (IMD seasons)",
                  V.bar(se, "season", "per_day", value_fmt=".2f", val_title="Accidents per calendar day",
                        color=[V.CATEGORICAL[i] for i in range(len(se))],
                        hover_extra={"accidents": ("Accidents", ",.0f"), "calendar_days": ("Days", ",.0f"),
                                     "fatal_rate": ("Fatality rate %", ".1f")}, height=330),
                  "Winter Jan–Feb · Summer Mar–May · Monsoon Jun–Sep · Post-monsoon Oct–Dec.")
