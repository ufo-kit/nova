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
admin.add_view(AdminModelView(nova.models.Access, db.session))
admin.add_view(AdminModelView(nova.models.Notification, db.session))
admin.add_view(AdminModelView(nova.models.Process, db.session))
admin.add_view(AdminModelView(nova.models.Reconstruction, db.session))


from nova.resources import (Datasets, Dataset, Search, Bookmarks, Bookmark,
        Reviews, Review, Notifications, Notification, Connections, Connection)

errors = {
    'BadSignature': {
        'message': "Token signature could not be verified",
        'status': 409,
    }
}

api = Api(app, errors=errors)
api.add_resource(Datasets, '/api/datasets')
api.add_resource(Dataset, '/api/datasets/<dataset_id>')
api.add_resource(Search, '/api/search')
api.add_resource(Bookmarks, '/api/user/<username>/bookmarks')
api.add_resource(Bookmark, '/api/user/<user_id>/bookmarks/<dataset_id>')
api.add_resource(Reviews, '/api/datasets/<dataset_id>/reviews')
api.add_resource(Review, '/api/datasets/<dataset_id>/reviews/<user_id>')
api.add_resource(Notifications, '/api/notifications')
api.add_resource(Notification, '/api/notification/<notification_id>')
api.add_resource(Connections, '/api/user/<user_id>/connections')
api.add_resource(Connection, '/api/connection/<from_id>/<to_id>/<option>')
import nova.views
