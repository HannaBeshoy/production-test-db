# Project guide

From the question "what does a test area need to remember?" to tables, constraints, data and queries. The query part follows the course lab notes A1 to D2 and the lab-test exercise types.

## 1. The world being modelled

A test area checks parts after assembly. Each **part** has a serial number and belongs to a **product type** and a production **lot**. Each product type passes a fixed set of **stations** (its route): an end-of-line test, a leak test, a vision check, a torque test. At each station a **test run** measures one or more quantities, each with a **specification** (lower and upper limit). A run passes when every measurement is inside its limits. A failed part may be tested again: a **retest**. An **operator** starts each run; operators report to a supervisor. Stations are **calibrated** regularly; a station past its calibration due date must not be trusted.

## 2. From the ER model to tables

| Entity / relationship | Table | Key | Why this way |
| --- | --- | --- | --- |
| product type | `pt_product_types` | `type_id` | a short `code` is also UNIQUE: people search by it |
| part | `pt_parts` | `serial_no` | the serial number is a natural key printed on the part; it never changes |
| station | `pt_stations` | `station_id` | |
| operator, supervises (1:N, recursive) | `pt_operators` | `operator_id` | the recursive relationship becomes the foreign key `supervisor_id` to the same table; NULL for a supervisor |
| specification (type × station × quantity) | `pt_test_specs` | `spec_id` | an N:M relationship between type and station with its own attributes (limits) becomes a table; UNIQUE (type, station, quantity) keeps the natural key |
| test run | `pt_test_runs` | `run_id` | UNIQUE (serial, station, attempt): a retest is a new row, never an overwritten result |
| measurement (run × spec) | `pt_measurements` | (`run_id`, `spec_id`) | a weak entity identified by its run; the composite key also stops one value being stored twice |
| calibration (weak entity of station) | `pt_calibrations` | (`station_id`, `cal_date`) | |

Two decisions worth defending:

- **Limits are not copied into the measurements.** If each measurement stored its own limits, a change of specification would leave old rows inconsistent and every out-of-limit query would have to trust copies. The limits live once, in `pt_test_specs`; a measurement points to its specification. (A real system that changes limits over time would add a validity period to the specification and keep old versions; noted as an extension.)
- **The result is stored in the run, although it could be computed from the measurements.** Strictly this is derived data. It is kept because an **aborted** run has no measurements but still has a result, because the result is what the station decided at the time (the record of what happened), and because almost every query filters on it. The CHECK constraint limits it to PASS, FAIL and ABORT.

## 3. Normalization

- **1NF**: every column holds one value. Measurements are rows, not a list of values in one column; a run with three quantities has three measurement rows.
- **2NF**: no non-key column depends on only part of a composite key. In `pt_measurements` (`run_id`, `spec_id` → `value`) the value needs both. The quantity name and unit depend on `spec_id` alone, so they are not in `pt_measurements` but in `pt_test_specs`. In `pt_calibrations`, `due_date` and `technician` depend on the whole (`station_id`, `cal_date`).
- **3NF**: no non-key column depends on another non-key column. In `pt_parts`, the product type's name and family depend on `type_id`, not on the serial number, so they are in `pt_product_types`. A part's lot number stays in `pt_parts`: the lot is an attribute of the part; a separate lot table would be needed only if lots had attributes of their own (supplier, material batch), noted as an extension. In `pt_test_runs`, the station's line and kind are reached through `station_id`, not stored again.

## 4. Constraints: the database refuses bad data

| Constraint | Stops |
| --- | --- |
| `CHECK (result IN ('PASS', 'FAIL', 'ABORT'))` | "Pass", "OK", "passed" and every other spelling |
| `CHECK (lower_limit < upper_limit)` | a specification no part could pass |
| `CHECK (due_date > cal_date)` | a calibration that is due before it was done |
| `CHECK (attempt >= 1)`, `UNIQUE (serial_no, station_id, attempt)` | two "first attempts" of one part at one station |
| foreign keys everywhere | a measurement of a run or a specification that does not exist |
| `CHECK (kind IN (...))`, `CHECK (family IN (...))` | unknown station kinds and product families |

## 5. Indexes

The foreign keys used in joins and filters get indexes: runs by (station, time) for every per-station and per-day query, runs by serial number for everything that follows a part, measurements by specification for the Cpk queries, parts by (type, lot). Oracle creates indexes for the primary and unique keys itself.

## 6. The data and its story

`tools/gen_data.py` writes one working week (2 to 6 November 2026): 40 bearings, 30 clutch release units and 20 actuators a day, each through its route, with a fixed random seed. Each measurement is drawn from a normal distribution around a nominal value. Four problems are planted, and the README shows that the queries find them: LEAK-1's leak readings drift up from Wednesday (a wearing seal), three clutch units skip the leak test, LEAK-3 is commissioned but not used, TORQ-2's calibration has expired. About 1 % of runs are aborted.

The same generator returns the rows as Python lists, and `tests/test_queries.py` recomputes each query's answer from them in plain Python. Two independent routes to one answer: if the SQL and the Python agree on all 24, both are very likely right. The tests were checked to catch mistakes by breaking queries on purpose (an inner join in B3, a missing condition in E1): both failed.

## 7. The queries, group by group

**A: one table.** A1 uses `LIKE` on the serial number (the date is part of it) and `TO_CHAR` to compare hours. A2 counts failures with `SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END)`, a pattern used throughout, and multiplies by `100.0`, not `100`: in PostgreSQL an integer divided by an integer is an integer (Oracle returns a decimal either way). `HAVING` keeps stations with enough runs for a rate to mean something.

**B: joins.** B1 joins the operator table to itself, the only way to put a supervisor's name next to an operator's. B2 joins four tables. B3 is the outer-join lesson: `LEFT OUTER JOIN` keeps LEAK-3, `COUNT(r.run_id)` counts 0 for it (whereas `COUNT(*)` would count 1, the station's own row), and `NVL` turns its NULL average into 0.

**C: subqueries.** A 0D subquery returns one value: C1 compares with one lot number, C2 with one average. 1D subqueries return a list: C3 shows `IN`, `NOT EXISTS`, `> ALL` and `= ANY`. Note that `> ALL (list)` means "greater than the maximum", and is true for an empty list. C4 uses set operators on two lists of serial numbers; `MINUS` (Oracle's name for `EXCEPT`) finds the escapes, the most important result of the project. C5 aggregates aggregates: the inner query gives one fail rate per day, the outer one their mean and maximum. C6 is the ROWNUM trap from the course notes: ROWNUM is assigned before `ORDER BY` in the same query, so the ordering must happen in a subquery and the outer query takes the first five.

**D: changing data.** D1 and D3 use correlated 0D subqueries (the inner query refers to the outer row: "the newest calibration of *this* station"). D2 uses a 1D list of station ids. D4 is a multi-column update, `SET (warn_lower, warn_upper) = (SELECT ..., ...)`, which computes both warning limits from one pass over the data.

**E: complex.** E1 computes first-pass yield with a double `NOT EXISTS` ("there is no station of the route where this part has no first-attempt pass"), in a 2D subquery that produces 0/1 flags per part, then aggregates them. E2 is process capability, Cpk = min(USL − mean, mean − LSL) / 3σ, the number a quality engineer looks at first. E3 is the week of LEAK-1 in one table and shows the point of warning limits: readings drift beyond mean + 3σ of the stable days on Wednesday, a day before the first failure. E4 shows why a raw failure count per team is misleading: 4 of 6 failures of Gabor Nagy's shift came from the worn station.

## 8. Oracle and PostgreSQL

The SQL is Oracle's, as in the labs. To test it without an Oracle server, `tools/runsql.py` translates each statement to PostgreSQL with sqlglot. Two translations had to be handled by hand: `ROWNUM` (rewritten to `LIMIT`) and `ROUND(x, n)`, which PostgreSQL accepts only for NUMERIC (the translation casts). GitHub Actions runs the tests on both: PostgreSQL 16, and Oracle Database 23ai Free in a container, so the Oracle SQL is checked on Oracle itself.

## Notes for the three tracks

- **Embedded systems.** This is where the data of a test bench ends up. The serial logger and the AWS pipeline of the other projects produce rows that fit `pt_test_runs` and `pt_measurements`.
- **FPGA to semiconductors.** Wafer and final test work the same way: lots, test programs with limits, bins, retests, yield and Cpk. The same queries apply with different names.
- **Product security.** Traceability is a security property too: the escape query (MINUS) is what an audit asks for, and the CHECK constraints are input validation at the last line of defence.

## Possible extensions

- specification versions with a validity period, so limits can change without rewriting history
- a lot table with supplier and material batch, for a lot-to-failure query
- a view `v_first_pass` for E1 and a materialized daily summary for dashboards
