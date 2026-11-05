-- Group C, aggregated 0D subquery as the condition
-- Runs at TORQ-2 that took more than 15 % longer than that station's mean test time.
SELECT run_id,
       serial_no,
       duration_s,
       result
FROM pt_test_runs
WHERE station_id = 5
  AND duration_s > (SELECT 1.15 * AVG(duration_s) FROM pt_test_runs WHERE station_id = 5)
ORDER BY duration_s DESC;
