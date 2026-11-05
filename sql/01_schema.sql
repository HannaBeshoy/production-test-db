-- 01_schema.sql - production-test database (Database Systems course project)
-- Oracle SQL; also runs on PostgreSQL 16 (the tests translate the few Oracle-only words).
-- Every table is in third normal form: each non-key column depends on the key, the whole key
-- and nothing but the key (docs/PROJECT_GUIDE.md walks through it).

CREATE TABLE pt_product_types (
    type_id        NUMBER(4)     PRIMARY KEY,
    code           VARCHAR2(12)  NOT NULL UNIQUE,
    name           VARCHAR2(60)  NOT NULL,
    family         VARCHAR2(20)  NOT NULL CHECK (family IN ('bearing', 'clutch', 'actuator')),
    target_cycle_s NUMBER(5,1)   NOT NULL CHECK (target_cycle_s > 0)
);

CREATE TABLE pt_stations (
    station_id     NUMBER(4)     PRIMARY KEY,
    name           VARCHAR2(12)  NOT NULL UNIQUE,
    line           VARCHAR2(4)   NOT NULL,
    kind           VARCHAR2(8)   NOT NULL CHECK (kind IN ('EOL', 'LEAK', 'VISION', 'TORQUE')),
    commissioned   DATE          NOT NULL,
    status         VARCHAR2(8)   DEFAULT 'ACTIVE' NOT NULL CHECK (status IN ('ACTIVE', 'OVERDUE', 'RETIRED'))
);

CREATE TABLE pt_operators (
    operator_id    NUMBER(4)     PRIMARY KEY,
    name           VARCHAR2(40)  NOT NULL,
    shift          CHAR(1)       NOT NULL CHECK (shift IN ('A', 'B')),
    supervisor_id  NUMBER(4)     REFERENCES pt_operators (operator_id)
);

CREATE TABLE pt_parts (
    serial_no      VARCHAR2(20)  PRIMARY KEY,
    type_id        NUMBER(4)     NOT NULL REFERENCES pt_product_types (type_id),
    lot_no         VARCHAR2(12)  NOT NULL,
    produced_at    TIMESTAMP     NOT NULL
);

-- what is measured on which product at which station, with its limits
CREATE TABLE pt_test_specs (
    spec_id        NUMBER(5)     PRIMARY KEY,
    type_id        NUMBER(4)     NOT NULL REFERENCES pt_product_types (type_id),
    station_id     NUMBER(4)     NOT NULL REFERENCES pt_stations (station_id),
    quantity       VARCHAR2(20)  NOT NULL,
    unit           VARCHAR2(10)  NOT NULL,
    lower_limit    NUMBER(10,4)  NOT NULL,
    upper_limit    NUMBER(10,4)  NOT NULL,
    warn_lower     NUMBER(10,4),             -- internal warning limits, set from process data (D4)
    warn_upper     NUMBER(10,4),
    CONSTRAINT pt_specs_unique UNIQUE (type_id, station_id, quantity),
    CONSTRAINT pt_specs_limits CHECK (lower_limit < upper_limit)
);

-- one test of one part at one station; a failed part may be tested again (a retest)
CREATE TABLE pt_test_runs (
    run_id         NUMBER(8)     PRIMARY KEY,
    serial_no      VARCHAR2(20)  NOT NULL REFERENCES pt_parts (serial_no),
    station_id     NUMBER(4)     NOT NULL REFERENCES pt_stations (station_id),
    operator_id    NUMBER(4)     NOT NULL REFERENCES pt_operators (operator_id),
    started_at     TIMESTAMP     NOT NULL,
    duration_s     NUMBER(6,1)   NOT NULL CHECK (duration_s > 0),
    attempt        NUMBER(2)     NOT NULL CHECK (attempt >= 1),
    result         VARCHAR2(5)   NOT NULL CHECK (result IN ('PASS', 'FAIL', 'ABORT')),
    CONSTRAINT pt_runs_attempt UNIQUE (serial_no, station_id, attempt)
);

CREATE TABLE pt_measurements (
    run_id         NUMBER(8)     NOT NULL REFERENCES pt_test_runs (run_id),
    spec_id        NUMBER(5)     NOT NULL REFERENCES pt_test_specs (spec_id),
    value          NUMBER(12,4)  NOT NULL,
    CONSTRAINT pt_measurements_pk PRIMARY KEY (run_id, spec_id)
);

CREATE TABLE pt_calibrations (
    station_id     NUMBER(4)     NOT NULL REFERENCES pt_stations (station_id),
    cal_date       DATE          NOT NULL,
    due_date       DATE          NOT NULL,
    technician     VARCHAR2(40)  NOT NULL,
    CONSTRAINT pt_calibrations_pk PRIMARY KEY (station_id, cal_date),
    CONSTRAINT pt_calibrations_due CHECK (due_date > cal_date)
);

-- the queries filter and join on these
CREATE INDEX pt_runs_station_time ON pt_test_runs (station_id, started_at);
CREATE INDEX pt_runs_serial ON pt_test_runs (serial_no);
CREATE INDEX pt_parts_type_lot ON pt_parts (type_id, lot_no);
CREATE INDEX pt_measurements_spec ON pt_measurements (spec_id);
