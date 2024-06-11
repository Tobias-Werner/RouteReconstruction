import logging
import math
import matplotlib.lines as mlines
from sqlalchemy import asc, desc
import matplotlib.pyplot as plt
import log

from utility import *


def prepare_subplot(the_axes, track_id, similar_track_ids, buffer_factor_x, buffer_factor_y, title):
    the_axes.set_title(title)
    bbox = plot_streets_around_track_ids(
        the_axes,
        similar_track_ids,
        buffer_factor_x,
        buffer_factor_y
    )
    the_axes.xaxis.set_visible(False)
    the_axes.yaxis.set_visible(False)
    xmin = bbox.bounds[0]
    ymin = bbox.bounds[3]
    xmax = bbox.bounds[2]
    ymax = bbox.bounds[1]
    the_axes.set_aspect('equal', adjustable='box')
    the_axes.set_ylim([ymax, ymin])
    the_axes.set_xlim([xmin, xmax])

    the_axes.plot([xmin + 100, xmin + 200 + 100], [ymax + 90, ymax + 90], marker='.', markersize=5, color='black')
    the_axes.text(xmin + 10 + 100, ymax + 20 + 100, "200m", fontsize=7)

    the_axes.set_aspect('equal', adjustable='box')
    the_axes.set_ylim([ymax, ymin])
    the_axes.set_xlim([xmin, xmax])

    with Session(get_engine()) as session:
        similar_track = session.query(
            TrackAnalysis
        ).filter(
            TrackAnalysis.track_id == track_id
        ).first()

        plot_linestring(the_axes, similar_track.geom, Colors.gradient_red_blue_9[0], 1.0, z_order=3)


def plot(track_id):
    fig, all_axes = plt.subplots(3, 2)
    fig.set_figwidth(7)
    fig.set_figheight(10)
    fig.dpi = 400

    buffer_factor_x = 0.4
    buffer_factor_y = 0.05

    with Session(get_engine()) as session:

        similar_tracks = session.query(
            TrackAnalysisSimilarity
        ).filter(
            TrackAnalysisSimilarity.track_id_1 == track_id
        ).order_by(
            desc(TrackAnalysisSimilarity.hausdorff_distance)
        ).all()

        similar_track_ids = [similar_track.track_id_2 for similar_track in similar_tracks]

        prepare_subplot(all_axes[0][0], track_id, similar_track_ids, buffer_factor_x, buffer_factor_y, "(A)")
        prepare_subplot(all_axes[0][1], track_id, similar_track_ids, buffer_factor_x, buffer_factor_y, "(B)")
        prepare_subplot(all_axes[1][0], track_id, similar_track_ids, buffer_factor_x, buffer_factor_y, "(C)")
        prepare_subplot(all_axes[1][1], track_id, similar_track_ids, buffer_factor_x, buffer_factor_y, "(D)")
        prepare_subplot(all_axes[2][0], track_id, similar_track_ids, buffer_factor_x, buffer_factor_y, "(E)")
        prepare_subplot(all_axes[2][1], track_id, similar_track_ids, buffer_factor_x, buffer_factor_y, "(F)")

        # All
        bbox = get_bbox_by([track_id], buffer_factor_x, buffer_factor_y)
        intersected_tracks = get_intersected_tracks(bbox)

        logging.info("Amount in (A): {}".format(len(intersected_tracks)))

        for track in intersected_tracks:
            plot_linestring(all_axes[0][0], track.geom, Colors.gradient_red_blue_9[6], 0.5, 2, True)

        # Has distance less than 20m

        sql = text("""
            WITH sub1 AS (
                SELECT t1.track_id, t1.geom
                FROM track_analysis AS t1
                LEFT JOIN track_analysis_exclude AS t2 ON t1.track_id = t2.track_id
                WHERE t2.track_id IS NULL
            )
            SELECT t2.track_id
            FROM sub1 AS t1
            JOIN sub1 AS t2 ON t1.geom && t2.geom
            WHERE t1.track_id=:track_id AND st_distance(t1.geom, t2.geom) < 50;
            """)

        d20_track_ids = [x[0] for x in session.execute(sql, {'track_id': track_id}).fetchall()]

        logging.info("Amount in (B): {}".format(len(d20_track_ids)))

        for track in session.query(TrackAnalysis).filter(TrackAnalysis.track_id.in_(d20_track_ids)):
            plot_linestring(all_axes[0][1], track.geom, Colors.gradient_red_blue_9[6], 0.5, 2, True)

        c_amount = 0
        d_amount = 0
        e_amount = 0
        f_amount = 0

        # Hausdorf 1
        for similar_track_id in similar_tracks:
            similar_track = session.query(
                TrackAnalysis
            ).filter(
                TrackAnalysis.track_id == similar_track_id.track_id_2
            ).first()

            if similar_track_id.hausdorff_distance < 500:
                c_amount = c_amount + 1
                plot_linestring(all_axes[1][0], similar_track.geom, Colors.gradient_red_blue_9[6], 1.0, z_order=2)

        # Hausdorf 2
        for similar_track_id in similar_tracks:
            similar_track = session.query(
                TrackAnalysis
            ).filter(
                TrackAnalysis.track_id == similar_track_id.track_id_2
            ).first()

            if similar_track_id.hausdorff_distance < 50:
                d_amount = d_amount + 1
                plot_linestring(all_axes[1][1], similar_track.geom, Colors.gradient_red_blue_9[6], 1.0, z_order=2)

        # Frechet 1
        for similar_track_id in similar_tracks:
            similar_track = session.query(
                TrackAnalysis
            ).filter(
                TrackAnalysis.track_id == similar_track_id.track_id_2
            ).first()

            if similar_track_id.frechet_distance < 500:
                e_amount = e_amount + 1
                plot_linestring(all_axes[2][0], similar_track.geom, Colors.gradient_red_blue_9[6], 1.0, z_order=2)

        # Frechet 2
        for similar_track_id in similar_tracks:
            similar_track = session.query(
                TrackAnalysis
            ).filter(
                TrackAnalysis.track_id == similar_track_id.track_id_2
            ).first()

            if similar_track_id.frechet_distance < 50:
                f_amount = f_amount + 1
                plot_linestring(all_axes[2][1], similar_track.geom, Colors.gradient_red_blue_9[6], 1.0, z_order=2)

        logging.info("Amount in (C): {}".format(c_amount))
        logging.info("Amount in (D): {}".format(d_amount))
        logging.info("Amount in (E): {}".format(e_amount))
        logging.info("Amount in (F): {}".format(f_amount))

        legend_items = [
            mlines.Line2D([], [], color=Colors.gradient_red_blue_9[0], marker='^', markersize=6),
            mlines.Line2D([], [], color=Colors.gradient_red_blue_9[0], marker='s', markersize=6),
            mlines.Line2D([], [], color=Colors.gradient_red_blue_9[6], marker='^', markersize=6),
            mlines.Line2D([], [], color=Colors.gradient_red_blue_9[6], marker='s', markersize=6)
        ]

        legend_labels = [
            'Reference track (start)',
            'Reference track (end)',
            'Candidate track (start)',
            'Candidate track (end)'
        ]

        all_axes[2][0].legend(
            handles=legend_items,
            labels=legend_labels,
            loc='upper left',
            bbox_to_anchor=(-0.05, 0.0),
            labelspacing=0.1,
            frameon=False
        )

        fig.subplots_adjust(right=0.7)

    plt.savefig("tracks_duplicates.png", bbox_inches='tight', pad_inches=0, dpi=500)
    plt.show()


if __name__ == "__main__":
    # data = get_data('5ebe77b265b80c5d6bed5532')
    data = plot('63948a37ad53a0015a075a94')
    # data = get_data('57e19112e4b0f05fc201b55b')
