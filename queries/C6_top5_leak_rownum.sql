-- Group C, ROWNUM filtering the records of an ordered 2D subquery
-- The five highest leak readings. ROWNUM is numbered before ORDER BY in the same query, so the
-- ordering must happen in the subquery (course notes C204).
SELECT serial_no, day, leak_sccm
FROM (SELECT r.serial_no,
             TO_CHAR(r.started_at, 'YYYY-MM-DD') AS day,
             m.value AS leak_sccm
      FROM pt_measurements m
      INNER JOIN pt_test_runs r ON r.run_id = m.run_id
      WHERE m.spec_id = 5
      ORDER BY m.value DESC)
WHERE ROWNUM <= 5;
