import os
import datetime
import hashlib
import shutil
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


def get_user(token):
    uid = int(token.split('.')[0])
    return db.session.query(models.User).filter(models.User.id == uid).first()


def check_token(token):
    uid, signature = token.split('.')
    user = get_user(token)

    if not user.is_token_valid(token):
        abort(401)

    return user


def copy(dataset, parent):
    def copytree(src, dst, symlinks=False, ignore=None):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                copytree(s, d, symlinks, ignore)
            else:
                if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                    shutil.copy2(s, d)

    root = app.config['NOVA_ROOT_PATH']
    src = os.path.join(root, parent.path)
    dst = os.path.join(root, dataset.path)
    app.logger.info("Copy data from {} to {}".format(src, dst))
    copytree(src, dst)
