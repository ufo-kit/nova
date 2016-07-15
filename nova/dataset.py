import os
import re
import json


def parent_path(parent):
    chain = [os.path.join(s, '.nova') for s in parent.split('/') if s]
    return os.path.join(*chain) if chain else ''


class Dataset(object):
    def __init__(self, path, name, parent, owner):
        self.path = path
        self.name = name
        self.parent = parent
        self.owner = owner

    def commit(self):
        path = os.path.join(self.path, parent_path(self.parent), self.name, '.nova')
        os.makedirs(path)

        with open(os.path.join(path, 'metadata.json'), 'w') as fp:
            json.dump(dict(name=self.name, owner=self.owner.uid, parent=self.parent), fp)


# def load_dataset(metadata_path):


class Control(object):
    def __init__(self, user_control, path='.'):
        self.user_control = user_control
        self.path = os.path.abspath(path)

        for root, dirs, files in os.walk(self.path):
            if '.nova' in dirs:
                print root, dirs, files

    def find_dataset(self, name, parent):
        chain = [os.path.join(s, '.nova') for s in parent.split('/') if s]
        chain = os.path.join(*chain) if chain else ''
        d = os.path.join(self.path, chain, name, '.nova', 'metadata.json')

        # if os.path.exists(d):
        #     return load_dataset(
        # print d

    def create_dataset(self, name, parent, owner):
        owner_uid = int(owner) if owner.isdigit() else None
        owner_name = owner if not owner.isdigit() else None
        result = self.user_control.find_user(name=owner_name, uid=owner_uid)
        
        if not result:
            raise Exception("Owner {} not found".format(owner))

        owner = result[0][1]

        # Check if name is valid filename
        if not re.match(r'^[A-Za-z0-9\.\[\]\(\)\+]+$', name):
            raise Exception("{} is not a valid dataset".format(name))

        # Check if dataset already exists
        if self.find_dataset(name, parent):
            raise Exception("{} already exists".format(name))

        dataset = Dataset(self.path, name, parent, owner)
        dataset.commit()
        # path = os.path.join(self.path, parent, '.nova', name, '.nova')
        # print path
        # os.makedirs(path)
