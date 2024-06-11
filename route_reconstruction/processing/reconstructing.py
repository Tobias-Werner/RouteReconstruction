import logging
import dotenv
import os
from postgis_lib.postgis_lib import Postgis

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def do():
    dotenv.load_dotenv('../.env')

    db = Postgis(
        host=os.environ['HOSTNAME'],
        db=os.environ['PGDB'],
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD']
    )

    drop_schema(db)
    create_schema(db)

    # ToDo: create a short connection from coordinate to existing network

    # track_id: 52624a54e4b000fe05806f94, start id = 31053656
    reconstruct(db, track_id='52624a54e4b000fe05806f94', start_osm_id=31053656)


def drop_schema(db):
    logging.info("Start dropping reconstruction schema")
    with db as conn:
        conn.load_sql('sql/drop_reconstruction_schema.sql')
        conn.execute()
        logging.info("Dropping reconstruction schema done")


def create_schema(db):
    logging.info("Start creating reconstruction schema")
    with db as conn:
        # conn.execute_file('sql/create_reconstruction_schema.sql')
        logging.info("Creating reconstruction schema done")


def reconstruct(db, track_id, start_osm_id):
    pass


if __name__ == '__main__':
    do()
