CREATE TABLE track
(
    id          TEXT,
    begin_ts    TIMESTAMP,
    end_ts      TIMESTAMP,
    length_km   DOUBLE PRECISION,
    description TEXT,
    status      TEXT,
    sensor      JSON
);

CREATE INDEX ON track (id);

CREATE TABLE measurement
(
    id          TEXT,
    time        TIMESTAMP,
    track_id    TEXT,
    phenomenons JSON
);

SELECT AddGeometryColumn('public', 'measurement', 'geom', '4326', 'POINT', 2);

CREATE INDEX ON measurement (id);
CREATE INDEX ON measurement (track_id);
CREATE INDEX ON measurement (time);
CREATE INDEX ON measurement((phenomenons->>'Speed'));
CREATE INDEX ON measurement((phenomenons->>'GPS Speed'));
CREATE INDEX ON measurement USING GIST (geom);

CREATE VIEW measurement_detail AS
SELECT id,
       time,
       track_id,
       (phenomenons -> 'Speed' ->> 'value')::DOUBLE PRECISION AS speed,
       geom
FROM measurement;

