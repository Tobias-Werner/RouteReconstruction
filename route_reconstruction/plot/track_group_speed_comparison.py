from datetime import timedelta
from utility import *
from postgis import *
from model import *
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.lines as mlines
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
import numpy as np


def plot(track_id):
    with Session(get_engine()) as session:

        similar_tracks = session.query(
            TrackAnalysisSimilarity
        ).filter(
            TrackAnalysisSimilarity.track_id_1 == track_id, TrackAnalysisSimilarity.frechet_distance < 50
        ).order_by(
            TrackAnalysisSimilarity.frechet_distance.desc()
        )

        track_ids = [similar_track.track_id_2 for similar_track in similar_tracks]
        frechet_distances = [similar_track.frechet_distance for similar_track in similar_tracks]

        times = []
        distances = []
        agg_distances = []
        speeds = []

        for similar_track_id in track_ids:
            measurements = session.query(
                SimTachographEnvirocar
            ).filter(
                SimTachographEnvirocar.track_id == similar_track_id
            ).order_by(
                SimTachographEnvirocar.time
            )

            distances.append([measurement.distance for measurement in measurements])
            agg_distances.append([measurement.agg_distance for measurement in measurements])
            speeds.append([measurement.speed for measurement in measurements])
            times.append([measurement.time for measurement in measurements])

    fig, all_ax = plt.subplots(nrows=3, ncols=1, figsize=(7, 16))

    cmap = plt.get_cmap('jet')

    max_speed = 0
    for track_speeds in speeds:
        max_speed = max(max_speed, max(track_speeds))

    max_speed = 65

    max_agg_distance = 0
    for track_agg_distances in agg_distances:
        max_agg_distance = max(max_agg_distance, max(track_agg_distances))

    max_time_interval = timedelta(seconds=1)
    for time in times:
        max_time_interval = max(max_time_interval, time[-1] - time[0])

    norm = plt.Normalize(0, max_speed)

    the_axes = all_ax[0]

    the_axes.xaxis.set_visible(False)
    the_axes.yaxis.set_visible(False)
    bbox = plot_streets_around_track_ids(the_axes, [track_id], 0.3, 0.1)
    plot_track(the_axes, track_id, norm, cmap)
    the_axes.set_aspect('equal', adjustable='box')
    the_axes.set_xlim(bbox.bounds[0], bbox.bounds[2])
    the_axes.set_ylim(bbox.bounds[1], bbox.bounds[3])
    the_axes.set_title('(A)', fontsize=15)

    xmin = bbox.bounds[0]
    ymin = bbox.bounds[3]
    xmax = bbox.bounds[2]
    ymax = bbox.bounds[1]
    the_axes.plot([xmin + 100, xmin + 200 + 100], [ymax + 90, ymax + 90], marker='.', markersize=12, color='black')
    the_axes.text(xmin + 10 + 100, ymax + 20 + 100, "200m", fontsize=14)

    the_axes = all_ax[1]

    speed_rect_height = 0.5
    ymax = len(track_ids) * speed_rect_height

    the_axes.set_ylim([0, ymax])
    the_axes.set_xlim([0, max_agg_distance])

    yticks = []
    # y2ticks = []
    #
    # reference_speeds = agg_distances[0]

    for i in range(len(track_ids)):

        yticks.append("{0:.2f}".format(frechet_distances[i]))

        track_distances = distances[i]
        track_agg_distances = agg_distances[i]
        track_speeds = speeds[i]

        # dtwdist, dtwarr = fastdtw(np.array(reference_speeds).reshape(-1, 1),
        #                           np.array(track_agg_distances).reshape(-1, 1), dist=euclidean)
        # y2ticks.append("{0:.2f}".format(dtwdist))

        prev_agg_distance = 0
        for j in range(len(track_agg_distances)):
            agg_distance = track_agg_distances[j]

            rectangle = Rectangle(
                (prev_agg_distance, i * speed_rect_height),
                track_distances[j],
                speed_rect_height,
                facecolor=cmap(norm(track_speeds[j]))
            )
            the_axes.add_patch(rectangle)
            prev_agg_distance = agg_distance

    the_axes.set_yticks([(v + speed_rect_height) / 2 for v in range(len(track_ids))])
    the_axes.set_yticklabels(yticks)
    the_axes.set_ylabel('Other tracks  frechet distance [m]', fontsize=13)

    # ax2 = the_axes.twinx()
    # ax2.set_ylabel('Y2 data')
    # ax2.set_yticks([(v + speed_rect_height) / 2 for v in range(len(track_ids))])
    # ax2.set_yticklabels(y2ticks)

    the_axes.set_xlabel('Distance traveled [m]', fontsize=13)
    the_axes.set_title('(B)', fontsize=15)

    ######
    the_axes = all_ax[2]

    the_axes.set_ylim([0, ymax])
    the_axes.set_xlim([0, max_time_interval.seconds])
    yticks = []
    for i in range(len(track_ids)):
        yticks.append("{0:.2f}".format(frechet_distances[i]))
        track_times = times[i]
        track_speeds = speeds[i]

        sum_time_interval = 0
        for j in range(len(track_times) - 1):
            t1 = track_times[j]
            t2 = track_times[j + 1]

            rectangle = Rectangle(
                (sum_time_interval, i * speed_rect_height),
                (t2 - t1).seconds,
                speed_rect_height,
                facecolor=cmap(norm(track_speeds[j]))
            )
            the_axes.add_patch(rectangle)
            sum_time_interval = sum_time_interval + (t2 - t1).seconds

    the_axes.set_yticks([(v + speed_rect_height) / 2 for v in range(len(track_ids))])
    the_axes.set_yticklabels(yticks)

    the_axes.set_ylabel('Other tracks frechet distance [m]', fontsize=13)
    the_axes.set_xlabel('Time elapsed [sec]', fontsize=13)
    the_axes.set_title('(C)', fontsize=15)

    legend_items = [
        mlines.Line2D([], [], color=Colors.gradient_red_blue_9[0], marker='^', markersize=8),
        mlines.Line2D([], [], color=Colors.gradient_red_blue_9[0], marker='s', markersize=8)
    ]

    legend_labels = [
        'Track start',
        'Track end'
    ]

    # all_ax[1].colorbar(label='Some Data')

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=max_speed))
    cbar = fig.colorbar(sm, ax=all_ax[0])
    # cbar.ax.tick_params(labelsize=13)
    cbar.set_label('Speed [km/h]', size=13)

    all_ax[0].legend(
        handles=legend_items,
        labels=legend_labels,
        loc='center left',
        bbox_to_anchor=(-0.5, 0.5),
        labelspacing=0.8,
        frameon=False,
        fontsize='13')

    plt.tight_layout()
    plt.savefig("track_group_speed_comparison.png", bbox_inches='tight', pad_inches=0, dpi=400)
    plt.show()


if __name__ == '__main__':
    # plot('5cd7492744ea8503027ad4de') # ok
    # plot('607a2df93b14785a90ce5af6')  # ok
    # plot('64cf5abdc7e42807e7e7069a')  # best
    # plot('646dc166ca0a730aef445133')  # best
    plot('63948a37ad53a0015a075a94')  # best
