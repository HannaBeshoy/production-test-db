-- Group C, 1D subquery with = ANY
-- The operators who ran at least one failed test (an operator with many may need training, or
-- may simply have been on the shift when LEAK-1 wore out: E3 tells which).
SELECT o.name,
       o.shift
FROM pt_operators o
WHERE o.operator_id = ANY (SELECT r.operator_id FROM pt_test_runs r WHERE r.result = 'FAIL')
ORDER BY o.shift, o.name;
