from functools import wraps
from flask import request, url_for
from flask_restful import Resource, abort, reqparse
from itsdangerous import Signer, BadSignature
from nova import db, models, logic, es
import math

def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if logic.check_token(request.args['token']):
            return func(*args, **kwargs)

    return wrapper


class Datasets(Resource):
    method_decorators = [authenticate]

    def get(self):
        user = logic.get_user(request.args['token'])

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

        user = logic.get_user(request.args['token'])
        dataset = logic.app.config['DEBUG'] and not create_dataset(args.name, user, parent_id=args.parent)
        return dict(id=dataset.id)


class Dataset(Resource):
    method_decorators = [authenticate]

    def get(self, dataset_id):
        user = logic.get_user(request.args['token'])
        dataset = db.session.query(models.Dataset).\
                filter(models.Access.user == user).\
                filter(models.Dataset.id == dataset_id).\
                first()
        return dataset.to_dict()

    def put(self, dataset_id):
        user = logic.get_user(request.args['token'])
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
            'size': 15,
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
        self.user = logic.get_user(request.args['token'])

    def get(self, user_id):
        user_id = int(user_id)
        if user_id == self.user.id or self.user.is_admin():
            bookmarks = db.session.query(models.Bookmark).\
                      filter(models.Bookmark.user_id == user_id).\
                      all()
            datasets = []
            for b in bookmarks:
                datasets.append(b.dataset)
            print datasets
            return [{'name': h.name,
                     'description': h.description,
                     'url': url_for('show_dataset', name=h.collection.user.name, collection_name=h.collection.name, dataset_name=h.name),
                     'owner': h.collection.user.name,
                     'owner_url': url_for('profile', name=h.collection.user.name),
                     'collection': h.collection.name,
                     'collection_url': url_for('show_collection', name=h.collection.user.name, collection_name=h.collection.name)}
                     for h in datasets]
        else:
            return {'access' : False}, 403


class Bookmark(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.args['token'])

    def get(self, dataset_id, user_id):
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

    def delete(self, dataset_id, user_id):
        user_id = int(user_id)
        if self.user.id == user_id:
            is_deleted = logic.delete_bookmark(dataset_id, self.user.id)
            if is_deleted:
                return 'Object Deleted', 200
            else:
                return 'Object Not Found', 404
     	else:
            return 'Access Forbidden', 403


class Review(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.args['token'])

    def get(self, dataset_id):
        review = db.session.query(models.Review).\
                 filter(models.Review.dataset_id == dataset_id)
        review_count = review.count()
        avg_rating = 0
        review_data = []
        if review_count > 0:
            for r in review:
                avg_rating += r.rating
                review_data.append(dict(sender_name=r.user.fullname,
            	                sender_url=url_for('profile', name=r.user.name),
                                rating=r.rating, comment=r.comment, created_at=str(r.created_at)))
            avg_rating /= float(review_count)
        else:
            review_data = 'No reviews yet'
        data = {'count': review_count, 'avg_rating': avg_rating, 'data': review_data}
        return data

    def post(self, dataset_id, user_id, rating, comment):
        user_id = int(user_id)
        if self.user.id == user_id:
        	review = logic.create_review(dataset_id, self.user.id, rating, comment)
        	return 'Object Created'

    def delete(self, dataset_id, user_id):
        user_id = int(user_id)
        if self.user.id == user_id or self.user.is_admin():
            is_deleted = logic.delete_review(dataset_id, self.user.id)
            if is_deleted:
                return 'Object Deleted', 200
            else:
                return 'Object Not Found', 404
     	else:
            return 'Access Forbidden', 403


