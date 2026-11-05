-- Group D, DELETE with a 0D subquery as the condition (correlated)
-- Keep only the newest calibration record of each station.
DELETE FROM pt_calibrations c
WHERE c.cal_date < (SELECT MAX(c2.cal_date) FROM pt_calibrations c2 WHERE c2.station_id = c.station_id);
