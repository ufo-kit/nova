from functools import wraps
from flask import request
from flask_restful import Resource, abort, reqparse
from itsdangerous import Signer, BadSignature
from nova import db, models, logic


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

        return [dict(name=d.name, id=d.id) for d in 
                    db.session.query(models.Dataset).\
                    filter(models.Access.user == user).\
                    all()]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, help="Dataset name")
        args = parser.parse_args()

        user = logic.get_user(request.args['token'])
        dataset = logic.create_dataset(args.name, user)
        return dict(id=dataset.id)


class Dataset(Resource):
    method_decorators = [authenticate]

    def get(self, dataset_id):
        user = logic.get_user(request.args['token'])
        dataset = db.session.query(models.Dataset).\
                filter(models.Access.user == user).\
                filter(models.Dataset.id == dataset_id).\
                first()
        return dict(name=dataset.name)

    def put(self, dataset_id):
        user = get_user()
        dataset = db.session.query(models.Dataset).\
                filter(models.Access.user == user).\
                filter(models.Dataset.id == dataset_id).\
                first()

        dataset.closed = request.form.get('closed', False)
        db.session.commit()
