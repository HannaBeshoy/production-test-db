-- Group C, aggregating the aggregated values of a 2D subquery
-- LEAK-1's first-attempt fail rate per day (inner query), then its mean and its worst day.
SELECT ROUND(AVG(fail_pct), 2) AS mean_daily_fail_pct,
       ROUND(MAX(fail_pct), 2) AS worst_daily_fail_pct,
       COUNT(*) AS days
FROM (SELECT TO_CHAR(started_at, 'YYYY-MM-DD') AS day,
             100.0 * SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) / COUNT(*) AS fail_pct
      FROM pt_test_runs
      WHERE station_id = 2 AND attempt = 1 AND result <> 'ABORT'
      GROUP BY TO_CHAR(started_at, 'YYYY-MM-DD'));
