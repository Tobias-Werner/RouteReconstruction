import shapely
from geoalchemy2.shape import to_shape
from postgis import *
from geoalchemy2 import WKTElement
from model import *
from shapely import Polygon
from geoalchemy2.functions import *


class Colors:
    white = '#FFFFFF'
    black = '#000000'
    blue = '#182d81'
    turquoise = '#20928c'
    green = '#70cf57'
    yellow = '#fde725'
    gray = '#E2E2E2'
    light_gray = '#DDDDDD'

    qualitative_1_lightblue = '#a6cee3'
    qualitative_1_blue = '#1f78b4'
    qualitative_1_lightgreen = '#b2df8a'
    qualitative_1_green = '#33a02c'

    qualitative_2_green = '#66c2a5'
    qualitative_2_salmon = '#fc8d62'
    qualitative_2_purple = '#8da0cb'

    gradient_red_blue_9 = [
        '#b2182b',
        '#d6604d',
        '#f4a582',
        '#fddbc7',
        '#f7f7f7',
        '#d1e5f0',
        '#92c5de',
        '#4393c3',
        '#2166ac'
    ]

    gradient_turquoise_orange_5 = [
        '#018571',
        '#80cdc1',
        '#DDDDDD',
        '#dfc27d',
        '#a6611a'
    ]


def get_tracks_near(track_id):
    with Session(get_engine()) as session:
        bbox = get_bbox_by([track_id], 0, 0)

        bbox_wkt = WKTElement(bbox.wkt, srid=25832)

        intersected_tracks = session.query(
            TrackAnalysis).filter(
            TrackAnalysis.geom.ST_Intersects(bbox_wkt)
        ).filter()

        return intersected_tracks


def get_bbox_by_edge_ids(edge_ids, buffer_factor_x, buffer_factor_y):
    xmin = None
    xmax = None
    ymin = None
    ymax = None

    with Session(get_engine()) as session:
        for edge_id in edge_ids:
            row = session.query(
                ST_XMin(
                    ST_Transform(Edge.geom_way, 25832)
                ), ST_XMax(
                    ST_Transform(Edge.geom_way, 25832)
                ), ST_YMin(
                    ST_Transform(Edge.geom_way, 25832)
                ), ST_YMax(
                    ST_Transform(Edge.geom_way, 25832)
                )
            ).filter(
                Edge.id == edge_id[0]
            ).first()

            # for row in rows:
            if xmin is None or row[0] < xmin:
                xmin = row[0]
            if xmax is None or row[1] > xmax:
                xmax = row[1]
            if ymin is None or row[2] < ymin:
                ymin = row[2]
            if ymax is None or row[3] > ymax:
                ymax = row[3]

        padding_x = (xmax - xmin) * buffer_factor_x
        padding_y = (ymax - ymin) * buffer_factor_y

        polygon = Polygon((
            (xmin - padding_x, ymin - padding_y),
            (xmin - padding_x, ymax + padding_y),
            (xmax + padding_x, ymax + padding_y),
            (xmax + padding_x, ymin - padding_y),
            (xmin - padding_x, ymin - padding_y)
        ))

        return polygon


def get_intersected_tracks(bbox):
    with get_session() as session:
        bbox_wkt = WKTElement(bbox.wkt, srid=25832)

        intersected_tracks = session.query(
            TrackAnalysis
        ).filter(
            TrackAnalysis.geom.ST_Intersects(
                bbox_wkt
            )
        ).all()

        return intersected_tracks


def get_intersected_streets(bbox):
    with get_session() as session:
        bbox_wkt = WKTElement(bbox.wkt, srid=25832)

        intersected_geoms = session.query(
            ST_Transform(Edge.geom_way, 25832)
        ).filter(
            Edge.geom_way.ST_Intersects(
                ST_Transform(bbox_wkt, 4326)
            )
        ).all()

        return intersected_geoms



def plot_streets_around_track_ids(the_axes, track_ids, buffer_factor_x, buffer_factor_y):
    bbox = get_bbox_by(track_ids, buffer_factor_x, buffer_factor_y)

    for intersected_geom in get_intersected_streets(bbox):
        plot_linestring(the_axes, intersected_geom[0], Colors.light_gray, 1.5, z_order=1, with_markers=False)

    return bbox


def get_bbox_by(track_ids, buffer_factor_x, buffer_factor_y):
    with get_session() as session:
        bbox = session.query(
            ST_XMin(ST_Extent(TrackAnalysis.geom).label('xmin')),
            ST_XMax(ST_Extent(TrackAnalysis.geom).label('xmax')),
            ST_YMax(ST_Extent(TrackAnalysis.geom).label('ymin')),
            ST_YMin(ST_Extent(TrackAnalysis.geom).label('ymax')),
        ).filter(TrackAnalysis.track_id.in_(track_ids)).first()

        xmin = bbox[0]
        xmax = bbox[1]
        ymin = bbox[2]
        ymax = bbox[3]

        padding_x = (xmax - xmin) * buffer_factor_x
        padding_y = (ymax - ymin) * buffer_factor_y

        polygon = Polygon((
            (xmin - padding_x, ymin - padding_y),
            (xmin - padding_x, ymax + padding_y),
            (xmax + padding_x, ymax + padding_y),
            (xmax + padding_x, ymin - padding_y),
            (xmin - padding_x, ymin - padding_y)
        ))

        return polygon


def fill_polygon_ring(axes, ring_wkt, color):
    ring_coords = ring_wkt[1:-1].split(',')
    ring_x_coords = [float(coord.split()[0]) for coord in ring_coords]
    ring_y_coords = [float(coord.split()[1]) for coord in ring_coords]
    axes.fill(ring_x_coords, ring_y_coords, color=color)


def plot_germany(axes, foreground_color, background_color):
    with get_session() as session:
        rows = session.query(ST_AsText(Germany.wkb_geometry)).filter(
            Germany.objid.not_in(['DEBKGVG500000CTL', 'DEBKGVG500000CTL', 'DEBKGVG500000CTM'])).all()

        for row in rows:
            polygon = str(row[0][8:-1])
            rings = polygon.split('),')

            fill_polygon_ring(axes, rings[0], foreground_color)

            for i in range(1, len(rings)):
                fill_polygon_ring(axes, rings[i], background_color)


def plot_track(axes, track_id, norm, cmap):
    with (get_session() as session):
        query = session.query(
            SimTachographEnvirocar.speed,
            ST_GeometryN(
                ST_Force2D(
                    ST_LocateAlong(TrackAnalysis.geom, SimTachographEnvirocar.agg_distance)
                ),
                1
            )
        ).join(
            TrackAnalysis,
            SimTachographEnvirocar.track_id == TrackAnalysis.track_id
        ).filter(
            SimTachographEnvirocar.track_id == track_id
        ).order_by(
            SimTachographEnvirocar.time
        ).all()

        speeds = [x[0] for x in query]
        points = [x[1] for x in query]

        for i in range(len(points) - 1):
            point_1 = points[i]
            point_2 = points[i + 1]
            speed = speeds[i]

            linestring = shapely.LineString([to_shape(point_1), to_shape(point_2)])

            coords = linestring.wkt[12:-1].split(',')
            x_coords = [float(coord.split()[0]) for coord in coords]
            y_coords = [float(coord.split()[1]) for coord in coords]
            axes.plot(x_coords, y_coords, color=cmap(norm(speed)), linewidth=5, zorder=3, solid_capstyle='round')

        axes.plot(
            [to_shape(points[0]).x],
            [to_shape(points[0]).y],
            marker='^',
            markersize=10,
            zorder=4,
            c=Colors.gradient_red_blue_9[0]
        )
        axes.plot(
            [to_shape(points[-1]).x],
            [to_shape(points[-1]).y],
            marker='s',
            markersize=10,
            zorder=4,
            c=Colors.gradient_red_blue_9[0]
        )


def plot_edges(axes, edge_ids, with_markers=False):
    with Session(get_engine()) as session:
        for edge_id in edge_ids:
            edge = session.query(ST_Transform(Edge.geom_way, 25832)).filter(Edge.id == edge_id[0])[0]

            plot_linestring(axes, edge[0], Colors.turquoise, 2, 1, True, begin_marker='o', end_marker='o', markersize=4)


def plot_linestring(axes, geom, color, linewidth, z_order, with_markers=True, linestyle='solid', begin_marker='^',
                    end_marker='s',
                    markersize=6, dashes=(1, 0)):
    linestring = to_shape(geom).wkt
    coords = linestring[12:-1].split(',')
    x_coords = [float(coord.split()[0]) for coord in coords]
    y_coords = [float(coord.split()[1]) for coord in coords]
    axes.plot(x_coords, y_coords, color=color, linewidth=linewidth, zorder=z_order, solid_capstyle='round',
              linestyle=linestyle, dashes=dashes)

    if with_markers:
        axes.plot([x_coords[0]], [y_coords[0]], marker=begin_marker, markersize=markersize, zorder=z_order, c=color)
        axes.plot([x_coords[-1]], [y_coords[-1]], marker=end_marker, markersize=markersize, zorder=z_order, c=color)


def plot_track_start_and_end(axes, geom, color, markersize=6):
    begin_marker = '^'
    end_marker = 's'
    linestring = to_shape(geom).wkt
    coords = linestring[12:-1].split(',')
    x_coords = [float(coord.split()[0]) for coord in coords]
    y_coords = [float(coord.split()[1]) for coord in coords]
    axes.plot([x_coords[0]], [y_coords[0]], marker=begin_marker, markersize=markersize, zorder=50, c=color)
    axes.plot([x_coords[-1]], [y_coords[-1]], marker=end_marker, markersize=markersize, zorder=50, c=color)
