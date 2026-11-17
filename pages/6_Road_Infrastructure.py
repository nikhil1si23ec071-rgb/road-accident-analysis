"""Page 6 — Road Infrastructure Analysis."""
import streamlit as st

from src import analysis as A
from src import config, ui
from src import visualizations as V

fdf = ui.filtered()
ui.page_header("Road Infrastructure",
               "Road type, lane count, traffic signals and traffic density at accident locations, and how "
               "severity and casualties vary across them.", fdf)
ui.guard(fdf)
k = A.kpis(fdf)
n = len(fdf)

ui.kpi_cards([
    {"label": "Highway accidents", "value": f"{(fdf['road_type'] == 'highway').mean() * 100:.1f}%",
     "sub": f"{(fdf['road_type'] == 'highway').sum():,} of {n:,}", "tone": "accent"},
    {"label": "At signalised locations", "value": f"{fdf['traffic_signal'].mean() * 100:.1f}%",
     "sub": f"{int(fdf['traffic_signal'].sum()):,} accidents"},
    {"label": "Average lanes", "value": f"{fdf['lanes'].mean():.2f}", "sub": "at the accident location"},
    {"label": "High-density traffic", "value": f"{(fdf['traffic_density'] == 'high').mean() * 100:.1f}%",
     "sub": "of accidents"},
])

rz = A.group_summary(fdf, "road_type")
rcol = V.color_map(rz["road_type"])
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Accidents by road type",
                  V.bar(rz, "road_type", "accidents", color=[rcol[r] for r in rz["road_type"]], val_title="Accidents",
                        hover_extra={"share_pct": ("Share %", ".1f"), "fatal": ("Fatal", ",.0f"),
                                     "avg_casualties": ("Avg casualties", ".2f")}, height=300))
with c2:
    ui.chart_card("Road type vs fatality rate", V.rate_ci(rz, "road_type", overall=k["fatal_pct"], height=300))

lz = A.group_summary(fdf, "lanes")
lz["lanes"] = lz["lanes"].astype(int).astype(str)
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Accidents by lane count",
                  V.bar(lz, "lanes", "accidents", val_title="Accidents", cat_title="Lanes",
                        color=V.CATEGORICAL[0], hover_extra={"fatal_rate": ("Fatality rate %", ".1f")}, height=300))
with c2:
    ui.chart_card("Fatality rate by lane count", V.rate_ci(lz, "lanes", overall=k["fatal_pct"], height=300, sort=False,
                                                           cat_title="Lanes"))

sz = A.group_summary(fdf, "signal_label")
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Traffic signal vs accident severity",
                  V.severity_stack(A.severity_mix(fdf, "signal_label"), "signal_label", height=300))
with c2:
    ui.chart_card("Fatality rate: signalised vs not", V.rate_ci(sz, "signal_label", overall=k["fatal_pct"], height=300))

c1, c2 = st.columns(2, gap="medium")
with c1:
    rd = fdf.groupby(["road_type", "traffic_density"]).size().rename("accidents").reset_index()
    import plotly.graph_objects as go
    fig = go.Figure()
    dcol = {"low": V.CATEGORICAL[0], "medium": V.CATEGORICAL[3], "high": V.CATEGORICAL[1]}
    for d in config.LEVEL_ORDER:
        s = rd[rd["traffic_density"] == d]
        fig.add_bar(x=s["road_type"], y=s["accidents"], name=d.title(), marker=dict(color=dcol[d], cornerradius=3),
                    hovertemplate=f"%{{x}} · {d} density<br>%{{y:,}} accidents<extra></extra>")
    fig.update_layout(barmode="group", bargroupgap=0.08)
    fig.update_yaxes(title_text="Accidents")
    ui.chart_card("Traffic density comparison by road type", V.finish(fig, 320))
with c2:
    m = fdf.pivot_table(index="road_type", columns="lanes", values="is_fatal", aggfunc="mean") * 100
    m.columns = [str(int(c)) for c in m.columns]
    ui.chart_card("Fatality rate: road type × lanes", V.heatmap(m.astype(float), height=320, x_title="Lanes",
                                                                z_label="Fatality %", value_fmt=".1f", show_text=True),
                  f"~{n / max(m.size, 1):.0f} accidents per cell on average; small cells are noisy.")

with st.container(border=True):
    ui.card_title("Road infrastructure and casualties",
                  "Casualty metrics for every road type × signal combination.")
    t = fdf.groupby(["road_type", "signal_label"]).agg(
        accidents=("accident_id", "size"), casualties=("casualties", "sum"),
        avg_casualties=("casualties", "mean"), fatal=("is_fatal", "sum"),
        avg_vehicles=("vehicles_involved", "mean"), avg_lanes=("lanes", "mean")).reset_index()
    t["fatal_rate"] = t["fatal"] / t["accidents"] * 100
    st.dataframe(t, hide_index=True, column_config={
        "road_type": "Road type", "signal_label": "Signal", "accidents": "Accidents", "casualties": "Casualties",
        "avg_casualties": st.column_config.NumberColumn("Avg casualties", format="%.2f"),
        "fatal": "Fatal", "fatal_rate": st.column_config.NumberColumn("Fatality rate", format="%.1f%%"),
        "avg_vehicles": st.column_config.NumberColumn("Avg vehicles", format="%.2f"),
        "avg_lanes": st.column_config.NumberColumn("Avg lanes", format="%.2f")})
    tests = [t_ for t_ in (A.fatal_rate_test(fdf, c) for c in ["road_type", "lanes", "signal_label", "traffic_density"])
             if t_["p_value"] == t_["p_value"]]
    if tests:
        st.caption("Fatality-rate χ² tests — " + " · ".join(
            f"{t_['test'].replace('Fatality rate differs by ', '').replace(' (χ²)', '')}: p = {t_['p_value']:.3f}"
            for t_ in tests) + ". p ≥ 0.05 means no evidence the infrastructure factor is associated with fatality.")
