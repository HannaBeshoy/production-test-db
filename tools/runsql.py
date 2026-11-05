#!/usr/bin/env python3
"""runsql.py - run the project's Oracle SQL on Oracle, or on PostgreSQL through a translation.

    python3 tools/runsql.py --pg  "dbname=prodtest"            queries/A2_station_fail_rate.sql
    python3 tools/runsql.py --oracle "system/pw@localhost/FREEPDB1" queries/*.sql
    python3 tools/runsql.py --pg "dbname=prodtest" --reset      # drop, create, load (01, 02)

The SQL is written for Oracle, as in the course labs. For PostgreSQL, sqlglot translates the
Oracle words (VARCHAR2, NUMBER, NVL, MINUS, ...), and one rewrite is done here because sqlglot
leaves it: an outer `WHERE ROWNUM <= n` over an ordered subquery becomes `LIMIT n`.
Results are printed as a table, or saved as CSV with --csv DIR.
"""
import argparse, csv, glob, os, re, sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = ["pt_calibrations", "pt_measurements", "pt_test_runs", "pt_test_specs", "pt_parts",
          "pt_operators", "pt_stations", "pt_product_types"]


def statements(text):
    """Split a script into statements: ';' at the end of a line, comments removed."""
    text = re.sub(r"--[^\n]*", "", text)
    out = [s.strip() for s in re.split(r";\s*\n", text + "\n")]
    return [s.rstrip(";").strip() for s in out if s.strip()]


ROWNUM = re.compile(r"\)\s*(?:\w+\s+)?WHERE\s+ROWNUM\s*<=\s*(\d+)\s*$", re.I | re.S)


def to_postgres(stmt):
    import sqlglot
    m = ROWNUM.search(stmt)
    limit = None
    if m:
        limit = m.group(1)
        stmt = stmt[:m.start()] + ") ranked"
    if re.match(r"\s*INSERT\b", stmt, re.I):
        pg = stmt                                    # the data uses standard literals only
    else:
        from sqlglot import exp
        tree = sqlglot.parse_one(stmt, read="oracle")

        def numeric_round(node):
            # Oracle's ROUND takes any number; PostgreSQL's ROUND(x, n) only NUMERIC
            if isinstance(node, exp.Round) and node.args.get("decimals") is not None \
                    and not isinstance(node.this, exp.Cast):
                node.set("this", exp.Cast(this=node.this, to=exp.DataType.build("DECIMAL")))
            return node

        pg = tree.transform(numeric_round).sql(dialect="postgres")
    if limit:
        pg += f" LIMIT {limit}"
    return pg


class DB:
    def __init__(self, pg=None, oracle=None):
        self.kind = "pg" if pg else "oracle"
        if pg:
            import psycopg
            self.conn = psycopg.connect(pg, autocommit=False)
        else:
            import oracledb
            user, rest = oracle.split("/", 1)
            pw, dsn = rest.split("@", 1)
            self.conn = oracledb.connect(user=user, password=pw, dsn=dsn)

    def run(self, stmt):
        """Run one statement; returns (columns, rows) for a query, (None, rowcount) otherwise."""
        sql = to_postgres(stmt) if self.kind == "pg" else stmt
        cur = self.conn.cursor()
        cur.execute(sql)
        if cur.description:
            cols = [d[0].lower() for d in cur.description]
            return cols, [tuple(norm(v) for v in r) for r in cur.fetchall()]
        return None, cur.rowcount

    def script(self, path):
        last = None
        for s in statements(open(path, encoding="utf-8").read()):
            if s.upper() == "COMMIT":
                self.conn.commit()
                continue
            last = self.run(s)
        return last

    def reset(self):
        cur = self.conn.cursor()
        for t in TABLES:
            try:
                cur.execute(f"DROP TABLE {t}" + (" CASCADE" if self.kind == "pg" else " CASCADE CONSTRAINTS"))
                self.conn.commit()
            except Exception:
                self.conn.rollback()
        self.script(os.path.join(ROOT, "sql", "01_schema.sql"))
        self.script(os.path.join(ROOT, "sql", "02_data.sql"))
        self.conn.commit()


def norm(v):
    """Same Python value from both databases: Decimal -> int or float rounded to 4 places."""
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else round(float(v), 4)
    if isinstance(v, float):
        return int(v) if v.is_integer() else round(v, 4)
    return v


def show(cols, rows, limit=40):
    w = [max(len(str(c)), *(len(str(r[i])) for r in rows[:limit])) if rows else len(c) for i, c in enumerate(cols)]
    print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(cols)))
    for r in rows[:limit]:
        print("  ".join(str(v).ljust(w[i]) for i, v in enumerate(r)))
    print(f"({len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pg")
    g.add_argument("--oracle")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--csv", help="save each query's result as DIR/<name>.csv")
    ap.add_argument("files", nargs="*")
    a = ap.parse_args()
    db = DB(a.pg, a.oracle)
    if a.reset:
        db.reset()
    for f in sorted(sum((glob.glob(x) for x in a.files), [])):
        print(f"== {os.path.basename(f)}")
        cols, rows = db.script(f)
        db.conn.rollback()                      # D queries change data: never keep the change
        if cols is None:
            print(f"({rows} rows changed, rolled back)")
            continue
        show(cols, rows)
        if a.csv:
            os.makedirs(a.csv, exist_ok=True)
            with open(os.path.join(a.csv, os.path.basename(f)[:-4] + ".csv"), "w", newline="") as fh:
                csv.writer(fh).writerows([cols] + list(rows))


if __name__ == "__main__":
    sys.exit(main())
