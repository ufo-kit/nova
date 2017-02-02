import os
from flask import abort
from nova import app, db, models


class InvalidTokenFormat(ValueError):

    pass


def create_collection(name, user, description=None):
    collection = models.Collection(name=name, user=user, description=description)
    db.session.add(collection)
    db.session.commit()
    return collection


def create_dataset(dtype, name, user, collection, **kwargs):
    # TODO: merge functionality with import_dataset
    root = app.config['NOVA_ROOT_PATH']
    path = os.path.join(root, user.name, collection.name, name)

    dataset = dtype(name=name, path=path, collection=collection, **kwargs)
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
    bookmark = models.Bookmark(dataset_id=dataset_id, user_id=user_id)
    db.session.add(bookmark)
    db.session.commit()
    return bookmark


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


def create_review(dataset_id, user_id, rating, comment):
    review = models.Review(dataset_id=dataset_id, user_id=user_id, rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()
    return review


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
    
