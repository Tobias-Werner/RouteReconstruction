from postgis import *
from sqlalchemy.orm import Session
from model import *
from sqlalchemy import MetaData, Table
from geoalchemy2.functions import *
from multiprocessing import Manager
import numpy

from multiprocess import MultiprocessTask

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def do():
    clear_table(TrackAnalysisExclude)

    with (Session(get_engine()) as session):
        count_tracks = session.query(Track).count()
        count_tracks_analysed = session.query(TrackAnalysis).count()

        if count_tracks != count_tracks_analysed:
            raise Exception("Not every track is analysed ({}/{})".format(count_tracks, count_tracks_analysed))
        else:
            logging.info("Found {} tracks. Start excluding.".format(count_tracks_analysed))

        metadata = MetaData()
        germany = Table('germany', metadata, autoload_with=get_engine())
        tracks_in_germany = session.query(TrackAnalysis).filter(
            ST_Contains(germany.c.wkb_geometry, TrackAnalysis.geom)
        ).all()

        track_ids_in_germany = [track_in_germany.track_id for track_in_germany in tracks_in_germany]

        manager = Manager()
        tracks_analysed = manager.list(session.query(TrackAnalysis).all())

        MultiprocessTask(target_function=exclude_worker,
                         target_args=[tracks_analysed, track_ids_in_germany]
                         ).start()


def exclude_worker(tracks_analysed, track_ids_in_germany, worker_id):
    with Session(get_engine()) as session:
        counter = 0

        while True:
            try:
                track_analysed = tracks_analysed.pop()
                counter = counter + 1
                if counter % 50 == 0:
                    logging.info("Worker {} processed {} tracks.".format(worker_id, counter))
            except IndexError:
                logging.info("Worker {} stopped regular.".format(worker_id))
                break

            exclude_reasons = []

            measurements = session.query(Measurement).filter_by(track_id=track_analysed.track_id).order_by(
                Measurement.time).all()

            if track_analysed.track_id not in track_ids_in_germany:
                exclude_reasons.append(ExcludeReason.outside_germany)

            if track_analysed.count_measurements != track_analysed.count_speeds:
                exclude_reasons.append(ExcludeReason.missing_speed_attributes)
            else:

                times = numpy.array([numpy.datetime64(measurement.time) for measurement in measurements])
                speeds = numpy.array([measurement.phenomenons['Speed']['value'] for measurement in measurements])
                time_deltas = numpy.diff(times)
                gps_speeds = []

                for i in range(len(measurements) - 1):
                    loc1 = session.scalar(ST_Transform(measurements[i].geom, 25832))
                    loc2 = session.scalar(ST_Transform(measurements[i + 1].geom, 25832))
                    gps_distance = session.scalar(ST_Distance(loc1, loc2))
                    delta_seconds = time_deltas[i].item().seconds
                    if gps_distance is not None and delta_seconds > 0:
                        gps_speeds.append((gps_distance / delta_seconds) * 3.6)

                if numpy.any(numpy.array(gps_speeds) > 240.0):
                    exclude_reasons.append(ExcludeReason.too_fast)
                if max(speeds) < 1.0:
                    exclude_reasons.append(ExcludeReason.not_driving)
                if min(speeds) < 0.0:
                    exclude_reasons.append(ExcludeReason.negative_speed_values)
                if len(times) < 10:
                    exclude_reasons.append(ExcludeReason.less_ten_measurement)
                if len(times) != len(numpy.unique(times)):
                    exclude_reasons.append(ExcludeReason.duplicated_time)
                if numpy.any(time_deltas > numpy.timedelta64(1, 'm')):
                    exclude_reasons.append(ExcludeReason.timedelta_exceeded)

            for exclude_reason in exclude_reasons:
                session.add(
                    TrackAnalysisExclude(
                        track_id=track_analysed.track_id,
                        reason=exclude_reason
                    )
                )

        logging.info("Worker {} commits".format(worker_id))
        session.commit()


if __name__ == "__main__":
    do()
