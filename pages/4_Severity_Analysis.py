"""Page 4 — Severity and Casualty Analysis."""
import streamlit as st

from src import analysis as A
from src import config, ui
from src import visualizations as V
from src.utils import fmt_int, fmt_pct

fdf = ui.filtered()
ui.page_header("Severity & Casualty Analysis",
               "How severe accidents are, how many people they affect, and whether any condition is associated "
               "with a higher share of fatal accidents.", fdf)
ui.guard(fdf)

k = A.kpis(fdf)
ui.kpi_cards([
    {"label": "Fatal accidents", "value": fmt_int(k["fatal"]), "sub": f"{fmt_pct(k['fatal_pct'])} of accidents", "tone": "fatal"},
    {"label": "Major accidents", "value": fmt_int(k["major"]), "sub": f"{k['major'] / k['accidents'] * 100:.1f}% of accidents", "tone": "major"},
    {"label": "Minor accidents", "value": fmt_int(k["minor"]), "sub": f"{k['minor'] / k['accidents'] * 100:.1f}% of accidents", "tone": "minor"},
    {"label": "Casualties in fatal accidents", "value": fmt_int(k["casualties_in_fatal"]),
     "sub": f"{k['casualties_in_fatal'] / max(k['casualties'], 1) * 100:.1f}% of all casualties"},
])
ui.note("<b>Fatal accidents ≠ fatalities.</b> A fatal accident is a record whose severity is 'fatal'. "
        "The dataset's <i>casualties</i> field counts persons affected (killed or injured) without separating "
        "deaths, so the number of people killed cannot be computed.", "info")

# ---- Distribution + casualties --------------------------------------------------
c1, c2, c3 = st.columns(3, gap="medium")
sv = A.group_summary(fdf, "accident_severity", config.SEVERITY_ORDER)
sv["label"] = sv["accident_severity"].map(V.SEVERITY_LABEL)
cols = [V.SEVERITY_COLORS[s] for s in sv["accident_severity"]]
with c1:
    ui.chart_card("Fatal, major and minor accidents",
                  V.bar(sv, "label", "accidents", color=cols, val_title="Accidents",
                        hover_extra={"share_pct": ("Share %", ".1f")}, height=300))
with c2:
    ui.chart_card("Total casualties by severity",
                  V.bar(sv, "label", "casualties", color=cols, val_title="Casualties",
                        hover_extra={"casualty_share_pct": ("Share of casualties %", ".1f")}, height=300))
with c3:
    ui.chart_card("Average casualties per accident",
                  V.bar(sv, "label", "avg_casualties", color=cols, value_fmt=".2f", val_title="Casualties per accident",
                        hover_extra={"accidents": ("Accidents", ",.0f")}, height=300),
                  f"{fmt_int(fdf['dq_major_zero_casualties'].sum())} 'major' records have zero casualties.")

# ---- Casualty distribution ------------------------------------------------------
ct = fdf.groupby(["casualties", "accident_severity"]).size().rename("count").reset_index()
with st.container(border=True):
    ui.card_title("Casualty-count distribution by severity",
                  "How many accidents had 0, 1, 2 … casualties. Fatal records never have zero casualties.")
    import plotly.graph_objects as go
    fig = go.Figure()
    for s in config.SEVERITY_ORDER:
        d = ct[ct["accident_severity"] == s]
        fig.add_bar(x=d["casualties"], y=d["count"], name=V.SEVERITY_LABEL[s],
                    marker=dict(color=V.SEVERITY_COLORS[s], cornerradius=3),
                    hovertemplate=f"{V.SEVERITY_LABEL[s]} · %{{x}} casualties<br>%{{y:,}} accidents<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig.update_xaxes(title_text="Casualties in the accident", dtick=1)
    fig.update_yaxes(title_text="Accidents")
    ui.chart(V.finish(fig, 300))

# ---- Severity by dimension --------------------------------------------------------
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Severity by state", V.severity_stack(A.severity_mix(fdf, "state"), "state", horizontal=True, height=340))
with c2:
    ui.chart_card("Severity by road type", V.severity_stack(A.severity_mix(fdf, "road_type"), "road_type", height=340))
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Severity by weather", V.severity_stack(A.severity_mix(fdf, "weather"), "weather", height=320))
with c2:
    ui.chart_card("Severity by traffic density",
                  V.severity_stack(A.severity_mix(fdf, "traffic_density", config.LEVEL_ORDER), "traffic_density", height=320))
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Severity by vehicles involved",
                  V.severity_stack(A.severity_mix(fdf, "vehicles_involved"), "vehicles_involved", height=320,
                                   cat_title="Vehicles involved"))
with c2:
    ui.chart_card("Severity by time of day",
                  V.severity_stack(A.severity_mix(fdf, "time_of_day", config.TIME_OF_DAY_ORDER), "time_of_day", height=320))

# ---- Fatality-rate comparison -------------------------------------------------------
DIMS = {"Road type": "road_type", "Weather": "weather", "Visibility": "visibility", "Traffic density": "traffic_density",
        "Cause": "cause", "City": "city", "State": "state", "Time of day": "time_of_day", "Day type": "day_type",
        "Peak hour": "peak_label", "Traffic signal": "signal_label", "Lanes": "lanes", "Season": "season",
        "Vehicles involved": "vehicles_involved", "Festival": "festival_name"}
with st.container(border=True):
    a, b = st.columns([2, 1])
    with a:
        ui.card_title("Fatality-rate comparison",
                      "Any dimension, with 95% Wilson intervals and a χ² test. Grey dots: fewer than "
                      f"{config.MIN_GROUP_N} accidents (unreliable).")
    with b:
        dim = st.selectbox("Compare by", list(DIMS), key="sev_dim")
    col = DIMS[dim]
    gs = A.group_summary(fdf, col)
    gs[col] = gs[col].astype(str)
    ui.chart(V.rate_ci(gs, col, overall=k["fatal_pct"], height=max(260, 46 * len(gs) + 80)))
    t = A.fatal_rate_test(fdf, col)
    if not t["valid"] and t["p_value"] != t["p_value"]:
        st.caption("No test: the selection needs at least two groups and both fatal and non-fatal accidents.")
    else:
        verdict = ("differences are statistically significant" if t["p_value"] < 0.05 else
                   "no statistically significant difference")
        st.caption(f"χ²({t['dof']}) = {t['statistic']:.2f}, p = {t['p_value']:.3f}, Cramér's V = {t['effect_size']:.3f} → "
                   f"{verdict}{'' if t['valid'] else ' (warning: small expected counts)'}.")

# ---- Severity over time --------------------------------------------------------------
c1, c2 = st.columns([1.4, 1], gap="medium")
with c1:
    q = A.severity_mix(fdf, "year_quarter", sorted(fdf["year_quarter"].unique()))
    ui.chart_card("Severity distribution across quarters",
                  V.severity_stack(q, "year_quarter", height=330), "2025-Q2 contains only 1–15 April.")
with c2:
    ys = A.group_summary(fdf, "year")
    ys["year"] = ys["year"].astype(str)
    ui.chart_card("Fatality rate by year", V.rate_ci(ys, "year", overall=k["fatal_pct"], height=330, sort=False))
