from multiprocessing import Manager
from multiprocess import MultiprocessTask
from postgis import *
from tachograph import *
from tachograph import *

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def do():
    clear_table(TrackAnalysisCorine)
    insert_corine_intersections()


def insert_corine_intersections():
    logging.info("Start inserting corine intersection")

    MultiprocessTask(
        target_function=worker_insert_corine_intersections,
        target_args=[get_cleansed_track_ids()]
    ).start()

    with Session(get_engine()) as session:
        session.execute(read_sql_file('sql/create_corine_intersection_indexes.sql'))
        session.commit()


def worker_insert_corine_intersections(track_ids, worker_id):
    counter = 0

    with Session(get_engine()) as session:
        stmt = read_sql_file('sql/insert_corine_intersection.sql')

        while True:

            try:
                track_id = track_ids.pop()
            except IndexError:
                logging.info("Worker {} stopped regular.".format(worker_id))
                break

            session.execute(stmt, {"track_id": track_id})

            counter += 1
            if counter % 50 == 0:
                logging.info("Worker {} intersected {} tracks with corine".format(worker_id, counter))

        session.commit()


if __name__ == "__main__":
    do()
