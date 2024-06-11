import logging


import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.patches import Patch
from utility import *


def get_data():
    with Session(get_engine()) as session:
        sql = text("""
        WITH 
        t1 AS (SELECT track_id, st_length(st_transform(geom, 25832)) AS sum_length FROM track_analysis), 
        urban AS (SELECT track_id, sum(intersected_length) AS length
               FROM track_analysis_corine
               WHERE corine_class <= 121
               GROUP BY track_id),
        rural AS (SELECT track_id, sum(intersected_length) AS length
               FROM track_analysis_corine
               WHERE corine_class > 121
               GROUP BY track_id)
        SELECT t1.track_id, t1.sum_length, urban.length AS urban_length, rural.length AS rural_length
        FROM t1
            LEFT JOIN urban ON t1.track_id = urban.track_id
            LEFT JOIN rural ON t1.track_id = rural.track_id
            
            ORDER BY t1.sum_length
            """)

        result_urban_lengths = []
        result_rural_lengths = []
        result_class = []

        m1 = np.tan(np.deg2rad(18 * 4))
        m2 = np.tan(np.deg2rad(18 * 3))
        m3 = np.tan(np.deg2rad(18 * 2))
        m4 = np.tan(np.deg2rad(18 * 1))

        for row in session.execute(statement=sql):
            result_urban_lengths.append(row[2] / 1000 if not row[2] is None else 0)
            result_rural_lengths.append(row[3] / 1000 if not row[3] is None else 0)

            if result_urban_lengths[-1] == 0 and result_rural_lengths[-1] == 0:
                logging.error("Missing proportions in track {}".format(row[0]))
                result_class.append(0)
            elif result_urban_lengths[-1] == 0 and result_rural_lengths[-1] > 0:
                result_class.append(1)
            elif result_urban_lengths[-1] > 0 and result_rural_lengths[-1] == 0:
                result_class.append(5)
            else:
                gradient = row[3] / row[2]

                if gradient > m1:
                    result_class.append(1)
                elif gradient > m2:
                    result_class.append(2)
                elif gradient > m3:
                    result_class.append(3)
                elif gradient > m4:
                    result_class.append(4)
                elif gradient < m4 and m4 > 0:
                    result_class.append(5)
                else:
                    raise Exception("Gradient failure {}".format(gradient))

    return result_urban_lengths, result_rural_lengths, result_class


def sub_plot(the_axes, sizes, colors, dataframe, title, ticks):
    the_axes.set_title(title)
    the_axes.set_aspect('equal', adjustable='box')

    the_axes.fill(
        [0, 600, 600, 0],
        [0, 0, 600, 600],
        color=Colors.gradient_turquoise_orange_5[4]
    )
    the_axes.fill(
        [0, np.tan(np.deg2rad(18 * 4)) * 600, 0, 0],
        [0, 600, 600, 0],
        color=Colors.gradient_turquoise_orange_5[3]
    )
    the_axes.fill(
        [0, np.tan(np.deg2rad(18 * 3)) * 600, 0, 0],
        [0, 600, 600, 0],
        color=Colors.gradient_turquoise_orange_5[2]
    )
    the_axes.fill(
        [0, np.tan(np.deg2rad(18 * 2)) * 600, 0, 0],
        [0, 600, 600, 0],
        color=Colors.gradient_turquoise_orange_5[1]
    )
    the_axes.fill(
        [0, np.tan(np.deg2rad(18 * 1)) * 600, 0, 0],
        [0, 600, 600, 0],
        color=Colors.gradient_turquoise_orange_5[0]
    )
    sns.scatterplot(x='Urban', y="Rural", s=sizes, c=colors, edgecolors='none', data=dataframe, ax=the_axes)

    the_axes.set_xlabel('Urban proportion [km]')
    the_axes.set_xticks(ticks)
    the_axes.set_ylabel('Rural proportion [km]')
    the_axes.set_yticks(ticks)
    the_axes.figure.tight_layout()
    the_axes.set_ylim([0, ticks[-1]])
    the_axes.set_xlim([0, ticks[-1]])


def plot():
    fig, axs = plt.subplots(2, 2)
    fig.set_figwidth(5.5)
    fig.set_figheight(6.3)

    sizes = [0.6 for _ in range(len(urban_lengths))]
    colors = ['#111111' for _ in range(len(urban_lengths))]
    df = pd.DataFrame({
        'Urban': urban_lengths,
        'Rural': rural_lengths
    })

    fig.tight_layout()
    plt.tight_layout()

    sub_plot(axs[0, 0], sizes, colors, df, '(A)', (0, 200, 400, 600))
    sub_plot(axs[0, 1], sizes, colors, df, '(B)', (0, 50, 100, 150, 200))
    sub_plot(axs[1, 0], sizes, colors, df, '(C)', (0, 10, 20, 30, 40, 50))
    sub_plot(axs[1, 1], sizes, colors, df, '(D)', (0, 2, 4, 6, 8, 10))

    rest = len(classes) - classes.count(1) - classes.count(2) - classes.count(3) - classes.count(4) - classes.count(5)

    legend_elements = [
        Patch(
            facecolor=Colors.gradient_turquoise_orange_5[0],
            linewidth=0,
            label='Rural [$n_r=' + str(classes.count(1)) + '$]'
        ),
        Patch(
            facecolor=Colors.gradient_turquoise_orange_5[1],
            linewidth=0,
            label='Semi-rural [$n_{sr}=' + str(classes.count(2)) + '$]'
        ),
        Patch(
            facecolor=Colors.gradient_turquoise_orange_5[2],
            linewidth=0,
            label='Mixed [$n_m=' + str(classes.count(3)) + '$]'
        ),
        Patch(
            facecolor=Colors.gradient_turquoise_orange_5[3],
            linewidth=0,
            label='Semi-urban [$n_{su}=' + str(classes.count(4)) + '$]'
        ),
        Patch(
            facecolor=Colors.gradient_turquoise_orange_5[4],
            linewidth=0,
            label='Urban [$n_u=' + str(classes.count(5)) + '$]'
        ),
        Patch(
            facecolor=Colors.white,
            linewidth=0,
            label='Not associated [$n_{na}=' + str(rest) + '$]'
        )
    ]

    fig.subplots_adjust(bottom=0.1)
    axs[1, 0].legend(
        handles=legend_elements,
        loc='lower center',
        bbox_to_anchor=(1.1, -0.65),
        ncol=2,
        labelspacing=0.1,
        frameon=False
    )

    plt.savefig("tracks_proportions_overview.png", bbox_inches='tight', pad_inches=0, dpi=500)
    plt.show(dpi=500)


if __name__ == "__main__":
    urban_lengths, rural_lengths, classes = get_data()
    plot()
