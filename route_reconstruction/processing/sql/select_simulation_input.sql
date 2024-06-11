SELECT t1.track_id,
       t2.time,
       (t2.phenomenons -> 'Speed' ->> 'value')::DOUBLE PRECISION AS speed
FROM track_analysis t1
         JOIN measurement t2 ON t1.track_id = t2.track_id
WHERE t1.count_measurements = t1.count_speeds
  AND st_numpoints(t1.geom) > 1
  AND
  -- st_length(st_transform(t1.geom, 25832)) BETWEEN 100 AND 3000 AND
    t1.track_id != '580c51e5e4b01fb1c08ce221'
ORDER BY t2.time