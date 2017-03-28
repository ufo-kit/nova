import os
import requests
import shutil
import subprocess
import shlex
from celery import Celery
from nova import celery, utils, db, models

URL = 'http://127.0.0.1:5000/api/datasets'


def create_dataset(token, parent_id, name):
    # TODO: refactor out with code from nova client
    headers = {'Auth-Token': token}
    data = dict(name=name, parent=parent_id)
    return requests.post(URL, headers=headers, data=data).json()


def get_dataset_info(token, dataset_id):
    headers = {'Auth-Token': token}
    return requests.get('{}/{}'.format(URL, dataset_id), headers=headers).json()


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
def reconstruct(token, result_id, parent_id, flats, darks, projections, outname):
    src = get_dataset_info(token, parent_id)
    dst = get_dataset_info(token, result_id)

    cmd = ('tofu tomo'
           ' --projections "{input}/{projections}/" '
           ' --darks "{input}/{darks}/"'
           ' --flats "{input}/{flats}/"'
           ' --output "{output}/{outname}"')

    cmd = cmd.format(input=src['path'], output=dst['path'], projections=projections,
                     darks=darks, flats=flats, outname=outname)

    args = shlex.split(cmd)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    print stdout, stderr
    proc.wait()

    cmd = ('ufo-launch'
           ' read path="{output}/" !'
           ' rescale width=128 height=128 !'
           ' map-slice number=256 !'
           ' write filename="{output}/.slicemaps/sm-128-128-2048-2048.jpg"')

    cmd = cmd.format(output=dst['path'])

    args = shlex.split(cmd)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    print stdout, stderr
    proc.wait()

    dataset = db.session.query(models.Dataset).\
        filter(models.Dataset.id == result_id).first()

    message = '{cname} / {dname} is ready.'.format(cname=dataset.collection.name, dname=dataset.name)

    notification = models.Notification(message=message, user=dataset.collection.user)

    db.session.add(notification)
    db.session.commit()
