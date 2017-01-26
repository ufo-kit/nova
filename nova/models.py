import os
import datetime
import hashlib
from nova import app, db
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
        return False

    def get_id(self):
        return self.name


class Dataset(db.Model):

    __tablename__ = 'datasets'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))

    name = db.Column(db.String)
    description = db.Column(db.String)
    path = db.Column(db.String)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    closed = db.Column(db.Boolean, default=False)
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'))

    has_thumbnail = db.Column(db.Boolean, default=False)

    collection = db.relationship('Collection')
    accesses = db.relationship('Access', cascade='all, delete, delete-orphan')

    __mapper_args__ = {
        'polymorphic_identity': 'dataset',
        'polymorphic_on': type
    }

    def to_dict(self):
        path = os.path.join(app.config['NOVA_ROOT_PATH'], self.path)
        return dict(name=self.name, path=path, closed=self.closed)

    def __repr__(self):
        return '<Dataset(name={}, path={}>'.format(self.name, self.path)


class Taxon(db.Model):

    __tablename__ = 'taxons'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    def __repr__(self):
        return '<Taxon(name={}>'.format(self.name)


class Order(db.Model):

    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    def __repr__(self):
        return '<Order(name={}>'.format(self.name)


class Family(db.Model):

    __tablename__ = 'families'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    def __repr__(self):
        return '<Family(name={}>'.format(self.name)


class Genus(db.Model):

    __tablename__ = 'genuses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    def __repr__(self):
        return '<Genus(name={}>'.format(self.name)


class SampleScan(Dataset):

    __tablename__ = 'samplescans'

    __mapper_args__ = {
        'polymorphic_identity': 'samplescan'
    }

    id = db.Column(db.Integer, db.ForeignKey('datasets.id'), primary_key=True)

    taxon_id = db.Column(db.Integer, db.ForeignKey('taxons.id'), nullable=True)
    genus_id = db.Column(db.Integer, db.ForeignKey('genuses.id'), nullable=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)

    taxon = db.relationship('Taxon')
    genus = db.relationship('Genus')
    family = db.relationship('Family')
    order = db.relationship('Order')


class Volume(Dataset):

    __tablename__ = 'volumes'

    __mapper_args__ = {
        'polymorphic_identity': 'volume'
    }

    id = db.Column(db.Integer, db.ForeignKey('datasets.id'), primary_key=True)

    slices = db.Column(db.String)


class Access(db.Model):

    __tablename__ = 'accesses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'))

    owner = db.Column(db.Boolean)
    writable = db.Column(db.Boolean)
    seen = db.Column(db.Boolean, default=False)

    user = db.relationship('User')
    dataset = db.relationship('Dataset', back_populates='accesses')

    def __repr__(self):
        return '<Access(user={}, dataset={}, owner={}, writable={}>'.format(self.user.name, self.dataset.name, self.owner, self.writable)


class Collection(db.Model):

    __tablename__ = 'collections'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    name = db.Column(db.String)
    description = db.Column(db.String)
    user = db.relationship('User')
    datasets = db.relationship('Dataset', cascade='all, delete, delete-orphan')

    def __repr__(self):
        return '<Collection(name={})>'.format(self.name)


class Notification(db.Model):

    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    user = db.relationship('User')

    def __repr__(self):
        return '<Notification(user={}, message={})>'.format(self.user.name, self.message)


class Process(db.Model):

    __tablename__ = 'processes'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))

    task_uuid = db.Column(db.String)

    source_id = db.Column(db.Integer, db.ForeignKey('datasets.id'))
    destination_id = db.Column(db.Integer, db.ForeignKey('datasets.id'))

    source = db.relationship('Dataset', foreign_keys=[source_id])
    destination = db.relationship('Dataset', foreign_keys=[destination_id])

    __mapper_args__ = {
        'polymorphic_identity': 'process',
        'polymorphic_on': type
    }

    def __repr__(self):
        return '<Process(src={}, dst={})>'.format(self.source.name, self.destination.name)


class Reconstruction(Process):

    __tablename__ = 'reconstructions'

    __mapper_args__ = {
        'polymorphic_identity': 'reconstruction'
    }

    id = db.Column(db.Integer, db.ForeignKey('processes.id'), primary_key=True)

    flats = db.Column(db.String())
    darks = db.Column(db.String())
    projections = db.Column(db.String())
    output = db.Column(db.String())





class Bookmark(db.Model):
    __tablename__ = 'bookmarks'
    id = db.Column(db.Integer,  primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'))

    user = db.relationship('User', foreign_keys=[user_id])
    dataset = db.relationship('Dataset', foreign_keys=[dataset_id])

    def __init__(self, user_id=None, dataset_id=None):
        self.user_id = user_id
        self.dataset_id = dataset_id

    def __repr__(self):
        return '<Bookmark(user={}, dataset={})>'.format(self.user, self.dataset)


