-- Calculate and insert intersection with corine data.
INSERT INTO track_analysis_corine(track_id, intersected_length, corine_class)
WITH t1 AS (SELECT track_id, geom AS geom
            FROM track_analysis
            WHERE track_id = :track_id)
SELECT t1.track_id,
       sum(st_length(st_intersection(t1.geom, t2.wkb_geometry)))::numeric AS intersected_length,
       t2.clc18::integer                                                  AS corine_class
FROM t1
         JOIN corine t2 ON st_intersects(t1.geom, t2.wkb_geometry)
GROUP BY t2.clc18, t1.geom, t1.track_id;
