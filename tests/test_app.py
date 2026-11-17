"""Headless UI tests with Streamlit's AppTest: every page renders without an
exception on the full data, under filters, under an empty selection and after
a reset; KPI numbers in the header follow the filters."""
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["pages/1_Overview.py", "pages/2_Geographical_Analysis.py", "pages/3_Temporal_Analysis.py",
         "pages/4_Severity_Analysis.py", "pages/5_Cause_Weather_Analysis.py", "pages/6_Road_Infrastructure.py",
         "pages/7_Risk_Insights.py", "pages/8_Data_Quality_Explorer.py"]
TIMEOUT = 120
ROOT = Path(__file__).resolve().parents[1]


def _app():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, at.exception
    return at


def _records_shown(at) -> int:
    html = " ".join(m.value for m in at.markdown)
    m = re.search(r'class="records-n">([\d,]+)<', html)
    return int(m.group(1).replace(",", "")) if m else -1


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_full_data(page):
    at = _app()
    at.switch_page(page).run()
    assert not at.exception, f"{page}: {at.exception}"
    assert _records_shown(at) == 20000


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_filtered_and_empty(page):
    at = _app()
    at.switch_page(page).run()
    at.multiselect(key="f_city").set_value(["Pune"]).run()
    at.multiselect(key="f_severity").set_value(["fatal"]).run()
    assert not at.exception, f"{page} filtered: {at.exception}"
    assert _records_shown(at) == 398  # independently: Pune fatal accidents
    # contradictory filters -> empty selection must not crash
    at.multiselect(key="f_state").set_value(["Delhi"]).run()   # removes Pune from city options
    at.multiselect(key="f_city").set_value(["Delhi"]).run()
    at.multiselect(key="f_cause").set_value(["weather"]).run()
    at.multiselect(key="f_weather").set_value(["clear"]).run()
    at.multiselect(key="f_road").set_value(["highway"]).run()
    at.multiselect(key="f_year").set_value([2025]).run()
    assert not at.exception, f"{page} narrow: {at.exception}"


def test_empty_selection_and_reset():
    at = _app()
    at.date_input(key="f_dates").set_value((__import__("datetime").date(2025, 4, 15),
                                           __import__("datetime").date(2025, 4, 15))).run()
    at.multiselect(key="f_city").set_value(["Delhi"]).run()
    at.multiselect(key="f_severity").set_value(["fatal"]).run()
    at.multiselect(key="f_weather").set_value(["fog"]).run()
    at.multiselect(key="f_cause").set_value(["distraction"]).run()
    assert not at.exception
    assert _records_shown(at) == 0
    assert any("No accidents match" in m.value for m in at.markdown)
    reset = [b for b in at.sidebar.button if "Reset" in b.label][0]
    reset.click().run()
    assert not at.exception
    assert _records_shown(at) == 20000
    assert at.multiselect(key="f_city").value == []


def test_state_filter_prunes_city_selection():
    at = _app()
    at.multiselect(key="f_city").set_value(["Pune", "Delhi"]).run()
    at.multiselect(key="f_state").set_value(["Maharashtra"]).run()
    assert not at.exception
    assert at.multiselect(key="f_city").value == ["Pune"]
    assert set(at.multiselect(key="f_city").options) == {"Mumbai", "Pune"}


SINGLE_VALUE_FILTERS = [("f_severity", ["fatal"]), ("f_severity", ["major"]), ("f_severity", ["minor"]),
                        ("f_year", [2022]), ("f_year", [2025]), ("f_weather", ["fog"]),
                        ("f_road", ["highway"]), ("f_cause", ["drunk driving"])]


@pytest.mark.parametrize("key,value", SINGLE_VALUE_FILTERS)
def test_every_page_under_single_value_filters(key, value):
    at = _app()
    at.multiselect(key=key).set_value(value).run()
    for page in PAGES:
        at.switch_page(page).run()
        assert not at.exception, f"{page} with {key}={value}: {at.exception}"


def test_single_day_selection():
    import datetime as dt
    at = _app()
    at.date_input(key="f_dates").set_value((dt.date(2023, 11, 12), dt.date(2023, 11, 12))).run()
    assert 0 < _records_shown(at) < 40
    for page in PAGES:
        at.switch_page(page).run()
        assert not at.exception, f"{page} single day: {at.exception}"
