from multiprocessing import Process
import logging


class MultiprocessTask:

    def __init__(self, target_function, target_args, num_workers=12):
        self._the_function = target_function
        self._target_args = target_args
        self._num_workers = num_workers

    def start(self):
        workers = []

        for worker_id in range(self._num_workers):
            target_args = self._target_args

            worker = Process(target=self._the_function, args=target_args + [worker_id])
            workers.append(worker)
            logging.info("Start worker {}".format(worker_id))
            worker.start()

        for worker in workers:
            worker.join()
