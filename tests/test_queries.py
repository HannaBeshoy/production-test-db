"""Every query is run on the database and compared with the same answer computed in plain Python
from the generator's rows. Two independent routes to one result: a wrong JOIN, a missing NULL
case or a ROWNUM mistake shows up as a difference.

    DB=pg  PG_DSN="dbname=prodtest"              python -m pytest tests     (default)
    DB=oracle ORACLE_DSN="system/pw@localhost/FREEPDB1" python -m pytest tests
"""
import os, statistics, sys
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen_data  # noqa: E402
from runsql import DB  # noqa: E402

D = gen_data.build()
RUNS = D["runs"]            # run_id, serial, station, operator, started_at, duration, attempt, result
MEAS = D["measurements"]    # run_id, spec_id, value
PARTS = {p[0]: p for p in D["parts"]}
RUN = {r[0]: r for r in RUNS}
SPEC = {s[0]: s for s in D["specs"]}
STATION = {s[0]: s for s in D["stations"]}
OPS = {o[0]: o for o in D["operators"]}
TYPES = {t[0]: t for t in D["types"]}


def rnd(x, d):
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))


def day(ts):
    return ts.strftime("%Y-%m-%d")


@pytest.fixture(scope="module")
def db():
    if os.environ.get("DB", "pg") == "oracle":
        d = DB(oracle=os.environ["ORACLE_DSN"])
    else:
        d = DB(pg=os.environ.get("PG_DSN", "dbname=prodtest"))
    d.reset()
    yield d
    d.conn.rollback()


def q(db, name):
    cols, rows = db.script(os.path.join(ROOT, "queries", name + ".sql"))
    db.conn.rollback()
    return rows


def same(actual, expected, tol=0.0):
    assert len(actual) == len(expected), f"{len(actual)} rows, expected {len(expected)}"
    for i, (a, e) in enumerate(zip(actual, expected)):
        assert len(a) == len(e), f"row {i}: {a} vs {e}"
        for x, y in zip(a, e):
            if isinstance(y, (int, float)) and not isinstance(y, bool):
                assert x is not None and abs(float(x) - y) <= tol + 1e-9, f"row {i}: {a} vs {e}"
            else:
                assert (x.strip() if isinstance(x, str) else x) == y, f"row {i}: {a} vs {e}"


# --- group A ----------------------------------------------------------------------------------
def test_A1(db):
    exp = sorted((p for p in PARTS.values() if p[0].startswith("CRU-200-261104-") and p[3].hour >= 14), key=lambda p: p[3])
    same(q(db, "A1_afternoon_clutch_units"), [(p[0], p[2], p[3].strftime("%H:%M"), p[0][-3:]) for p in exp])


def test_A2(db):
    by = defaultdict(list)
    for r in RUNS:
        if r[7] != "ABORT":
            by[r[2]].append(r)
    exp = []
    for st, rs in by.items():
        if len(rs) >= 100:
            fails = sum(r[7] == "FAIL" for r in rs)
            exp.append((st, len(rs), fails, rnd(100 * fails / len(rs), 2), rnd(statistics.mean(r[5] for r in rs), 1)))
    exp.sort(key=lambda e: (-e[3], e[0]))
    same(q(db, "A2_station_fail_rate"), exp, tol=0.01)


# --- group B ----------------------------------------------------------------------------------
def test_B1(db):
    exp = sorted(((o[1], o[2], OPS[o[3]][1]) for o in OPS.values() if o[3]), key=lambda e: (e[2], e[0]))
    same(q(db, "B1_operators_and_supervisors"), exp)


def test_B2(db):
    exp = []
    for run_id, spec_id, v in MEAS:
        s, r = SPEC[spec_id], RUN[run_id]
        if v < s[5] or v > s[6]:
            exp.append((r[4], s[3], (r[1], STATION[r[2]][1], s[3], v, s[5], s[6], r[4].strftime("%Y-%m-%d %H:%M"))))
    exp.sort(key=lambda e: (e[0], e[1]))
    same(q(db, "B2_out_of_limit_measurements"), [e[2] for e in exp], tol=0.0005)


def test_B3_outer_join_keeps_the_idle_station(db):
    exp = []
    for sid, s in STATION.items():
        rs = [r for r in RUNS if r[2] == sid]
        exp.append((s[1], s[3], len(rs), rnd(statistics.mean(r[5] for r in rs), 1) if rs else 0))
    exp.sort(key=lambda e: (-e[2], e[0]))
    rows = q(db, "B3_station_load_outer_join")
    same(rows, exp, tol=0.05)
    assert rows[-1][:3] == ("LEAK-3", "LEAK", 0)


# --- group C ----------------------------------------------------------------------------------
def test_C1(db):
    lot = PARTS["CRU-200-261105-011"][2]
    exp = sorted((p for p in PARTS.values() if p[2] == lot and p[0] != "CRU-200-261105-011"), key=lambda p: p[3])
    same(q(db, "C1_same_lot_as_failed_part"), [(p[0], p[3].strftime("%H:%M")) for p in exp])


def test_C2(db):
    rs = [r for r in RUNS if r[2] == 5]
    limit = 1.15 * statistics.mean(r[5] for r in rs)
    exp = sorted((r for r in rs if r[5] > limit), key=lambda r: -r[5])
    rows = q(db, "C2_slow_runs")
    assert sorted(rows, key=lambda r: (-r[2], r[0])) == sorted([(r[0], r[1], r[5], r[7]) for r in exp], key=lambda r: (-r[2], r[0]))


def test_C3_in(db):
    leak = {sid for sid, s in STATION.items() if s[3] == "LEAK"}
    serials = sorted({r[1] for r in RUNS if r[7] == "FAIL" and r[2] in leak})
    same(q(db, "C3_in_failed_leak"), [(s, PARTS[s][2]) for s in serials])


def test_C3_not_exists(db):
    failed = {r[1] for r in RUNS if r[7] == "FAIL"}
    c = Counter(TYPES[p[1]][1] for p in PARTS.values() if p[0] not in failed)
    same(q(db, "C3_not_exists_never_failed"), sorted(c.items()))


def test_C3_all(db):
    monday = [v for rid, sid, v in MEAS if sid == 5 and day(RUN[rid][4]) == "2026-11-02"]
    exp = sorted(((RUN[rid][1], day(RUN[rid][4]), v) for rid, sid, v in MEAS if sid == 5 and v > max(monday)), key=lambda e: -e[2])
    same(q(db, "C3_all_above_monday"), exp, tol=0.0005)


def test_C3_any(db):
    ids = {r[3] for r in RUNS if r[7] == "FAIL"}
    exp = sorted(((o[1], o[2]) for o in OPS.values() if o[0] in ids), key=lambda e: (e[1], e[0]))
    same(q(db, "C3_any_operators"), exp)


def test_C4_minus_finds_the_three_escapes(db):
    passed_eol = {r[1] for r in RUNS if r[2] == 1 and r[7] == "PASS" and r[1].startswith("CRU-")}
    leak_tested = {r[1] for r in RUNS if STATION[r[2]][3] == "LEAK"}
    exp = sorted(passed_eol - leak_tested)
    assert set(exp) == gen_data.ESCAPES
    same(q(db, "C4_escapes_minus"), [(s,) for s in exp])


def test_C4_intersect(db):
    a = {(r[1], r[2]) for r in RUNS if r[6] == 1 and r[7] == "FAIL"}
    b = {(r[1], r[2]) for r in RUNS if r[6] == 2 and r[7] == "PASS"}
    same(q(db, "C4_rescued_intersect"), sorted(a & b))


def test_C4_union(db):
    same(q(db, "C4_attention_union"), [(s,) for s in sorted({r[1] for r in RUNS if r[7] in ("FAIL", "ABORT")})])


def test_C5(db):
    by = defaultdict(list)
    for r in RUNS:
        if r[2] == 2 and r[6] == 1 and r[7] != "ABORT":
            by[day(r[4])].append(r[7] == "FAIL")
    rates = [100 * sum(v) / len(v) for v in by.values()]
    same(q(db, "C5_daily_fail_rate_of_leak1"), [(rnd(statistics.mean(rates), 2), rnd(max(rates), 2), len(rates))], tol=0.01)


def test_C6_rownum_top5(db):
    vals = sorted(((RUN[rid][1], day(RUN[rid][4]), v) for rid, sid, v in MEAS if sid == 5), key=lambda e: -e[2])[:5]
    same(q(db, "C6_top5_leak_rownum"), vals, tol=0.0005)


# --- group D: the change is checked, then rolled back ------------------------------------------
def after(db, name, check_sql):
    db.script(os.path.join(ROOT, "queries", name + ".sql"))
    out = db.run(check_sql)[1]
    db.conn.rollback()
    return out


def test_D1_keeps_newest_calibration_per_station(db):
    newest = {}
    for c in D["calibrations"]:
        newest[c[0]] = max(newest.get(c[0], c[1]), c[1])
    rows = after(db, "D1_delete_old_calibrations", "SELECT station_id, TO_CHAR(cal_date, 'YYYY-MM-DD') FROM pt_calibrations ORDER BY station_id")
    assert rows == [(s, d.strftime("%Y-%m-%d")) for s, d in sorted(newest.items())]


def test_D2_removes_only_aborted_leak_runs(db):
    left = after(db, "D2_delete_aborted_leak_runs", "SELECT COUNT(*) FROM pt_test_runs")
    gone = [r for r in RUNS if r[7] == "ABORT" and STATION[r[2]][3] == "LEAK"]
    assert gone and left == [(len(RUNS) - len(gone),)]


def test_D3_marks_overdue(db):
    due = {}
    for c in D["calibrations"]:
        due[c[0]] = max(due.get(c[0], c[2]), c[2])
    exp = [STATION[s][1] for s, d in sorted(due.items()) if d.isoformat() < "2026-11-06"]
    rows = after(db, "D3_update_overdue_stations", "SELECT name FROM pt_stations WHERE status = 'OVERDUE' ORDER BY station_id")
    assert [r[0] for r in rows] == exp == ["TORQ-2"]


def test_D4_sets_both_warning_limits_from_one_subquery(db):
    rows = after(db, "D4_update_warning_limits", "SELECT spec_id, warn_lower, warn_upper FROM pt_test_specs ORDER BY spec_id")
    for spec_id, lo, hi in rows:
        vs = [v for rid, sid, v in MEAS if sid == spec_id and RUN[rid][7] == "PASS" and RUN[rid][4].isoformat() < "2026-11-04"]
        m, sd = statistics.mean(vs), statistics.stdev(vs)
        assert lo == pytest.approx(m - 3 * sd, abs=0.0011) and hi == pytest.approx(m + 3 * sd, abs=0.0011)


# --- group E ----------------------------------------------------------------------------------
def test_E1_first_pass_and_final_yield(db):
    route = defaultdict(set)
    for s in SPEC.values():
        route[s[1]].add(s[2])
    by = defaultdict(list)
    for p in PARTS.values():
        rs = [r for r in RUNS if r[1] == p[0]]
        fp = all(any(r[2] == st and r[6] == 1 and r[7] == "PASS" for r in rs) for st in route[p[1]])
        fin = all(any(r[2] == st and r[7] == "PASS" for r in rs) for st in route[p[1]])
        by[(TYPES[p[1]][1], day(p[3]))].append((fp, fin))
    exp = [(k[0], k[1], len(v), rnd(100 * sum(a for a, _ in v) / len(v), 1), rnd(100 * sum(b for _, b in v) / len(v), 1))
           for k, v in sorted(by.items())]
    same(q(db, "E1_first_pass_yield"), exp, tol=0.1)


def test_E2_cpk(db):
    exp = []
    for sid, s in SPEC.items():
        vs = [v for _, sp, v in MEAS if sp == sid]
        m, sd = statistics.mean(vs), statistics.stdev(vs)
        exp.append((TYPES[s[1]][1], STATION[s[2]][1], s[3], len(vs), rnd(m, 3), rnd(sd, 3), rnd(min(s[6] - m, m - s[5]) / (3 * sd), 2)))
    exp.sort(key=lambda e: (e[6], e[0]))
    same(q(db, "E2_cpk_per_quantity"), exp, tol=0.011)


def test_E3_warnings_come_before_failures(db):
    base = [v for rid, sid, v in MEAS if sid == 5 and RUN[rid][7] == "PASS" and RUN[rid][4].isoformat() < "2026-11-04"]
    warn = statistics.mean(base) + 3 * statistics.stdev(base)
    by = defaultdict(list)
    for rid, sid, v in MEAS:
        if sid == 5 and RUN[rid][6] == 1:
            by[day(RUN[rid][4])].append((v, RUN[rid][7]))
    exp = []
    for d, xs in sorted(by.items()):
        vs = [v for v, _ in xs]
        m, sd = statistics.mean(vs), statistics.stdev(vs)
        exp.append((d, len(vs), rnd(m, 3), rnd(min(2.0 - m, m) / (3 * sd), 2), sum(r == "FAIL" for _, r in xs),
                    sum(r == "PASS" and v > warn for v, r in xs)))
    rows = q(db, "E3_leak1_daily_trend")
    same(rows, exp, tol=0.011)
    first_warning = next(r[0] for r in rows if r[5] > 0)
    first_fail = next(r[0] for r in rows if r[4] > 0)
    assert first_warning < first_fail                     # the early warning is earlier


def test_E4(db):
    by = defaultdict(lambda: [0, 0, 0])
    for o in OPS.values():
        if o[3]:
            by[(OPS[o[3]][1], o[2])]
    for r in RUNS:
        o = OPS[r[3]]
        if o[3] and r[7] != "ABORT":
            e = by[(OPS[o[3]][1], o[2])]
            e[0] += 1
            e[1] += r[7] == "FAIL"
            e[2] += r[7] == "FAIL" and r[2] == 2
    same(q(db, "E4_operator_shift_failures"), [(k[0], k[1], *v) for k, v in sorted(by.items())])
