"""Page 5 — Cause and Weather Analysis."""
import streamlit as st

from src import analysis as A
from src import config, ui
from src import visualizations as V

fdf = ui.filtered()
ui.page_header("Causes & Weather",
               "What the records attribute accidents to, and the weather, visibility, temperature and traffic "
               "conditions they occurred in.", fdf)
ui.guard(fdf)
k = A.kpis(fdf)

# ---- Causes ---------------------------------------------------------------------
cz = A.group_summary(fdf, "cause")
cz["cause_t"] = cz["cause"].str.title()
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Accidents by cause",
                  V.bar(cz, "cause_t", "accidents", horizontal=True, sort=True, val_title="Accidents",
                        hover_extra={"share_pct": ("Share %", ".1f"), "casualties": ("Casualties", ",.0f"),
                                     "avg_casualties": ("Avg casualties", ".2f")}, height=320))
with c2:
    ui.chart_card("Fatality rate by cause", V.rate_ci(cz, "cause_t", overall=k["fatal_pct"], height=320),
                  "95% Wilson intervals; dotted line = overall rate.")

c1, c2 = st.columns([1.4, 1], gap="medium")
with c1, st.container(border=True):
    a, b = st.columns([2, 1])
    with a:
        ui.card_title("Cause × severity", "Stacked by recorded severity.")
    with b:
        pct = (st.segmented_control("Scale", ["Counts", "Percent"], default="Counts", key="cw_cause_scale",
                                    label_visibility="collapsed") or "Counts") == "Percent"
    mix = A.severity_mix(fdf, "cause")
    mix["cause"] = mix["cause"].str.title()
    ui.chart(V.severity_stack(mix, "cause", percent=pct, height=330))
with c2:
    ui.chart_card("Casualties by cause",
                  V.bar(cz, "cause_t", "casualties", horizontal=True, sort=True, val_title="Casualties",
                        hover_extra={"avg_casualties": ("Avg per accident", ".2f"),
                                     "casualty_share_pct": ("Share %", ".1f")}, height=330),
                  "Total persons killed or injured.")

# ---- Weather & visibility -----------------------------------------------------------
ui.section("Weather and visibility")
wz = A.group_summary(fdf, "weather")
wcol = V.color_map(wz["weather"])
c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    ui.chart_card("Accidents by weather",
                  V.bar(wz, "weather", "accidents", color=[wcol[w] for w in wz["weather"]], val_title="Accidents",
                        hover_extra={"fatal": ("Fatal accidents", ",.0f"), "avg_casualties": ("Avg casualties", ".2f")},
                        height=300), "Without weather-hours exposure, counts do not show which weather is riskier.")
with c2:
    ui.chart_card("Fatal accidents by weather",
                  V.bar(wz, "weather", "fatal", color=V.SEVERITY_COLORS["fatal"], val_title="Fatal accidents",
                        hover_extra={"fatal_rate": ("Fatality rate %", ".1f")}, height=300))
with c3:
    ui.chart_card("Average casualties by weather",
                  V.bar(wz, "weather", "avg_casualties", color=[wcol[w] for w in wz["weather"]], value_fmt=".2f",
                        val_title="Casualties per accident", height=300))

c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Visibility vs accident severity",
                  V.severity_stack(A.severity_mix(fdf, "visibility", config.LEVEL_ORDER), "visibility", height=320))
with c2:
    wv = fdf.pivot_table(index="weather", columns="visibility", values="accident_id", aggfunc="count", fill_value=0)
    wv = wv.reindex(columns=[c for c in config.LEVEL_ORDER if c in wv.columns])
    ui.chart_card("Weather × visibility (data structure)",
                  V.heatmap(wv.astype(float), height=320, x_title="Visibility", z_label="Accidents", show_text=True),
                  "Visibility is determined by weather in this dataset: clear → high, fog → low, rain → low/medium. "
                  "The two cannot be analysed as independent factors.")

c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Weather-wise risk score",
                  V.bar(wz, "weather", "avg_risk", color=[wcol[w] for w in wz["weather"]], value_fmt=".3f",
                        val_title="Average risk score", hover_extra={"avg_condition_risk": ("Condition risk (excl. severity)", ".3f")},
                        height=300),
                  "Higher for fog/rain by construction: the formula adds +0.15 for fog/rain and +0.20 for low visibility.")
with c2:
    vz = A.group_summary(fdf, "visibility", config.LEVEL_ORDER)
    ui.chart_card("Fatality rate by visibility", V.rate_ci(vz, "visibility", overall=k["fatal_pct"], height=300, sort=False))

# ---- Temperature -------------------------------------------------------------------
ui.section("Temperature")
c1, c2 = st.columns(2, gap="medium")
with c1:
    tc = fdf.groupby("temperature").size().rename("accidents").reset_index()
    tc["t"] = tc["temperature"].astype(int).astype(str)
    fig = V.bar(tc, "t", "accidents", val_title="Accidents", text=False, height=300, color=V.CATEGORICAL[0])
    fig.update_xaxes(title_text="Temperature (°C)")
    ui.chart_card("Temperature vs accident frequency", fig,
                  "Accidents recorded at each temperature. Without the distribution of hours at each temperature, "
                  "this is not a risk curve.")
with c2:
    tb = A.temperature_bands(fdf)
    ui.chart_card("Fatality rate by temperature band", V.rate_ci(tb, "temp_band", overall=k["fatal_pct"], height=300, sort=False))

# ---- Traffic density ----------------------------------------------------------------
ui.section("Traffic density")
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Traffic density vs accident severity",
                  V.severity_stack(A.severity_mix(fdf, "traffic_density", config.LEVEL_ORDER), "traffic_density", height=320))
with c2:
    dh = fdf.pivot_table(index="traffic_density", columns="hour", values="accident_id", aggfunc="count", fill_value=0)
    dh = dh.reindex([d for d in config.LEVEL_ORDER if d in dh.index])
    dh.columns = [f"{c:02d}" for c in dh.columns]
    share = dh.div(dh.sum(axis=0), axis=1) * 100
    ui.chart_card("Traffic density by hour", V.heatmap(share, height=320, x_title="Hour of day",
                                                       z_label="% of hour", value_fmt=".0f"),
                  "Share of each hour's accidents by density — high density concentrates in the 08–10 and 17–19 "
                  "peaks. This is one of the few non-random structures in the data.")
