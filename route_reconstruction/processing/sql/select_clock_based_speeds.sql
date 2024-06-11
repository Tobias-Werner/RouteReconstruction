-- This statement creates clock-based speed information
WITH t1 AS (SELECT second::timestamp AS clock
            FROM generate_series(
                         (SELECT min(time) FROM sim_tachograph_envirocar WHERE track_id = '52624a54e4b000fe05806f94'),
                         (SELECT max(time) FROM sim_tachograph_envirocar WHERE track_id = '52624a54e4b000fe05806f94'),
                         '1 second') second)
SELECT t1.clock, t2.time, t2.speed
FROM t1
         LEFT JOIN sim_tachograph_envirocar t2 ON t1.clock = t2.time
ORDER BY t1.clock;