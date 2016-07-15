import os
import json
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Dataset



DB_NAME = 'nova.db'


def database_uri(path='.'):
    return 'sqlite:///{}'.format(os.path.join(os.path.abspath(path), DB_NAME))


class Control(object):
    def __init__(self, path='.'):
        self.path = os.path.abspath(path)
        self.engine = create_engine(database_uri(path))
        self.session_factory = sessionmaker(bind=self.engine)
        self.session = self.session_factory()

    def create_dataset(self, user, name, parent=None):
        if parent:
            parent = self.session.query(Dataset).filter(Dataset.name == parent).first()

        path = hashlib.sha256(user.name + name).hexdigest()
        dataset = Dataset(name=name, owner=user, path=path, parent=[parent])
        abspath = os.path.join(self.path, path)
        os.makedirs(abspath)

