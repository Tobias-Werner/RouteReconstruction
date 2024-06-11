import os
import requests
import zipfile
import logging

from urllib.parse import urlparse


def download_and_unzip(url, user, password):
    zip_file_path = download_file(url, user, password)
    target_dir = os.path.dirname(zip_file_path)

    logging.info("Unzipping {} to {}".format(zip_file_path, target_dir))
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
        logging.info("Unzip done")


def download_file(url, user, password):
    target_dir = '../../tmp/'
    filename = os.path.basename(urlparse(url).path)
    logging.info("Downloading {}".format(url))
    r = requests.get(url, auth=(user, password))
    logging.info("HTTP Response is {}".format(r.status_code))
    if r.status_code == 200:
        file_path = target_dir + filename
        logging.info("Start writing file to {}".format(file_path))
        with open(file_path, 'wb') as out:
            out.write(r.content)
            logging.info("Download done")
            return file_path
