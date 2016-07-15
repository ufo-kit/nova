import os
import io
import datetime
import shutil
from functools import wraps
from nova import app, db, login_manager, fs, logic, memtar
from nova.models import User, Dataset, Access
from flask import (Response, render_template, request, flash, redirect,
                   abort, url_for)
from flask_login import login_user, logout_user, current_user
from flask_wtf import Form
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired
from itsdangerous import Signer


def login_required(admin=False):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()

            if admin and not current_user.is_admin:
                return login_manager.unauthorized()

            return func(*args, **kwargs)
        return decorated_view
    return wrapper


class LoginForm(Form):
    name = StringField('name', validators=[DataRequired()])
    password = StringField('password', validators=[DataRequired()])


class SignupForm(Form):
    name = StringField('name', validators=[DataRequired()])
    fullname = StringField('fullname', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired()])
    password = StringField('password', validators=[DataRequired()])
    is_admin = BooleanField('is_admin')


class CreateForm(Form):
    name = StringField('name', validators=[DataRequired()])


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).filter(User.name == user_id).first()


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = db.session.query(User).filter(User.name == form.name.data).first()

        if user.password == form.password.data:
            login_user(user)

            flash('Logged in successfully')
            return redirect(url_for('index'))
        else:
            return abort(401)

    return render_template('user/login.html', form=form)


@app.route('/logout')
@login_required(admin=False)
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/')
@login_required(admin=False)
def index():
    result = db.session.query(Dataset, Access).\
            filter(Access.user == current_user).\
            filter(Access.dataset_id == Dataset.id).\
            all()

    datasets, accesses = zip(*result) if result else ([], [])

    shared = db.session.query(Dataset, Access).\
            filter(Access.user == current_user).\
            filter(Access.dataset_id == Dataset.id).\
            filter(Access.owner == False).\
            filter(Access.seen == False).\
            all()

    shared, shared_accesses = zip(*shared) if shared else ([], [])

    for access in shared_accesses:
        access.seen = True

    db.session.commit()

    # XXX: we should cache this and compute outside
    num_files, total_size = fs.get_statistics(datasets)
    return render_template('index.html', result=result, shared=shared, num_files=num_files, total_size=total_size)


@app.route('/user/admin')
@login_required(admin=True)
def admin():
    users = db.session.query(User).all()
    return render_template('user/admin.html', users=users)


@app.route('/user/settings')
@login_required(admin=False)
def settings():
    return render_template('user/settings.html')


@app.route('/user/token/generate')
@login_required(admin=False)
def generate_token():
    time = datetime.datetime.utcnow()
    signer = Signer(current_user.password.hash + time.isoformat())
    current_user.token = signer.sign(str(current_user.id))
    current_user.token_time = time
    db.session.commit()
    return redirect(url_for('settings'))


@app.route('/user/token/revoke')
@login_required(admin=False)
def revoke_token():
    current_user.token = None
    db.session.commit()
    return redirect(url_for('settings'))


@app.route('/signup', methods=['GET', 'POST'])
@login_required(admin=True)
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        user = User(name=form.name.data, fullname=form.fullname.data,
                    email=form.email.data, password=form.password.data,
                    is_admin=form.is_admin.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('admin'))

    return render_template('user/signup.html', form=form)


@app.route('/create', methods=['GET', 'POST'])
@login_required(admin=False)
def create():
    form = CreateForm()

    if form.validate_on_submit():
        logic.create_dataset(form.name.data, current_user)
        return redirect(url_for('index'))

    return render_template('dataset/create.html', form=form)


@app.route('/share/<int:dataset_id>')
@app.route('/share/<int:dataset_id>/<int:user_id>')
@login_required(admin=False)
def share(dataset_id, user_id=None):
    if not user_id:
        users = db.session.query(User).filter(User.id != current_user.id).all()
        return render_template('dataset/share.html', users=users, dataset_id=dataset_id)

    user = db.session.query(User).filter(User.id == user_id).first()
    dataset = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()
    access = Access(user=user, dataset=dataset, owner=False, writable=False)
    db.session.add(access)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/process/<int:dataset_id>')
@app.route('/process/<int:dataset_id>/<process>', methods=['GET', 'POST'])
@login_required(admin=False)
def process(dataset_id, process=None):
    processors = {
        'copy': logic.copy
    }

    parent = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not process:
        return render_template('dataset/process.html', dataset=parent)

    dataset = logic.create_dataset(request.form['name'], current_user, parent=parent)
    processors[process](dataset, parent)

    return redirect(url_for('index'))


@app.route('/detail/<int:dataset_id>')
@app.route('/detail/<int:dataset_id>/<path:path>')
@login_required(admin=False)
def detail(dataset_id=None, path=''):
    dataset = db.session.query(Dataset).\
            filter(Dataset.id == dataset_id).\
            filter(Access.user == current_user).\
            filter(Access.dataset_id == dataset_id).first()

    # FIXME: scream if no dataset found
    origin = []
    parent = dataset.parent[0] if dataset.parent else None

    while parent:
        origin.append(parent)
        parent = parent.parent[0] if parent.parent else None

    origin = origin[::-1]

    parts = path.split('/')
    subpaths = []

    for part in parts:
        if subpaths:
            subpaths.append((part, os.path.join(subpaths[-1][1], part)))
        else:
            subpaths.append((part, part))

    dirs = fs.get_dirs(dataset, path)
    files = fs.get_files(dataset, path)
    params = dict(dataset=dataset, path=path, subpaths=subpaths,
                  files=files, dirs=dirs, origin=origin)

    return render_template('dataset/detail.html', **params)


@app.route('/delete/<int:dataset_id>')
@login_required(admin=False)
def delete(dataset_id=None):
    result = db.session.query(Dataset, Access).\
            filter(Access.user == current_user).\
            filter(Access.dataset_id == dataset_id).first()

    dataset, access = result

    if dataset:
        shutil.rmtree(os.path.join(app.config['NOVA_ROOT_PATH'], dataset.path))
        db.session.delete(dataset)
        db.session.delete(access)
        db.session.commit()

    return redirect(url_for('index'))


@app.route('/upload/<int:dataset_id>', methods=['POST'])
def upload(dataset_id):
    user = logic.check_token(request.args.get('token'))
    dataset = db.session.query(Dataset).\
            filter(Access.user == user).\
            filter(Access.dataset_id == dataset_id).\
            filter(Dataset.id == dataset_id).first()

    f = io.BytesIO(request.data)
    memtar.extract_tar(f, os.path.join(app.config['NOVA_ROOT_PATH'], dataset.path))
    return ''


@app.route('/clone/<int:dataset_id>')
def clone(dataset_id):
    user = logic.check_token(request.args.get('token'))
    dataset = db.session.query(Dataset).\
            filter(Access.user == user).\
            filter(Access.dataset_id == dataset_id).\
            filter(Dataset.id == dataset_id).first()

    root = app.config['NOVA_ROOT_PATH']
    path = os.path.join(root, dataset.path)
    fileobj = memtar.create_tar(path)
    fileobj.seek(0)

    def generate():
        while True:
            data = fileobj.read(4096)

            if not data:
                break

            yield data

    return Response(generate(), mimetype='application/gzip')
