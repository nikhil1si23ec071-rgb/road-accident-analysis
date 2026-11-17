"""Central configuration: paths, schema, category vocabularies and constants.

Everything that encodes an *assumption* about the data lives here so that it is
documented in one place and can be audited.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# RAA_DATA_DIR lets the test-suite point the whole pipeline at a temporary data
# root (with its own raw/ and processed/ folders) so test fixtures never touch
# the real data folders.
DATA_DIR = Path(os.environ.get("RAA_DATA_DIR", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = Path(os.environ.get("RAA_REPORTS_DIR", PROJECT_ROOT / "reports"))

RAW_FILE = RAW_DIR / "indian_roads_dataset.csv"
CLEAN_FILE = PROCESSED_DIR / "cleaned_road_accidents.csv"
PROFILE_JSON = PROCESSED_DIR / "data_profile.json"
CLEANING_LOG_JSON = PROCESSED_DIR / "cleaning_log.json"

USING_TEST_DATA = "RAA_DATA_DIR" in os.environ

# --------------------------------------------------------------------------- #
# Expected raw schema (24 columns, as published on Kaggle by user sehaj1104)
# --------------------------------------------------------------------------- #
EXPECTED_COLUMNS = [
    "accident_id", "city", "state", "latitude", "longitude", "date", "time",
    "hour", "day_of_week", "is_weekend", "road_type", "lanes", "traffic_signal",
    "weather", "visibility", "temperature", "traffic_density", "cause",
    "accident_severity", "vehicles_involved", "casualties", "is_peak_hour",
    "festival", "risk_score",
]

NUMERIC_COLUMNS = [
    "latitude", "longitude", "hour", "lanes", "temperature",
    "vehicles_involved", "casualties", "risk_score",
]
BINARY_COLUMNS = ["is_weekend", "traffic_signal", "is_peak_hour"]
CATEGORICAL_COLUMNS = [
    "city", "state", "day_of_week", "road_type", "weather", "visibility",
    "traffic_density", "cause", "accident_severity", "festival",
]

# Plausibility bounds. Values outside are physically impossible or clearly
# erroneous for this domain; they are set to NaN (never silently dropped).
VALID_RANGES = {
    "hour": (0, 23),
    "lanes": (1, 12),
    "temperature": (-30, 55),        # °C, Indian climate extremes with margin
    "vehicles_involved": (1, 100),   # an accident involves at least one vehicle
    "casualties": (0, 500),
    "risk_score": (0.0, 1.0),
}
# Bounding box of India (mainland + islands, generous margin)
INDIA_LAT = (6.0, 37.6)
INDIA_LON = (68.0, 97.6)
# A point further than this from its city's median coordinate is flagged.
MAX_KM_FROM_CITY_CENTRE = 75

# --------------------------------------------------------------------------- #
# Category standardisation. Keys are lower-cased, whitespace-collapsed, with
# '_' and '-' turned into spaces. Values are the canonical label.
# --------------------------------------------------------------------------- #
CITY_ALIASES = {
    "bengaluru": "Bangalore", "bangalore": "Bangalore", "bombay": "Mumbai",
    "mumbai": "Mumbai", "new delhi": "Delhi", "delhi": "Delhi",
    "calcutta": "Kolkata", "kolkata": "Kolkata", "madras": "Chennai",
    "chennai": "Chennai", "poona": "Pune", "pune": "Pune",
    "hyderabad": "Hyderabad", "chandigarh": "Chandigarh",
}
STATE_ALIASES = {
    "nct of delhi": "Delhi", "delhi": "Delhi", "tamilnadu": "Tamil Nadu",
    "tamil nadu": "Tamil Nadu", "west bengal": "West Bengal",
    "maharashtra": "Maharashtra", "karnataka": "Karnataka",
    "telangana": "Telangana", "punjab": "Punjab",
}
CAUSE_ALIASES = {
    "over speeding": "overspeeding", "overspeed": "overspeeding",
    "speeding": "overspeeding", "drunk driving": "drunk driving",
    "drink driving": "drunk driving", "drunken driving": "drunk driving",
    "distracted driving": "distraction", "poor roads": "poor road",
    "bad road": "poor road",
}
SEVERITY_ALIASES = {"fatality": "fatal", "serious": "major", "slight": "minor"}
WEATHER_ALIASES = {"foggy": "fog", "rainy": "rain", "sunny": "clear"}

SEVERITY_ORDER = ["fatal", "major", "minor"]
SEVERITY_RANK = {"minor": 1, "major": 2, "fatal": 3}
LEVEL_ORDER = ["low", "medium", "high"]
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
               "Oct", "Nov", "Dec"]

# Time-of-day buckets (hour -> label). Four buckets as requested.
TIME_OF_DAY_ORDER = ["Morning", "Afternoon", "Evening", "Night"]


def time_of_day(hour: float) -> str | None:
    if hour != hour:  # NaN
        return None
    h = int(hour)
    if 5 <= h <= 11:
        return "Morning"
    if 12 <= h <= 16:
        return "Afternoon"
    if 17 <= h <= 20:
        return "Evening"
    return "Night"   # 21:00 - 04:59


# India Meteorological Department (IMD) seasons
SEASON_BY_MONTH = {
    1: "Winter", 2: "Winter",
    3: "Summer", 4: "Summer", 5: "Summer",
    6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Post-monsoon", 11: "Post-monsoon", 12: "Post-monsoon",
}
SEASON_ORDER = ["Winter", "Summer", "Monsoon", "Post-monsoon"]

# Reference calendar used ONLY to audit whether the `festival` labels fall on
# the real festival dates (a provenance check). Dates are the main observance
# day in India; a +/-1 day tolerance is applied.
FESTIVAL_CALENDAR = {
    "Diwali":   ["2022-10-24", "2023-11-12", "2024-10-31", "2024-11-01",
                 "2025-10-20"],
    "Holi":     ["2022-03-18", "2023-03-08", "2024-03-25", "2025-03-14"],
    # Eid al-Fitr (the labelled records fall in April, i.e. Eid al-Fitr)
    "Eid":      ["2022-05-03", "2023-04-22", "2024-04-11", "2025-03-31"],
    "New Year": ["2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01"],
}

# Statistical settings
ALPHA = 0.05
MIN_GROUP_N = 30          # below this a rate is reported as "unreliable"
RISK_BANDS = [(0.0, 0.25, "Low"), (0.25, 0.50, "Moderate"),
              (0.50, 0.75, "High"), (0.75, 1.0001, "Very high")]
