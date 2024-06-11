WITH t1 AS (SELECT track_id, count(*) AS count_measurements FROM measurement GROUP BY track_id)
UPDATE track_analysis t2
SET count_measurements = (SELECT count_measurements FROM t1 WHERE t2.track_id = t1.track_id);