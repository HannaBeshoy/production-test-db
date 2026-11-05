-- Group E, complex: first-pass yield and final yield per product type and day
-- First-pass yield (FPY): the share of parts whose FIRST attempt passed at every station of
-- their route. Final yield: the share that, in the end, passed at every station of their route
-- (retests count). A part never tested at a station of its route has not passed there.
-- The inner query gives one row per part with two 0/1 flags ("no station of the route
-- without a pass"); the outer query aggregates them.
SELECT code,
       day,
       COUNT(*) AS parts,
       ROUND(100.0 * SUM(first_pass) / COUNT(*), 1) AS fpy_pct,
       ROUND(100.0 * SUM(final_pass) / COUNT(*), 1) AS final_yield_pct
FROM (SELECT t.code,
             TO_CHAR(p.produced_at, 'YYYY-MM-DD') AS day,
             CASE WHEN NOT EXISTS (
                      SELECT 1 FROM pt_test_specs sp
                      WHERE sp.type_id = p.type_id
                        AND NOT EXISTS (SELECT 1 FROM pt_test_runs r
                                        WHERE r.serial_no = p.serial_no AND r.station_id = sp.station_id
                                          AND r.attempt = 1 AND r.result = 'PASS'))
                  THEN 1 ELSE 0 END AS first_pass,
             CASE WHEN NOT EXISTS (
                      SELECT 1 FROM pt_test_specs sp
                      WHERE sp.type_id = p.type_id
                        AND NOT EXISTS (SELECT 1 FROM pt_test_runs r
                                        WHERE r.serial_no = p.serial_no AND r.station_id = sp.station_id
                                          AND r.result = 'PASS'))
                  THEN 1 ELSE 0 END AS final_pass
      FROM pt_parts p
      INNER JOIN pt_product_types t ON t.type_id = p.type_id)
GROUP BY code, day
ORDER BY code, day;
