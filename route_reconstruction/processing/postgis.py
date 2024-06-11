import sqlalchemy
from sqlalchemy.sql import text
import logging
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
from model import *


def clear_table(table):
    logging.info("Clear table {}".format(table.__tablename__))
    with Session(get_engine()) as session:
        session.query(table).delete()
        session.commit()


def read_sql_file(path):
    logging.info("Reading sql {}".format(path))
    sql = open(path, "r").read()

    return text(sql)


def get_session():
    return Session(get_engine())


def get_engine():
    load_dotenv("../.env")

    # logging.info("Creating engine postgresql+psycopg2://{}:XXXXXX@{}:{}/{}".format(os.environ['PGUSER'],
    #                                                                               os.environ['HOSTNAME'],
    #                                                                               5432,
    #                                                                               os.environ['PGDB']))
    url = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
        os.environ['PGUSER'],
        os.environ['PGPASSWORD'],
        os.environ['HOSTNAME'],
        5432,
        os.environ['PGDB']
    )
    return sqlalchemy.create_engine(url)
