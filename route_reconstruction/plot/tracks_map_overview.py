import matplotlib.pyplot as plt
from utility import *
from sqlalchemy.orm import Session

breaks = None
number_of_classes = 20


def do_plot():
    fig, the_axes = plt.subplots(1, 1)
    fig.set_figwidth(7)
    fig.set_figheight(7)
    fig.dpi = 400

    with Session(get_engine()) as session:
        plot_germany(the_axes, 'white', "#E2E2E2")

        results = session.query(TrackAnalysis).filter(ST_Contains(Germany.wkb_geometry, TrackAnalysis.geom),
                                                      TrackAnalysis.count_measurements > 1)

        for result in results:
            plot_linestring(the_axes, result.geom, '#2ca25f', linewidth=0.5, z_order=1, with_markers=False)

        the_axes.xaxis.set_visible(False)
        the_axes.yaxis.set_visible(False)
        the_axes.set_aspect('equal', adjustable='box')
        the_axes.set_facecolor("#E2E2E2")

        plt.savefig("tracks_map_overview.png", bbox_inches='tight', pad_inches=0, dpi=500)
        plt.show()


def normalize_value_to_color(value):
    for j in range(len(breaks)):
        if j > 0 and value <= breaks[j]:
            return j / number_of_classes


if __name__ == "__main__":
    do_plot()
