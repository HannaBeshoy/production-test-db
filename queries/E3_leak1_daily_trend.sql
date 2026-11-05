-- Group E, complex: LEAK-1 day by day - mean leak, Cpk, first-attempt failures, and the
-- readings that already passed the 3-sigma warning limit computed from Monday and Tuesday
-- (the seal wear shows up there days before the failures do).
-- The warning limit is one value (a 0D inline view), joined to every row.
SELECT TO_CHAR(r.started_at, 'YYYY-MM-DD') AS day,
       COUNT(*) AS n,
       ROUND(AVG(m.value), 3) AS mean_sccm,
       ROUND(LEAST(2.0 - AVG(m.value), AVG(m.value) - 0) / (3 * STDDEV(m.value)), 2) AS cpk,
       SUM(CASE WHEN r.result = 'FAIL' THEN 1 ELSE 0 END) AS fails,
       SUM(CASE WHEN r.result = 'PASS' AND m.value > w.warn_upper THEN 1 ELSE 0 END) AS warnings
FROM pt_measurements m
INNER JOIN pt_test_runs r ON r.run_id = m.run_id
CROSS JOIN (SELECT AVG(m2.value) + 3 * STDDEV(m2.value) AS warn_upper
            FROM pt_measurements m2
            INNER JOIN pt_test_runs r2 ON r2.run_id = m2.run_id
            WHERE m2.spec_id = 5 AND r2.result = 'PASS'
              AND r2.started_at < TIMESTAMP '2026-11-04 00:00:00') w
WHERE m.spec_id = 5 AND r.attempt = 1
GROUP BY TO_CHAR(r.started_at, 'YYYY-MM-DD')
ORDER BY day;
