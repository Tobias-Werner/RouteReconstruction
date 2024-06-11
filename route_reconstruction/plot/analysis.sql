-- Create cleaned version of track analysis
CREATE TABLE track_analysis_clean AS
SELECT track_analysis.*
FROM track_analysis
         LEFT JOIN track_analysis_exclude ON track_analysis.track_id = track_analysis_exclude.track_id
WHERE track_analysis_exclude.track_id is NULL;


-- Summarize corine detail data per clean track
CREATE TEMPORARY TABLE track_analysis_corine_overview AS
WITH t1 AS (SELECT track_id, st_length(st_transform(geom, 25832)) AS sum_length FROM track_analysis_clean),
     urban AS (SELECT track_id, sum(intersected_length) AS length
               FROM track_analysis_corine
               WHERE corine_class <= 121
               GROUP BY track_id),
     rural AS (SELECT track_id, sum(intersected_length) AS length
               FROM track_analysis_corine
               WHERE corine_class > 121
               GROUP BY track_id)
SELECT t1.track_id, t1.sum_length, urban.length AS urban_length, rural.length AS rural_length
FROM t1
         LEFT JOIN urban ON t1.track_id = urban.track_id
         LEFT JOIN rural ON t1.track_id = rural.track_id
ORDER BY t1.sum_length;


--
SELECT track_analysis_corine_overview.*, urban_length / sum_length AS percent
FROM track_analysis_corine_overview
WHERE sum_length BETWEEN 19000 AND 21000
  AND urban_length / sum_length BETWEEN 0.2 AND 0.3
ORDER BY sum_length;
