-- Group C, set operator UNION
-- Every part that needs a second look: any failed run, or any aborted run (each part once).
SELECT serial_no FROM pt_test_runs WHERE result = 'FAIL'
UNION
SELECT serial_no FROM pt_test_runs WHERE result = 'ABORT'
ORDER BY 1;
