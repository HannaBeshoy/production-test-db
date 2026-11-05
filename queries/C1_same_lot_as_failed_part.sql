-- Group C, non-aggregated 0D subquery as the condition
-- CRU-200-261105-011 failed the leak test on Thursday. Which other parts are in its lot
-- (candidates for a containment check)?
SELECT serial_no,
       TO_CHAR(produced_at, 'HH24:MI') AS made_at
FROM pt_parts
WHERE lot_no = (SELECT lot_no FROM pt_parts WHERE serial_no = 'CRU-200-261105-011')
  AND serial_no <> 'CRU-200-261105-011'
ORDER BY produced_at;
