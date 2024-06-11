import argparse
import logging
import dotenv
import enviro_car_lib
from downloader import download_and_unzip
from postgis_lib import Postgis
import os

parser = argparse.ArgumentParser(
    prog='enviro_car',
    description="Interacting with enviroCar API",
    add_help=False
)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
parser.add_argument("task", choices=['dropschema', 'createschema', 'filldb', 'syncdb'])
args = parser.parse_args()

dotenv.load_dotenv('../.env')

db = enviro_car_lib.Postgis(
    host=os.environ['HOSTNAME'],
    db=os.environ['PGDB'],
    user=os.environ['PGUSER'],
    password=os.environ['PGPASSWORD']
)

if str.lower(args.task) == "dropschema":
    logging.info("Start dropping schema")
    with db as conn:
        conn.load_sql("sql/drop_schema.sql").execute()
        logging.info("Dropping schema done")

elif str.lower(args.task) == "createschema":
    logging.info("Start creating schema")
    with db as conn:
        conn.load_sql("sql/create_schema.sql").execute()
        logging.info("Creating schema done")

elif str.lower(args.task) == "filldb":
    logging.info("Start filling database")

    envirocar_backup_url = os.environ['ENVIROCAR_BACKUP_URL']
    envirocar_backup_user = os.environ['ENVIROCAR_BACKUP_USER']
    envirocar_backup_pass = os.environ['ENVIROCAR_BACKUP_PASS']

    download_and_unzip(url=envirocar_backup_url, user=envirocar_backup_user, password=envirocar_backup_pass)

    with db as conn:
        logging.info("Do import tracks to database")
        conn.load_sql("../../tmp/track.sql").execute()

        logging.info("Do import measurements to database")
        conn.execute_file_lines("../../tmp/measurement.sql")
    logging.info("Filling db done")

elif str.lower(args.task) == "syncdb":
    logging.info("Start fetching (from enviroCar-API) and sync database")

    harvester = enviro_car_lib.Harvester(db)
    harvester.harvest_tracks()

    enviro_db = enviro_car_lib.EnviroDB(db)

    for track in enviro_db.get_tracks_without_measurements():
        logging.info("Fetch track {} ...".format(track.id))
        harvester.harvest_measurements(track_id=track.id)

else:
    logging.error("Error while task interpretation")
