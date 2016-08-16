import os
import requests
import shutil
import subprocess
import shlex
from celery import Celery
from nova import celery, utils

URL = 'http://127.0.0.1:5000/api/datasets'


def create_dataset(token, parent_id, name):
    # TODO: refactor out with code from nova client
    data = dict(name=name, parent=parent_id)
    return requests.post(URL, params=dict(token=token), data=data).json()


def get_dataset_info(token, dataset_id):
    return requests.get('{}/{}'.format(URL, dataset_id), params=dict(token=token)).json()


@celery.task
def copy(token, name, parent_id):
    # fetch path info about parent and new dataset
    src = get_dataset_info(token, parent_id)

    # TODO: check if parent is not closed yet and error
    result = create_dataset(token, parent_id, name)

    # check path info of new dataset
    dst = get_dataset_info(token, result['id'])

    # NOTE: we are doing a fast path here and I am not sure if this is really
    # the way to go ...

    utils.copy(src['path'], dst['path'])


@celery.task
def rmtree(path):
    shutil.rmtree(path)


@celery.task
def run_command(token, name, parent_id, payload):
    # XXX: danger zone ahead ...

    cmd = os.path.join('/usr/bin', payload['command-line'])
    output_data = payload['output']

    src = get_dataset_info(token, parent_id)
    result = create_dataset(token, parent_id, name)
    dst = get_dataset_info(token, result['id'])

    # sanitize data paths, e.g. make directories relative to dataset roots
    input_data = os.path.join(src['path'], payload['input'])
    output_data = os.path.join(dst['path'], payload['output'])

    args = shlex.split(cmd.format(input=input_data, output=output_data))
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    proc.wait()

    # What to do with stdout, stderr, stdin?
    print stdout, stderr

    # create process.json
