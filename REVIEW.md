# REVIEW.md

Review findings for the supplied starter. Verify these against the final implementation before submitting; add any additional defects you discover while testing.

| # | Where (function / line) | What is wrong | How you'd notice it (test, input, or symptom) | How it is fixed in this version |
|---|---|---|---|---|
| 1 | `compute_late_minutes` | It assumes the local date is the shift date and does not correctly account for overnight shifts. | Punch in at 02:00 for a 22:00–06:00 shift. | Resolve the attendance day first, then compare the punch instant to that day's shift start in IST. |
| 2 | `compute_late_minutes` | The timestamp isn't truncated to whole seconds before calculating lateness. | A timestamp ending in fractional seconds can change the boundary result. | Normalize all instants to whole seconds at the API boundary. |
| 3 | `compute_work_hours` | Python `round()` uses ties-to-even and floating-point arithmetic. | Test a duration exactly at a half-centesimal rounding boundary. | Use `Decimal` with `ROUND_HALF_UP`. |
| 4 | `compute_overtime` | It calculates the shift end on the record date even for an overnight shift. | A 22:00–06:00 shift with a punch-out after 06:00 next day. | Move the end instant to the next calendar day when `shift_end <= shift_start`. |
| 5 | `compute_overtime` | It counts every positive overtime minute; the contract requires at least 30 minutes before any overtime is counted. | Punch out 29 minutes after shift end; expected overtime is zero. | Apply the 30-minute threshold after flooring elapsed whole minutes. |
| 6 | `GET /health` | It returns success without checking whether MongoDB is reachable. | Stop MongoDB and call the endpoint. | Ping MongoDB and return 503 on a database error. |
| 7 | `POST /employees` | Check-then-insert is race-prone and has no database uniqueness guarantee. | Submit simultaneous creates for the same `emp_code`. | Create a unique index and translate `DuplicateKeyError` to 409. |
| 8 | `POST /employees` | `created_at` is stored as a local naive time and returned in the wrong representation. | Compare response `created_at` with epoch milliseconds and stored UTC. | Store a whole-second UTC BSON datetime and return epoch milliseconds. |
| 9 | `GET /employees` | `skip = page * page_size` skips the first page. | Request page 1 and page 2 for known records. | Use `(page - 1) * page_size`. |
| 10 | `GET /employees` | `total` counts the entire collection rather than the filtered department. | Request a department with fewer employees than the whole collection. | Use the same filter for `count_documents` and the page query. |
| 11 | `GET /employees` | It does not enforce page/page-size bounds or sort by `emp_code`. | Use invalid page sizes or compare repeatable page results. | Validate page values and sort ascending by `emp_code`. |
| 12 | `POST /attendance/punch-in` | Unknown employees cause a `KeyError`/500 instead of 404. | Punch in with an unknown `emp_code`. | Check employee existence and return 404. |
| 13 | `POST /attendance/punch-in` | It interprets epoch milliseconds as seconds and uses the machine's local timezone. | Supply an epoch-millisecond timestamp or run on a non-IST machine. | Validate integer epoch milliseconds and convert to UTC/IST explicitly. |
| 14 | `POST /attendance/punch-in` | Check-then-insert does not prevent concurrent duplicate attendance records; there is no unique natural-key index. | Send parallel punch-in requests for the same employee and day. | Enforce unique `(emp_code, date)` in MongoDB and handle duplicate-key errors. |
| 15 | `POST /attendance/punch-in` | It doesn't validate status or consistently apply overnight attendance-date rules. | Send `ABSENT`, or punch in after midnight for an overnight shift. | Restrict punch-in to presence statuses and calculate attendance date from the shift. |
| 16 | `GET /attendance` | It loads all matching records into Python, sorts them there, and slices afterward. This is slow at the required scale. | Run against a large collection and inspect memory/query plan. | Filter, sort, skip, limit, and count in MongoDB, supported by indexes. |
| 17 | `GET /attendance` | The old sort omits the required `emp_code` tie-breaker. | Multiple employees have records on the same date. | Sort by `date` descending and `emp_code` ascending. |
| 18 | Missing punch-out endpoint | The starter cannot close records, compute work hours/overtime/half-day, or guard against concurrent punch-outs. | Call the required endpoint or send simultaneous punch-outs. | Add an atomic compare-and-set update and calculate derived fields. |
| 19 | Missing correction endpoint | There is no validation, recalculation, or append-only audit history. | Correct a timestamp and inspect history. | Validate the final record, recompute derived fields, append exactly one history entry atomically, and reject no-op edits. |
| 20 | Missing analytics endpoints | The four reporting endpoints are absent. | Call each analytics route. | Add MongoDB aggregation pipelines for monthly, department, leaderboard and trend reports. |
| 21 | Missing explain endpoint | The app cannot return execution-statistics plans for the required report queries. | Call `/admin/explain/...`. | Reuse query/pipeline builders and run `explain` with `executionStats`. |

## Reviewed and retained

- The `emp_code` business identifier is used instead of exposing MongoDB `_id`; this matches the contract.
- The natural attendance key is `(emp_code, date)`; the fix is to enforce it with a unique index, not replace it with a client-facing ID.
- A weekday with no attendance document is not the same as an `ABSENT` record; analytics preserve this distinction.
- Stored derived attendance values are authoritative for analytics; aggregation pipelines read those stored values instead of silently recalculating historical seed data.
