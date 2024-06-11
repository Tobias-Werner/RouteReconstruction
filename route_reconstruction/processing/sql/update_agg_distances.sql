WITH t1 AS (SELECT time,
                   speed,
                   track_id,
                   distance,
                   sum(distance)
                   OVER (order by time asc rows between unbounded preceding and current row) AS agg_distance
            FROM sim_tachograph_envirocar
            WHERE track_id = :track_id
            ORDER BY time)
UPDATE sim_tachograph_envirocar
SET agg_distance=t1.agg_distance
FROM t1
WHERE t1.track_id = sim_tachograph_envirocar.track_id
  AND t1.time = sim_tachograph_envirocar.time;