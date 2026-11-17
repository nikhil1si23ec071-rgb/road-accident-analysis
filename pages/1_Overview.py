"""Page 1 — Executive Overview."""
import streamlit as st

from src import analysis as A
from src import config, ui
from src import visualizations as V
from src.insights import generate_insights

fdf = ui.filtered()
ui.page_header("Executive Overview",
               "Headline accident, severity and casualty metrics for the current selection, "
               "with automatically generated, statistically checked insights.", fdf)
ui.guard(fdf)

k = A.kpis(fdf)
ui.kpi_cards(ui.standard_kpis(k))

# ---- Row 1: trend + severity ------------------------------------------------
c1, c2 = st.columns([1.65, 1], gap="medium")
with c1, st.container(border=True):
    yt = A.yearly_trend(fdf)
    head, toggle = st.columns([1.6, 1])
    with head:
        ui.card_title("Year-wise accident trend",
                      "Accidents per observed day removes the partial-2025 effect (data ends "
                      f"{fdf['date'].max():%d %b %Y}).")
    with toggle:
        metric = st.segmented_control("Metric", ["Per day", "Annual total"], default="Per day",
                                      key="ov_trend_metric", label_visibility="collapsed") or "Per day"
    ycol = "accidents_per_day" if metric == "Per day" else "accidents"
    yt["year_label"] = yt.apply(lambda r: f"{int(r.year)}{' (partial)' if r.is_partial else ''}", axis=1)
    fig = V.lines(yt, "year_label", ycol, y_title="Accidents per day" if ycol != "accidents" else "Accidents",
                  value_fmt=".2f" if ycol != "accidents" else ",.0f",
                  hover_extra={"accidents": ("Accidents", ",.0f"), "days_observed": ("Days observed", ",.0f"),
                               "fatal_rate": ("Fatal rate %", ".1f")}, height=300)
    if ycol == "accidents_per_day" and len(yt):
        lo, hi = yt[ycol].min(), yt[ycol].max()
        pad = max((hi - lo) * 1.5, hi * 0.05)
        fig.update_yaxes(range=[max(lo - pad, 0), hi + pad])
    ui.chart(fig)
with c2, st.container(border=True):
    ui.card_title("Severity distribution", "Share of accidents by recorded severity.")
    counts = [k[s] for s in config.SEVERITY_ORDER]
    ui.chart(V.donut([V.SEVERITY_LABEL[s] for s in config.SEVERITY_ORDER], counts,
                     [V.SEVERITY_COLORS[s] for s in config.SEVERITY_ORDER], height=300,
                     center_text=f"<b>{k['accidents']:,}</b><br><span style='font-size:11px;color:#7C8391'>accidents</span>"))

# ---- Row 2: cities + causes -------------------------------------------------
c1, c2 = st.columns(2, gap="medium")
with c1, st.container(border=True):
    ui.card_title("Top 10 accident-prone cities", "Absolute accident counts (no population/traffic exposure data available).")
    cs = A.group_summary(fdf, "city").nlargest(10, "accidents")
    ui.chart(V.bar(cs, "city", "accidents", horizontal=True, sort=True, val_title="Accidents",
                   hover_extra={"fatal": ("Fatal accidents", ",.0f"), "fatal_rate": ("Fatality rate %", ".1f"),
                                "casualties": ("Casualties", ",.0f")}, height=330))
with c2, st.container(border=True):
    ui.card_title("Top accident causes", "Recorded primary cause.")
    cz = A.group_summary(fdf, "cause").sort_values("accidents", ascending=False)
    cz["cause"] = cz["cause"].str.title()
    ui.chart(V.bar(cz, "cause", "accidents", val_title="Accidents",
                   hover_extra={"share_pct": ("Share %", ".1f"), "fatal_rate": ("Fatality rate %", ".1f"),
                                "avg_casualties": ("Avg casualties", ".2f")}, height=330))

# ---- Row 3: time of day -----------------------------------------------------
c1, c2 = st.columns([1, 1.65], gap="medium")
with c1, st.container(border=True):
    ui.card_title("Accidents by time of day",
                  "Per clock-hour, because buckets differ in length (Night 21–04 h, Morning 05–11, "
                  "Afternoon 12–16, Evening 17–20).")
    tod = A.per_slot_rate(fdf)
    ui.chart(V.bar(tod, "time_of_day", "accidents_per_hour", val_title="Accidents per clock-hour",
                   value_fmt=",.0f", hover_extra={"accidents": ("Total accidents", ",.0f"),
                                                  "hours_in_bucket": ("Hours in bucket", ".0f"),
                                                  "fatal_rate": ("Fatality rate %", ".1f")}, height=300))
with c2, st.container(border=True):
    ui.card_title("24-hour accident profile", "Accidents at each hour of the day, by severity.")
    hm = fdf.groupby(["hour", "accident_severity"]).size().rename("accidents").reset_index()
    hm["accident_severity"] = hm["accident_severity"].map(V.SEVERITY_LABEL)
    fig = V.lines(hm, "hour", "accidents", group="accident_severity",
                  colors={V.SEVERITY_LABEL[s]: c for s, c in V.SEVERITY_COLORS.items()},
                  x_title="Hour of day", y_title="Accidents", height=300, markers=False)
    fig.update_xaxes(dtick=2, type="linear", range=[-0.5, 23.5])
    ui.chart(fig)

# ---- Insights ---------------------------------------------------------------
ui.section("Automatically generated insights",
           "Recomputed for every filter change. Each card states whether the pattern survives a hypothesis "
           "test — a 'highest' value that is not significant is indistinguishable from chance.")
ui.insight_cards(generate_insights(fdf))
ui.note("<b>Reading these numbers.</b> <i>Accidents</i> are records; <i>fatal accidents</i> are records with "
        "severity = fatal; <i>casualties</i> are persons killed or injured (deaths are not recorded separately, "
        "so no fatality head-count is reported). Associations are not causes. Statistical fingerprints show this "
        "dataset is simulated — see <b>Data Quality & Explorer</b>.", "accent")
