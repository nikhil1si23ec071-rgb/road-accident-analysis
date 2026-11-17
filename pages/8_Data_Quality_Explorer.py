"""Page 8 — Data Quality & Explorer: provenance, profile, cleaning log and a
searchable table of the filtered records."""
import json

import pandas as pd
import streamlit as st

from src import config, ui

fdf = ui.filtered()
ui.page_header("Data Quality & Explorer",
               "Where the data comes from, what the profile found, every cleaning decision, and the filtered "
               "records themselves.", fdf)


@st.cache_data(show_spinner=False)
def _json(path: str, mtime: float):
    return json.loads(open(path).read())


prof = _json(str(config.PROFILE_JSON), config.PROFILE_JSON.stat().st_mtime) if config.PROFILE_JSON.exists() else None
log = _json(str(config.CLEANING_LOG_JSON), config.CLEANING_LOG_JSON.stat().st_mtime) if config.CLEANING_LOG_JSON.exists() else []

tab1, tab2, tab3, tab4 = st.tabs(["Provenance", "Dataset profile", "Cleaning log", "Data explorer"])

with tab1:
    if prof:
        pv = prof["provenance"]
        kept = len(ui.get_data())
        dropped = prof["shape"]["rows"] - kept
        miss = {c["column"]: c["missing"] for c in prof["columns"] if c["missing"]}
        miss_sub = ("none" if not miss else "all in 'festival' (structural)" if list(miss) == ["festival"]
                    else ", ".join(f"{k}: {v:,}" for k, v in miss.items()))
        ui.kpi_cards([
            {"label": "Raw records", "value": f"{prof['shape']['rows']:,}", "sub": f"{prof['shape']['columns']} columns", "tone": "accent"},
            {"label": "Records kept", "value": f"{kept:,}",
             "sub": "no rows dropped" if dropped == 0 else f"{dropped:,} exact duplicates removed"},
            {"label": "Verdict", "value": "Simulated" if pv["likely_synthetic"] else "Unverified",
             "sub": "based on statistical fingerprints", "tone": "fatal"},
            {"label": "Missing values", "value": f"{sum(miss.values()):,}", "sub": miss_sub},
        ])
        ui.note(f"<b>Source.</b> {pv['source']}<br><br><b>Verdict.</b> {pv['verdict']}", "warn")
        ui.section("Evidence")
        for s in pv["signals"]:
            st.markdown(f"- {s}")
        ui.section("What this means for the analysis")
        st.markdown(
            "- Findings describe **this dataset**, not Indian road safety. For official figures see the Ministry of "
            "Road Transport & Highways' annual *Road Accidents in India* report and NCRB's *Accidental Deaths & "
            "Suicides in India*.\n"
            "- Near-uniform marginals mean that 'highest' and 'lowest' rankings are mostly noise; the dashboard "
            "marks each with its statistical test.\n"
            "- `risk_score` is a deterministic formula of other columns (including severity), so it carries no "
            "independent information.\n"
            "- `visibility` is a function of `weather`; `hour`, `day_of_week`, `is_weekend` and `is_peak_hour` are "
            "functions of `date`/`time`.")
    else:
        st.info("Run `python -m src.preprocessing` to generate the profile.")

with tab2:
    if prof:
        st.markdown("**Columns**")
        cols = pd.DataFrame(prof["columns"])
        cols["examples"] = cols["examples"].map(lambda x: ", ".join(x))
        st.dataframe(cols, hide_index=True)
        st.markdown("**Derived and leakage-prone columns**")
        st.dataframe(pd.DataFrame(prof["derived_columns"]), hide_index=True, column_config={
            "agreement_pct": st.column_config.NumberColumn("Agreement with rule", format="%.2f%%")})
        st.markdown("**Uniformity tests** — χ² goodness-of-fit against an even split")
        st.dataframe(pd.DataFrame(prof["uniformity"]).T.reset_index().rename(columns={"index": "variable"}), hide_index=True)
        st.markdown("**Logical consistency**")
        cons = {k: v for k, v in prof["consistency"].items() if not isinstance(v, dict)}
        st.dataframe(pd.DataFrame(cons.items(), columns=["check", "value"]).astype(str), hide_index=True)
        st.markdown("**Festival labels vs the real festival calendar**")
        st.dataframe(pd.DataFrame(prof["festival"].get("calendar_coverage", [])), hide_index=True)
        dt = prof["dates_times"]
        st.markdown(f"**Dates** {dt['date']['min'][:10]} → {dt['date']['max'][:10]} · {dt['date']['distinct_days']:,} distinct days "
                    f"· records per year {dt['date']['records_per_year']} · time formats {dt['time']['format_patterns']} "
                    f"· {dt['time']['share_on_the_hour_pct']}% on the hour.")
        co = prof["coordinates"]
        st.markdown(f"**Coordinates** outside India: {co['outside_india_bbox']} · (0,0): {co['zero_zero']} · "
                    f"median distance to city centre {co['km_from_city_median']['median']:.1f} km, max "
                    f"{co['km_from_city_median']['max']:.1f} km.")
        st.caption("Full report: reports/data_profile.md")

with tab3:
    if log:
        st.dataframe(pd.DataFrame(log), hide_index=True, column_config={
            "rows_affected": st.column_config.NumberColumn("Rows", format="%d")})
        st.caption("Full report: reports/cleaning_report.md. Raw file checksum is verified unchanged after every run.")

with tab4:
    if fdf.empty:
        ui.empty_state()
    else:
        default_cols = ["accident_id", "date", "time", "city", "state", "road_type", "weather", "visibility",
                        "traffic_density", "cause", "accident_severity", "vehicles_involved", "casualties",
                        "risk_score", "festival_name", "time_of_day", "season"]
        a, b = st.columns([3, 1])
        with a:
            show_cols = st.multiselect("Columns", list(fdf.columns), default=default_cols, key="ex_cols")
        with b:
            q = st.text_input("Search (any shown column)", key="ex_q", placeholder="e.g. Pune, fog")
        view = fdf[show_cols or default_cols]
        if q:
            terms = [t.strip().lower() for t in q.split(",") if t.strip()]
            text = view.astype(str).apply(lambda r: " ".join(r).lower(), axis=1)
            for t in terms:
                view = view[text.loc[view.index].str.contains(t, regex=False)]
        st.caption(f"{len(view):,} rows shown of {len(fdf):,} filtered records ({len(ui.get_data()):,} total).")
        st.dataframe(view, hide_index=True, height=520,
                     column_config={"date": st.column_config.DateColumn("date", format="DD MMM YYYY")})
        ui.download_csv(fdf, key="ex_download")
