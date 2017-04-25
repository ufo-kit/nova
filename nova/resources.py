from functools import wraps
from flask import request, url_for
from flask_restful import Resource, abort, reqparse
from itsdangerous import Signer, BadSignature
from nova import db, models, logic, es
from sqlalchemy import desc
import math


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'Auth-Token' not in request.headers:
            abort(401)

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
                    filter(models.Permission.can_read).\
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

    def get(self, collection, dataset):
        user = logic.get_user(request.headers['Auth-Token'])
        dataset = db.session.query(models.Dataset).\
                filter(models.Dataset.name == dataset).\
                first()

        if dataset is None:
            abort(404)

        return dataset.to_dict()

    def put(self, collection, dataset):
        user = logic.get_user(request.headers['Auth-Token'])
        dataset = db.session.query(models.Dataset).\
                filter(models.Permission.owner == user).\
                filter(models.Dataset.name == dataset).\
                first()

        dataset.closed = request.form.get('closed', False)
        db.session.commit()

    def patch(self, collection, dataset):
        user = logic.get_user(request.headers['Auth-Token'])
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
                'url': url_for('show_dataset', name=d.permissions[0].owner.name, collection_name=d.collection.name, dataset_name=d.name),
                'owner': d.permissions[0].owner.name,
                'owner_url': url_for('profile', name=d.permissions[0].owner.name),
                'collection': d.collection.name,
                'collection_url': url_for('show_collection', name=d.permissions[0].owner.name, collection_name=d.collection.name)}
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

        # notify owner
        owner = db.session.query(models.User).\
            filter(models.Dataset.id == dataset_id).\
            first()

        if owner.id == user_id:
            return 201

        # FIXME: ratelimit bookmarking or DOS attacks become a piece of cake
        message = "{} bookmarked a dataset".format(user.name)
        notification = models.Notification(owner, type='bookmark', message=message)
        db.session.add(notification)
        db.session.commit()

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
        if review['exists']:
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


class Connection(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

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
        self.user = logic.get_user(request.headers['Auth-Token'])

    def get(self, query_id):
        connections = db.session.query(models.Connection).\
                    filter(or_(models.Connection.from_id == query_id, models.Connection.to_id == query_id))
        return [{'id': c.id, 'from_user': c.from_id, 'to_user':c.to_id, 'degree':c.degree}
                 for c in connections]


class Activity(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def get(self, query_id):
        connections = db.session.query(models.Connection).\
                    filter(or_(
                        models.Connection.from_id == query_id,
                        models.Connection.to_id == query_id))
        return [{'id': c.id, 'from_user': c.from_id, 'to_user':c.to_id, 'degree':c.degree}
                 for c in connections]


class AccessRequests(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def get(self):
        dataset_access_requests = db.session.query(models.AccessRequest).\
            join(models.Dataset).join(models.Permission).\
            filter(models.Permission.owner == self.user).\
            filter(models.AccessRequest.dataset_id == models.Permission.dataset_id)

        collection_access_requests = db.session.query(models.AccessRequest).\
            join(models.Collection).join(models.Permission).\
            filter(models.Permission.owner == self.user).\
            filter(models.AccessRequest.collection_id == models.Permission.collection_id)

        access_requests = dataset_access_requests.union(collection_access_requests).\
                        order_by(desc(models.AccessRequest.created_at)).all()
        return [{'id': ar.id, 'user_id': ar.user_id, 'username': ar.user.name,
                'user_url': url_for('profile', name=ar.user.name),
                'dataset_id':ar.dataset_id, 'collection_id':ar.collection_id,
                'object': {
                    'type':'dataset',
                    'name':ar.dataset.name,
                    'url': url_for('show_dataset', name=self.user.name, collection_name=ar.dataset.collection.name, dataset_name=ar.dataset.name)
                } if ar.dataset.id else {
                    'type':'collection',
                    'name':ar.collection.name,
                    'url': url_for('show_collection', name=self.user.name, collection_name=ar.collection.name)
                }, 'options_url': url_for('grant_access', ar_id=ar.id)}
                for ar in access_requests]


class AccessRequest(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def get(self, user_id, object_id, object_type):
        owner_id = logic.get_owner_id_from_permission(object_type, object_id)
        if user.id == user_id or user.id == owner_id:
            access_request = logic.get_access_request(object_type, object_id, user_id)
            if access_request['exists']:
                return access_request
            abort(404)
        abort(401)


    def put(self, user_id, object_id, object_type):
        user = logic.get_user(request.headers['Auth-Token'])
        data = request.get_json()
        message = data['message']
        permissions = data['permissions']
        owner_id = logic.get_owner_id_from_permission(object_type, object_id)
        if user.id == int(user_id):
            access_request = logic.get_access_request(object_type, object_id, user_id)
            if access_request['exists']:
                if logic.update_access_request(object_type, object_id, user_id, permissions, message):
                    return 200
                abort(500, 'Failed to update object')
            else:
                if logic.create_access_request(object_type, object_id, user_id, permissions, message):
                    return 201
                abort(500, 'Failed to create object')
        abort(401)


    def delete(self, user_id, object_id, object_type):
        user = logic.get_user(request.headers['Auth-Token'])
        owner_id = logic.get_owner_id_from_permission(object_type, object_id)
        if user.id == int(user_id) or user.id == owner_id:
            if not logic.delete_access_request(object_type, object_id, user_id):
                abort(404)
            return 200
        abort(401)


class Permission(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def patch(self, request_id):
        access_request = db.session.query(models.AccessRequest).\
                       filter(models.AccessRequest.id == request_id).first()
        perm = db.session.query(models.Permission).\
             filter(models.Permission.collection_id == access_request.collection_id).\
             filter(models.Permission.dataset_id == access_request.dataset_id).\
             first()
        if perm:
            new_permissions = request.get_json()
            perm.can_read = new_permissions['read']
            perm.can_interact = new_permissions['interact']
            perm.can_fork = new_permissions['fork']
            db.session.commit()
            if access_request.dataset_id:
                logic.delete_access_request('datasets', access_request.dataset_id, access_request.user_id)
            else:
                logic.delete_access_request('collections', access_request.collection_id, access_request.user_id)
            #TODO combine delete access request and patch permission into single transaction
            #TODO issue notification that public permission has been changed
            return 200
        abort(404, "Permissions do not exist")


class DirectAccess(Resource):
    method_decorators = [authenticate]

    def __init__(self):
        self.user = logic.get_user(request.headers['Auth-Token'])

    def put(self, request_id):
        access_request = db.session.query(models.AccessRequest).\
                       filter(models.AccessRequest.id == request_id).first()
        user_id = access_request.user_id
        print("user id is : " + str(user_id))
        if access_request.dataset_id:
            object_type = 'datasets'
            object_id = access_request.dataset_id
        else:
            object_type = 'collections'
            object_id = access_request.collection_id
        data = request.get_json()
        direct_access = logic.get_direct_access(object_type, object_id, user_id)
        #TODO combine delete access request and grant direct access into single transaction
        #TODO issue notification that access has been granted
        if direct_access['exists']:
            direct_access = logic.update_direct_access(object_type, object_id, user_id, data)
            logic.delete_access_request(object_type, object_id, user_id)
            return 201
        direct_access = logic.create_direct_access(object_type, object_id, user_id, data)
        logic.delete_access_request(object_type, object_id, user_id)
        return 200



