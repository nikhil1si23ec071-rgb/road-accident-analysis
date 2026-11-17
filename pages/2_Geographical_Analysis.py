"""Page 2 — Geographical Intelligence."""
import streamlit as st

from src import analysis as A
from src import ui
from src import visualizations as V
from src.utils import fmt_int, fmt_pct

fdf = ui.filtered()
ui.page_header("Geographical Intelligence",
               "Where accidents are recorded: an interactive map of every valid coordinate, plus state and "
               "city comparisons of counts, casualties and fatality rates.", fdf)
ui.guard(fdf)

valid = fdf[fdf["coord_valid"] == 1]
k = A.kpis(fdf)
ui.kpi_cards([
    {"label": "Cities in selection", "value": fdf["city"].nunique(), "sub": f"{fdf['state'].nunique()} states", "tone": "accent"},
    {"label": "Mapped accidents", "value": fmt_int(len(valid)),
     "sub": f"{len(valid) / len(fdf) * 100:.1f}% have valid coordinates"},
    {"label": "Fatal accidents", "value": fmt_int(k["fatal"]), "sub": f"{fmt_pct(k['fatal_pct'])} fatality rate", "tone": "fatal"},
    {"label": "Casualties", "value": fmt_int(k["casualties"]), "sub": f"{k['avg_casualties']:.2f} per accident"},
])

# ---- Map --------------------------------------------------------------------
with st.container(border=True):
    h1, h2, h3, h4 = st.columns([1.5, 1, 1.1, 0.8])
    with h1:
        ui.card_title("Accident map",
                      "Every record with coordinates inside India and within 75 km of its city centre. "
                      "Nothing is geocoded or imputed.")
    with h2:
        focus = st.selectbox("Focus city", ["All cities"] + sorted(fdf["city"].unique()), key="geo_focus")
    with h3:
        mode = st.segmented_control("Layer", ["Points", "Hotspot density"], default="Points", key="geo_mode") or "Points"
    with h4:
        basemap = st.toggle("Street basemap", value=True, key="geo_basemap",
                            help="Dark street tiles from CARTO (needs internet). Turn off to plot points on a plain background.")
    mdf = fdf if focus == "All cities" else fdf[fdf["city"] == focus]
    ui.chart(V.map_points(mdf, mode="density" if mode == "Hotspot density" else "points",
                             height=540, basemap=basemap))
    excluded = int((mdf["coord_valid"] == 0).sum())
    st.caption(f"{fmt_int((mdf['coord_valid'] == 1).sum())} points shown"
               + (f" · {excluded} records excluded for invalid coordinates" if excluded else
                  " · no records excluded") +
               ". Coordinates scatter up to ~37 km around each city centre with no road-network snapping, "
               "so hotspots below city level should not be interpreted.")

# ---- States -----------------------------------------------------------------
ss = A.group_summary(fdf, "state")
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("State-wise accident distribution",
                  V.bar(ss, "state", "accidents", horizontal=True, sort=True, val_title="Accidents",
                        hover_extra={"share_pct": ("Share %", ".1f"), "casualties": ("Casualties", ",.0f"),
                                     "fatal": ("Fatal accidents", ",.0f")}, height=330),
                  "Maharashtra contains two cities (Mumbai, Pune) in this dataset, which doubles its count.")
with c2:
    ui.chart_card("State-wise fatality rate",
                  V.rate_ci(ss, "state", overall=k["fatal_pct"], height=330),
                  "Dots = fatal ÷ accidents; bars = 95% Wilson confidence interval. Overlapping intervals "
                  "mean states cannot be distinguished.")

# ---- Cities -----------------------------------------------------------------
cs = A.group_summary(fdf, "city")
METRICS = {"Accidents": ("accidents", ",.0f", ""), "Casualties": ("casualties", ",.0f", ""),
           "Fatal accidents": ("fatal", ",.0f", ""), "Fatality rate": ("fatal_rate", ".1f", "%"),
           "Avg casualties / accident": ("avg_casualties", ".2f", "")}
c1, c2 = st.columns(2, gap="medium")
with c1, st.container(border=True):
    a, b = st.columns([1.2, 1])
    with a:
        ui.card_title("City-wise comparison", "Pick the metric to compare.")
    with b:
        m = st.selectbox("Metric", list(METRICS), key="geo_city_metric", label_visibility="collapsed")
    col, fmt, suf = METRICS[m]
    ui.chart(V.bar(cs, "city", col, horizontal=True, sort=True, val_title=m, value_fmt=fmt, suffix=suf,
                   hover_extra={"accidents": ("Accidents", ",.0f"), "fatal_rate": ("Fatality rate %", ".1f"),
                                "casualties": ("Casualties", ",.0f")}, height=340))
with c2:
    top_fatal = cs.nlargest(10, "fatal")
    ui.chart_card("Top 10 cities by fatal accidents",
                  V.bar(top_fatal, "city", "fatal", horizontal=True, sort=True, color=V.SEVERITY_COLORS["fatal"],
                        val_title="Fatal accidents", hover_extra={"accidents": ("All accidents", ",.0f"),
                                                                  "fatal_rate": ("Fatality rate %", ".1f")},
                        height=340),
                  "Counts of accidents with severity = fatal (not a count of deaths).")

c1, c2 = st.columns([1, 1], gap="medium")
with c1:
    ui.chart_card("Severity mix by city", V.severity_stack(A.severity_mix(fdf, "city"), "city", horizontal=True,
                                                         height=360), "Share of each city's accidents.")
with c2:
    ui.chart_card("Casualty distribution by city",
                  V.bar(cs, "city", "casualty_share_pct", horizontal=True, sort=True, value_fmt=".1f", suffix="%",
                        val_title="Share of all casualties (%)", color=V.ACCENT,
                        hover_extra={"casualties": ("Casualties", ",.0f"), "avg_casualties": ("Avg per accident", ".2f")},
                        height=360),
                  "Each city's share of the selection's total casualties.")

with st.container(border=True):
    ui.card_title("City summary table", "All metrics, sortable. Rates use each city's own accident count as denominator.")
    t = cs[["city", "accidents", "share_pct", "fatal", "fatal_rate", "ci_low", "ci_high", "casualties",
            "avg_casualties", "avg_vehicles", "avg_risk"]].sort_values("accidents", ascending=False)
    st.dataframe(t, hide_index=True, column_config={
        "city": "City", "accidents": st.column_config.NumberColumn("Accidents", format="%d"),
        "share_pct": st.column_config.ProgressColumn("Share", format="%.1f%%", min_value=0, max_value=max(t["share_pct"].max(), 1)),
        "fatal": st.column_config.NumberColumn("Fatal", format="%d"),
        "fatal_rate": st.column_config.NumberColumn("Fatality rate", format="%.1f%%"),
        "ci_low": st.column_config.NumberColumn("CI low", format="%.1f%%"),
        "ci_high": st.column_config.NumberColumn("CI high", format="%.1f%%"),
        "casualties": st.column_config.NumberColumn("Casualties", format="%d"),
        "avg_casualties": st.column_config.NumberColumn("Avg casualties", format="%.2f"),
        "avg_vehicles": st.column_config.NumberColumn("Avg vehicles", format="%.2f"),
        "avg_risk": st.column_config.NumberColumn("Avg risk", format="%.3f")})
    t_city = A.fatal_rate_test(fdf, "city") if fdf["city"].nunique() > 1 else None
    if t_city and t_city["p_value"] == t_city["p_value"]:
        st.caption(f"χ² test of fatality rate across cities: p = {t_city['p_value']:.3f}, Cramér's V = "
                   f"{t_city['effect_size']:.3f} — "
                   + ("cities differ beyond chance." if t_city["p_value"] < 0.05 else
                      "no evidence that cities differ in fatality rate."))
