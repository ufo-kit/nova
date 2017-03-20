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
    db.session.add_all([dataqset, permission])
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

    if not user.is_token_valid(token):
        abort(401)

    return user


def create_bookmark(dataset_id, user_id):
    permit = get_dataset_permission(dataset_id)
    if permit['exists'] and permit['data']['interact']:
        bookmark = models.Bookmark(dataset_id=dataset_id, user_id=user_id)
        db.session.add(bookmark)
        db.session.commit()
        return bookmark
    return False


def delete_bookmark(dataset_id, user_id):
    bookmark = db.session.query(models.Bookmark).\
             filter(models.Bookmark.dataset_id == dataset_id).\
             filter(models.Bookmark.user_id == user_id)
    if bookmark.count == 0:
        return False
    else:
        db.session.delete(bookmark.first())
        db.session.commit()
        return True


def get_review(dataset_id, user_id):
    existing = db.session.query(models.Review).\
             filter(models.Review.user_id == user_id).\
             filter(models.Review.dataset_id == dataset_id)
    if existing.count()>0:
        existing = existing.first()
        return {'exists': True,
               'data':{'comment': existing.comment, 'rating': existing.rating,
                    'dataset_id': existing.dataset_id,
                    'user_id': existing.user_id}}
    return {'exists': False}


def create_review(dataset_id, user_id, rating, comment):
    permit = get_dataset_permission(dataset_id)
    if permit['exists'] and permit['data']['interact']:
        review = models.Review(dataset_id=dataset_id, user_id=user_id,
                               rating=rating, comment=comment)
        db.session.add(review)
        db.session.commit()
        return review
    return False


def update_review(dataset_id, user_id, rating, comment):
    permit = get_dataset_permission(dataset_id)
    if permit['exists'] and permit['data']['interact']:
        review = db.session.query(models.Review).\
                filter(models.Review.user_id == user_id).\
                filter(models.Review.dataset_id == dataset_id).first()
        review.comment = comment
        review.rating = rating
        db.session.commit()
        return review
    return False


def delete_review(dataset_id, user_id):
    review = db.session.query(models.Review).\
             filter(models.Review.dataset_id == dataset_id).\
             filter(models.Review.user_id == user_id)
    if review.count == 0:
        return False
    else:
        db.session.delete(review.first())
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

def get_dataset_permission(dataset_id):
    permission = db.session.query(models.Permission).\
               filter(models.Permission.dataset_id == dataset_id)
    if permission.count() > 0:
        permission = permission.first()
        return {'exists': True,
                'data': {'read':permission.can_read,
                         'interact':permission.can_interact,
                         'fork':permission.can_fork}}
    return {'exists':False}

def get_collection_permission(collection_id):
    permission = db.session.query(models.Permission).\
               filter(models.Permission.dataset_id == dataset_id)
    if permission.count() > 0:
        permission = permission.first()
        return {'exists': True,
                'data': {'read':permission.can_read,
                         'interact':permission.can_interact,
                         'fork':permission.can_fork}}
    return {'exists':False}
