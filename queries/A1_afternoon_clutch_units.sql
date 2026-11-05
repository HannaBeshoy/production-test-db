-- Group A, non-aggregated query (selection with pattern matching, a built-in function, sorting)
-- The clutch release units made on 4 November in the afternoon shift (from 14:00), with the
-- time they were made and the number within the day.
SELECT serial_no,
       lot_no,
       TO_CHAR(produced_at, 'HH24:MI') AS made_at,
       SUBSTR(serial_no, LENGTH(serial_no) - 2) AS day_number
FROM pt_parts
WHERE serial_no LIKE 'CRU-200-261104-%'
  AND TO_CHAR(produced_at, 'HH24') >= '14'
ORDER BY produced_at;
