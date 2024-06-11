from postgis import *
from model import *
from geoalchemy2.functions import *
from sqlalchemy import func
import logging
from sklearn.cluster import DBSCAN
import numpy as np
from sqlalchemy import and_
from sqlalchemy import desc

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def classify(track_id):
    with Session(get_engine()) as session:
        sql = text("""
        WITH 
        t1 AS (SELECT track_id, st_length(st_transform(geom, 25832)) AS sum_length FROM track_analysis WHERE track_id=:track_id), 
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

        # result_urban_lengths = []
        # result_rural_lengths = []
        # result_class = []

        m1 = np.tan(np.deg2rad(18 * 4))
        m2 = np.tan(np.deg2rad(18 * 3))
        m3 = np.tan(np.deg2rad(18 * 2))
        m4 = np.tan(np.deg2rad(18 * 1))

        row = session.execute(statement=sql, params={'track_id': track_id}).fetchone()

        result_urban_length = row[2] / 1000 if not row[2] is None else 0
        result_rural_length = row[3] / 1000 if not row[3] is None else 0

        if result_urban_length == 0 and result_rural_length == 0:
            logging.error("Missing proportions in track {}".format(row[0]))
            result_class = 0
        elif result_urban_length == 0 and result_rural_length > 0:
            result_class = 1
        elif result_urban_length > 0 and result_rural_length == 0:
            result_class = 5
        else:
            gradient = row[3] / row[2]

            if gradient > m1:
                result_class = 1
            elif gradient > m2:
                result_class = 2
            elif gradient > m3:
                result_class = 3
            elif gradient > m4:
                result_class = 4
            elif gradient < m4 and m4 > 0:
                result_class = 5
            else:
                logging.error("{} has no class now".format(track_id))
                # raise Exception("Gradient failure {}".format(gradient))

    return result_urban_length, result_rural_length, result_class


def do_analysis():
    with Session(get_engine()) as session:
        # m1 = np.tan(np.deg2rad(18 * 4))
        # m2 = np.tan(np.deg2rad(18 * 3))
        # m3 = np.tan(np.deg2rad(18 * 2))
        # m4 = np.tan(np.deg2rad(18 * 1))
        #
        # for row in session.execute(statement=sql):
        #     result_urban_lengths.append(row[2] / 1000 if not row[2] is None else 0)
        #     result_rural_lengths.append(row[3] / 1000 if not row[3] is None else 0)
        #
        #     if result_urban_lengths[-1] == 0 and result_rural_lengths[-1] == 0:
        #         logging.error("Missing proportions in track {}".format(row[0]))
        #         result_class.append(0)
        #     elif result_urban_lengths[-1] == 0 and result_rural_lengths[-1] > 0:
        #         result_class.append(1)
        #     elif result_urban_lengths[-1] > 0 and result_rural_lengths[-1] == 0:
        #         result_class.append(5)
        #     else:
        #         gradient = row[3] / row[2]
        #
        #         if gradient > m1:
        #             result_class.append(1)
        #         elif gradient > m2:
        #             result_class.append(2)
        #         elif gradient > m3:
        #             result_class.append(3)
        #         elif gradient > m4:
        #             result_class.append(4)
        #         elif gradient < m4 and m4 > 0:
        #             result_class.append(5)
        #         else:
        #             raise Exception("Gradient failure {}".format(gradient))

        region_types = []
        shortest_count = []
        fastest_count = []
        both_count = []

        rural_shortest = 0
        semi_rural_shortest = 0
        mixed_shortest = 0
        semi_urban_shortest = 0
        urban_shortest = 0

        rural_fastest = 0
        semi_rural_fastest = 0
        mixed_fastest = 0
        semi_urban_fastest = 0
        urban_fastest = 0

        rural_both = 0
        semi_rural_both = 0
        mixed_both = 0
        semi_urban_both = 0
        urban_both = 0

        track_ids = set(x.track_id for x in session.query(RouteP2PResults).all())
        track_ids = [x for x in track_ids]

        #track_ids = track_ids[0:50]

        logging.info("Track id amount: {}".format(len(track_ids)))

        for i in range(len(track_ids)):
            result_urban_length, result_rural_length, result_class = classify(track_ids[i])
            region_types.append(result_class)

            shortest = session.query(
                RouteP2PResults
            ).filter(
                and_(
                    RouteP2PResults.track_id == track_ids[i],
                    RouteP2PResults.type == 'shortest'
                )
            ).one()

            fastest = session.query(
                RouteP2PResults
            ).filter(
                and_(
                    RouteP2PResults.track_id == track_ids[i],
                    RouteP2PResults.type == 'fastest'
                )
            ).one()

            if shortest.frechet_dist < 50 and fastest.frechet_dist < 50 and abs(
                    shortest.frechet_dist - fastest.frechet_dist) < 0.001:
                if result_class == 1:
                    rural_both += 1
                elif result_class == 2:
                    semi_rural_both += 1
                elif result_class == 3:
                    mixed_both += 1
                elif result_class == 4:
                    semi_urban_both += 1
                elif result_class == 5:
                    urban_both += 1

            elif 50 > shortest.frechet_dist > fastest.frechet_dist:
                if result_class == 1:
                    rural_fastest += 1
                elif result_class == 2:
                    semi_rural_fastest += 1
                elif result_class == 3:
                    mixed_fastest += 1
                elif result_class == 4:
                    semi_urban_fastest += 1
                elif result_class == 5:
                    urban_fastest += 1

            elif 50 > fastest.frechet_dist > shortest.frechet_dist:
                if result_class == 1:
                    rural_shortest += 1
                elif result_class == 2:
                    semi_rural_shortest += 1
                elif result_class == 3:
                    mixed_shortest += 1
                elif result_class == 4:
                    semi_urban_shortest += 1
                elif result_class == 5:
                    urban_shortest += 1

            if i % 10 == 0:
                logging.info(i)
            # else:
            #     logging.error("Fehler {}".format(track_ids[i]))

        logging.info("Sum rural: {}".format(len([x for x in region_types if x == 1])))
        logging.info("Sum semi rural: {}".format(len([x for x in region_types if x == 2])))
        logging.info("Sum mixed rural: {}".format(len([x for x in region_types if x == 3])))
        logging.info("Sum semi urban: {}".format(len([x for x in region_types if x == 4])))
        logging.info("Sum urban: {}".format(len([x for x in region_types if x == 5])))

        logging.info("rural_shortest: {}".format(rural_shortest))
        logging.info("semi_rural_shortest: {}".format(semi_rural_shortest))
        logging.info("mixed_shortest: {}".format(mixed_shortest))
        logging.info("semi_urban_shortest: {}".format(semi_urban_shortest))
        logging.info("urban_shortest: {}".format(urban_shortest))
        logging.info("rural_fastest: {}".format(rural_fastest))
        logging.info("semi_rural_fastest: {}".format(semi_rural_fastest))
        logging.info("mixed_fastest: {}".format(mixed_fastest))
        logging.info("semi_urban_fastest: {}".format(semi_urban_fastest))
        logging.info("urban_fastest: {}".format(urban_fastest))
        logging.info("rural_both: {}".format(rural_both))
        logging.info("semi_rural_both: {}".format(semi_rural_both))
        logging.info("mixed_both: {}".format(mixed_both))
        logging.info("semi_urban_both: {}".format(semi_urban_both))
        logging.info("urban_both: {}".format(urban_both))



        # route_types = [x.type for x in session.query(RouteP2PResults).all()]
        # frechet_distance = [x.frechet_dist for x in session.query(RouteP2PResults).all()]

        # result = session.query(
        #     TrackAnalysisSimilarity.track_id_1,
        #     func.count(TrackAnalysisSimilarity.track_id_2).label("count")
        # ).group_by(
        #     TrackAnalysisSimilarity.track_id_1
        # ).order_by(desc("count")).all()
        #
        # for i in range(10):
        #     print("{} {}".format(result[i].track_id_1, result[i].count))

        # with get_session() as session:
        #     # cnt = session.query(Track).count()
        #     # logging.info("Number of upstream tracks: {}".format(cnt))
        #     #
        #     # cnt = session.query(Measurement).count()
        #     # logging.info("Number of measurements: {}".format(cnt))
        #
        #     result = session.query(TrackAnalysisSimilarity.track_id_1,
        #                            func.count(TrackAnalysisSimilarity.track_id_2)).filter(
        #         TrackAnalysisSimilarity.frechet_distance < 200).group_by(TrackAnalysisSimilarity.track_id_1).order_by(
        #         func.count(TrackAnalysisSimilarity.track_id_2).desc())
        #
        #     for i in range(5):
        #         print(result[i])
        #
        # result = session.query(TrackAnalysisCorine)


if __name__ == "__main__":
    do_analysis()
