import os
import humanize
import jinja2
from flask import Flask
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_restful import Api
from celery import Celery
from nova.fs import Filesystem

__version__ = '0.1.0'

app = Flask(__name__)
app.secret_key = 'KU5bF1K4ZQdjHSg91bJGnAkStAeEDIAg'

app.config['DEBUG'] = True
app.config['NOVA_ROOT_PATH'] = '/home/vogelgesang/tmp/nova'
app.config['NOVA_FS_LAYOUT'] = jinja2.Template('{{ root }}/{{ user }}/{{ dataset }}')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.config['NOVA_ROOT_PATH'], 'nova.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['CELERY_BROKER_URL'] = 'amqp://guest@localhost//'


@app.template_filter('naturaltime')
def naturaltime(t):
    return humanize.naturaltime(t)


@app.template_filter('naturalsize')
def naturalsize(s):
    return humanize.naturalsize(int(s))


db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

fs = Filesystem(app)

migrate = Migrate(app, db)

celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])


from nova.models import (User, Dataset, Access, Deletion, Taxon, Order, Family,
        Genus, SampleScan)

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

admin = Admin(app)
admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Dataset, db.session))
admin.add_view(AdminModelView(Access, db.session))
admin.add_view(AdminModelView(Deletion, db.session))
admin.add_view(AdminModelView(Taxon, db.session))
admin.add_view(AdminModelView(Order, db.session))
admin.add_view(AdminModelView(Family, db.session))
admin.add_view(AdminModelView(Genus, db.session))
admin.add_view(AdminModelView(SampleScan, db.session))


from nova.resources import Datasets, Dataset

errors = {
    'BadSignature': {
        'message': "Token signature could not be verified",
        'status': 409,
    },
}

api = Api(app, errors=errors)
api.add_resource(Datasets, '/api/datasets')
api.add_resource(Dataset, '/api/datasets/<dataset_id>')


import nova.views
