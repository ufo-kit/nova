import requests
from celery import Celery
from nova import utils



app = Celery('tasks', broker='amqp://guest@localhost//')


@app.task
def copy(token, name, parent_id):
    url = 'http://127.0.0.1:5000/api/datasets'
    params = dict(token=token)

    # fetch path info about parent and new dataset
    src = requests.get('{}/{}'.format(url, parent_id), params=params).json()

    # TODO: check if parent is not closed yet and error

    # TODO: refactor out with code from nova client
    data = dict(name=name, parent=parent_id)

    # create new dataset
    r = requests.post(url, params=params, data=data)
    result = r.json()

    # check path info of new dataset
    dest = requests.get('{}/{}'.format(url, result['id']), params=params).json()

    # NOTE: we are doing a fast path here and I am not sure if this is really
    # the way to go ...

    utils.copy(src['path'], dest['path'])
