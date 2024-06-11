import logging

import psycopg2 as pgsql

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


class Postgis:

    def __init__(self, host, db, user, password):
        self._host = host
        self._db = db
        self._user = user
        self._sql = None
        self._password = password
        self._connection = None

    def __enter__(self):
        data = "dbname='{}' user='{}' host='{}' password='{}'".format(self._db, self._user, self._host, self._password)
        self._connection = pgsql.connect(data)
        self._connection.autocommit = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._connection.close()

    def commit(self):
        if self._connection is None:
            raise Exception("DB not connected")
        self._connection.commit()

    def execute_file_lines(self, path):
        file = open(path, "r")

        if self._connection is None:
            raise Exception("DB not connected")

        cursor = self._connection.cursor()

        lines_executed = 0
        for line in file:
            cursor.execute(line)
            lines_executed += 1

            if lines_executed % 100 == 0:
                logging.info("{} lines executed".format(lines_executed))

        self.commit()

    def load_sql_string(self, sql):
        self._sql = sql
        logging.info("Loading {}".format(sql))

        return self

    def load_sql(self, path):
        self._sql = open(path, "r").read()
        logging.info("Loading {}".format(path))

        return self

    def execute(self, data=(), commit=True, silent=False):
        result = None

        # if not silent:
        #    logging.info("Executing {}".format(self._sql))

        if self._connection is None:
            raise Exception("DB not connected")

        cursor = self._connection.cursor()

        cursor.execute(self._sql, data)
        if commit:
            self.commit()

        if cursor.description is not None:
            result = cursor.fetchall()

        return result

    # def execute(self, sql, data=()):
    #     result = None
    #
    #     if self._connection is None:
    #         raise Exception("DB not connected")
    #
    #     cursor = self._connection.cursor()
    #
    #     cursor.execute(sql, data)
    #
    #     if cursor.description is not None:
    #         result = cursor.fetchall()
    #
    #     cursor.close()
    #
    #     return result
