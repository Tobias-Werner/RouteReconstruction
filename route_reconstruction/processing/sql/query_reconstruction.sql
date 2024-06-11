-- track_id: 52624a54e4b000fe05806f94

CREATE TABLE dijkstra_result AS
SELECT *
FROM pgr_dijkstra(
        'SELECT id, source, target, km AS cost, km AS reverse_cost FROM de_2po_4pgr',
        106357, 923470
     );


CREATE TABLE dijkstra_routes_result AS
SELECT t1.*, t2.geom_way
FROM dijkstra_result t1
         LEFT JOIN de_2po_4pgr t2 ON t1.edge = t2.id;


CREATE TABLE reachability_result AS
SELECT *
FROM pgr_drivingDistance(
        'SELECT id, source, target, km AS cost, km AS reverse_cost FROM de_2po_4pgr',
        106357, 7
     );


CREATE TABLE reachability_routes_result AS
SELECT t1.*, t2.geom_way
FROM reachability_result t1
         LEFT JOIN de_2po_4pgr t2 ON t1.edge = t2.id;



-- WITH t1 AS (SELECT track_id, st_transform(geom, 25832) AS geom
--             FROM track_analysis
--             WHERE track_id = '52624a54e4b000fe05806f94'),
--      t2 AS (SELECT t1.track_id, st_addmeasure(t1.geom, 0, st_length(t1.geom)) AS geom FROM t1)
-- SELECT t2.track_id, st_locatealong(t2.geom,  FROM t2;

-- 52624a54e4b000fe05806f96
-- DROP TABLE IF EXISTS nearest_point;
-- CREATE TABLE nearest_point AS
-- SELECT ST_ClosestPoint(de_2po_4pgr.geom_way, ) )
