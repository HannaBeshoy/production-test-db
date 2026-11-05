-- Group C, 1D subquery with NOT EXISTS
-- How many parts of each type never failed a single test (first-time-right or not)?
SELECT t.code,
       COUNT(*) AS never_failed
FROM pt_parts p
INNER JOIN pt_product_types t ON t.type_id = p.type_id
WHERE NOT EXISTS (SELECT 1 FROM pt_test_runs r WHERE r.serial_no = p.serial_no AND r.result = 'FAIL')
GROUP BY t.code
ORDER BY t.code;
