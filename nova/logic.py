import os
from flask import abort
from nova import app, db, fs, models


def create_collection(name, user, description=None):
    collection = models.Collection(name=name, description=description)
    permission = models.Permission(owner=user)
    db.session.add_all([collection, permission])
    db.session.commit()
    return collection


def create_group(creator, name, description=None, users=None):
    group = models.Group(name=name, description=description)
    creator_membership = models.Membership(user=creator, group=group, is_creator=True, is_admin = True)
    additions = [group, creator_membership]
    if users:
        for u in users:
            user_object = models.User.query.filter(models.User.name == u).first()
            if user_object:
                membership = models.Membership(user=user_object, group=group)
                additions.append(membership)
    db.session.add_all(additions)
    db.session.commit()


def create_dataset(dtype, name, user, collection, path=None, **kwargs):
    abspath = fs.create_workspace(user, collection, name, path)
    dataset = dtype(name=name, path=abspath, collection=collection, **kwargs)
    permission = models.Permission(owner=user, dataset=dataset, can_read=True,
                                   can_interact=True, can_fork=False)
    db.session.add_all([dataset, permission])
    db.session.commit()
    return dataset


def derive_dataset(dtype, dataset, user, name, path=None, permissions=[True,True,False]):
    root = app.config['NOVA_ROOT_PATH']
    if path is None:
        path = os.path.join(root, dataset.collection.name, name)
        abspath = os.path.join(root, path)
        os.makedirs(abspath)
    else:
        # TODO: verify path
        abspath = os.path.abspath(path)
    derived_dataset = dtype(name=name, path=abspath, collection=dataset.collection, description=dataset.description)
    derivation = models.Derivation(source=dataset, destination=derived_dataset, collection=dataset.collection)
    permission = models.Permission(owner=user, dataset=derived_dataset, can_read=permissions[0],
                                   can_interact=permissions[1], can_fork=permissions[2])
    db.session.add_all([derived_dataset, derivation, permission])
    db.session.commit()
    return derived_dataset


def get_connection(from_id, to_id):
    connection = db.session.query(models.Connection).\
                   filter(models.Connection.from_id == from_id).\
                   filter(models.Connection.to_id == to_id)
    if connection.count() > 0:
        connection = connection.first()
        return {'exists': True,
                'data': {'id':connection.id, 'degree':connection.degree,
                        'from':connection.from_id, 'to': connection.to_id}}
    return {'exists': False}

def create_connection(from_id, to_id):
    connection = models.Connection(from_id=from_id, to_id=to_id)
    db.session.add(connection)
    db.session.commit()
    return connection


def update_connection(from_id, to_id, change):
    connection = db.session.query(models.Connection).\
                   filter(models.Connection.from_id == from_id).\
                   filter(models.Connection.to_id == to_id).first()
    connection.degree += change
    db.session.commit()
    return connection

def increase_connection(from_id, to_id):
    connection = db.session.query(models.Connection).\
                   filter(models.Connection.from_id == from_id).\
                   filter(models.Connection.to_id == to_id)
    if connection.count() > 0:
        connection = connection.first()
        connection.degree += 1
    else:
        connection = models.Connection(from_id=from_id, to_id=to_id)


def decrease_connection(from_id, to_id):
    connection = db.session.query(models.Connection).\
                   filter(models.Connection.from_id == from_id).\
                   filter(models.Connection.to_id == to_id)
    if connection.count() > 0:
        connection = connection.first()
        connection.degree -= 1
    else:
        connection = models.Connection(from_id=from_id, to_id=to_id)
