import os
from flask import abort
from nova import app, db, models


def dataset_path(user_name, dataset_name):
    data = dict(root=app.config['NOVA_ROOT_PATH'], user=user_name, dataset=dataset_name)
    return app.config['NOVA_FS_LAYOUT'].render(**data)


def create_collection(name, user, description=None):
    collection = models.Collection(name=name, user=user, description=description)
    db.session.add(collection)
    db.session.commit()
    return collection


def create_dataset(name, user, description=None):
    # TODO: merge functionality with import_dataset
    root = app.config['NOVA_ROOT_PATH']
    path = dataset_path(user.name, name)
    dataset = models.Dataset(name=name, path=path, description=description)
    abspath = os.path.join(root, path)
    os.makedirs(abspath)

    access = models.Access(user=user, dataset=dataset, owner=True, writable=True, seen=True)
    db.session.add_all([dataset, access])
    db.session.commit()
    return dataset


def import_sample_scan(name, user, path, description=None):
    collection = models.Collection(user=user, name=name, description=description)
    dataset = models.SampleScan(name=name, path=path, collection=collection,
            genus=None, family=None, order=None)
    access = models.Access(user=user, dataset=dataset, owner=True, writable=True, seen=True)
    db.session.add_all([collection, dataset, access])
    db.session.commit()
    return dataset


def get_user(token):
    uid = int(token.split('.')[0])
    return db.session.query(models.User).filter(models.User.id == uid).first()


def check_token(token):
    uid, signature = token.split('.')
    user = get_user(token)

    if not user.is_token_valid(token):
        abort(401)

    return user
