#!/usr/bin/env python3
"""gen_data.py - the test data: one week of a small bearing / clutch / actuator test area.

    python3 tools/gen_data.py > sql/02_data.sql

Deterministic (fixed seed), so the expected results never change. The data has a story the
queries should find:
  - LEAK-1's seal wears: its leak readings drift up from Wednesday, and failures rise;
  - three clutch units were never leak-tested (escapes), found with MINUS;
  - LEAK-3 was commissioned on Thursday and has no runs yet (shows up only with an OUTER JOIN);
  - TORQ-2's calibration is overdue;
  - a few runs were aborted (no measurements).
`build()` returns the same rows as Python lists, used by the tests as an independent reference.
"""
import datetime as dt
import random

TYPES = [  # type_id, code, name, family, target cycle
    (1, "BRG-6204", "Deep groove ball bearing 6204", "bearing", 18.0),
    (2, "CRU-200", "Clutch release unit", "clutch", 32.0),
    (3, "ACT-E40", "Electric clutch actuator", "actuator", 45.0),
]
STATIONS = [  # station_id, name, line, kind, commissioned
    (1, "EOL-1", "L1", "EOL", dt.date(2024, 3, 1)),
    (2, "LEAK-1", "L1", "LEAK", dt.date(2024, 3, 1)),
    (3, "VIS-1", "L1", "VISION", dt.date(2025, 1, 15)),
    (4, "EOL-2", "L2", "EOL", dt.date(2024, 9, 2)),
    (5, "TORQ-2", "L2", "TORQUE", dt.date(2024, 9, 2)),
    (6, "LEAK-3", "L3", "LEAK", dt.date(2026, 11, 5)),
]
OPERATORS = [  # operator_id, name, shift, supervisor
    (1, "Katalin Szabo", "A", None),
    (2, "Gabor Nagy", "B", None),
    (3, "Peter Kovacs", "A", 1),
    (4, "Anna Toth", "A", 1),
    (5, "Laszlo Horvath", "A", 1),
    (6, "Eszter Varga", "B", 2),
    (7, "Mate Kiss", "B", 2),
    (8, "Reka Molnar", "B", 2),
]
SPECS = [  # spec_id, type, station, quantity, unit, lower, upper, mean, sigma
    (1, 1, 1, "noise", "dB", 0, 42, 36.0, 2.6),
    (2, 1, 1, "run_out", "um", 0, 8, 4.5, 1.5),
    (3, 1, 3, "seal_offset", "um", -40, 40, 0.0, 15.0),
    (4, 2, 1, "noise", "dB", 0, 48, 41.0, 3.0),
    (5, 2, 2, "leak_rate", "sccm", 0, 2.0, 0.9, 0.3),
    (6, 2, 3, "seal_offset", "um", -50, 50, 2.0, 18.0),
    (7, 3, 4, "current", "A", 1.8, 2.6, 2.2, 0.15),
    (8, 3, 4, "stroke", "mm", 11.5, 12.5, 12.0, 0.18),
    (9, 3, 5, "torque", "Nm", 3.8, 4.4, 4.1, 0.11),
]
ROUTES = {1: [1, 3], 2: [1, 2, 3], 3: [4, 5]}   # stations each product type passes, in order
CALIBRATIONS = [  # station, cal_date, due_date, technician
    (1, dt.date(2026, 5, 4), dt.date(2026, 11, 4), "Metrology lab"),
    (1, dt.date(2026, 11, 3), dt.date(2027, 5, 3), "Metrology lab"),
    (2, dt.date(2026, 6, 1), dt.date(2026, 12, 1), "Metrology lab"),
    (3, dt.date(2026, 2, 10), dt.date(2027, 2, 10), "Vision supplier"),
    (4, dt.date(2026, 3, 2), dt.date(2026, 9, 2), "Metrology lab"),
    (4, dt.date(2026, 9, 1), dt.date(2027, 3, 1), "Metrology lab"),
    (5, dt.date(2026, 4, 20), dt.date(2026, 10, 20), "Torque supplier"),
    (6, dt.date(2026, 11, 4), dt.date(2027, 5, 4), "Metrology lab"),
]
DAYS = [dt.date(2026, 11, 2) + dt.timedelta(days=d) for d in range(5)]   # Monday to Friday
PARTS_PER_DAY = {1: 40, 2: 30, 3: 20}
ESCAPES = {"CRU-200-261103-007", "CRU-200-261104-015", "CRU-200-261105-022"}


def build(seed=6204):
    rnd = random.Random(seed)
    parts, runs, meas = [], [], []
    run_id = 0
    spec_by = {}
    for s in SPECS:
        spec_by.setdefault((s[1], s[2]), []).append(s)
    for day_i, day in enumerate(DAYS):
        for type_id, code, *_ in TYPES:
            for k in range(1, PARTS_PER_DAY[type_id] + 1):
                serial = f"{code}-{day:%y%m%d}-{k:03d}"
                lot = f"{code[:3]}{day:%y%m%d}"
                produced = dt.datetime.combine(day, dt.time(6)) + dt.timedelta(minutes=rnd.randint(0, 900))
                parts.append((serial, type_id, lot, produced))
                t = produced + dt.timedelta(minutes=rnd.randint(5, 40))
                for station_id in ROUTES[type_id]:
                    if serial in ESCAPES and station_id == 2:
                        continue
                    attempt = 1
                    while True:
                        run_id += 1
                        shift = "A" if t.hour < 14 else "B"
                        op = rnd.choice([o[0] for o in OPERATORS if o[2] == shift])
                        target = TYPES[type_id - 1][4]
                        duration = round(max(3.0, rnd.gauss(target, target * 0.08)), 1)
                        if rnd.random() < 0.012:
                            runs.append((run_id, serial, station_id, op, t, duration, attempt, "ABORT"))
                            attempt += 1
                            t += dt.timedelta(minutes=3)
                            continue
                        ok = True
                        values = []
                        for spec_id, _, _, q, _, lo, hi, mean, sigma in spec_by[(type_id, station_id)]:
                            m = mean
                            if spec_id == 5 and day_i >= 2:          # LEAK-1 seal wear from Wednesday
                                m += 0.3 * (day_i - 1)
                            if attempt > 1:                           # a retest after re-seating the part
                                m = mean
                            v = round(rnd.gauss(m, sigma), 3)
                            values.append((run_id, spec_id, v))
                            ok = ok and lo <= v <= hi
                        runs.append((run_id, serial, station_id, op, t, duration, attempt, "PASS" if ok else "FAIL"))
                        meas += values
                        t += dt.timedelta(seconds=int(duration) + rnd.randint(20, 300))
                        if ok or attempt >= 2:
                            break
                        attempt += 1
    return {"types": TYPES, "stations": STATIONS, "operators": OPERATORS, "parts": parts,
            "specs": [s[:7] for s in SPECS], "runs": runs, "measurements": meas, "calibrations": CALIBRATIONS}


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, dt.datetime):
        return f"TIMESTAMP '{v:%Y-%m-%d %H:%M:%S}'"
    if isinstance(v, dt.date):
        return f"DATE '{v:%Y-%m-%d}'"
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    return repr(v)


TABLES = [("pt_product_types", "types"), ("pt_stations", "stations"), ("pt_operators", "operators"),
          ("pt_parts", "parts"), ("pt_test_specs", "specs"), ("pt_test_runs", "runs"),
          ("pt_measurements", "measurements"), ("pt_calibrations", "calibrations")]
COLUMNS = {
    "pt_product_types": "type_id, code, name, family, target_cycle_s",
    "pt_stations": "station_id, name, line, kind, commissioned",
    "pt_operators": "operator_id, name, shift, supervisor_id",
    "pt_parts": "serial_no, type_id, lot_no, produced_at",
    "pt_test_specs": "spec_id, type_id, station_id, quantity, unit, lower_limit, upper_limit",
    "pt_test_runs": "run_id, serial_no, station_id, operator_id, started_at, duration_s, attempt, result",
    "pt_measurements": "run_id, spec_id, value",
    "pt_calibrations": "station_id, cal_date, due_date, technician",
}


def sql(data):
    out = ["-- 02_data.sql - generated by tools/gen_data.py; do not edit by hand"]
    for table, key in TABLES:
        rows = data[key]
        if key == "operators":   # supervisors first, so the self-reference exists
            rows = sorted(rows, key=lambda r: r[3] is not None)
        out.append(f"\n-- {table}: {len(rows)} rows")
        for r in rows:
            out.append(f"INSERT INTO {table} ({COLUMNS[table]}) VALUES ({', '.join(lit(v) for v in r)});")
    out.append("\nCOMMIT;")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(sql(build()), end="")
