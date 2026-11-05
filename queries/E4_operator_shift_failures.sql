-- Group E, complex: failures by shift and supervisor, with the share that came from LEAK-1
-- (a team's failure count says little until the station's own problem is taken out).
SELECT s.name AS supervisor,
       o.shift,
       COUNT(r.run_id) AS runs,
       SUM(CASE WHEN r.result = 'FAIL' THEN 1 ELSE 0 END) AS fails,
       SUM(CASE WHEN r.result = 'FAIL' AND r.station_id = 2 THEN 1 ELSE 0 END) AS fails_at_leak1
FROM pt_operators s
INNER JOIN pt_operators o ON o.supervisor_id = s.operator_id
LEFT OUTER JOIN pt_test_runs r ON r.operator_id = o.operator_id AND r.result <> 'ABORT'
GROUP BY s.name, o.shift
ORDER BY s.name;
