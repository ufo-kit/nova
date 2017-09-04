import io
import math
import datetime
from functools import wraps
from flask import request, url_for, Response
from flask_restful import Resource, abort, reqparse
from itsdangerous import Signer, BadSignature
from nova import db, models, logic, es, users, memtar, fs, search
from sqlalchemy import desc, func


# TODO: serialize this in the DB?
services = {}


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'Auth-Token' not in request.headers:
            abort(401)

        user = users.check_token(request.headers['Auth-Token'])

        if user is None:
            abort(401)

        return func(*args, user=user, **kwargs)

    return wrapper


def get_dataset_owner(dataset):
    return db.session.query(models.User).\
        filter(models.Dataset.id == dataset.id).\
        first()


class Services(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True)
        parser.add_argument('url', type=str, required=True)
        parser.add_argument('secret', type=str, required=True)
        args = parser.parse_args()

        if args.name in services:
            abort(400, error="Service `{}' already exists".format(args.name))

        services[args.name] = dict(name=args.name, url=args.url)

    def get(self):
        return services.values()


class Service(Resource):
    def delete(self, name):
        parser = reqparse.RequestParser()
        parser.add_argument('secret', type=str, required=True)

        args = parser.parse_args()

        if not name in services:
            abort(400, error="Service `{}' is not registered".format(name))

        del services[name]


class Datasets(Resource):
    method_decorators = [authenticate]

    def get(self, user=None):
        return [d.to_dict() for d in
                    db.session.query(models.Dataset).\
                    filter(models.Permission.can_read).\
                    all()]

    def post(self, user=None):
        def validate_datetime(x):
            return datetime.strptime(x, '%Y-%m-%dT%H:%M:%S')

        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, help="Dataset name")
        parser.add_argument('collection', type=str, help="Collection name")
        parser.add_argument('description', type=str, help="Description")
        parser.add_argument('path', type=str, help="Data path")
        parser.add_argument('created', type=validate_datetime, help="Time of creation")
        args = parser.parse_args()

        collection = db.session.query(models.Collection).\
            filter(models.Collection.name == args.collection).\
            first()

        if collection is None:
            abort(404, error="Collection `{}' does not exist".format(args.collection))

        abspath = fs.create_workspace(user, collection, args.name, args.path)
        dataset = models.Dataset(name=args.name, path=abspath, collection=collection, description=args.description, created=args.created)

        permission = models.Permission(owner=user, dataset=dataset, can_read=True, can_interact=True, can_fork=False)
        db.session.add_all([dataset, permission])
        db.session.commit()
        search.insert(dataset)
        return dict(id=dataset.id)


class Dataset(Resource):
    method_decorators = [authenticate]

    def get(self, collection, dataset, user=None):
        dataset = db.session.query(models.Dataset).\
                filter(models.Dataset.name == dataset).\
                first()

        if dataset is None:
            abort(404)

        return dataset.to_dict()

    def put(self, collection, dataset, user=None):
        dataset = db.session.query(models.Dataset).\
                filter(models.Permission.owner == user).\
                filter(models.Dataset.name == dataset).\
                first()

        dataset.closed = request.form.get('closed', False)
        db.session.commit()

    def patch(self, collection, dataset, user=None):
        payload = request.get_json()

        dataset = db.session.query(models.Dataset).\
                filter(models.Permission.owner == user).\
                filter(models.Dataset.name == dataset).\
                first()

        if dataset is None:
            abort(404, "Dataset does not exist for this user")

        if not 'description' in payload:
            abort(400, "Cannot modify attributes other than description")

        # TODO: sanitize input
        dataset.description = payload['description']
        db.session.commit()


class DeriveDataset(Resource):
    method_decorators = [authenticate]
    def post(self, collection, dataset, user=None):
        payload = request.get_json()
        name = payload['name']
        if not name or name is '':
            abort(401)
        permissions = payload['permissions']
        permission_list = [permissions['read'], permissions['interact'], permissions['fork']]
        dataset = db.session.query(models.Dataset).\
                filter(models.Dataset.name == dataset).first()
        if not dataset:
            abort(404)

        derived_dataset = logic.derive_dataset(models.Dataset, dataset, user,
                                               name, permissions=permission_list)
        search.insert(derived_dataset)
        d = derived_dataset.to_dict()
        return {'url': url_for('show_dataset', collection_name=derived_dataset.collection.name, dataset_name=derived_dataset.name)}, 201

class Data(Resource):
    method_decorators = [authenticate]

    def get(self, collection, dataset, user=None):
        dataset = db.session.query(models.Dataset).\
                filter(models.Permission.owner == user).\
                filter(models.Collection.name == collection).\
                filter(models.Dataset.name == dataset).\
                first()

        if dataset is None:
            abort(404, error="Dataset `{}/{}' does not exist".format(collection, dataset))

        fileobj = memtar.create_tar(fs.path_of(dataset))
        fileobj.seek(0)

        def generate():
            while True:
                data = fileobj.read(4096)

                if not data:
                    break

                yield data

        return Response(generate(), mimetype='application/gzip')

    def post(self, collection, dataset, user=None):
        dataset = db.session.query(models.Dataset).\
                filter(models.Permission.owner == user).\
                filter(models.Dataset.name == dataset).\
                first()

        f = io.BytesIO(request.data)
        memtar.extract_tar(f, fs.path_of(dataset))

class Search(Resource):
    method_decorators = [authenticate]

    def get(self, user=None):
        parser = reqparse.RequestParser()
        parser.add_argument('q')
        query = parser.parse_args()['q']

        if query is None:
            abort(400, error="No query specified.")

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


class UserBookmarks(Resource):
    method_decorators = [authenticate]

    def get(self, username, user=None):
        bookmarks = db.session.query(models.Bookmark).join(models.Bookmark.user).\
                  filter(models.User.name == username).\
                  all()
        datasets = []
        for b in bookmarks:
            datasets.append(b.dataset)
        return [{'name': d.name,
                'description': d.description,
                'url': url_for('show_dataset', name=d.permissions[0].owner.name, collection_name=d.collection.name, dataset_name=d.name),
                'owner': d.permissions[0].owner.name,
                'owner_url': url_for('profile', name=d.permissions[0].owner.name),
                'collection': d.collection.name,
                'collection_url': url_for('show_collection', name=d.permissions[0].owner.name, collection_name=d.collection.name)}
                for d in datasets]


class Bookmarks(Resource):
    method_decorators = [authenticate]

    def get(self, collection_name, dataset_name, user=None):
        bookmark = db.session.query(models.Bookmark).\
                join(models.Dataset).\
                join(models.Collection).\
                join(models.User).\
                filter(models.Collection.name == collection_name).\
                filter(models.Dataset.name == dataset_name).\
                filter(models.Bookmark.user == user).\
                first()
        return bookmark.to_dict() if bookmark else {}

    def post(self, collection_name, dataset_name, user=None):
        if self.get(collection_name, dataset_name, user):
            # bookmark exists already
            return 200

        dataset, permission = db.session.query(models.Dataset, models.Permission).\
                join(models.Collection).\
                filter(models.Collection.name == collection_name).\
                filter(models.Dataset.name == dataset_name).\
                first()

        if not permission.can_interact:
            abort(401)

        bookmark = models.Bookmark(user, dataset)
        db.session.add(bookmark)
        db.session.commit()

        # notify owner
        owner = get_dataset_owner(dataset)

        if owner.id == user.id:
            return 201

        # FIXME: ratelimit bookmarking or DOS attacks become a piece of cake
        message = "{} bookmarked {}/{}".format(user.name, collection_name, dataset_name)
        notification = models.Notification(owner, type='bookmark', message=message)
        db.session.add(notification)
        db.session.commit()

        return 201

    def delete(self, collection_name, dataset_name, user=None):
        dataset, bookmark = db.session.query(models.Dataset, models.Bookmark).\
                join(models.Collection).\
                filter(models.Collection.name == collection_name).\
                filter(models.Dataset.name == dataset_name).\
                first()

        if dataset is None or bookmark is None:
            abort(204)

        db.session.delete(bookmark)
        db.session.commit()

        return 200


class Reviews(Resource):
    method_decorators = [authenticate]

    def put(self, collection_name, dataset_name, user=None):
        data = request.get_json()

        # sanitize this
        comment = data['comment']
        rating = data['rating']

        dataset, permission = db.session.query(models.Dataset, models.Permission).\
                join(models.Collection).\
                filter(models.Collection.name == collection_name).\
                filter(models.Dataset.name == dataset_name).\
                first()

        if not permission.can_interact:
            abort(401)

        review = db.session.query(models.Review).\
                filter(models.Review.user == user).\
                filter(models.Review.dataset == dataset).\
                first()

        if review is None:
            review = models.Review(user, dataset, rating, comment)
            db.session.add(review)
        else:
            review.comment = comment
            review.rating = rating

        db.session.commit()

        owner = get_dataset_owner(dataset)

        if owner.id == user.id:
            return 201

        message = "{} reviewed {}/{}".format(user.name, collection_name, dataset_name)
        notification = models.Notification(owner, type='review', message=message)
        db.session.add(notification)
        db.session.commit()

        return 200

    def delete(self, collection_name, dataset_name, user=None):
        review = db.session.query(models.Review).\
                join(models.Dataset).\
                join(models.Collection).\
                filter(models.Collection.name == collection_name).\
                filter(models.Dataset.name == dataset_name).\
                first()

        if review is None:
            abort(204)

        db.session.delete(review)
        db.session.commit()
        return 200

    def get(self, collection_name, dataset_name, user=None):
        dataset = db.session.query(models.Dataset).\
                join(models.Collection).\
                filter(models.Collection.name == collection_name).\
                filter(models.Dataset.name == dataset_name).\
                first()

        reviews = db.session.query(models.Review).\
                filter(models.Review.dataset == dataset)

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

            data.append(dict(name=review.user.name, url=url_for('profile', name=review.user.name),
                             rating=review.rating, comment=review.comment,
                             created_at=str(review.created_at),
                             editable=current_i_review))

        average = total / float(number) if number > 0 else 0
        return {'count': number, 'rating': average, 'data': data, 'self_reviewed': i_reviewed}


class Notifications(Resource):
    method_decorators = [authenticate]

    def get(self, user=None):
        notifications = db.session.query(models.Notification).\
            filter(models.Notification.user_id == user.id).\
            all()

        return {'notifications': [n.to_dict() for n in notifications]}

    def patch(self, user=None):
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

    def delete(self, notification_id, user=None):
        notification = db.session.query(models.Notification).\
            filter(models.Notification.id == notification_id).\
            filter(models.Notification.user_id == user.id).\
            first()

        if notification:
            db.session.delete(notification)
            db.session.commit()

        return 200


class Connection(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = users.from_token(request.headers['Auth-Token'])

    def get(self, from_id, to_id):
        connection = logic.get_connection(from_id, to_id)
        if connection['exists']:
            return connection
        abort(404, "Connection does not exist")

    def put(self, from_id, to_id, option):
        connection = logic.get_connection(from_id, to_id)
        change = int(option)
        if connection['exists']:
            logic.update_connection(from_id, to_id, change)
            return 'Object Modified', 200
        if increase >= 0:
            connection = logic.create_connection(from_id, to_id)
            if connection:
                return 'Object Created', 201
        abort(500, 'Failed')


class Connections(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = users.from_token(request.headers['Auth-Token'])

    def get(self, query_id):
        connections = db.session.query(models.Connection).\
                    filter(or_(models.Connection.from_id == query_id, models.Connection.to_id == query_id))
        return [{'id': c.id, 'from_user': c.from_id, 'to_user':c.to_id, 'degree':c.degree}
                 for c in connections]


class Activity(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = users.from_token(request.headers['Auth-Token'])

    def get(self, query_id):
        connections = db.session.query(models.Connection).\
                    filter(or_(
                        models.Connection.from_id == query_id,
                        models.Connection.to_id == query_id))
        return [{'id': c.id, 'from_user': c.from_id, 'to_user':c.to_id, 'degree':c.degree}
                 for c in connections]


class AccessRequests(Resource):
    method_decorators = [authenticate]

    def get(self, user=None):
        dataset_access_requests = db.session.query(models.AccessRequest).\
            join(models.Dataset).join(models.Permission).\
            filter(models.Permission.owner == user).\
            filter(models.AccessRequest.dataset_id == models.Permission.dataset_id)

        collection_access_requests = db.session.query(models.AccessRequest).\
            join(models.Collection).join(models.Permission).\
            filter(models.Permission.owner == user).\
            filter(models.AccessRequest.collection_id == models.Permission.collection_id)

        access_requests = dataset_access_requests.union(collection_access_requests).\
                        order_by(desc(models.AccessRequest.created_at)).all()
        return [{'id': ar.id, 'user_id': ar.user_id, 'username': ar.user.name,
                'user_url': url_for('profile', name=ar.user.name),
                'dataset_id':ar.dataset_id, 'collection_id':ar.collection_id,
                'object': {
                    'type':'dataset',
                    'name':ar.dataset.name,
                    'url': url_for('show_dataset', name=user.name, collection_name=ar.dataset.collection.name, dataset_name=ar.dataset.name)
                } if ar.dataset.id else {
                    'type':'collection',
                    'name':ar.collection.name,
                    'url': url_for('show_collection', name=user.name, collection_name=ar.collection.name)
                }, 'options_url': url_for('grant_access', ar_id=ar.id)}
                for ar in access_requests]


class AccessRequest(Resource):
    method_decorators = [authenticate]

    def put(self, collection_name, dataset_name, user=None):
        # XXX: sanitize data ...
        data = request.get_json()
        message = data['message']
        requested = data['permissions']

        dataset, permission = db.session.query(models.Dataset, models.Permission).\
                join(models.Collection).\
                filter(models.Collection.name == collection_name).\
                filter(models.Dataset.name == dataset_name).\
                first()

        owner = get_dataset_owner(dataset)

        existing = db.session.query(models.AccessRequest).\
                filter(models.AccessRequest.user == owner).\
                filter(models.AccessRequest.dataset == dataset).\
                first()

        if existing is None:
            access_request = models.AccessRequest(user=user, dataset=dataset,
                    message=message, can_read=requested['read'],
                    can_interact=requested['interact'],
                    can_fork=requested['fork'])
            db.session.add(access_request)
        else:
            existing.message = message
            existing.can_read = requested['read']
            existing.can_interact = requested['interact']
            existing.can_fork = requested['fork']

        db.session.commit()

        return 200


class Permission(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = user.from_token(request.headers['Auth-Token'])

    def patch(self,  collection_name, dataset_name, user=None):
        permission = db.session.query(models.Permission).\
            join(models.Dataset).\
            join(models.Collection).\
            filter(models.Collection.name == collection_name).\
            filter(models.Dataset.name == dataset_name).\
            first()

        if not permission:
            abort(404, "Permissions do not exist")

        new_permissions = request.get_json()
        permission.can_read = new_permissions['read']
        permission.can_interact = new_permissions['interact']
        permission.can_fork = new_permissions['fork']
        db.session.commit()


class DirectAccess(Resource):
    method_decorators = [authenticate]

    def patch(self, collection_name, dataset_name, request_id, user=None):
        access_request = db.session.query(models.AccessRequest).\
            join(models.Dataset).\
            join(models.Permission).\
            filter(models.Permission.owner == user).\
            filter(models.AccessRequest.id == request_id).\
            first()

        if access_request is None:
            abort(404, "Request does not exists")

        access = db.session.query(models.DirectAccess).\
            filter(models.Collection.name == collection_name).\
            filter(models.Dataset.name == dataset_name).\
            filter(models.DirectAccess.user == access_request.user).\
            first()

        permissions = request.get_json()

        if access is not None:
            access.can_read = permissions['read']
            access.can_interact = permissions['interact']
            access.can_fork = permissions['fork']
        else:
            access = models.DirectAccess(user=user, can_read=permissions['read'],
                    can_interact=permissions['interact'], can_fork=permissions['fork'])
            db.session.add(access)

        message = '{} granted access to {}/{}'.format(user.name, collection_name, dataset_name)
        notification = models.Notification(access_request.user, type='bookmark', message=message)
        db.session.add(notification)
        db.session.delete(access_request)
        db.session.commit()

        return 200

    def delete(self, collection_name, dataset_name, request_id, user=None):
        access_request = db.session.query(models.AccessRequest).\
            join(models.Dataset).\
            join(models.Permission).\
            filter(models.Permission.owner == user).\
            filter(models.AccessRequest.id == request_id).\
            first()

        # notify requester
        if access_request is not None:
            message = '{} denied access to {}/{}'.format(user.name, collection_name, dataset_name)
            notification = models.Notification(access_request.user, type='bookmark', message=message)
            db.session.add(notification)
            db.session.delete(access_request)
            db.session.commit()


class CheckDatasetNameAvailability(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True)
        name = parser.parse_args()['name']
        dataset = db.session.query(models.Dataset).\
            filter(func.lower(models.Dataset.name) == func.lower(name)).first()
        return {'available': dataset == None}, 200
