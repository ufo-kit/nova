import os
import datetime
import hashlib
from flask import abort
from nova import app, db, models
from itsdangerous import Signer, BadSignature


def create_dataset(name, user, parent=None):
    root = app.config['NOVA_ROOT_PATH']
    path = hashlib.sha256(user.name + name + str(datetime.datetime.now())).hexdigest()
    dataset = models.Dataset(name=name, path=path, parent=[parent] if parent else [])
    abspath = os.path.join(root, path)
    os.makedirs(abspath)

    access = models.Access(user=user, dataset=dataset, owner=True, writable=True, seen=True)
    db.session.add_all([dataset, access])
    db.session.commit()
    return dataset


def check_token(token):
    uid, signature = token.split('.')
    user = db.session.query(models.User).filter(models.User.id == int(uid)).first()
    signer = Signer(user.password.hash + user.token_time.isoformat())

    try:
        if uid != signer.unsign(token):
            abort(401)
    except BadSignature:
        abort(401)

    return user
