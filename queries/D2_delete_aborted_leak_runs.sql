-- Group D, DELETE with a 1D subquery as the condition
-- Remove the aborted runs of the leak-test stations (they carry no measurement).
DELETE FROM pt_test_runs
WHERE result = 'ABORT'
  AND station_id IN (SELECT station_id FROM pt_stations WHERE kind = 'LEAK');
