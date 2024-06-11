import logging
from sqlalchemy.orm import Session
from postgis import *
from model import *
from postgis import read_sql_file, get_engine

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def do():
    clear_table(TrackAnalysis)

    with Session(get_engine()) as session:
        session.execute(read_sql_file('sql/insert_track_analysis.sql'))
        session.execute(read_sql_file('sql/update_count_measurements.sql'))
        session.execute(read_sql_file('sql/update_count_speed.sql'))
        session.execute(read_sql_file('sql/update_count_gpsspeed.sql'))
        session.execute(read_sql_file('sql/update_linestring_from_location.sql'))

        session.commit()


if __name__ == "__main__":
    do()
