-- This statement queries speed classes
WITH t1 AS (SELECT * FROM generate_series(0, 100000, 500) AS length_class),
     t2 AS (SELECT track_id, st_length(st_transform(geom, 25832)) AS length FROM track_analysis)
SELECT CONCAT(CAST (t1.length_class AS text), ' bis ', CAST ((t1.length_class + 500) AS text)), count(*) AS classes
FROM t1
         JOIN t2 ON t2.length >= t1.length_class AND t2.length < t1.length_class + 500
GROUP BY t1.length_class;