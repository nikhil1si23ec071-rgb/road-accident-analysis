"""Page 7 — Risk and Advanced Insights."""
import streamlit as st

from src import analysis as A
from src import config, ui
from src import visualizations as V
from src.profiling import RISK_FORMULA_TEXT

fdf = ui.filtered()
ui.page_header("Risk & Advanced Insights",
               "The dataset's risk score, correlations, statistical tests and the highest-risk accident profiles "
               "actually observed.", fdf)
ui.guard(fdf)
k = A.kpis(fdf)

ui.note(f"<b>How risk_score is built.</b> It is reproduced exactly (100% of rows) by <code>{RISK_FORMULA_TEXT}</code>. "
        "Because severity is an input, risk score is higher for fatal accidents by construction and must not be "
        "read as evidence that 'risk predicts fatality'. <b>Condition risk</b> (the same rule without the severity "
        "term) is shown alongside for a non-circular comparison.", "warn")

# ---- Distribution + by severity ----------------------------------------------
c1, c2 = st.columns(2, gap="medium")
with c1, st.container(border=True):
    a, b = st.columns([1.6, 1])
    with a:
        ui.card_title("Risk score distribution", "18 discrete values in steps of 0.05.")
    with b:
        which = st.segmented_control("Score", ["Risk", "Condition"], default="Risk",
                                     key="rk_hist", label_visibility="collapsed") or "Risk"
    col = "risk_score" if which == "Risk" else "condition_risk"
    ui.chart(V.histogram(fdf[col], nbins=20, x_title="Risk score" if which == "Risk" else "Condition risk (excl. severity)",
                         height=300))
with c2:
    ui.chart_card("Risk score by accident severity",
                  V.box_by(fdf, "risk_score", "accident_severity", config.SEVERITY_ORDER, V.SEVERITY_COLORS,
                           height=345, value_title="Risk score", labels=V.SEVERITY_LABEL),
                  "Fatal is ~0.2 higher purely because the formula adds +0.20 for severity = fatal.")

# ---- By city / cause ------------------------------------------------------------------
cs = A.group_summary(fdf, "city")
cz = A.group_summary(fdf, "cause")
cz["cause_t"] = cz["cause"].str.title()
c1, c2 = st.columns(2, gap="medium")
with c1:
    ui.chart_card("Average risk score by city",
                  V.bar(cs, "city", "avg_risk", horizontal=True, sort=True, value_fmt=".3f", val_title="Average risk score",
                        hover_extra={"avg_condition_risk": ("Condition risk", ".3f"), "accidents": ("Accidents", ",.0f")},
                        height=330), "Axis starts at zero, so near-identical bars mean near-identical averages.")
with c2:
    ui.chart_card("Average risk score by cause",
                  V.bar(cz, "cause_t", "avg_risk", horizontal=True, sort=True, value_fmt=".3f", val_title="Average risk score",
                        hover_extra={"avg_condition_risk": ("Condition risk", ".3f"), "accidents": ("Accidents", ",.0f")},
                        height=330), "Cause is not an input to the score.")

# ---- Correlation + scatter ---------------------------------------------------------------
c1, c2 = st.columns([1.3, 1], gap="medium")
with c1:
    ui.chart_card("Correlation heatmap (Spearman ρ)", V.corr_heatmap(A.correlation_matrix(fdf), height=540),
                  "Rank correlation, robust to the discrete scales. Correlation is not causation; the strongest "
                  "pairs (casualties–vehicles, risk–peak hour) are construction rules of the dataset.")
with c2:
    sc = V.scatter_jitter(fdf, "vehicles_involved", "casualties", x_title="Vehicles involved", y_title="Casualties",
                          height=540)
    rho = fdf[["vehicles_involved", "casualties"]].corr(method="spearman").iloc[0, 1]
    ui.chart_card("Vehicles involved vs casualties", sc,
                  f"Jittered points (integer data). Spearman ρ = {rho:.2f}. Casualties never exceed vehicles, "
                  "and fatal records sit exactly on casualties = vehicles.")

# ---- Highest-risk profiles ---------------------------------------------------------------
DIMS = {"Road type": "road_type", "Weather": "weather", "Time of day": "time_of_day",
        "Traffic density": "traffic_density", "Cause": "cause", "City": "city", "Day type": "day_type",
        "Traffic signal": "signal_label", "Lanes": "lanes", "Season": "season", "Visibility": "visibility"}
with st.container(border=True):
    ui.card_title("Highest-risk accident profiles (observed)",
                  "Combinations of conditions ranked by an observed outcome. Only combinations with enough accidents "
                  "are ranked; each is tested against the overall rate with FDR correction across all combinations.")
    a, b, c = st.columns([2, 1, 1])
    with a:
        dims = st.multiselect("Combine conditions", list(DIMS), default=["Road type", "Weather", "Time of day", "Traffic density"],
                              key="rk_dims", max_selections=5)
    with b:
        min_n = st.number_input("Minimum accidents per profile", min_value=10, max_value=2000, value=50, step=10,
                                key="rk_min_n")
    with c:
        rank = st.selectbox("Rank by", ["Fatality rate", "Avg casualties", "Avg risk score"], key="rk_rank")
    if dims:
        rp = A.risk_profiles(fdf, [DIMS[d] for d in dims], min_n=int(min_n),
                             sort_by={"Fatality rate": "fatal_rate", "Avg casualties": "avg_casualties",
                                      "Avg risk score": "avg_risk"}[rank])
        if rp.empty:
            st.info(f"No combination has at least {int(min_n)} accidents. Lower the minimum or combine fewer conditions.")
        else:
            n_tested = int(rp["combinations_tested"].iloc[0])
            n_sig = int(rp["significant_after_correction"].sum())
            show = rp.drop(columns=["p_value", "combinations_tested", "ci_excludes_overall"]).rename(
                columns={v: k_ for k_, v in DIMS.items()})
            st.dataframe(show, hide_index=True, column_config={
                "accidents": "Accidents", "fatal": "Fatal",
                "fatal_rate": st.column_config.NumberColumn("Fatality rate", format="%.1f%%"),
                "ci_low": st.column_config.NumberColumn("95% CI low", format="%.1f%%"),
                "ci_high": st.column_config.NumberColumn("95% CI high", format="%.1f%%"),
                "vs_overall_pp": st.column_config.NumberColumn("vs overall (pp)", format="%+.1f"),
                "avg_casualties": st.column_config.NumberColumn("Avg casualties", format="%.2f"),
                "avg_risk": st.column_config.NumberColumn("Avg risk", format="%.3f"),
                "p_adjusted": st.column_config.NumberColumn("p (FDR-adjusted)", format="%.3f"),
                "significant_after_correction": st.column_config.CheckboxColumn("Significant")})
            ui.note(f"{n_tested} combinations met the size threshold; <b>{n_sig}</b> differ from the overall fatality "
                    f"rate ({k['fatal_pct']:.1f}%) after correcting for multiple comparisons. "
                    + ("The top of this list is therefore what chance alone produces when many groups are ranked — "
                       "it should not be read as a set of genuinely dangerous conditions."
                       if n_sig == 0 else "Significant rows are associations in this dataset, not causes."),
                    "info" if n_sig else "warn")

# ---- Statistical tables ------------------------------------------------------------------
ui.section("Statistical summary", "Assumptions are checked before a test is interpreted; p-values are FDR-adjusted.")
t1, t2, t3, t4 = st.tabs(["Hypothesis tests", "Descriptive statistics", "Outliers", "Severity profile"])
with t1:
    tb = A.test_battery(fdf)
    if tb.empty:
        st.info(f"At least {config.MIN_GROUP_N} records are needed to run the tests.")
    else:
        st.dataframe(tb[["test", "statistic", "dof", "p_value", "p_adjusted", "effect_name", "effect_size", "n",
                         "valid", "interpretation"]], hide_index=True, column_config={
            "statistic": st.column_config.NumberColumn("Statistic", format="%.2f"),
            "dof": st.column_config.NumberColumn("df", format="%d"),
            "p_value": st.column_config.NumberColumn("p", format="%.4f"),
            "p_adjusted": st.column_config.NumberColumn("p (FDR)", format="%.4f"),
            "effect_size": st.column_config.NumberColumn("Effect", format="%.3f"),
            "effect_name": "Effect measure", "valid": st.column_config.CheckboxColumn("Assumptions met")})
        st.caption("χ² = Pearson chi-square test of independence (valid when ≥80% of expected counts ≥ 5). "
                   "Kruskal–Wallis and Mann–Whitney are rank tests, used because casualties and risk score are "
                   "discrete and non-normal. Cramér's V < 0.1 is a negligible association.")
with t2:
    st.dataframe(A.descriptive_stats(fdf).round(3))
with t3:
    st.dataframe(A.outlier_summary(fdf).round(3), hide_index=True)
    st.caption("IQR rule (1.5×IQR) and |z| > 3. Outliers are flagged in the cleaned data, never deleted.")
with t4:
    prof = fdf.groupby("accident_severity").agg(
        accidents=("accident_id", "size"), avg_casualties=("casualties", "mean"), avg_vehicles=("vehicles_involved", "mean"),
        avg_risk=("risk_score", "mean"), avg_condition_risk=("condition_risk", "mean"), avg_temp=("temperature", "mean"),
        pct_peak=("is_peak_hour", "mean"), pct_weekend=("is_weekend", "mean"), pct_festival=("festival_flag", "mean"),
    ).reindex([s for s in config.SEVERITY_ORDER if s in fdf["accident_severity"].unique()])
    for c in ("pct_peak", "pct_weekend", "pct_festival"):
        prof[c] = prof[c].astype(float) * 100
    st.dataframe(prof.round(3), column_config={
        "pct_peak": st.column_config.NumberColumn("% peak hour", format="%.1f%%"),
        "pct_weekend": st.column_config.NumberColumn("% weekend", format="%.1f%%"),
        "pct_festival": st.column_config.NumberColumn("% festival", format="%.2f%%")})
    st.caption("Condition risk is identical across severities, confirming that severity is unrelated to the "
               "recorded conditions; the gap in risk_score comes entirely from its severity term.")
