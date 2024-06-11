from sqlalchemy import Column, Integer, String, Numeric, DateTime, BigInteger, JSON
from sqlalchemy.orm import DeclarativeBase, relationship
from typing import List
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from geoalchemy2 import WKBElement
from datetime import datetime
from enum import Enum


class ExcludeReason(str, Enum):
    outside_germany = "outside_germany"
    missing_speed_attributes = "missing_speed_attributes"
    not_driving = "speeds_sum_zero"
    duplicated_time = "duplicated_time"
    negative_speed_values = "negative_speed_values"
    less_ten_measurement = "less_ten_measurement"
    timedelta_exceeded = "timedelta_exceeded"
    too_fast = "too_fast"


class EnviroCar(DeclarativeBase):
    pass


class Processing(DeclarativeBase):
    pass


class Osm(DeclarativeBase):
    pass


class SimTachographEnvirocar(Processing):
    __tablename__ = "sim_tachograph_envirocar"

    # Columns
    time: Mapped[datetime] = mapped_column(primary_key=True)
    speed: Mapped[int] = mapped_column()
    track_id: Mapped[str] = mapped_column(primary_key=True)
    distance: Mapped[float] = mapped_column(nullable=True)
    agg_distance: Mapped[float] = mapped_column(nullable=True)


class TrackAnalysis(Processing):
    __tablename__ = "track_analysis"

    # Columns
    track_id: Mapped[str] = mapped_column(primary_key=True)
    count_measurements: Mapped[int] = mapped_column(index=True, nullable=True)
    count_speeds: Mapped[int] = mapped_column(index=True, nullable=True)
    count_gps_speeds: Mapped[int] = mapped_column(index=True, nullable=True)
    geom: Mapped[WKBElement] = mapped_column(
        Geometry(
            geometry_type="LINESTRINGM",
            srid=25832,
            dimension=3,
            spatial_index=True
        ),
        nullable=True
    )


class TrackAnalysisCorine(Processing):
    __tablename__ = "track_analysis_corine"

    # Columns
    track_id: Mapped[str] = mapped_column(primary_key=True)
    intersected_length: Mapped[float] = mapped_column()
    corine_class: Mapped[int] = mapped_column(primary_key=True)


class TrackAnalysisExclude(Processing):
    __tablename__ = "track_analysis_exclude"

    # Columns
    track_id: Mapped[str] = mapped_column(primary_key=True)
    reason: Mapped[str] = mapped_column(primary_key=True)


class Track(EnviroCar):
    __tablename__ = "track"

    # Columns
    id: Mapped[str] = mapped_column(primary_key=True)
    begin_ts: Mapped[datetime] = mapped_column()
    end_ts: Mapped[datetime] = mapped_column()
    length_km: Mapped[float] = mapped_column()
    description: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    sensor: Mapped[dict] = mapped_column(JSON)


class TrackAnalysisSimilarity(Processing):
    __tablename__ = "track_analysis_similarity"

    # Columns
    track_id_1: Mapped[str] = mapped_column(primary_key=True)
    track_id_2: Mapped[str] = mapped_column(primary_key=True)
    hausdorff_distance: Mapped[float] = mapped_column(index=True)
    frechet_distance: Mapped[float] = mapped_column(index=True)


class Measurement(EnviroCar):
    __tablename__ = "measurement"

    # Columns
    id: Mapped[str] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column()
    track_id: Mapped[str] = mapped_column()
    phenomenons: Mapped[dict] = mapped_column(JSON)
    geom: Mapped[WKBElement] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            dimension=2,
            spatial_index=True
        ))


class Edge(Osm):
    __tablename__ = "de_2po_4pgr"

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[int] = mapped_column()
    target: Mapped[int] = mapped_column()
    geom_way: Mapped[WKBElement] = mapped_column(
        Geometry(
            geometry_type="LINESTRING",
            srid=4326,
            dimension=2,
            spatial_index=True
        ))


class TempEdge(Processing):
    __tablename__ = "osm_temp"

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[int] = mapped_column()
    target: Mapped[int] = mapped_column()
    km: Mapped[float] = mapped_column()
    cost: Mapped[float] = mapped_column()
    reverse_cost: Mapped[float] = mapped_column()
    geom_way: Mapped[WKBElement] = mapped_column(
        Geometry(
            geometry_type="LINESTRING",
            srid=25832,
            dimension=2
        ))


class TempDegree2Nodes(Processing):
    __tablename__ = "degree_node_temp"

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column()
    edge_id: Mapped[int] = mapped_column()
    source: Mapped[int] = mapped_column()
    target: Mapped[int] = mapped_column()


class RouteP2PResults(Processing):
    __tablename__ = "route_p2p_results"

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[str] = mapped_column()
    type: Mapped[str] = mapped_column()
    frechet_dist: Mapped[float] = mapped_column()
    geom_way: Mapped[WKBElement] = mapped_column(
        Geometry(
            geometry_type="LINESTRING",
            srid=25832,
            dimension=2
        ))


class Germany(Osm):
    __tablename__ = "germany"

    # Columns
    ogc_fid: Mapped[int] = mapped_column(primary_key=True)
    objid: Mapped[str] = mapped_column()
    wkb_geometry: Mapped[WKBElement] = mapped_column(
        Geometry(
            geometry_type="POLYGON",
            srid=25832,
            dimension=2,
            spatial_index=True
        ))
