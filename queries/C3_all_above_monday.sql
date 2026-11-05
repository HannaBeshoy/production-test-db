-- Group C, 1D subquery with ALL
-- Leak readings higher than every leak reading of Monday: how far the seal wear has gone.
SELECT r.serial_no,
       TO_CHAR(r.started_at, 'YYYY-MM-DD') AS day,
       m.value AS leak_sccm
FROM pt_measurements m
INNER JOIN pt_test_runs r ON r.run_id = m.run_id
WHERE m.spec_id = 5
  AND m.value > ALL (SELECT m2.value
                     FROM pt_measurements m2
                     INNER JOIN pt_test_runs r2 ON r2.run_id = m2.run_id
                     WHERE m2.spec_id = 5
                       AND TO_CHAR(r2.started_at, 'YYYY-MM-DD') = '2026-11-02')
ORDER BY m.value DESC, r.serial_no;
