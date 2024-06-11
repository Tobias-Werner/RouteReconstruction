import math
import numpy
import scipy
from postgis import *
from sqlalchemy.orm import Session
from multiprocessing import Manager
from multiprocess import MultiprocessTask
from model import *
from tachograph import *

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')


def do():
    clear_table(SimTachographEnvirocar)
    track_ids = get_cleansed_track_ids()
    interpolate_measurements(track_ids)


def interpolate_measurements(track_ids):
    logging.info("Interpolating measurements for {} tracks".format(len(track_ids)))

    MultiprocessTask(
        target_function=worker_interpolate_measurements,
        target_args=[track_ids],
        num_workers=12
    ).start()


def worker_interpolate_measurements(track_ids, worker_id):
    counter = 0

    with Session(get_engine()) as session:

        while True:
            try:
                track_id = track_ids.pop()
            except IndexError:
                break

            measurements = session.query(Measurement).filter_by(track_id=track_id).order_by(
                Measurement.time).all()

            times = numpy.array([numpy.datetime64(measurement.time) for measurement in measurements])
            speeds = numpy.array([measurement.phenomenons['Speed']['value'] for measurement in measurements])

            interpolator = scipy.interpolate.PchipInterpolator(times, speeds)

            interpolated_times = []
            interpolated_speeds = []

            current_evaluation_time = times[0]

            while current_evaluation_time <= times[-1]:
                interpolated_speed = math.floor(interpolator(current_evaluation_time).flat[0])

                if len(interpolated_speeds) == 0 or interpolated_speeds[-1] != interpolated_speed:
                    interpolated_speeds.append(interpolated_speed)
                    interpolated_times.append(current_evaluation_time)

                current_evaluation_time += numpy.timedelta64(1, 's')

                if interpolated_speeds[-1] == -1:
                    logging.info("Correcting speed {} to 0. Prev: {} {} {}".format(interpolated_speeds[-1],
                                                                                   interpolated_speeds[-2],
                                                                                   interpolated_speeds[-3],
                                                                                   interpolated_speeds[-4]))
                    interpolated_speeds[-1] = 0

            aggregated_distance = 0
            prev_timestamp = None
            distance = 0

            for i in range(len(interpolated_times)):
                if i > 0:
                    time_delta_sec = (interpolated_times[i] - prev_timestamp).item().total_seconds()
                    distance = time_delta_sec * (interpolated_speeds[i] / 3.6)
                    aggregated_distance = aggregated_distance + distance

                session.add(
                    SimTachographEnvirocar(
                        time=interpolated_times[i].astype(datetime),
                        speed=interpolated_speeds[i],
                        track_id=track_id,
                        distance=distance,
                        agg_distance=aggregated_distance
                    )
                )

                prev_timestamp = interpolated_times[i]

            session.commit()

            counter = counter + 1
            if counter % 10 == 0:
                logging.info("Worker {} stored {} interpolated track".format(worker_id, counter))

        logging.info("Worker {} finished".format(worker_id))


if __name__ == "__main__":
    do()
