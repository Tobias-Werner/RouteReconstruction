-- This statement fills the column distances
UPDATE sim_tachograph_envirocar
SET distance=t2.distance
FROM (SELECT t1.time,
             t1.track_id,
             LAG(speed, 1) OVER (
                 ORDER BY time
                 ) / 3.6 * EXTRACT(epoch FROM (time - LAG(time, 1) OVER (
                 ORDER BY time
                 ))) AS distance
      FROM sim_tachograph_envirocar t1
      ORDER BY time) AS t2
WHERE sim_tachograph_envirocar.time = t2.time
  AND sim_tachograph_envirocar.track_id = t2.track_id;