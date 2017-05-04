import os
from flask import abort
from nova import app, db, models


class InvalidTokenFormat(ValueError):

    pass


def create_collection(name, user, description=None):
    collection = models.Collection(name=name, description=description)
    permission = models.Permission(owner=user, collection=collection)
    db.session.add_all([collection, permission])
    db.session.commit()
    return collection


def create_dataset(dtype, name, user, collection, **kwargs):
    # TODO: merge functionality with import_dataset
    root = app.config['NOVA_ROOT_PATH']
    path = os.path.join(root, user.name, collection.name, name)

    dataset = dtype(name=name, path=path, collection=collection, **kwargs)
    abspath = os.path.join(root, path)
    os.makedirs(abspath)

    permission = models.Permission(owner=user, dataset=dataset, can_read=True,
                                   can_interact=True, can_fork=False)
    db.session.add_all([dataset, permission])
    db.session.commit()
    return dataset


def import_sample_scan(name, user, path, description=None):
    collection = models.Collection(name=name, description=description)
    dataset = models.SampleScan(name=name, path=path, collection=collection,
            genus=None, family=None, order=None)
    collection_permission = models.Permission(owner=user, collection=collection,
                                              can_read=True, can_interact=True,
                                              can_fork=False)
    dataset_permission = models.Permission(owner=user, dataset=dataset,
                                           can_read=True, can_interact=True,
                                           can_fork=False)
    db.session.add_all([collection, dataset, collection_permission,
                       dataset_permission])
    db.session.commit()
    return dataset


def get_user(token):
    if not '.' in token:
        raise InvalidTokenFormat("No '.' in the token")

    parts = token.split('.')

    if len(parts) != 2:
        raise InvalidTokenFormat("Token cannot be separated")

    try:
        uid = int(parts[0])
    except ValueError as e:
        raise InvalidTokenFormat(str(e))

    return db.session.query(models.User).filter(models.User.id == uid).first()


def check_token(token):
    uid, signature = token.split('.')
    try:
        user = get_user(token)
    except InvalidTokenFormat as e:
        abort(400)

    if user is None:
        abort(401, "Unknown user")

    if not user.is_token_valid(token):
        abort(401)

    return user


def get_owner_id_from_permission(object_type, object_id):
    pr = db.session.query(models.Permission)
    if object_type == 'collections':
        pr = pr.filter(models.Permission.collection_id == object_id)
    elif object_type == 'datasets':
        pr = pr.filter(models.Permission.dataset_id == object_id)
    owner_id = pr.first().owner_id
    return owner_id

def get_access_request(object_type, object_id, user_id):
    existing = db.session.query(models.AccessRequest).\
             filter(models.AccessRequest.user_id == user_id)
    if object_type == 'datasets':
        existing = existing.filter(models.AccessRequest.dataset_id == object_id)
    elif object_type == 'collections':
        existing = existing.filter(models.AccessRequest.collection_id == object_id)
    if existing.count()>0:
        existing = existing.first()
        return {'exists': True,
               'data':{'message': existing.message, 'can_read': existing.can_read,
                    'can_interact': existing.can_interact, 'can_fork': existing.can_fork,
                    'dataset_id': existing.dataset_id, 'collection_id': existing.collection_id,
                    'user_id': existing.user_id}}
    return {'exists': False}


def create_access_request(object_type, object_id, user_id, permissions, message):
    access_request = models.AccessRequest(user_id=user_id, message=message,
                   can_read=permissions['read'],
                   can_interact=permissions['interact'],
                   can_fork=permissions['fork'])
    if object_type == 'collections':
        access_request.collection_id = object_id
    elif object_type == 'datasets':
        access_request.dataset_id=object_id
    db.session.add(access_request)
    db.session.commit()
    return access_request


def update_access_request(object_type, object_id, user_id, permissions, message):
    access_request = db.session.query(models.AccessRequest).\
                   filter(models.AccessRequest.user_id == user_id)
    if object_type == 'datasets':
        access_request = access_request.\
                       filter(models.AccessRequest.dataset_id == object_id)
    elif object_type == 'collections':
        access_request = access_request.\
                       filter(models.AccessRequest.collection_id == object_id)
    access_request = access_request.first()
    access_request.message = message
    access_request.can_read=permissions['read']
    access_request.can_interact=permissions['interact']
    access_request.can_fork=permissions['fork']
    db.session.commit()
    return access_request

def delete_access_request(object_type, object_id, user_id):
    access_request = db.session.query(models.AccessRequest).\
                   filter(models.AccessRequest.user_id == user_id)
    if object_type == 'datasets':
        access_request = access_request.\
                       filter(models.AccessRequest.dataset_id == object_id)
    elif object_type == 'collections':
        access_request = access_request.\
                       filter(models.AccessRequest.collection_id == object_id)
    if access_request.count() == 0:
        return False
    else:
        db.session.delete(access_request.first())
        db.session.commit()
        return True




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


def get_direct_access(object_type, object_id, user_id):
    access = db.session.query(models.DirectAccess).\
        filter(models.DirectAccess.user_id == user_id)
    if object_type == 'collections':
        access = access.filter(models.DirectAccess.collection_id == object_id)
    elif object_type == 'datasets':
        access = access.filter(models.DirectAccess.dataset_id == object_id)
    access = access.first()
    if access:
        return { 'exists': True }
    return {'exists': False }

def create_direct_access(object_type, object_id, user_id, permissions):
    direct_access = models.DirectAccess(user_id=user_id,
                  can_read=permissions['read'],
                  can_interact=permissions['interact'],
                  can_fork=permissions['fork'])
    if object_type == 'collections':
        direct_access.collection_id = object_id
    elif object_type == 'datasets':
        direct_access.dataset_id = object_id
    db.session.add(direct_access)
    db.session.commit()

def update_direct_access(object_type, object_id, user_id, permissions):
    access = db.session.query(models.DirectAccess).\
                  filter(models.DirectAccess.user_id == user_id)
    if object_type == 'collections':
        access = access.filter(models.DirectAccess.collection_id == object_id)
    elif object_type == 'datasets':
        access = access.filter(models.DirectAccess.dataset_id == object_id)
    access = access.first()
    access.can_read = permissions['read']
    access.can_interact = permissions['interact']
    access.can_fork = permissions['fork']
    db.session.commit()

def delete_direct_access(object_type, object_id, user_id):
    access = db.session.query(models.DirectAccess).\
                  filter(models.DirectAccess.user_id == user_id)
    if object_type == 'collections':
        access = access.filter(models.DirectAccess.collection_id == object_id)
    elif object_type == 'datasets':
        access = access.filter(models.DirectAccess.dataset_id == object_id)
    access = access.first()
    db.session.delete(access)
    db.session.commit()
