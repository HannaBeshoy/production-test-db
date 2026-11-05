-- Group B, non-aggregated INNER JOIN
-- Every measurement outside its limits: which part, station, quantity, the value and the limits.
SELECT r.serial_no,
       st.name AS station,
       sp.quantity,
       m.value,
       sp.lower_limit,
       sp.upper_limit,
       TO_CHAR(r.started_at, 'YYYY-MM-DD HH24:MI') AS tested_at
FROM pt_measurements m
INNER JOIN pt_test_specs sp ON sp.spec_id = m.spec_id
INNER JOIN pt_test_runs r ON r.run_id = m.run_id
INNER JOIN pt_stations st ON st.station_id = r.station_id
WHERE m.value < sp.lower_limit OR m.value > sp.upper_limit
ORDER BY r.started_at, sp.quantity;
