"""Builds a small, deliberately *dirty* TEST FIXTURE that follows the real
24-column schema. It exists only to prove the cleaning pipeline copes with
problems the real file happens not to have (duplicates, spelling variants,
impossible values, bad dates/coordinates, missing values).

It is never written to data/raw/ and never used for analysis.
"""
from pathlib import Path

import numpy as np
import pandas as pd


def build_dirty_fixture(real_csv: Path, n: int = 400, seed: int = 0) -> pd.DataFrame:
    df = pd.read_csv(real_csv).sample(n, random_state=seed).reset_index(drop=True)
    df = df.astype(object)
    # 1 exact duplicate rows
    df = pd.concat([df, df.iloc[[0, 1, 2]]], ignore_index=True)
    # 2 duplicate id with different content
    clash = df.iloc[[3]].copy(); clash["casualties"] = 0
    df = pd.concat([df, clash], ignore_index=True)
    # 3 spelling / case / whitespace variants
    df.loc[4, "city"] = "  bengaluru "
    df.loc[5, "city"] = "BOMBAY"
    df.loc[6, "cause"] = "Over-Speeding"
    df.loc[7, "cause"] = "Drunk_Driving"
    df.loc[8, "accident_severity"] = "FATAL "
    df.loc[9, "weather"] = "Foggy"
    df.loc[10, "state"] = "tamilnadu"
    # 4 impossible numeric values
    df.loc[11, "casualties"] = -3
    df.loc[12, "risk_score"] = 1.7
    df.loc[13, "hour"] = 27
    df.loc[14, "temperature"] = 80
    df.loc[15, "vehicles_involved"] = 0
    df.loc[16, "lanes"] = "two"
    # 5 bad coordinates
    df.loc[17, ["latitude", "longitude"]] = [0.0, 0.0]
    df.loc[18, ["latitude", "longitude"]] = [51.5, -0.12]
    # 6 dates / times
    df.loc[19, "date"] = "not a date"
    df.loc[20, "time"] = "7:00"; df.loc[20, "hour"] = 9          # hour disagrees with time
    df.loc[21, "day_of_week"] = "Funday"
    # 7 missing values
    df.loc[22, "weather"] = np.nan
    df.loc[23, "casualties"] = np.nan
    df.loc[24, "accident_severity"] = "catastrophic"
    df.loc[25, "festival"] = "  "
    return df
