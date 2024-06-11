-- Calculate and update amount of GPS speed values
WITH t1 AS (SELECT track_id, count(*) AS count_gps_speeds
            FROM measurement
            WHERE phenomenons -> 'GPS Speed' IS NOT NULL
            GROUP BY track_id)
UPDATE track_analysis t2
SET count_gps_speeds = (SELECT count_gps_speeds FROM t1 WHERE t2.track_id = t1.track_id);
UPDATE track_analysis
SET count_gps_speeds = 0
WHERE count_gps_speeds IS NULL;