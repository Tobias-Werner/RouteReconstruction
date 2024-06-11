from postgis import *
from model import *

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def do():
    engine = get_engine()

    logging.info("Drop tables")
    Processing.metadata.drop_all(engine)

    logging.info("Create tables")
    Processing.metadata.create_all(engine)


if __name__ == "__main__":
    do()
