import json
import math

import requests
import logging
import csv
from datetime import datetime
import dateutil.parser

import geopy.distance

import time
import dotenv
import os
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches
import scipy

import numpy as np
from matplotlib.colors import ListedColormap

from postgis_lib import Postgis


class Track:

    def __init__(self, id=None, begin=None, end=None, length=None, status=None, sensor=None):
        self.id = id
        self.begin = begin
        self.end = end
        self.length = length
        self.status = status
        self.sensor = sensor

    def __eq__(self, other):
        return self.id == other.id


class Measurement:

    def __init__(self, data):
        self.id = data['properties']['id']
        self.time = dateutil.parser.isoparse(data['properties']['time'])
        self.track_id = data['properties']['track']
        self.phenomenons = data['properties']['phenomenons']
        self.x = data['geometry']['coordinates'][0]
        self.y = data['geometry']['coordinates'][1]


class EnviroAPIMeasurementIterator:

    def __init__(self, track_id, delay=0.5):
        self._track_id = track_id
        self._delay = delay

    def __iter__(self):
        self._next_url = "https://envirocar.org/api/stable/tracks/{}/measurements".format(self._track_id)
        self._data = []

        return self

    def __next__(self):

        if len(self._data) == 0:

            if self._next_url is None:
                raise StopIteration

            time.sleep(self._delay)
            logging.info("Do GET: {}".format(self._next_url))
            response = requests.get(self._next_url)
            self._data.extend([Measurement(m) for m in response.json()['features']])

            if 'next' in response.links:
                self._next_url = response.links['next']['url'].replace("http://envirocar.org/",
                                                                       "https://envirocar.org/api/stable/")
            elif 'last' in response.links:
                self._next_url = response.links['last']['url'].replace("http://envirocar.org/",
                                                                       "https://envirocar.org/api/stable/")
            else:
                self._next_url = None

        return self._data.pop()


class EnviroDB:

    def __init__(self, postgis):
        self._postgis = postgis

    def get_tracks_without_measurements(self):
        sql = "SELECT track.id, begin_ts, end_ts, length_km, description, status, sensor FROM track " \
              "LEFT JOIN measurement ON track.id = measurement.track_id " \
              "WHERE measurement.track_id IS NULL;"

        tracks = []

        with self._postgis as postgis:
            postgis.load_sql_string(sql)
            for row in postgis.execute():
                tracks.append(
                    Track(id=row[0], begin=row[1], end=row[2], length=row[3], status=row[4], sensor=row[5])
                )

        return tracks

    def get_tracks(self):
        sql = "SELECT id, begin_ts, end_ts, length_km, description, status, sensor FROM track"

        tracks = []

        with self._postgis as postgis:
            for row in postgis.execute(sql):
                id = row[0]
                begin = row[1]
                end = row[2]
                length = row[3]
                status = row[4]
                sensor = row[5]

                track = Track(id=id, begin=begin, end=end, length=length, status=status, sensor=sensor)
                tracks.append(track)

        return tracks


class EnviroAPITrackIterator:

    def __iter__(self, page_limit=100, page_start=0, delay=0.5):
        self._root_node = requests.get('https://envirocar.org/api/stable').json()
        self._count_tracks = self._root_node['counts']['tracks']
        self._count_processed_tracks = 0
        self._delay = delay
        self._next_url = "{}?limit={}&page={}".format(self._root_node['tracks'], page_limit, page_start)
        self._data = []

        logging.info("{} tracks found".format(self._count_tracks))
        logging.info("{:.0f} queries will be made".format(self._count_tracks / page_limit))

        return self

    def __next__(self):

        if len(self._data) == 0:

            if self._next_url is None:
                raise StopIteration

            time.sleep(self._delay)
            logging.info("Do GET: {}".format(self._next_url))
            response = requests.get(self._next_url)

            for track in response.json()['tracks']:
                id = track['id']
                begin = dateutil.parser.isoparse(track['begin']) if 'begin' in track else None
                end = dateutil.parser.isoparse(track['end']) if 'end' in track else None
                length = track['length'] if 'length' in track else None
                status = track['status'] if 'status' in track else None
                sensor = track['sensor'] if 'sensor' in track else None

                self._data.append(Track(id=id, begin=begin, end=end, length=length, status=status, sensor=sensor))

            if 'next' in response.links:
                self._next_url = response.links['next']['url'].replace("http://envirocar.org/",
                                                                       "https://envirocar.org/api/stable/")
            elif 'last' in response.links:
                self._next_url = response.links['last']['url'].replace("http://envirocar.org/",
                                                                       "https://envirocar.org/api/stable/")
            else:
                self._next_url = None

            self._count_processed_tracks += 1

            if self._count_processed_tracks % 50 == 0:
                logging.info("{:.2f}% processed".format(self._count_processed_tracks / self._count_tracks * 100))

        return self._data.pop()


class Harvester:

    def __init__(self, db):
        self._db = db

    def harvest_tracks(self):
        sql = "SELECT id, begin_ts, end_ts, length_km, description, status, sensor FROM track;"

        remote_tracks = []
        local_missed_tracks = []

        with self._db as conn:
            local_tracks = [
                Track(
                    id=row[0],
                    begin=row[1],
                    end=row[2],
                    length=row[3],
                    status=row[4],
                    sensor=row[5]
                ) for row in conn.load_sql_string(sql).execute()
            ]

        for track in EnviroAPITrackIterator():
            remote_tracks.append(track)

        for remote_track in remote_tracks:
            if remote_track not in local_tracks:  # ToDo when the differ
                local_missed_tracks.append(remote_track)

        logging.info("Missing {} tracks".format(len(local_missed_tracks)))

        sql = "INSERT INTO track(id, begin_ts, end_ts, length_km, description, status, sensor) VALUES(%s,%s,%s,%s,%s,%s,%s)"

        with self._db as conn:
            conn.load_sql_string(sql)
            for track in local_missed_tracks:
                conn.execute(data=(
                    track.id, track.begin, track.end, track.length, "EnviroCar", track.status, json.dumps(track.sensor))
                )

    def harvest_measurements(self, track_id):

        sql = "INSERT INTO measurement(id, time, track_id, phenomenons, geom) VALUES(%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s), 4326))"

        with self._db as conn:
            conn.load_sql_string(sql)
            for measurement in EnviroAPIMeasurementIterator(track_id=track_id):
                conn.execute((
                    measurement.id,
                    measurement.time,
                    measurement.track_id,
                    json.dumps(measurement.phenomenons),
                    measurement.x,
                    measurement.y), commit=False)

            conn.commit()
