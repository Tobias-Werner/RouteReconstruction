import logging
import math

from geoalchemy2.functions import ST_Transform, ST_Length

from postgis import *
from model import *
from shapely.geometry import LineString, Polygon, Point
from geoalchemy2.shape import to_shape
import matplotlib.pyplot as plt
from geoalchemy2 import WKBElement
from shapely import wkb
import pandas as pd
import geopandas as gpd
import matplotlib.lines as mlines
from tachograph import *

import log
from utility import *


def get_sim_data(track_id):
    logging.info("Getting tachograph data")

    with Session(get_engine()) as session:
        tachograph = session.query(
            SimTachographEnvirocar
        ).filter(
            SimTachographEnvirocar.track_id == track_id
        ).order_by(
            SimTachographEnvirocar.time
        ).all()

        return pd.DataFrame({
            'time': [t.time for t in tachograph],
            'speed': [t.speed for t in tachograph],
            'distance': [t.distance for t in tachograph],
            'agg_distance': [t.agg_distance for t in tachograph]
        })


def get_nearest_edge(session, point):
    logging.info("Getting nearest edge to point. Point: {}".format(point))

    query_params = {
        'x': point.x,
        'y': point.y
    }

    sql = text("""
            SELECT 
                id, geom_way <-> st_transform(st_point(:x, :y, 25832), 4326) AS dist
            FROM 
                de_2po_4pgr
            ORDER BY 
                dist
            LIMIT 1
    """)

    edge_id = session.execute(sql, params=query_params).fetchone()[0]

    return session.query(Edge).filter(Edge.id == edge_id)[0]


def get_visitable_nodes(session, edge, distance):
    logging.info("Getting visitable nodes. Edge: {}, Distance: {}".format(edge.id, distance))

    query_params = {
        'node_id1': edge.source,
        'node_id2': edge.target,
        'distance': distance
    }

    sql = text("""
        SELECT 
            pgr_dd.pred, 
            pgr_dd.node
        FROM
            pgr_drivingDistance(
                'SELECT id, source, target, km AS cost, km AS reverse_cost FROM osm_temp',
                array[:node_id1, :node_id2],:distance, equicost => true) AS pgr_dd
        """)

    node_ids = set()

    for edge in session.execute(sql, params=query_params).fetchall():
        node_ids.add(edge[0])
        node_ids.add(edge[1])

    logging.info("Found {} visitable nodes".format(len(node_ids)))

    sql = text("""
        CREATE TEMPORARY TABLE visitable_nodes (
            id integer PRIMARY KEY
        );
    """)
    session.execute(sql)

    sql = text("""
            INSERT INTO visitable_nodes(id) VALUES (:id)    
    """)

    for node_id in node_ids:
        session.execute(sql, params={'id': node_id})


def get_track_length(session, track_id):
    length = session.query(
        ST_Length(ST_Transform(TrackAnalysis.geom, 25832))
    ).filter(
        TrackAnalysis.track_id == track_id
    ).first()[0]

    return length / 1000


def node_to_edges(session):
    logging.info("Expanding nodes to edges")

    sql = text("""
        SELECT DISTINCT 
            public.de_2po_4pgr.id
        FROM 
            de_2po_4pgr
        JOIN 
            visitable_nodes
        ON
            visitable_nodes.id = de_2po_4pgr.source OR
            visitable_nodes.id = de_2po_4pgr.target 
    """)

    edge_ids = set()

    for x in session.execute(sql).fetchall():
        edge_ids.add(x)

    logging.info("Expanded to {} edges".format(len(edge_ids)))

    return edge_ids


# def get_network(track_id):
#     with Session(get_engine()) as session:
#         track = get_track_geom(session, track_id)
#
#         distance = get_track_length(session, track_id)
#
#         start_point = Point(track.coords[0][0], track.coords[0][1])
#
#         nearest_edge = get_nearest_edge(session, start_point)
#
#         create_temp_clip(session, start_point, distance)
#
#         get_visitable_nodes(session, nearest_edge, distance)
#
#         edge_ids = node_to_edges(session)
#
#         return edge_ids


# sql = text("""
#         WITH t3 AS (WITH t2 AS (WITH t1 AS
#                                  xxxxx
#
#                 SELECT t2.pred AS way_id
#                 FROM t2
#                 UNION
#                 SELECT t2.node AS way_id
#                 FROM t2)
#             SELECT
#                 DISTINCT id, source, target, st_transform(geom_way, 25832) AS geom, km, kmh
#             FROM
#                 de_2po_4pgr,
#                 t3
#             WHERE
#                 source IN (t3.way_id) OR
#                 target IN (t3.way_id)
#     """)
#
# gdf = gpd.read_postgis(sql, get_engine(), geom_col='geom', params=query_params)
# print(gdf)


# with Session(get_engine()) as session:
#     result = session.execute(sql, query_params).fetchall()
#
#     for row in result:
#         id = row[0]
#         source = row[1]
#         target = row[2]
#         geom = row[3]
#         km = row[4]
#         kmh = row[5]
#
#         print(id)


#
# with Session(get_engine()) as session:
#     osm_ways = session.execute(sql, {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax}).fetchall()
#
#     network = gpd.GeoDataFrame({
#         'id': [x[0] for x in osm_ways],
#         'source': [x[2] for x in osm_ways],
#         'target': [x[3] for x in osm_ways],
#     },
#         geometry=gpd.GeoSeries([to_shape(WKBElement(x[1])) for x in osm_ways], crs="EPSG:25832")
#     )

# return network


def plot(track_id):
    fig, all_axes = plt.subplots(1, 1)
    fig.set_figwidth(6)
    fig.set_figheight(6)
    fig.dpi = 400

    # bbox = get_bbox_by_edge_ids(edge_ids, 0.05, 0.05)

    with Session(get_engine()) as session:
        track_geom = get_track_geom(session, track_id)
        driven_distance = get_track_length(session, track_id) * 1000
        start_point = Point(track_geom.coords[0][0], track_geom.coords[0][1])
        end_point = Point(track_geom.coords[-1][0], track_geom.coords[-1][1])

        x_diff = end_point.x - start_point.x
        y_diff = end_point.y - start_point.y

        center_x = start_point.x + (x_diff * 0.5)
        center_y = start_point.y + (y_diff * 0.5)

        direct_distance = math.sqrt((x_diff * x_diff) + (y_diff * y_diff))

        xmin = center_x - driven_distance * 0.9
        ymin = center_y - driven_distance * 0.9
        xmax = center_x + driven_distance * 0.9
        ymax = center_y + driven_distance * 0.9

        all_axes.set_ylim([ymin, ymax])
        all_axes.set_xlim([xmin, xmax])

        clip_network_bbox(session, xmin, ymin, xmax, ymax)

        amount_all_edges = 0
        amount_all_edges_length = 0
        amount_cliped_edges = 0
        amount_cliped_edges_length = 0
        amount_visitable_edges = 0
        amount_visitable_edges_length = 0

        for osm_edge in session.query(TempEdge).all():
            amount_all_edges = amount_all_edges + 1
            amount_all_edges_length = amount_all_edges_length + to_shape(osm_edge.geom_way).length
            plot_linestring(all_axes, osm_edge.geom_way, Colors.light_gray, 1.5, z_order=1, with_markers=False)

        clip_network_ellipse(session, start_point, end_point, driven_distance)

        for osm_edge in session.query(TempEdge).all():
            amount_cliped_edges = amount_cliped_edges + 1
            amount_cliped_edges_length = amount_cliped_edges_length + to_shape(osm_edge.geom_way).length
            plot_linestring(all_axes, osm_edge.geom_way, Colors.qualitative_1_lightblue, 1.5, z_order=2,
                            with_markers=False)

        plot_track_start_and_end(all_axes, from_shape(track_geom), Colors.gradient_red_blue_9[0])

        start_point_id = integrate_point_to_network(session, start_point)
        end_point_id = integrate_point_to_network(session, end_point)

        further_nodes_available = True
        while further_nodes_available:
            further_nodes_available = contract_network(session, (start_point_id, end_point_id))

        G = load_network(session)

        G = reduce_nodes(session, G, start_point_id, end_point_id, driven_distance / 1000)

        for osm_edge in session.query(TempEdge).all():
            amount_visitable_edges = amount_visitable_edges + 1
            amount_visitable_edges_length = amount_visitable_edges_length + to_shape(osm_edge.geom_way).length
            plot_linestring(all_axes, osm_edge.geom_way, Colors.qualitative_1_blue, 1.5, z_order=5, with_markers=False)



        # reachable_nodes = [n for n in G.nodes()]
        #
        # reachable_nodes_geom = []
        #
        # for reachable_node in reachable_nodes:
        #     edge_start_point_row = session.query(
        #         ST_StartPoint(TempEdge.geom_way).label("start_point")
        #     ).filter(
        #         TempEdge.source == reachable_node
        #     ).first()
        #
        #     if edge_start_point_row is not None:
        #         reachable_nodes_geom.append(to_shape(edge_start_point_row.start_point))
        #
        #     edge_end_point_row = session.query(
        #         ST_EndPoint(TempEdge.geom_way).label("end_point")
        #     ).filter(
        #         TempEdge.target == reachable_node
        #     ).first()
        #
        #     if edge_end_point_row is not None:
        #         reachable_nodes_geom.append(to_shape(edge_end_point_row.end_point))
        #
        # scatter_x = [p.x for p in reachable_nodes_geom]
        # scatter_y = [p.y for p in reachable_nodes_geom]
        #
        # all_axes.scatter(scatter_x, scatter_y, s=5, zorder=3)

        # clip_network_ellipse(session, start_point, end_point, track_geom.length)

    # plot_edges(all_axes, edge_ids)
    #
    # with Session(get_engine()) as session:
    #     track = session.query(
    #         TrackAnalysis
    #     ).filter(
    #         TrackAnalysis.track_id == track_id
    #     ).first()
    #
    #     plot_linestring(all_axes, track.geom, Colors.gradient_red_blue_9[0], 3, z_order=2, with_markers=True,
    #                     markersize=12)
    #
    # all_axes.set_xlim(bbox.bounds[0], bbox.bounds[2])
    # all_axes.set_ylim(bbox.bounds[1], bbox.bounds[3])

    #
    # xmin = bbox.bounds[0]
    # ymin = bbox.bounds[3]
    # xmax = bbox.bounds[2]
    # ymax = bbox.bounds[1]
    #
    # all_axes.plot([xmin + 100, xmin + 500 + 100], [ymax + 90, ymax + 90], marker='.', markersize=12, color='black')
    # all_axes.text(xmin + 10 + 180, ymax + 20 + 100, "500m", fontsize=20)
    #
    # all_axes.set_aspect('equal', adjustable='box')
    #
    # legend_items = [
    #     mlines.Line2D([], [], color=Colors.gradient_red_blue_9[0], marker='^', linewidth=3, markersize=12),
    #     mlines.Line2D([], [], color=Colors.gradient_red_blue_9[0], marker='s', linewidth=3, markersize=12),
    #     mlines.Line2D([], [], color=Colors.turquoise, marker='o', linewidth=3, markersize=12),
    #     mlines.Line2D([], [], color=Colors.light_gray, linewidth=3, markersize=12)
    # ]
    #
    # legend_labels = [
    #     'Reference track (start)',
    #     'Reference track (end)',
    #     'Reachable street segment',
    #     'Street network (car)'
    # ]
    #
    # all_axes.legend(
    #     handles=legend_items,
    #     labels=legend_labels,
    #     loc='lower center',
    #     ncol=2,
    #     bbox_to_anchor=(0.5, -0.075),
    #     fontsize=14,
    #     labelspacing=0.3,
    #     frameon=False
    # )
    all_axes.set_aspect('equal', adjustable='box')

    all_axes.plot([xmin + 300, xmin + 1300], [ymin + 200, ymin + 200], marker='.', markersize=9, color='black')
    all_axes.text(xmin + 400, ymin + 400, "1000m", fontsize=9)

    legend_items = [
        mlines.Line2D([], [], color=Colors.gradient_red_blue_9[0], marker='^', markersize=8),
        mlines.Line2D([], [], color=Colors.gradient_red_blue_9[0], marker='s', markersize=8),
        mlines.Line2D([], [], color=Colors.qualitative_1_lightblue, linewidth=3, markersize=12),
        mlines.Line2D([], [], color=Colors.qualitative_1_blue, linewidth=3, markersize=12),
        mlines.Line2D([], [], color=Colors.light_gray, linewidth=3, markersize=12)
    ]

    legend_labels = [
        'Track start',
        'Track end',
        'Edge by intersection (n={}, total distance={}km)'.format(amount_cliped_edges, int(amount_cliped_edges_length/1000)),
        'Edge by Dijkstra (n={}, total distance={}km)'.format(amount_visitable_edges, int(amount_visitable_edges_length/1000)),
        'Street network (n={}, total distance={}km)'.format(amount_all_edges, int(amount_all_edges_length/1000))
    ]

    all_axes.legend(
        handles=legend_items,
        labels=legend_labels,
        loc='lower left',
        ncol=1,
        bbox_to_anchor=(0.0, -0.27),
        fontsize=9,
        labelspacing=0.6,
        frameon=False
    )

    plt.tight_layout()
    all_axes.xaxis.set_visible(False)
    all_axes.yaxis.set_visible(False)
    plt.savefig("tracks_p2p_multi_step_filter.png", bbox_inches='tight', pad_inches=0, dpi=500)
    plt.show()

    # def get_route_candidates(network, track_id):
    #     track = get_track_geom(track_id)
    #     start_point = Point(track.coords[0][0], track.coords[0][1])


#     distances = network.geometry.distance(start_point)
#     nearest_index = distances.idxmin()
#     nearest_linestring = network.loc[nearest_index]
#
#     source = nearest_linestring['source']
#     target = nearest_linestring['target']
#
#     edge_set = set()
#
#     searched_id = target
#     while True:
#         filtered_df = network[network['source'] == searched_id]
#
#         if filtered_df.empty:
#             break
#
#         for i in range(filtered_df.count()):
#             edge_set.add(filtered_df.iloc[0]['id'])
#             searched_id = filtered_df.iloc[0]['target']
#
#     print(edge_set)

# def reconstruct(track_id):
#     from pyrosm import OSM, get_data
#     import os

# Define your bounding box [west, south, east, north]
# BBOX = [16.26, 48.12, 16.40, 48.24]  # Vienna city center as an example

# fp = get_data("vienna", directory="my_database", bounding_box=BBOX)

# network = get_network(track_id)

# get_route_candidates(network, track_id)
# print("query fertig")
#
# all_point_angles = []
# all_angle_point_x = []
# all_angle_point_y = []
#
# all_intersection_point_x = []
# all_intersection_point_y = []
#
# for w in osm_ways:
#     shapely_geom = wkb.loads(w[1])
#     point_x, point_y, angles = calculate_angles(shapely_geom)
#
#     all_point_angles = all_point_angles + angles
#     all_angle_point_x = all_angle_point_x + point_x
#     all_angle_point_y = all_angle_point_y + point_y
#
#     linestring = shapely_geom.wkt
#     coords = linestring[12:-1].split(',')
#     x_coords = [float(coord.split()[0]) for coord in coords]
#     y_coords = [float(coord.split()[1]) for coord in coords]
#
#     all_intersection_point_x.append(x_coords[0])
#     all_intersection_point_x.append(x_coords[-1])
#     all_intersection_point_y.append(y_coords[0])
#     all_intersection_point_y.append(y_coords[-1])
#
#     all_axes.plot(x_coords, y_coords, color="black", linewidth=0.2,
#                   solid_capstyle='round')
#
# all_axes.scatter([first_coordinate[0]], [first_coordinate[1]], marker="^", s=12, c='red', zorder=3)
# all_axes.scatter(all_angle_point_x, all_angle_point_y, edgecolors='none', marker="o", s=0.5, c='red',
#                  zorder=3)
# all_axes.scatter(all_intersection_point_x, all_intersection_point_y, edgecolors='none', marker="o", s=1,
#                  c='blue', zorder=3)
#
# for i in range(len(all_point_angles)):
#     all_axes.text(all_angle_point_x[i], all_angle_point_y[i], "{0:.1f}".format(all_point_angles[i]),
#                   fontsize=2)
#
# plt.show()


def calculate_angles(linestring):
    from math import atan2, degrees

    angles = []
    point_x = []
    point_y = []

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

    return point_x, point_y, angles


if __name__ == "__main__":
    track_id = '640782635244bc763c99ef5f'
    plot(track_id)
