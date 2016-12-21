from functools import wraps
from flask import request, url_for
from flask_restful import Resource, abort, reqparse
from itsdangerous import Signer, BadSignature
from nova import db, models, logic, es


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
        dataset = logic.create_dataset(args.name, user, parent_id=args.parent)
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
