from functools import wraps
from flask import request, url_for
from flask_restful import Resource, abort, reqparse
from itsdangerous import Signer, BadSignature
from nova import db, models, logic, es
import math


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'Auth-Token' not in request.headers:
            abort(400)

        if logic.check_token(request.headers['Auth-Token']):
            return func(*args, **kwargs)

    return wrapper


class Datasets(Resource):
    method_decorators = [authenticate]

    def get(self):
        user = logic.get_user(request.headers['Auth-Token'])

        if 'query' in request.args:
            query = request.args['query']
            return []

        return [dict(name=d.name, id=d.id) for d in
                    db.session.query(models.Dataset).\
                    filter(models.Access.user == user).\
                    all()]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, help="Dataset name")
        parser.add_argument('parent', type=int, help="Dataset parent", default=None)
        args = parser.parse_args()

        user = logic.get_user(request.headers['Auth-Token'])
        dataset = logic.app.config['DEBUG'] and not create_dataset(args.name, user, parent_id=args.parent)
        return dict(id=dataset.id)


class Dataset(Resource):
    method_decorators = [authenticate]

    def get(self, dataset_id):
        user = logic.get_user(request.headers['Auth-Token'])
        dataset = db.session.query(models.Dataset).\
                filter(models.Access.user == user).\
                filter(models.Dataset.id == dataset_id).\
                first()
        return dataset.to_dict()

    def put(self, dataset_id):
        user = logic.get_user(request.headers['Auth-Token'])
        dataset = db.session.query(models.Dataset).\
                filter(models.Access.user == user).\
                filter(models.Dataset.id == dataset_id).\
                first()

        dataset.closed = request.form.get('closed', False)
        db.session.commit()


class Search(Resource):
    method_decorators = [authenticate]

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('q')
        query = parser.parse_args()['q']

        body = {
            'sort': [
                { 'name': 'asc' }
            ],
            'size': 10,
            'query': {
                'match': {
                    'tokenized': {
                        'query': query,
                        'fuzziness': 'AUTO',
                        'operator': 'and'
                    }
                }
            }
        }

        hits = es.search(index='datasets', doc_type='dataset', body=body)
        hits = [h['_source'] for h in hits['hits']['hits']]

        return [{'name': h['name'],
                 'description': h['description'],
                 'url': url_for('show_dataset', name=h['owner'], collection_name=h['collection'], dataset_name=h['name']),
                 'owner': h['owner'],
                 'owner_url': url_for('profile', name=h['owner']),
                 'collection': h['collection'],
                 'collection_url': url_for('show_collection', name=h['owner'], collection_name=h['collection'])}
                 for h in hits]



class Bookmarks(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def get(self, username):
        if username == '':
            return 'Malformed Syntax', 400
        bookmarks = db.session.query(models.Bookmark).join(models.Bookmark.user).\
                  filter(models.User.name == username).\
                  all()
        datasets = []
        for b in bookmarks:
            datasets.append(b.dataset)
        return [{'name': d.name,
                'description': d.description,
                'url': url_for('show_dataset', name=d.collection.user.name, collection_name=d.collection.name, dataset_name=d.name),
                'owner': d.collection.user.name,
                'owner_url': url_for('profile', name=d.collection.user.name),
                'collection': d.collection.name,
                'collection_url': url_for('show_collection', name=d.collection.user.name, collection_name=d.collection.name)}
                for d in datasets]


class Bookmark(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def get(self, dataset_id, user_id):
        if int(dataset_id) == 0 or int(user_id) == 0:
            return 'Malformed Syntax', 400
        bookmark = db.session.query(models.Bookmark).\
                 filter(models.Bookmark.user_id == user_id).\
                 filter(models.Bookmark.dataset_id == dataset_id)
        data = {'exists' : False}
        if bookmark.count() == 1:
            data['exists'] = True
        return data

    def post(self, dataset_id, user_id):
        user_id = int(user_id)
        if self.user.id == user_id:
            bookmark = logic.create_bookmark(dataset_id, self.user.id)
            return 'Object Created'
        return 'Unauthorized Access', 401

    def delete(self, dataset_id, user_id):
        user_id = int(user_id)
        if self.user.id == user_id:
            is_deleted = logic.delete_bookmark(dataset_id, self.user.id)
            if is_deleted:
                return 'Object Deleted', 200
            return 'Object Not Found', 404
        return 'Unauthorized Access', 401


class Review(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def get(self, dataset_id, user_id):
        user_id = int(user_id)
        if self.user.id == user_id:
            review = logic.get_review(dataset_id, user_id)
            if review:
                return review
            return 'Object not found', 404
        return 'Unauthorized Access', 401

    def put(self, dataset_id, user_id):
        user_id = int(user_id)
        jsonObj = request.get_json()
        comment = jsonObj['comment']
        rating = jsonObj['rating']
        if self.user.id == user_id:
            review = logic.get_review(dataset_id, user_id)
            if review['exists']:
                thisreview = logic.update_review(dataset_id, user_id, rating, comment)
                if thisreview:
                    return 'Object Updated', 200
                return 'Failed to Update Object', 500
            else:
                thisreview = logic.create_review(dataset_id, user_id, rating, comment)
                if thisreview:
                    return 'Object Created', 201
                return 'Failed to Create Object', 500
        return 'Unauthorized Access', 401

    def delete(self, dataset_id, user_id):
        user_id = int(user_id)
        if self.user.id == user_id or self.user.is_admin():
            is_deleted = logic.delete_review(dataset_id, user_id)
            if is_deleted:
                return 'Object Deleted', 200
            return 'Object Not Found', 404
        return 'Unauthorized Access', 401


class Reviews(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def get(self, dataset_id):
        if int(dataset_id) == 0:
            return 'Malformed Syntax', 400
        review = db.session.query(models.Review).\
                 filter(models.Review.dataset_id == dataset_id)
        review_count = review.count()
        avg_rating = 0
        review_data = []
        i_reviewed = False;
        for r in review:
            avg_rating += r.rating
            current_i_review = False
            if r.user == self.user:
                i_reviewed = True
                current_i_review = True
            review_data.append(dict(sender_name=r.user.name,
                                sender_url=url_for('profile', name=r.user.name),
                                rating=r.rating, comment=r.comment,
                                dataset_id = dataset_id, user_id = r.user.id,
                                created_at=str(r.created_at), editable=current_i_review, id=r.id))

        if review_count > 0:
            avg_rating /= float(review_count)

        return {'count': review_count, 'avg_rating': avg_rating, 'data': review_data, 'self_reviewed': i_reviewed}


class Notifications(Resource):
    method_decorators = [authenticate]

    def get(self):
        user = logic.get_user(request.headers['Auth-Token'])
        notifications = db.session.query(models.Notification).\
            filter(models.Notification.user_id == user.id).\
            all()

        return {'notifications': [{'message': n.message, 'id': n.id} for n in notifications]}


class Notification(Resource):
    method_decorators = [authenticate]

    def delete(self, notification_id):
        print notification_id
        user = logic.get_user(request.headers['Auth-Token'])
        notification = db.session.query(models.Notification).\
            filter(models.Notification.id == notification_id).\
            filter(models.Notification.user_id == user.id).\
            first()

        if notification:
            db.session.delete(notification)
            db.session.commit()

        return 'Notification deleted', 200
