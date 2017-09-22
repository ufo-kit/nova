import os
import jinja2
from flask import Flask
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_restful import Api
from celery import Celery
from elasticsearch import Elasticsearch
from nova.fs import Filesystem

__version__ = '0.1.0'

app = Flask(__name__)
app.secret_key = 'KU5bF1K4ZQdjHSg91bJGnAkStAeEDIAg'

app.config.from_object('nova.settings')
app.config.from_envvar('NOVA_SETTINGS')

if not 'NOVA_ROOT_PATH' in app.config:
    raise RuntimeError("'NOVA_ROOT_PATH' is not set in the configuration file.")

app.config['NOVA_FS_LAYOUT'] = jinja2.Template('{{ root }}/{{ user }}/{{ dataset }}')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.config['NOVA_ROOT_PATH'], 'nova.db')



@app.template_filter('group')
def group(l, n):
    for i in range(0, len(l), n):
        yield tuple(l[i:i+n])


db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

fs = Filesystem(app)

migrate = Migrate(app, db)

celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])

es = Elasticsearch()

if not app.config['DEBUG'] and not es.ping():
    raise RuntimeError("Cannot connect to Elastisearch, please start or "
                       "provide correct connection details")

import nova.models

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

admin = Admin(app)
admin.add_view(AdminModelView(nova.models.User, db.session))
admin.add_view(AdminModelView(nova.models.Collection, db.session))
admin.add_view(AdminModelView(nova.models.Dataset, db.session))
admin.add_view(AdminModelView(nova.models.Permission, db.session))
admin.add_view(AdminModelView(nova.models.Notification, db.session))
admin.add_view(AdminModelView(nova.models.Review, db.session))
admin.add_view(AdminModelView(nova.models.Bookmark, db.session))
admin.add_view(AdminModelView(nova.models.AccessRequest, db.session))
admin.add_view(AdminModelView(nova.models.DirectAccess, db.session))


from nova import resources

errors = {
    'BadSignature': {
        'message': "Token signature could not be verified",
        'status': 409,
    }
}

api = Api(app, errors=errors)
api.add_resource(resources.Groups, '/api/groups')
api.add_resource(resources.Group, '/api/groups/<group_id>')
api.add_resource(resources.Datasets, '/api/datasets')
api.add_resource(resources.Dataset, '/api/datasets/<owner>/<dataset>')
api.add_resource(resources.DeriveDataset, '/api/datasets/<owner>/<dataset>/derive')
api.add_resource(resources.Data, '/api/datasets/<owner>/<dataset>/data')
api.add_resource(resources.Bookmarks, '/api/datasets/<owner>/<dataset>/bookmarks')
api.add_resource(resources.Reviews, '/api/datasets/<owner>/<dataset>/reviews')
api.add_resource(resources.Permission, '/api/datasets/<owner>/<dataset>/permissions')
api.add_resource(resources.AccessRequest, '/api/datasets/<owner>/<dataset>/request')
api.add_resource(resources.DirectAccess, '/api/datasets/<owner>/<dataset>/request/<request_id>')
api.add_resource(resources.Search, '/api/search')
api.add_resource(resources.UserBookmarks, '/api/user/<username>/bookmarks')
api.add_resource(resources.Notifications, '/api/notifications')
api.add_resource(resources.Notification, '/api/notification/<notification_id>')
api.add_resource(resources.Connections, '/api/user/<user_id>/connections')
api.add_resource(resources.Connection, '/api/connection/<from_id>/<to_id>/<option>')
api.add_resource(resources.Services, '/api/services')
api.add_resource(resources.Service, '/api/service/<name>')

import nova.views

