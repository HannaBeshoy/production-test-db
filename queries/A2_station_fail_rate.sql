-- Group A, aggregated query (COUNT, SUM, AVG with HAVING)
-- For every station with at least 100 completed runs: runs, failures, fail rate in % and the
-- mean test time. Aborted runs are not test results and are left out. Worst station first.
SELECT station_id,
       COUNT(*) AS runs,
       SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) AS fails,
       ROUND(100.0 * SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) / COUNT(*), 2) AS fail_pct,
       ROUND(AVG(duration_s), 1) AS mean_s
FROM pt_test_runs
WHERE result <> 'ABORT'
GROUP BY station_id
HAVING COUNT(*) >= 100
ORDER BY fail_pct DESC, station_id;
