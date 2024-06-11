import matplotlib.pyplot as plt
import jenkspy
import matplotlib.patches as patches
from matplotlib import colors
from matplotlib.colors import LinearSegmentedColormap
from utility import *

breaks = None
number_of_classes = 20


def get_colormap():
    return LinearSegmentedColormap.from_list(
        "myclrmap",
        [Colors.blue, Colors.turquoise, Colors.green, Colors.yellow],
        N=number_of_classes
    )


def subplot(the_axes):
    global breaks

    plot_germany(the_axes, 'white', Colors.gray)

    with Session(get_engine()) as session:

        sql = "SELECT ST_AsText(st_transform(geom, 25832)), cnt FROM track_density"
        results = session.execute(text(sql)).fetchall()

        polygons = []
        all_counts = []

        for result in results:
            polygon = result[0]
            count = result[1]

            coords = polygon[9:-2].split(',')
            coords.append(coords[0])

            x_coords = [float(coord.split()[0]) for coord in coords]
            y_coords = [float(coord.split()[1]) for coord in coords]

            polygons.append((x_coords, y_coords))
            all_counts.append(count)

        breaks = jenkspy.jenks_breaks(all_counts, n_classes=10)

        for i in range(len(polygons)):
            x_coords = polygons[i][0]
            y_coords = polygons[i][1]

            count = all_counts[i]

            normalized = normalize_value_to_color(count)
            the_axes.fill(x_coords, y_coords, color=get_colormap()(normalized))

        the_axes.xaxis.set_visible(False)
        the_axes.yaxis.set_visible(False)
        the_axes.set_aspect('equal', adjustable='box')

        the_axes.set_facecolor(Colors.gray)


def plot():
    fig, axes = plt.subplots(1, 2)
    fig.set_figwidth(7)
    fig.set_figheight(5)
    fig.dpi = 400

    highlight_y = [5630000, 5710000]
    highlight_x = [270000, 350000]

    with Session(get_engine()) as session:
        sql = """
            CREATE TABLE IF NOT EXISTS track_density AS
            WITH t1 AS (SELECT *
                FROM track_analysis
                INNER JOIN germany ON st_contains(germany.wkb_geometry, st_transform(geom, 25832)))
            SELECT laea_5km.rowid, laea_5km.geom, count(t1.*) AS cnt
            FROM laea_5km
            JOIN t1
                ON st_intersects(
                    st_transform(laea_5km.geom, 25832),
                    st_transform(t1.geom, 25832)
                )
            GROUP BY public.laea_5km.rowid;
        """

        session.execute(text(sql))
        session.commit()

        subplot(axes[0])

        rect = patches.Rectangle((
            highlight_x[0], highlight_y[0]),
            highlight_x[1] - highlight_x[0],
            highlight_y[1] - highlight_y[0],
            linewidth=2,
            edgecolor='r',
            facecolor='none')

        axes[0].add_patch(rect)

        subplot(axes[1])

        cbar_ax = fig.add_axes([0.1, 0.1, 0.8, 0.05])
        norm = colors.BoundaryNorm(breaks, get_colormap().N)
        fig.colorbar(
            plt.cm.ScalarMappable(cmap=get_colormap(), norm=norm),
            cax=cbar_ax,
            orientation="horizontal",
            ticks=breaks,
            label='Amount of tracks'
        )

        axes[1].set_aspect('equal', adjustable='box')

        axes[1].set_ylim(highlight_y)
        axes[1].set_xlim(highlight_x)

        plt.subplots_adjust(left=0.1, bottom=0.2, right=0.9, top=0.9, wspace=0.2, hspace=0.2)
        plt.savefig("tracks_map_overview_density.png", bbox_inches='tight', pad_inches=0, dpi=500)
        plt.show()


def normalize_value_to_color(value):
    for j in range(len(breaks)):
        if j > 0 and value <= breaks[j]:
            return j / number_of_classes


if __name__ == "__main__":
    plot()
