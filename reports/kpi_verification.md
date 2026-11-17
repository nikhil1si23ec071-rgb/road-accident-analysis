# KPI Verification

Expected values are recomputed with plain pandas from the **raw** CSV (no project code) and compared with the dashboard's functions on the **cleaned** data. Notebook values were read from the outputs embedded in the original notebook.

**Result: ALL 60 CHECKS PASS** (60/60 vs raw; 15/15 vs notebook)

| Metric | Independent (raw) | Dashboard | Match | Notebook | Matches notebook |
|---|---|---|---|---|---|
| accidents | 20,000 | 20,000 | ✅ | 20,000 | ✅ |
| casualties | 34,529 | 34,529 | ✅ |  |  |
| fatal | 2,987 | 2,987 | ✅ | 2,987 | ✅ |
| major | 5,988 | 5,988 | ✅ | 5,988 | ✅ |
| minor | 11,025 | 11,025 | ✅ | 11,025 | ✅ |
| fatal_pct | 14.935 | 14.935 | ✅ |  |  |
| avg_casualties | 1.72645 | 1.72645 | ✅ |  |  |
| avg_vehicles | 2.992 | 2.992 | ✅ |  |  |
| avg_risk | 0.437585 | 0.437585 | ✅ |  |  |
| city:Chandigarh | 2,577 | 2,577 | ✅ | 2,577 | ✅ |
| city:Chennai | 2,575 | 2,575 | ✅ |  |  |
| city:Kolkata | 2,559 | 2,559 | ✅ |  |  |
| city:Pune | 2,517 | 2,517 | ✅ |  |  |
| city:Mumbai | 2,492 | 2,492 | ✅ |  |  |
| city:Bangalore | 2,438 | 2,438 | ✅ |  |  |
| city:Delhi | 2,433 | 2,433 | ✅ |  |  |
| city:Hyderabad | 2,409 | 2,409 | ✅ | 2,409 | ✅ |
| state:Maharashtra | 5,009 | 5,009 | ✅ | 5,009 | ✅ |
| state:Punjab | 2,577 | 2,577 | ✅ |  |  |
| state:Tamil Nadu | 2,575 | 2,575 | ✅ |  |  |
| state:West Bengal | 2,559 | 2,559 | ✅ |  |  |
| state:Karnataka | 2,438 | 2,438 | ✅ |  |  |
| state:Delhi | 2,433 | 2,433 | ✅ |  |  |
| state:Telangana | 2,409 | 2,409 | ✅ |  |  |
| casualties city:Bangalore | 4,128 | 4,128 | ✅ |  |  |
| casualties city:Chandigarh | 4,377 | 4,377 | ✅ |  |  |
| casualties city:Chennai | 4,567 | 4,567 | ✅ | 4,567 | ✅ |
| casualties city:Delhi | 4,175 | 4,175 | ✅ |  |  |
| casualties city:Hyderabad | 4,058 | 4,058 | ✅ |  |  |
| casualties city:Kolkata | 4,508 | 4,508 | ✅ |  |  |
| casualties city:Mumbai | 4,297 | 4,297 | ✅ |  |  |
| casualties city:Pune | 4,419 | 4,419 | ✅ |  |  |
| cause:distraction | 4,026 | 4,026 | ✅ | 4,026 | ✅ |
| cause:overspeeding | 4,025 | 4,025 | ✅ |  |  |
| cause:weather | 3,997 | 3,997 | ✅ |  |  |
| cause:drunk driving | 3,978 | 3,978 | ✅ |  |  |
| cause:poor road | 3,974 | 3,974 | ✅ |  |  |
| weather:clear | 6,690 | 6,690 | ✅ |  |  |
| weather:rain | 6,677 | 6,677 | ✅ |  |  |
| weather:fog | 6,633 | 6,633 | ✅ | 6,633 | ✅ |
| fatal_rate road:highway | 14.8579 | 14.8579 | ✅ |  |  |
| fatal_rate road:rural | 14.5353 | 14.5353 | ✅ |  |  |
| fatal_rate road:urban | 15.404 | 15.404 | ✅ | 15.404 | ✅ |
| fatal_rate cause:distraction | 13.4625 | 13.4625 | ✅ |  |  |
| fatal_rate cause:drunk driving | 15.5354 | 15.5354 | ✅ |  |  |
| fatal_rate cause:overspeeding | 14.9814 | 14.9814 | ✅ |  |  |
| fatal_rate cause:poor road | 15.6769 | 15.6769 | ✅ | 15.68 | ✅ |
| fatal_rate cause:weather | 15.0363 | 15.0363 | ✅ |  |  |
| festival:Holi | 38 | 38 | ✅ | 38 | ✅ |
| festival:Eid | 34 | 34 | ✅ |  |  |
| festival:Diwali | 31 | 31 | ✅ |  |  |
| festival:New Year | 12 | 12 | ✅ |  |  |
| peak accidents | 4,948 | 4,948 | ✅ | 4,948 | ✅ |
| avg_casualties fatal | 3.00167 | 3.00167 | ✅ | 3.00167 | ✅ |
| year:2022 | 6,117 | 6,117 | ✅ |  |  |
| year:2023 | 6,088 | 6,088 | ✅ |  |  |
| year:2024 | 6,061 | 6,061 | ✅ |  |  |
| year:2025 | 1,734 | 1,734 | ✅ |  |  |
| weekend accidents | 5,723 | 5,723 | ✅ |  |  |
| Pune fatal | 398 | 398 | ✅ |  |  |
