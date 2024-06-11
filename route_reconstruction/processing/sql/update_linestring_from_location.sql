-- Generate and update linestrings from points
WITH t3 AS (SELECT t1.track_id,
                   st_makeline(ARRAY(SELECT t2.geom
                                     FROM measurement t2
                                     WHERE t2.track_id = t1.track_id
                                     ORDER BY time)) AS geom
            FROM measurement t1
            GROUP BY t1.track_id)
UPDATE track_analysis
SET geom = (SELECT st_addmeasure(st_transform(geom, 25832), 0, st_length(st_transform(geom, 25832)))
            FROM t3
            WHERE t3.track_id = track_analysis.track_id);