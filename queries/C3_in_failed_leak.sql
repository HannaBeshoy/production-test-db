-- Group C, 1D subquery with IN
-- The clutch units that failed at least once at a leak-test station.
SELECT serial_no, lot_no
FROM pt_parts
WHERE serial_no IN (SELECT serial_no
                    FROM pt_test_runs
                    WHERE result = 'FAIL'
                      AND station_id IN (SELECT station_id FROM pt_stations WHERE kind = 'LEAK'))
ORDER BY serial_no;
