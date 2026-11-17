"""Indian Road Accident Analytics & Intelligence Dashboard (2022–2025).

    streamlit run app.py

app.py is the router: it loads the (cached) dataset, draws the shared sidebar
(brand, navigation, global filters, download) and then runs the selected page.
All pages read the same filter state from st.session_state via src.ui.
"""
import streamlit as st

from src import ui

st.set_page_config(page_title="Road Accident Intelligence · India", page_icon="🛣️",
                   layout="wide", initial_sidebar_state="expanded")
ui.load_css()

pages = {
    "Dashboard": [
        st.Page("pages/1_Overview.py", url_path="overview", title="Executive Overview", icon=":material/dashboard:", default=True),
        st.Page("pages/2_Geographical_Analysis.py", url_path="geography", title="Geographical Intelligence", icon=":material/map:"),
        st.Page("pages/3_Temporal_Analysis.py", url_path="temporal", title="Temporal Analytics", icon=":material/schedule:"),
        st.Page("pages/4_Severity_Analysis.py", url_path="severity", title="Severity & Casualties", icon=":material/emergency:"),
        st.Page("pages/5_Cause_Weather_Analysis.py", url_path="causes-weather", title="Causes & Weather", icon=":material/rainy:"),
        st.Page("pages/6_Road_Infrastructure.py", url_path="infrastructure", title="Road Infrastructure", icon=":material/add_road:"),
        st.Page("pages/7_Risk_Insights.py", url_path="risk", title="Risk & Advanced Insights", icon=":material/insights:"),
    ],
    "Data": [
        st.Page("pages/8_Data_Quality_Explorer.py", url_path="data", title="Data Quality & Explorer", icon=":material/table_view:"),
    ],
}

st.logo("assets/logo.svg", size="large", icon_image="assets/logo_icon.svg")
nav = st.navigation(pages)
df = ui.data_or_stop()
ui.render_filters(df)
fdf = ui.filtered()
st.sidebar.markdown(f'<div class="sb-foot"><b>{len(fdf):,}</b> of {len(df):,} records match</div>',
                    unsafe_allow_html=True)
ui.download_csv(fdf, key="sb_download", where=st.sidebar)
st.sidebar.markdown(
    '<div class="sb-foot">Source: Kaggle upload (sehaj1104). Statistical checks indicate the records are '
    '<b>simulated</b>, not official MoRTH/NCRB data. See <i>Data Quality</i>.</div>',
    unsafe_allow_html=True)

nav.run()
