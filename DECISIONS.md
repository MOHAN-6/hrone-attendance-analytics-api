# DECISIONS.md

1. **Indexes.** A unique `employees.emp_code` index prevents duplicate identities. A unique `(emp_code, date)` attendance index is the concurrency guard for punch-in. Employee department/join-date and attendance date/employee, employee/date/status, employee/punch-in, and date/late-minute indexes support filtered lists, joins, punch-out selection and analytics. I would not add an index for every optional filter because each index increases write cost and storage; I would validate candidates with `explain` on the grading-shaped queries.

2. **Punch-in race.** Both requests may check the employee, but only one insert can win the unique `(emp_code, date)` index. MongoDB rejects the other insert with a duplicate-key error, which the API maps to 409. A check-then-insert alone is not the guarantee.

3. **Ties.** The leaderboard uses MongoDB `$rank` over total late minutes, then filters `rank <= limit`. A tie at the cutoff is fully included; tied employees are ordered by `emp_code`.

4. **Headcount.** Department summary starts from eligible employees, including those with no attendance records, and looks up that employee's logs. Employees joining after month-end are excluded.

5. **100x data.** I would measure explain plans and latency, add automated performance tests, review compound index order against real filters, and consider pre-aggregated daily summaries for expensive reports while retaining raw logs as the source of truth.
