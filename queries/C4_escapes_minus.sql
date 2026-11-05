-- Group C, set operator MINUS between two 1D subqueries
-- Escapes: clutch units that passed end-of-line test but were never leak-tested.
SELECT serial_no FROM pt_test_runs
WHERE station_id = 1 AND result = 'PASS' AND serial_no LIKE 'CRU-%'
MINUS
SELECT serial_no FROM pt_test_runs
WHERE station_id IN (SELECT station_id FROM pt_stations WHERE kind = 'LEAK')
ORDER BY 1;
