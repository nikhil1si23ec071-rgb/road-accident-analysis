# Dataset Profile — raw `indian_roads_dataset.csv`

_Generated automatically by `python -m src.preprocessing`. The raw file is never modified._

**Records:** 20,000 · **Columns:** 24 · **Memory:** 5.26 MB

Missing expected columns: none · Unexpected columns: none


## 1. Provenance assessment

**Source.** Kaggle dataset 'Indian Road Accident Dataset 2022–2025' uploaded by user sehaj1104. No collecting agency, methodology or licence linking it to MoRTH, NCRB or iRAD records is documented.

**Verdict: Likely SIMULATED / SYNTHETIC. Treat all findings as properties of this dataset, not of Indian road safety.**

- 8 of 9 categorical/temporal marginals are statistically indistinguishable from a uniform distribution (chi-square, α=0.05).
- Every timestamp is exactly on the hour (minutes = 00).
- risk_score takes only 18 discrete values (step 0.05).
- risk_score is reproduced exactly (100.0% of rows) by a simple additive rule: risk_score = min(1, 0.10 + 0.20·[severity = fatal] + 0.20·[traffic_density = high] + 0.15·[is_peak_hour] + 0.15·[weather ∈ {fog, rain}] + 0.20·[visibility = low] + 0.10·[festival recorded]).
- For every fatal accident, casualties == vehicles_involved exactly; casualties never exceed vehicles in any record — a generation rule, not an observed pattern.
- 1,725 'major' accidents record zero casualties (logically inconsistent with a major-injury classification).
- Festival labels cover only some years; real festival days with records but no label: Diwali 2022-10-24, Holi 2022-03-18, Holi 2025-03-14, Eid 2022-05-03, Eid 2025-03-31, New Year 2022-01-01, New Year 2024-01-01, New Year 2025-01-01.
- accident_id is a plain 0…n-1 row index rather than an official FIR / iRAD reference.


## 2. Columns

| column | dtype | role | missing | missing_pct | unique | examples |
|---|---|---|---|---|---|---|
| accident_id | int64 | identifier | 0 | 0 | 20000 | 0, 1, 2, 3, 4 |
| city | str | categorical | 0 | 0 | 8 | Pune, Mumbai, Chandigarh, Chennai, Delhi |
| state | str | categorical | 0 | 0 | 7 | Maharashtra, Punjab, Tamil Nadu, Delhi, Karnataka |
| latitude | float64 | numeric | 0 | 0 | 19907 | 18.680827, 18.817732, 19.096889, 30.787805, 12.965155 |
| longitude | float64 | numeric | 0 | 0 | 19927 | 73.930388, 72.790846, 72.819424, 76.847507, 80.283313 |
| date | str | date/time | 0 | 0 | 1201 | 2023-10-22, 2023-05-21, 2024-07-10, 2025-03-30, 2024-01-25 |
| time | str | date/time | 0 | 0 | 24 | 5:00, 4:00, 13:00, 11:00, 16:00 |
| hour | int64 | numeric | 0 | 0 | 24 | 5, 4, 13, 11, 16 |
| day_of_week | str | categorical | 0 | 0 | 7 | Sunday, Wednesday, Thursday, Monday, Friday |
| is_weekend | int64 | binary | 0 | 0 | 2 | 1, 0 |
| road_type | str | categorical | 0 | 0 | 3 | highway, urban, rural |
| lanes | int64 | numeric | 0 | 0 | 6 | 3, 4, 1, 5, 6 |
| traffic_signal | int64 | binary | 0 | 0 | 2 | 1, 0 |
| weather | str | categorical | 0 | 0 | 3 | fog, clear, rain |
| visibility | str | categorical | 0 | 0 | 3 | low, high, medium |
| temperature | int64 | numeric | 0 | 0 | 26 | 32, 34, 21, 30, 24 |
| traffic_density | str | categorical | 0 | 0 | 3 | high, low, medium |
| cause | str | categorical | 0 | 0 | 5 | weather, distraction, overspeeding, drunk driving, poor road |
| accident_severity | str | categorical | 0 | 0 | 3 | fatal, major, minor |
| vehicles_involved | int64 | numeric | 0 | 0 | 5 | 2, 4, 1, 5, 3 |
| casualties | int64 | numeric | 0 | 0 | 6 | 2, 3, 1, 4, 0 |
| is_peak_hour | int64 | binary | 0 | 0 | 2 | 0, 1 |
| festival | str | categorical | 19885 | 99.42 | 4 | Holi, Diwali, Eid, New Year |
| risk_score | float64 | numeric | 0 | 0 | 18 | 0.85, 0.1, 0.45, 0.65, 0.3 |


## 3. Numerical columns

| column | count | mean | std | min | median | max | iqr_outliers | impossible_values | distinct_values |
|---|---|---|---|---|---|---|---|---|---|
| latitude | 20000 | 20.39 | 6.166 | 12.8 | 18.81 | 30.8 | 0 | None | 19907 |
| longitude | 20000 | 78.17 | 4.486 | 72.7 | 77.3 | 88.5 | 0 | None | 19927 |
| hour | 20000 | 11.49 | 6.946 | 0 | 12 | 23 | 0 | 0 | 24 |
| lanes | 20000 | 3.494 | 1.705 | 1 | 4 | 6 | 0 | 0 | 6 |
| temperature | 20000 | 27.58 | 7.455 | 15 | 28 | 40 | 0 | 0 | 26 |
| vehicles_involved | 20000 | 2.992 | 1.416 | 1 | 3 | 5 | 0 | 0 | 5 |
| casualties | 20000 | 1.726 | 1.489 | 0 | 1 | 5 | 0 | 0 | 6 |
| risk_score | 20000 | 0.4376 | 0.2181 | 0.1 | 0.45 | 1 | 0 | 0 | 18 |
| is_weekend | 20000 | 0.2862 | 0.452 | 0 | 0 | 1 | None | None | 2 |
| traffic_signal | 20000 | 0.4999 | 0.5 | 0 | 0 | 1 | None | None | 2 |
| is_peak_hour | 20000 | 0.2474 | 0.4315 | 0 | 0 | 1 | None | None | 2 |


## 4. Categorical columns

- **city** — 8 unique: Chandigarh (2,577), Chennai (2,575), Kolkata (2,559), Pune (2,517), Mumbai (2,492), Bangalore (2,438), Delhi (2,433), Hyderabad (2,409)
- **state** — 7 unique: Maharashtra (5,009), Punjab (2,577), Tamil Nadu (2,575), West Bengal (2,559), Karnataka (2,438), Delhi (2,433), Telangana (2,409)
- **day_of_week** — 7 unique: Monday (2,966), Friday (2,879), Tuesday (2,871), Saturday (2,867), Sunday (2,856), Thursday (2,835), Wednesday (2,726)
- **road_type** — 3 unique: urban (6,745), rural (6,639), highway (6,616)
- **weather** — 3 unique: clear (6,690), rain (6,677), fog (6,633)
- **visibility** — 3 unique: low (9,987), high (6,690), medium (3,323)
- **traffic_density** — 3 unique: low (7,067), high (7,034), medium (5,899)
- **cause** — 5 unique: distraction (4,026), overspeeding (4,025), weather (3,997), drunk driving (3,978), poor road (3,974)
- **accident_severity** — 3 unique: minor (11,025), major (5,988), fatal (2,987)
- **festival** — 4 unique: <missing> (19,885), Holi (38), Eid (34), Diwali (31), New Year (12)


## 5. Duplicates and identifiers

- exact duplicate rows: **0**
- accident id unique: **True**
- duplicate accident ids: **0**
- missing accident ids: **0**
- accident id is sequential 0 to n minus 1: **True**
- duplicate rows ignoring id: **0**

## 6. Dates and times

- date · iso yyyy mm dd share pct: 100.0
- date · unparseable: 0
- date · missing: 0
- date · min: 2022-01-01 00:00:00
- date · max: 2025-04-15 00:00:00
- date · distinct days: 1201
- date · records per year: {2022: 6117, 2023: 6088, 2024: 6061, 2025: 1734}
- date · last month days covered: 15
- date · last month days in month: 30
- date · months covered per year: {2022: 12, 2023: 12, 2024: 12, 2025: 4}
- time · format patterns: {'99:99': 11680, '9:99': 8320}
- time · unparseable: 0
- time · share on the hour pct: 100.0
- time · hour matches time pct: 100.0
- day of week matches date pct: 100.0%
- is weekend matches date pct: 100.0%
- inferred peak hours: [8, 9, 10, 17, 18, 19] (rule agreement 100.0%)

## 7. Coordinates

- available: True
- missing: 0
- outside india bbox: 0
- zero zero: 0
- decimal places typical: 6
- km from city median: {'median': 14.033027029774495, 'p95': 26.472987625627287, 'max': 37.238942648185684, 'beyond_75km': 0}
- cities mapped to multiple states: []

## 8. Logical consistency

- fatal with zero casualties: 0
- major with zero casualties: 1725
- casualties by severity mean: {'fatal': 3.0016739203213927, 'major': 1.4948229792919172, 'minor': 1.5067573696145125}
- zero casualty records: 4925
- casualties equal vehicles pct: 39.825
- casualties exceed vehicles pct: 0.0
- fatal casualties equal vehicles pct: 100.0
- weather vs visibility: {'clear': {'high': 6690, 'low': 0, 'medium': 0}, 'fog': {'high': 0, 'low': 6633, 'medium': 0}, 'rain': {'high': 0, 'low': 3354, 'medium': 3323}}
- visibility determined by weather pct: 83.385

## 9. Derived / leakage-prone columns

| column | derived_from | agreement_pct |
|---|---|---|
| hour | time | 100 |
| day_of_week | date | 100 |
| is_weekend | date | 100 |
| is_peak_hour | hour ∈ [8, 9, 10, 17, 18, 19] | 100 |
| visibility | weather (modal mapping) | 83.39 |
| risk_score | composite; strongest single input = visibility (53.4% of variance) | None |


**risk_score reconstruction:** `risk_score = min(1, 0.10 + 0.20·[severity = fatal] + 0.20·[traffic_density = high] + 0.15·[is_peak_hour] + 0.15·[weather ∈ {fog, rain}] + 0.20·[visibility = low] + 0.10·[festival recorded])` → exact match on **100.0%** of rows (max |Δ| = 1.1e-16). Because severity is an input, risk_score must not be used to explain or predict severity.


`risk_score`: 18 distinct values; mean by severity {'fatal': 0.608, 'major': 0.407, 'minor': 0.408}.

Share of risk_score variance explained by each column (η² or Spearman ρ²):

| column | variance_explained |
|---|---|
| visibility | 0.5337 |
| weather | 0.4612 |
| traffic_density | 0.2844 |
| time | 0.1987 |
| is_peak_hour | 0.1498 |
| accident_severity | 0.1066 |
| hour | 0.0134 |
| casualties | 0.0126 |
| festival | 0.0021 |
| cause | 0.0004 |
| road_type | 0.0001 |
| city | 0.0001 |
| day_of_week | 0.0001 |
| lanes | 0 |
| temperature | 0 |
| vehicles_involved | 0 |
| is_weekend | 0 |
| traffic_signal | 0 |


## 10. Uniformity tests (synthetic-data fingerprint)

| variable | categories | chi2 | p_value | max_to_min_ratio | consistent_with_uniform |
|---|---|---|---|---|---|
| city | 8 | 12.8 | 0.07711 | 1.07 | True |
| hour | 24 | 22.83 | 0.471 | 1.13 | True |
| day_of_week | 7 | 10.61 | 0.1013 | 1.088 | True |
| cause | 5 | 0.6175 | 0.9611 | 1.013 | True |
| weather | 3 | 0.2677 | 0.8747 | 1.009 | True |
| road_type | 3 | 1.42 | 0.4916 | 1.019 | True |
| lanes | 6 | 4.199 | 0.5212 | 1.035 | True |
| traffic_density | 3 | 132.7 | 1.547e-29 | 1.198 | False |
| month (complete months) | 39 | 50.04 | 0.09148 | 1.262 | True |


## 11. Festival label audit

Records with a festival label: 115

| festival | records | distinct_dates | months_seen | on_actual_festival_date_pct | dates |
|---|---|---|---|---|---|
| Diwali | 31 | 2 | 11 | 100 | 2023-11-12, 2024-11-01 |
| Eid | 34 | 2 | 4 | 100 | 2023-04-22, 2024-04-10 |
| Holi | 38 | 2 | 3 | 100 | 2023-03-08, 2024-03-25 |
| New Year | 12 | 1 | 1 | 100 | 2023-01-01 |


Coverage of real festival dates inside the data window:

| festival | reference_date | records_on_date | labelled_within_1_day |
|---|---|---|---|
| Diwali | 2022-10-24 | 14 | 0 |
| Diwali | 2023-11-12 | 12 | 12 |
| Diwali | 2024-10-31 | 9 | 19 |
| Diwali | 2024-11-01 | 19 | 19 |
| Holi | 2022-03-18 | 9 | 0 |
| Holi | 2023-03-08 | 15 | 15 |
| Holi | 2024-03-25 | 23 | 23 |
| Holi | 2025-03-14 | 16 | 0 |
| Eid | 2022-05-03 | 19 | 0 |
| Eid | 2023-04-22 | 20 | 20 |
| Eid | 2024-04-11 | 15 | 14 |
| Eid | 2025-03-31 | 14 | 0 |
| New Year | 2022-01-01 | 18 | 0 |
| New Year | 2023-01-01 | 12 | 12 |
| New Year | 2024-01-01 | 11 | 0 |
| New Year | 2025-01-01 | 12 | 0 |

