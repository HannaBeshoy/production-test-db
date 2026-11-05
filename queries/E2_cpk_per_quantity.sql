-- Group E, complex: process capability (Cpk) of every measured quantity
-- Cpk = min(USL - mean, mean - LSL) / (3 * standard deviation). Below 1.33 the process is not
-- capable: too many parts will fall outside the limits. Worst first.
SELECT t.code,
       st.name AS station,
       sp.quantity,
       COUNT(*) AS n,
       ROUND(AVG(m.value), 3) AS mean,
       ROUND(STDDEV(m.value), 3) AS sd,
       ROUND(LEAST(sp.upper_limit - AVG(m.value), AVG(m.value) - sp.lower_limit) / (3 * STDDEV(m.value)), 2) AS cpk
FROM pt_measurements m
INNER JOIN pt_test_specs sp ON sp.spec_id = m.spec_id
INNER JOIN pt_product_types t ON t.type_id = sp.type_id
INNER JOIN pt_stations st ON st.station_id = sp.station_id
GROUP BY t.code, st.name, sp.quantity, sp.lower_limit, sp.upper_limit
ORDER BY cpk, t.code;
