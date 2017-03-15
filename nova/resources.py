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

    def get(self, username):
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

    def get(self, dataset_id, user_id):
        if int(dataset_id) == 0 or int(user_id) == 0:
            return abort(400)

        bookmark = db.session.query(models.Bookmark).\
                 filter(models.Bookmark.user_id == user_id).\
                 filter(models.Bookmark.dataset_id == dataset_id)
        return {'exists' : bookmark.count() == 1}

    def post(self, dataset_id, user_id):
        user = logic.get_user(request.headers['Auth-Token'])
        user_id = int(user_id)

        if user.id != user_id:
            abort(401)

        logic.create_bookmark(dataset_id, user_id)
        return 201

    def delete(self, dataset_id, user_id):
        user = logic.get_user(request.headers['Auth-Token'])
        user_id = int(user_id)

        if user.id != user_id:
            abort(401)

        if not logic.delete_bookmark(dataset_id, user_id):
            abort(404)

        return 200


class Review(Resource):
    method_decorators = [authenticate]

    def get(self, dataset_id, user_id):
        user = logic.get_user(request.headers['Auth-Token'])
        user_id = int(user_id)

        if user.id != user_id:
            abort(401)

        review = logic.get_review(dataset_id, user_id)

        if review:
            return review

        abort(404)

    def put(self, dataset_id, user_id):
        user = logic.get_user(request.headers['Auth-Token'])
        user_id = int(user_id)
        data = request.get_json()
        comment = data['comment']
        rating = data['rating']

        if user.id != user_id:
            abort(401)

        review = logic.get_review(dataset_id, user_id)

        if review['exists']:
            if logic.update_review(dataset_id, user_id, rating, comment):
                return 200

            abort(500, 'Failed to update object')
        else:
            if logic.create_review(dataset_id, user_id, rating, comment):
                return 201
            abort(500, 'Failed to create object')


    def delete(self, dataset_id, user_id):
        user = logic.get_user(request.headers['Auth-Token'])
        user_id = int(user_id)

        if user.id != user_id:
            abort(401)

        if not logic.delete_review(dataset_id, user_id):
            abort(404)

        return 200

class Reviews(Resource):
    method_decorators = [authenticate]

    def get(self, dataset_id):
        user = logic.get_user(request.headers['Auth-Token'])

        if int(dataset_id) == 0:
            abort(400, 'Malformed syntax')

        reviews = db.session.query(models.Review).\
                 filter(models.Review.dataset_id == dataset_id)
        number = reviews.count()
        total = 0
        data = []
        i_reviewed = False;

        for review in reviews:
            total += review.rating
            current_i_review = False

            if review.user == user:
                i_reviewed = True
                current_i_review = True

            data.append(dict(sender_name=review.user.name,
                             sender_url=url_for('profile', name=review.user.name),
                             rating=review.rating, comment=review.comment,
                             dataset_id=dataset_id, user_id=review.user.id,
                             created_at=str(review.created_at),
                             editable=current_i_review, id=review.id))

        average = total / float(number) if number > 0 else 0
        return {'count': number, 'avg_rating': average, 'data': data, 'self_reviewed': i_reviewed}


class Notifications(Resource):
    method_decorators = [authenticate]

    def get(self):
        user = logic.get_user(request.headers['Auth-Token'])
        notifications = db.session.query(models.Notification).\
            filter(models.Notification.user_id == user.id).\
            all()

        return {'notifications': [n.to_dict() for n in notifications]}

    def patch(self):
        payload = request.get_json()

        if 'ids' not in payload:
            abort(400, message="ids not specified")

        ids = payload['ids']
        db.session.query(models.Notification).\
            filter(models.Notification.id.in_(payload['ids'])).\
            delete(synchronize_session=False)
        db.session.commit()

        return 200


class Notification(Resource):
    method_decorators = [authenticate]

    def delete(self, notification_id):
        user = logic.get_user(request.headers['Auth-Token'])
        notification = db.session.query(models.Notification).\
            filter(models.Notification.id == notification_id).\
            filter(models.Notification.user_id == user.id).\
            first()

        if notification:
            db.session.delete(notification)
            db.session.commit()

        return 200
