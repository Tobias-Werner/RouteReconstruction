-- This statements create main schema
CREATE TABLE sim_tachograph_envirocar
(
    time         TIMESTAMP,
    speed        BIGINT,
    track_id     TEXT,
    distance     numeric,
    agg_distance numeric
);

COMMIT;

CREATE TABLE track_analysis
(
    track_id           TEXT,
    count_measurements BIGINT,
    count_speeds       BIGINT,
    count_gps_speeds   BIGINT,

    PRIMARY KEY (track_id)
);

CREATE INDEX ON track_analysis (count_speeds);
CREATE INDEX ON track_analysis (count_gps_speeds);
CREATE INDEX ON track_analysis (count_measurements);

-- Add geom column (linestring)
SELECT AddGeometryColumn('public', 'track_analysis', 'geom', '4326', 'LINESTRING', 2);
CREATE INDEX ON track_analysis USING gist (geom);
CREATE INDEX ON track_analysis USING gist (st_transform(geom, 25832));


COMMIT;

-- Generate table that holds track length of intersected corine classes
CREATE TABLE track_analysis_corine
(
    track_id           TEXT,
    intersected_length numeric,
    class              INTEGER
);

COMMIT;