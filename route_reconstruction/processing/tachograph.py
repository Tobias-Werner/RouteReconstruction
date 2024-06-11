from sqlalchemy.orm import Session
from multiprocessing import Manager
from postgis import *
from model import *
import numpy
import gc
import logging

import log
from collections import deque
from math import atan2, degrees

import networkx as nx
import numpy
from geoalchemy2.functions import ST_Transform, ST_Length, ST_ClosestPoint, ST_Split, ST_Buffer
from geoalchemy2.shape import to_shape, from_shape
from shapely import Point, geometry, ops, reverse, LineString
from shapely import to_wkb, frechet_distance
from sqlalchemy import func, or_, and_
from collections import Counter

from custom_exception import *
from multiprocess import *


def get_track_length(session, track_id):
    length = session.query(
        ST_Length(ST_Transform(TrackAnalysis.geom, 25832))
    ).filter(
        TrackAnalysis.track_id == track_id
    ).first()[0]

    return length


def get_nearest_edge(session: Session, point: Point) -> TempEdge:
    edge = session.query(
        TempEdge
    ).order_by(
        TempEdge.geom_way.distance_centroid(
            from_shape(point, 25832)
        )
    ).first()

    return edge


def create_new_ids(session: Session, num_edge_ids: int, num_node_ids: int) -> (deque, deque):
    max_node_id, max_edge_id = session.query(
        func.greatest(
            func.max(TempEdge.source),
            func.max(TempEdge.target)
        ),
        func.max(TempEdge.id),
    ).one()

    edge_ids = deque([max_edge_id + i + 1 for i in range(num_edge_ids)])
    node_ids = deque([max_node_id + i + 1 for i in range(num_node_ids)])

    return edge_ids, node_ids


def get_closes_point_on_edge(session: Session, point: Point, edge: TempEdge):
    closest_point = session.query(
        ST_ClosestPoint(
            TempEdge.geom_way, from_shape(point, 25832)
        ).label("closest_point")
    ).filter(
        TempEdge.id == edge.id
    ).first()

    return to_shape(closest_point.closest_point)


def integrate_point_to_network(session, origin):
    new_edge_ids, new_node_ids = create_new_ids(session, 2, 1)

    created_point_id = new_node_ids.pop()
    created_edge_id_1 = new_edge_ids.pop()
    created_edge_id_2 = new_edge_ids.pop()

    nearest_edge = get_nearest_edge(session, origin)

    new_point = get_closes_point_on_edge(session, origin, nearest_edge)

    existing_source_point = Point(to_shape(nearest_edge.geom_way).coords[0])
    existing_target_point = Point(to_shape(nearest_edge.geom_way).coords[-1])

    if new_point.distance(existing_source_point) < 1.0:
        return nearest_edge.source
    if new_point.distance(existing_target_point) < 1.0:
        return nearest_edge.target

    splitted_edge = session.query(
        ST_Split(
            TempEdge.geom_way,
            ST_Buffer(
                from_shape(new_point, 25832), 0.1
            )
        ).label('geoms')
    ).filter(TempEdge.id == nearest_edge.id).first()

    sub_multi_lines = to_shape(splitted_edge.geoms)

    if len(sub_multi_lines.geoms) != 3:
        raise CustomException("Result parts not equal to 3")

    sub_lines = [g for g in sub_multi_lines.geoms if g.length > 0.5]

    if len(sub_lines) != 2:
        raise CustomException("Splitted lines are not equal to 2")

    first_sub_line_start_is_source = Point(sub_lines[0].coords[0]).distance(existing_source_point) < 0.5
    first_sub_line_end_is_source = Point(sub_lines[0].coords[-1]).distance(existing_source_point) < 0.5

    source_side_geom_idx = 0 if first_sub_line_start_is_source or first_sub_line_end_is_source else 1

    first_sub_line_start_is_target = Point(sub_lines[0].coords[0]).distance(existing_target_point) < 0.5
    first_sub_line_end_is_target = Point(sub_lines[0].coords[-1]).distance(existing_target_point) < 0.5

    target_side_geom_idx = 0 if first_sub_line_start_is_target or first_sub_line_end_is_target else 1

    if source_side_geom_idx == target_side_geom_idx:
        raise CustomException("Source and target side geoms are equal")

    # Processing source side geometry

    source_side_geom = sub_lines[source_side_geom_idx]

    start_is_source = Point(source_side_geom.coords[0]).distance(existing_source_point) < 0.5
    end_is_source = Point(source_side_geom.coords[-1]).distance(existing_source_point) < 0.5

    if start_is_source == end_is_source:
        raise CustomException("Start point and end point cannot be source")

    geom = source_side_geom if start_is_source else reverse(source_side_geom)
    coords = list(geom.coords)
    coords.append(origin)
    geom = LineString(coords)

    proportion = source_side_geom.length / to_shape(nearest_edge.geom_way).length
    cost = nearest_edge.cost * proportion if nearest_edge.cost < 1000000 else nearest_edge.cost
    reverse_cost = nearest_edge.reverse_cost * proportion if nearest_edge.reverse_cost < 1000000 else nearest_edge.reverse_cost

    new_source_side_edge = TempEdge(
        id=created_edge_id_1,
        km=source_side_geom.length / 1000,
        cost=cost,
        source=nearest_edge.source,
        target=created_point_id,
        reverse_cost=reverse_cost,
        geom_way=from_shape(geom, 25832)
    )
    session.add(new_source_side_edge)

    # Processing target side geometry

    target_side_geom = sub_lines[target_side_geom_idx]

    start_is_target = Point(target_side_geom.coords[0]).distance(existing_target_point) < 0.5
    end_is_target = Point(target_side_geom.coords[-1]).distance(existing_target_point) < 0.5

    if start_is_target == end_is_target:
        raise CustomException("Start point and end point cannot be target")

    geom = target_side_geom if end_is_target else reverse(target_side_geom)
    coords = list(geom.coords)
    coords.insert(0, origin)
    geom = LineString(coords)

    proportion = target_side_geom.length / to_shape(nearest_edge.geom_way).length
    cost = nearest_edge.cost * proportion if nearest_edge.cost < 1000000 else nearest_edge.cost
    reverse_cost = nearest_edge.reverse_cost * proportion if nearest_edge.reverse_cost < 1000000 else nearest_edge.reverse_cost

    new_target_side_edge = TempEdge(
        id=created_edge_id_2,
        km=target_side_geom.length / 1000,
        cost=cost,
        source=created_point_id,
        target=nearest_edge.target,
        reverse_cost=reverse_cost,
        geom_way=from_shape(geom, 25832)
    )
    session.add(new_target_side_edge)

    # End

    session.delete(nearest_edge)

    session.commit()

    return created_point_id


def load_network(session: Session) -> nx.MultiDiGraph:
    logging.info("Loading postgis network into NetworkX")
    G = nx.MultiDiGraph()

    for edge in session.query(TempEdge).all():
        if edge.cost < 1000000:
            G.add_edge(
                edge.source,
                edge.target,
                id=edge.id,
                cost=edge.cost,
                km=edge.km
            )
        if edge.reverse_cost < 1000000:
            G.add_edge(
                edge.target,
                edge.source,
                id=edge.id,
                cost=edge.reverse_cost,
                km=edge.km
            )

    return G


def calculate_shortest_path(session: Session, G: nx.MultiDiGraph, start_point: Point, start_point_id: int,
                            end_point_id: int) -> LineString:
    logging.info("Calculate shortest path")
    path = nx.shortest_path(G, source=start_point_id, target=end_point_id, weight='km')

    return path_to_linestring(session, G, path, start_point)


def calculate_fastest_path(session: Session, G: nx.MultiDiGraph, start_point: Point, start_point_id: int,
                           end_point_id: int) -> LineString:
    logging.info("Calculate fastest path")
    path = nx.shortest_path(G, source=start_point_id, target=end_point_id, weight='cost')

    return path_to_linestring(session, G, path, start_point)


def reduce_node_worker(G, node_ids, start_node_id, end_node_id, reachable_node_ids, distance, worker_id):
    processed = 0

    try:
        while True:
            node_id = node_ids.pop()

            try:
                path_to_start = nx.shortest_path(G, source=start_node_id, target=node_id, weight='km')
                path_to_end = nx.shortest_path(G, source=node_id, target=end_node_id, weight='km')

                cost_to_start = 0
                cost_to_end = 0

                for i in range(len(path_to_start) - 1):

                    keys = G[path_to_start[i]][path_to_start[i + 1]].keys()
                    km = 9999999999

                    for key in keys:
                        edge_data = G.get_edge_data(path_to_start[i], path_to_start[i + 1], key)
                        if edge_data['km'] < km:
                            km = edge_data['km']

                    cost_to_start += km

                for i in range(len(path_to_end) - 1):

                    keys = G[path_to_end[i]][path_to_end[i + 1]].keys()
                    km = 9999999999

                    for key in keys:
                        edge_data = G.get_edge_data(path_to_end[i], path_to_end[i + 1], key)
                        if edge_data['km'] < km:
                            km = edge_data['km']

                    cost_to_end += km

                total_cost = cost_to_start + cost_to_end

                d = distance * 1.01

                if total_cost < d:
                    reachable_node_ids.append(node_id)
            except Exception as e:
                pass

            processed = processed + 1

            if processed % 20 == 0:
                logging.info("Worker {} processed {} nodes".format(worker_id, processed))
    except Exception as e:
        logging.info("Worker {} stopped regular".format(worker_id))


def reduce_nodes(session, G, start_point_id, end_point_id, distance):
    logging.info("Reducing nodes")
    manager = Manager()
    reachable_node_ids = manager.list()
    node_ids = manager.list([n for n in G.nodes()])

    MultiprocessTask(
        reduce_node_worker,
        [G, node_ids, start_point_id, end_point_id, reachable_node_ids, distance],
        10
    ).start()

    node_ids = {n for n in G.nodes()}
    reachable_node_ids = {n for n in reachable_node_ids}

    extended_reachable_node_ids = set()

    for reachable_node_id in reachable_node_ids:
        extended_reachable_node_id_rows = session.query(
            TempEdge.source,
            TempEdge.target
        ).filter(
            or_(
                TempEdge.source == reachable_node_id,
                TempEdge.target == reachable_node_id
            )
        ).all()

        for source, target in extended_reachable_node_id_rows:
            extended_reachable_node_ids.add(source)
            extended_reachable_node_ids.add(target)

    deletable_node_ids = node_ids - extended_reachable_node_ids

    logging.info("Deleting {} nodes (reachable {} from {})".format(len(deletable_node_ids), len(reachable_node_ids),
                                                                   len(node_ids)))

    for deletable_node_id in deletable_node_ids:
        sql = text("""
            DELETE FROM osm_temp WHERE source = :id OR target = :id 
        """)
        session.execute(sql, {'id': deletable_node_id})

    session.commit()

    return load_network(session)


def calculate_angles(linestring):
    angles = []
    point_x = []
    point_y = []
    distances = []

    for i in range(len(linestring.coords) - 2):
        p1 = linestring.coords[i]
        p2 = linestring.coords[i + 1]
        p3 = linestring.coords[i + 2]

        angle_line1 = atan2(
            p2[1] - p1[1],
            p2[0] - p1[0]
        )
        angle_line2 = atan2(
            p3[1] - p2[1],
            p3[0] - p2[0]
        )

        angle_diff = degrees(angle_line1 - angle_line2)
        if angle_diff < -180.0:
            angle_diff = 360 + angle_diff
        if angle_diff > 180.0:
            angle_diff = 360 - angle_diff

        angles.append(angle_diff)
        point_x.append(p2[0])
        point_y.append(p2[1])

        distances.append(Point(p1).distance(Point(p2)))

    return point_x, point_y, angles, distances


def path_to_linestring(session: Session, G: nx.MultiDiGraph, path, origin: Point) -> LineString:
    logging.info("Creating linestring by path")
    geoms = []
    start_point = origin

    for i in range(len(path) - 1):

        keys = G[path[i]][path[i + 1]].keys()

        geom = None
        km = 9999999999

        for key in keys:
            edge_data = G.get_edge_data(path[i], path[i + 1], key)
            if edge_data['km'] < km:
                edge_id = edge_data['id']

                geom, = session.query(TempEdge.geom_way).filter(TempEdge.id == edge_id).one()
                geom = to_shape(geom)
                km = edge_data['km']

        if start_point.distance(Point(geom.coords[0])) < 0.5:
            geoms.append(geom)
        else:
            geoms.append(reverse(geom))

        start_point = Point(geoms[-1].coords[-1])

    mlinestring = geometry.MultiLineString(geoms)

    merged = ops.linemerge(mlinestring)

    return merged


def identify_degree_2_nodes(session: Session, ignored_node_ids: iter):
    query_source_node_ids = session.query(TempEdge.source.label("node_id"))
    query_target_node_ids = session.query(TempEdge.target.label("node_id"))

    query = query_source_node_ids.union_all(query_target_node_ids).order_by("node_id")

    node_ids = [n[0] for n in query.all()]
    id_counter = Counter(node_ids)

    return [node_id for node_id, degree in id_counter.items() if degree == 2 and node_id not in ignored_node_ids]


def contract_network(session: Session, ignored_node_ids: iter) -> bool:
    logging.info("Start contracting network")
    nodes_ids = identify_degree_2_nodes(session, ignored_node_ids)

    new_edge_ids, _ = create_new_ids(session, len(nodes_ids), 0)

    blocked_node_ids = set()

    for node_id in nodes_ids:

        if node_id not in blocked_node_ids:

            edges = session.query(TempEdge).filter(or_(TempEdge.source == node_id, TempEdge.target == node_id)).all()

            if len(edges) == 2 and len({edges[0].source, edges[0].target, edges[1].source, edges[1].target}) == 3:

                one_way_involved = (edges[0].cost >= 1000000 or
                                    edges[0].reverse_cost >= 1000000 or
                                    edges[1].cost >= 1000000 or
                                    edges[1].reverse_cost >= 1000000)

                linestring_1 = to_shape(edges[0].geom_way)
                linestring_2 = to_shape(edges[1].geom_way)

                start_point_1 = Point(linestring_1.coords[0])
                start_point_2 = Point(linestring_2.coords[0])
                end_point_1 = Point(linestring_1.coords[-1])
                end_point_2 = Point(linestring_2.coords[-1])

                if not one_way_involved:

                    blocked_node_ids.add(edges[0].source)
                    blocked_node_ids.add(edges[0].target)
                    blocked_node_ids.add(edges[1].source)
                    blocked_node_ids.add(edges[1].target)

                    new_edge = TempEdge(
                        id=new_edge_ids.pop(),
                        km=edges[0].km + edges[1].km,
                        cost=edges[0].cost + edges[1].cost,
                        reverse_cost=edges[0].reverse_cost + edges[1].reverse_cost,
                    )

                    if edges[0].source == edges[1].source:

                        if not start_point_1.distance(start_point_2) < 0.5:
                            raise CustomException("Start points do not match")

                        new_edge.source = edges[0].target
                        new_edge.target = edges[1].target
                        new_edge.geom_way = from_shape(
                            LineString(list(reverse(linestring_1).coords) + list(linestring_2.coords)[1:]), 25832
                        )

                    elif edges[0].target == edges[1].target:

                        if not end_point_1.distance(end_point_2) < 0.5:
                            raise CustomException("End points do not match")

                        new_edge.source = edges[0].source
                        new_edge.target = edges[1].source
                        new_edge.geom_way = from_shape(
                            LineString(list(linestring_1.coords) + list(reverse(linestring_2).coords)[1:]), 25832
                        )

                    elif edges[0].target == edges[1].source:
                        if not end_point_1.distance(start_point_2) < 0.5:
                            raise CustomException("End point does not match to start point")

                        new_edge.source = edges[0].source
                        new_edge.target = edges[1].target
                        new_edge.geom_way = from_shape(
                            LineString(list(linestring_1.coords) + list(linestring_2.coords)[1:]), 25832
                        )
                    elif edges[0].source == edges[1].target:
                        if not start_point_1.distance(end_point_2) < 0.5:
                            raise CustomException("Start point does not match to end point")

                        new_edge.source = edges[0].target
                        new_edge.target = edges[1].source
                        new_edge.geom_way = from_shape(
                            LineString(list(reverse(linestring_1).coords) + list(reverse(linestring_2).coords)[1:]),
                            25832
                        )
                    else:
                        raise CustomException("Node cannot be contracted")

                    session.add(new_edge)
                    session.delete(edges[0])
                    session.delete(edges[1])
                    session.commit()

    return len(blocked_node_ids) != 0


def get_track_geom(session, track_id):
    track = session.query(
        TrackAnalysis
    ).filter(
        TrackAnalysis.track_id == track_id
    ).first()

    return to_shape(track.geom)


def clip_network_bbox(session, xmin, ymin, xmax, ymax):
    logging.info("Start clipping network by bbox")

    sql = text("""
            DROP TABLE IF EXISTS osm_temp;
            CREATE TABLE osm_temp AS
                   SELECT id, st_transform(geom_way, 25832) AS geom_way, km, source, target, cost, reverse_cost FROM de_2po_4pgr
                   WHERE st_intersects(
                        geom_way, st_transform(
                            ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 25832),
                            4326
                        )
                   );
            CREATE INDEX ON osm_temp(id);
            CREATE INDEX ON osm_temp(source);
            CREATE INDEX ON osm_temp(target);
            CREATE INDEX ON osm_temp(km);
        """)

    params = {
        'xmin': xmin,
        'ymin': ymin,
        'xmax': xmax,
        'ymax': ymax
    }

    session.execute(sql, params=params)
    session.commit()


def clip_network_ellipse(session, point1, point2, track_length):
    logging.info("Start clipping network by ellipse")
    distance = point1.distance(point2)

    ankathete = distance
    hypotenuse = track_length
    alpha = numpy.arccos(ankathete / hypotenuse)

    beta = (numpy.pi / 2) - alpha

    buffer = (numpy.cos(beta) * hypotenuse) / 2

    query_params = {
        'x1': point1.x,
        'y1': point1.y,
        'x2': point2.x,
        'y2': point2.y,
        'buffer': buffer
    }

    sql = text("""
        DROP TABLE IF EXISTS osm_temp;
        CREATE TEMPORARY TABLE osm_temp AS
               SELECT id, st_transform(geom_way, 25832) AS geom_way, km, source, target, cost, reverse_cost FROM de_2po_4pgr
               WHERE st_intersects(
                    geom_way, st_transform(
                        st_buffer(
                            ST_MakeLine(
                                st_point(:x1, :y1, 25832),
                                st_point(:x2, :y2, 25832)
                            ),
                            :buffer
                        ),
                        4326
                    )
               );
        CREATE INDEX ON osm_temp(id);
        CREATE INDEX ON osm_temp(source);
        CREATE INDEX ON osm_temp(target);
        CREATE INDEX ON osm_temp(km);
    """)

    session.execute(sql, params=query_params)
    session.commit()


def get_cleansed_track_ids(max_length_m=None, min_length_m=None):
    manager = Manager()

    with Session(get_engine()) as session:

        if max_length_m is None:
            available_track_ids = [t.track_id for t in session.query(TrackAnalysis).all()]
            excluded_track_ids = [track_id[0] for track_id in
                                  session.query(TrackAnalysisExclude.track_id).distinct().all()]
        elif min_length_m is None:

            result = session.query(
                TrackAnalysis
            ).filter(
                ST_Length(TrackAnalysis.geom) < max_length_m
            ).all()

            available_track_ids = [t.track_id for t in result]
            excluded_track_ids = [track_id[0] for track_id in
                                  session.query(TrackAnalysisExclude.track_id).distinct().all()]

        else:
            result = session.query(
                TrackAnalysis
            ).filter(
                and_(ST_Length(TrackAnalysis.geom) < max_length_m, ST_Length(TrackAnalysis.geom) > min_length_m)
            ).all()

            available_track_ids = [t.track_id for t in result]
            excluded_track_ids = [track_id[0] for track_id in
                                  session.query(TrackAnalysisExclude.track_id).distinct().all()]

    return manager.list([track_id for track_id in available_track_ids if track_id not in excluded_track_ids])
