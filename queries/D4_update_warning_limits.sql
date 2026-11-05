-- Group D, UPDATE with a multi-column subquery
-- Set internal warning limits for every quantity at mean +/- 3 standard deviations of Monday's
-- and Tuesday's passed runs: a reading inside the spec but outside these is an early warning.
UPDATE pt_test_specs sp
SET (warn_lower, warn_upper) =
    (SELECT ROUND(AVG(m.value) - 3 * STDDEV(m.value), 3),
            ROUND(AVG(m.value) + 3 * STDDEV(m.value), 3)
     FROM pt_measurements m
     INNER JOIN pt_test_runs r ON r.run_id = m.run_id
     WHERE m.spec_id = sp.spec_id
       AND r.result = 'PASS'
       AND r.started_at < TIMESTAMP '2026-11-04 00:00:00');
