-- Group D, UPDATE with a 0D subquery as the condition (correlated)
-- Mark the stations whose newest calibration is already due on Friday 6 November.
UPDATE pt_stations s
SET status = 'OVERDUE'
WHERE (SELECT MAX(c.due_date) FROM pt_calibrations c WHERE c.station_id = s.station_id) < DATE '2026-11-06';
