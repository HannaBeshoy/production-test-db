-- Group C, set operator INTERSECT
-- Parts and stations where the first attempt failed and the second attempt passed: the retest
-- "rescued" them (a quality engineer wants to know how often this happens).
SELECT serial_no, station_id FROM pt_test_runs WHERE attempt = 1 AND result = 'FAIL'
INTERSECT
SELECT serial_no, station_id FROM pt_test_runs WHERE attempt = 2 AND result = 'PASS'
ORDER BY 1, 2;
