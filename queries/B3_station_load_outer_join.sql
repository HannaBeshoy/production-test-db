-- Group B, aggregated OUTER JOIN
-- The load of every station, including stations with no runs at all (LEAK-3, new on Thursday):
-- an inner join would silently drop them.
SELECT s.name AS station,
       s.kind,
       COUNT(r.run_id) AS runs,
       NVL(ROUND(AVG(r.duration_s), 1), 0) AS mean_s
FROM pt_stations s
LEFT OUTER JOIN pt_test_runs r ON r.station_id = s.station_id
GROUP BY s.name, s.kind
ORDER BY runs DESC, s.name;
