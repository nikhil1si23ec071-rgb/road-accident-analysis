"""Streamlit presentation helpers: styling, data access, global filters,
KPI cards and insight cards. Pages import from here so every page shares one
filter state (st.session_state) and one cached dataset."""
from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

from src import config
from src.data_loader import DatasetMissingError, ensure_clean_data
from src.utils import fmt_int, fmt_num, fmt_pct
from src.visualizations import PLOTLY_CONFIG

# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
def load_css() -> None:
    css = (config.PROJECT_ROOT / "assets" / "styles.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading and validating the dataset…")
def get_data() -> pd.DataFrame:
    return ensure_clean_data()


def data_or_stop() -> pd.DataFrame:
    try:
        return get_data()
    except DatasetMissingError as exc:
        st.error("Dataset not found")
        st.markdown(
            f"{exc}\n\nThen run `python -m src.preprocessing` (or simply reload this page — the "
            "pipeline runs automatically).")
        st.stop()


FILTERS = {  # session key -> (column, label)
    "f_year": ("year", "Year"),
    "f_state": ("state", "State"),
    "f_city": ("city", "City"),
    "f_severity": ("accident_severity", "Severity"),
    "f_cause": ("cause", "Cause"),
    "f_road": ("road_type", "Road type"),
    "f_weather": ("weather", "Weather"),
}


def _date_bounds(df) -> tuple[date, date]:
    return df["date"].min().date(), df["date"].max().date()


def _init_state(df) -> None:
    for key in FILTERS:
        st.session_state.setdefault(key, [])
    st.session_state.setdefault("f_dates", _date_bounds(df))


def reset_filters() -> None:
    df = get_data()
    for key in FILTERS:
        st.session_state[key] = []
    st.session_state["f_dates"] = _date_bounds(df)


def _options(df, col):
    vals = df[col].dropna().unique().tolist()
    if col == "accident_severity":
        return [s for s in config.SEVERITY_ORDER if s in vals]
    return sorted(vals)


def render_filters(df: pd.DataFrame) -> None:
    """Draw the global filter panel in the sidebar (called once, from app.py)."""
    _init_state(df)
    sb = st.sidebar
    sb.markdown('<div class="sb-title">Filters</div>', unsafe_allow_html=True)
    sb.multiselect("Year", _options(df, "year"), key="f_year", placeholder="All years")
    lo, hi = _date_bounds(df)
    sb.date_input("Date range", min_value=lo, max_value=hi, key="f_dates", format="DD/MM/YYYY")
    sb.multiselect("State", _options(df, "state"), key="f_state", placeholder="All states")
    states = st.session_state["f_state"]
    city_pool = df[df["state"].isin(states)] if states else df
    city_opts = _options(city_pool, "city")
    # drop cities that no longer belong to the chosen states (before the widget is drawn)
    st.session_state["f_city"] = [c for c in st.session_state["f_city"] if c in city_opts]
    sb.multiselect("City", city_opts, key="f_city", placeholder="All cities")
    sb.multiselect("Severity", _options(df, "accident_severity"), key="f_severity",
                   placeholder="All severities", format_func=str.title)
    sb.multiselect("Cause", _options(df, "cause"), key="f_cause", placeholder="All causes",
                   format_func=str.title)
    sb.multiselect("Road type", _options(df, "road_type"), key="f_road", placeholder="All road types",
                   format_func=str.title)
    sb.multiselect("Weather", _options(df, "weather"), key="f_weather", placeholder="All weather",
                   format_func=str.title)
    sb.button("↺  Reset filters", on_click=reset_filters, width="stretch", type="secondary")


def filter_signature() -> tuple:
    dates = st.session_state.get("f_dates", ())
    if isinstance(dates, (list, tuple)) and len(dates) == 2:
        d = (str(dates[0]), str(dates[1]))
    elif isinstance(dates, (list, tuple)) and len(dates) == 1:
        d = (str(dates[0]), str(dates[0]))  # mid-selection in the picker
    else:
        d = ()
    return tuple(tuple(sorted(map(str, st.session_state.get(k, [])))) for k in FILTERS) + (d,)


@st.cache_data(show_spinner=False, max_entries=64)
def _apply(signature: tuple) -> pd.DataFrame:
    df = get_data()
    mask = pd.Series(True, index=df.index)
    for (key, (col, _)), chosen in zip(FILTERS.items(), signature[:-1]):
        if chosen:
            mask &= df[col].astype(str).isin(chosen)
    if signature[-1]:
        start, end = pd.Timestamp(signature[-1][0]), pd.Timestamp(signature[-1][1])
        mask &= df["date"].between(start, end)
    return df[mask]


def filtered() -> pd.DataFrame:
    return _apply(filter_signature())


def active_filters() -> list[str]:
    chips = []
    for key, (_, label) in FILTERS.items():
        v = st.session_state.get(key) or []
        if v:
            shown = ", ".join(str(x).title() for x in v[:3]) + (f" +{len(v) - 3}" if len(v) > 3 else "")
            chips.append(f"{label}: {shown}")
    df = get_data()
    d = st.session_state.get("f_dates")
    if d and len(d) == 2 and tuple(d) != _date_bounds(df):
        chips.append(f"Dates: {d[0]:%d %b %Y} – {d[1]:%d %b %Y}")
    return chips


# --------------------------------------------------------------------------- #
# Components
# --------------------------------------------------------------------------- #
def page_header(title: str, subtitle: str, fdf: pd.DataFrame) -> None:
    total = len(get_data())
    chips = active_filters()
    chip_html = "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips) or \
        '<span class="chip chip-muted">No filters · full dataset</span>'
    st.markdown(f"""
<div class="page-head">
  <div>
    <div class="eyebrow">Indian Road Accident Intelligence · 2022–2025</div>
    <h1>{html.escape(title)}</h1>
    <p class="sub">{html.escape(subtitle)}</p>
  </div>
  <div class="records"><span class="records-n">{len(fdf):,}</span>
    <span class="records-l">of {total:,} accidents</span></div>
</div>
<div class="chips">{chip_html}</div>""", unsafe_allow_html=True)


def kpi_cards(items: list[dict], cols: int = 4) -> None:
    """items: dicts with label, value, sub (optional), tone (optional)."""
    cards = []
    for it in items:
        tone = it.get("tone", "")
        cards.append(f"""<div class="kpi {tone}">
  <div class="kpi-label">{html.escape(it['label'])}</div>
  <div class="kpi-value">{html.escape(str(it['value']))}</div>
  <div class="kpi-sub">{html.escape(it.get('sub', ''))}</div></div>""")
    st.markdown(f'<div class="kpi-grid cols-{cols}">{"".join(cards)}</div>', unsafe_allow_html=True)


def standard_kpis(k: dict) -> list[dict]:
    n = k["accidents"]
    share = (lambda x: f"{x / n * 100:.1f}% of accidents") if n else (lambda x: "")
    return [
        {"label": "Total accidents", "value": fmt_int(n), "sub": f"over {k['days']:,} days", "tone": "accent"},
        {"label": "Total casualties", "value": fmt_int(k["casualties"]), "sub": "killed + injured persons"},
        {"label": "Fatal accidents", "value": fmt_int(k["fatal"]), "sub": share(k["fatal"]), "tone": "fatal"},
        {"label": "Major accidents", "value": fmt_int(k["major"]), "sub": share(k["major"]), "tone": "major"},
        {"label": "Minor accidents", "value": fmt_int(k["minor"]), "sub": share(k["minor"]), "tone": "minor"},
        {"label": "Fatal accident rate", "value": fmt_pct(k["fatal_pct"]), "sub": "fatal ÷ all accidents"},
        {"label": "Avg casualties / accident", "value": fmt_num(k["avg_casualties"]),
         "sub": f"{fmt_num(k['avg_vehicles'])} vehicles per accident"},
        {"label": "Avg risk score", "value": fmt_num(k["avg_risk"], 3), "sub": "dataset's 0–1 composite"},
    ]


def section(title: str, caption: str = "") -> None:
    cap = f'<div class="sec-cap">{html.escape(caption)}</div>' if caption else ""
    st.markdown(f'<div class="sec"><div class="sec-title">{html.escape(title)}</div>{cap}</div>',
                unsafe_allow_html=True)


def card_title(title: str, caption: str = "") -> None:
    cap = f'<div class="card-cap">{html.escape(caption)}</div>' if caption else ""
    st.markdown(f'<div class="card-title">{html.escape(title)}</div>{cap}', unsafe_allow_html=True)


def chart(fig, key: str | None = None) -> None:
    st.plotly_chart(fig, theme=None, config=PLOTLY_CONFIG, key=key)


def chart_card(title: str, fig, caption: str = "", key: str | None = None) -> None:
    with st.container(border=True):
        card_title(title, caption)
        chart(fig, key)


def note(text: str, kind: str = "info") -> None:
    st.markdown(f'<div class="note note-{kind}">{text}</div>', unsafe_allow_html=True)


STATUS_LABEL = {"significant": "Statistically significant", "weak": "Weak evidence",
                "not_significant": "Not significant", "unreliable": "Low reliability",
                "descriptive": "Descriptive"}


def insight_cards(items: list[dict], columns: int = 3) -> None:
    cards = []
    for it in items:
        cards.append(f"""<div class="ins ins-{it['status']}">
  <div class="ins-top"><span class="ins-cat">{html.escape(it['category'])}</span>
  <span class="badge b-{it['status']}">{STATUS_LABEL[it['status']]}</span></div>
  <div class="ins-title">{html.escape(it['title'])}</div>
  <div class="ins-value">{html.escape(str(it['value']))}</div>
  <div class="ins-detail">{html.escape(it['detail'])}</div></div>""")
    st.markdown(f'<div class="ins-grid cols-{columns}">{"".join(cards)}</div>', unsafe_allow_html=True)


def empty_state() -> None:
    st.markdown("""<div class="empty">
  <div class="empty-icon">∅</div>
  <div class="empty-title">No accidents match these filters</div>
  <div class="empty-sub">Combine fewer filters or use <b>Reset filters</b> in the sidebar.</div>
</div>""", unsafe_allow_html=True)


def guard(fdf: pd.DataFrame) -> None:
    if fdf.empty:
        empty_state()
        st.stop()


def download_csv(fdf: pd.DataFrame, key: str, label: str = "⬇  Download filtered data (CSV)", where=None) -> None:
    (where or st).download_button(label, data=_csv_bytes(filter_signature()), file_name="filtered_road_accidents.csv",
                       mime="text/csv", key=key, width="stretch", disabled=fdf.empty)


@st.cache_data(show_spinner=False, max_entries=16)
def _csv_bytes(signature: tuple) -> bytes:
    d = _apply(signature).copy()
    d["date"] = d["date"].dt.strftime("%Y-%m-%d")
    return d.to_csv(index=False).encode("utf-8")
