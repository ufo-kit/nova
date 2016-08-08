import datetime
import hashlib
from nova import db
from sqlalchemy_utils import PasswordType, force_auto_coercion
from itsdangerous import Signer, BadSignature


force_auto_coercion()


class User(db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    email = db.Column(db.String)
    fullname = db.Column(db.String)
    is_admin = db.Column(db.Boolean, default=False)
    password = db.Column(PasswordType(
        schemes=['pbkdf2_sha512'],
        pbkdf2_sha512__default_rounds=50000,
        pbkdf2_sha512__salt_size=16),
        nullable=False)
    token = db.Column(db.String)
    token_time = db.Column(db.DateTime)
    gravatar = db.Column(db.String)
    first_time = db.Column(db.Boolean, default=True)

    def __init__(self, name=None, fullname=None, email=None, password=None, is_admin=False):
        self.name = name
        self.fullname = fullname
        self.email = email
        self.password = password
        self.is_admin = is_admin
        self.gravatar = hashlib.md5(email.lower()).hexdigest()
        self.token = None

    def __repr__(self):
        return '<User(name={}, fullname={}>'.format(self.name, self.fullname)

    def get_signer(self):
        return Signer(self.password.hash + self.token_time.isoformat())

    def generate_token(self):
        self.token_time = datetime.datetime.utcnow()
        self.token = self.get_signer().sign(str(self.id))
        db.session.commit()

    def is_token_valid(self, token):
        try:
            if str(self.id) != self.get_signer().unsign(token):
                return False
        except BadSignature:
            return False

        return True

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        False

    def get_id(self):
        return self.name


class Dataset(db.Model):

    __tablename__ = 'datasets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    path = db.Column(db.String)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    closed = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=True)

    parent = db.relationship('Dataset')

    def __repr__(self):
        return '<Dataset(name={}, path={}>'.format(self.name, self.path)


class Access(db.Model):

    __tablename__ = 'accesses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'))

    owner = db.Column(db.Boolean)
    writable = db.Column(db.Boolean)
    seen = db.Column(db.Boolean, default=False)

    user = db.relationship('User')
    dataset = db.relationship('Dataset')

    def __repr__(self):
        return '<Access(user={}, dataset={}, owner={}, writable={}>'.format(self.user.name, self.dataset.name, self.owner, self.writable)


class Deletion(db.Model):

    __tablename__ = 'deletions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    dataset_name = db.Column(db.String)

    user = db.relationship('User')

    def __repr__(self):
        return '<Deletion(user={}, dataset={})>'.format(self.user.name, self.dataset_name)
