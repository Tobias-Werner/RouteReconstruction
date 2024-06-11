from multiprocess import MultiprocessTask
from tachograph import *
import geopandas
from shapely import frechet_distance, hausdorff_distance
from multiprocessing import Manager

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def do_one(track_id):
    manager = Manager()
    track_ids = manager.list([track_id])

    MultiprocessTask(
        target_function=worker_calculate_similarity,
        target_args=[track_ids],
        num_workers=1
    ).start()


def do_all():
    clear_table(TrackAnalysisSimilarity)
    track_ids = get_cleansed_track_ids()

    MultiprocessTask(
        target_function=worker_calculate_similarity,
        target_args=[track_ids],
        num_workers=14
    ).start()


def worker_calculate_similarity(track_ids, worker_id):
    counter = 0

    sql = """
            SELECT t1.track_id, ST_RemoveRepeatedPoints(t1.geom) AS geom
            FROM track_analysis AS t1
            LEFT JOIN track_analysis_exclude AS t2 ON t1.track_id = t2.track_id
            WHERE t2.track_id IS NULL
        """

    df_tracks = geopandas.GeoDataFrame.from_postgis(sql, get_engine())

    with Session(get_engine()) as session:
        while True:
            try:
                track_id = track_ids.pop()

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
                    WHERE t1.track_id=:track_id AND st_distance(t1.geom, t2.geom) < 20;
                """)
                nearby_track_ids = [x for x in session.execute(sql, {"track_id": track_id}).all()]

                selected_geom = df_tracks[df_tracks["track_id"] == track_id].geom.iloc[0]

                for nearby_track_id in nearby_track_ids:
                    nearby_geom = df_tracks[df_tracks["track_id"] == nearby_track_id[0]].geom.iloc[0]
                    hausdorff_dist = hausdorff_distance(selected_geom, nearby_geom)
                    frechet_dist = frechet_distance(selected_geom, nearby_geom)

                    if hausdorff_dist < 300 or frechet_dist < 300:
                        session.add(
                            TrackAnalysisSimilarity(
                                track_id_1=track_id,
                                track_id_2=nearby_track_id[0],
                                hausdorff_distance=hausdorff_dist,
                                frechet_distance=frechet_dist
                            )
                        )
                session.flush()
                session.commit()

                counter = counter + 1
                if counter % 10 == 0:
                    logging.info("Worker {} processed {} tracks".format(worker_id, counter))

            except IndexError:
                logging.info("Worker {} stopped regular".format(worker_id))
                break
            session.query(TrackAnalysis)


if __name__ == '__main__':
    #do_all()
    do_one('63948a37ad53a0015a075a94')
