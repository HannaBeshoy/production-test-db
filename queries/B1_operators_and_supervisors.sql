-- Group B, non-aggregated self-join
-- Every operator with the supervisor they report to (supervisors themselves report to nobody
-- and do not appear on the left).
SELECT o.name AS operator,
       o.shift,
       s.name AS supervisor
FROM pt_operators o
INNER JOIN pt_operators s ON o.supervisor_id = s.operator_id
ORDER BY s.name, o.name;
