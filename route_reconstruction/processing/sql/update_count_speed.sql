WITH t1 AS (SELECT track_id, count(*) AS count_speeds
            FROM measurement
            WHERE phenomenons -> 'Speed' IS NOT NULL
            GROUP BY track_id)
UPDATE track_analysis t2
SET count_speeds = (SELECT count_speeds FROM t1 WHERE t2.track_id = t1.track_id);
UPDATE track_analysis
SET count_speeds = 0
WHERE count_speeds IS NULL;