import os
import io
import re
from functools import wraps
from nova import (app, db, login_manager, fs, logic, memtar, tasks, models, es,
        users)
from nova.models import (User, Collection, Dataset, SampleScan, Genus, Family,
        Order, Notification, Process, Bookmark, Permission,
        AccessRequest, DirectAccess)
from flask import (Response, render_template, request, flash, redirect,
        url_for, jsonify, send_from_directory, abort)
from flask_login import login_user, logout_user, current_user
from flask_wtf import Form
from flask_sqlalchemy import Pagination
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired
from sqlalchemy import or_, and_


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
    description = StringField('description')


class CreateCollectionForm(Form):
    name = StringField('name', validators=[DataRequired()])
    description = StringField('description')


class RunCommandForm(Form):
    name = StringField('name', validators=[DataRequired()])
    command_line = StringField('command-line', validators=[DataRequired()])
    input = StringField('input', validators=[DataRequired()])
    output = StringField('output', validators=[DataRequired()])


class SearchForm(Form):
    query = StringField('query', validators=[DataRequired()])


class ImportForm(Form):
    path_template = StringField('template', validators=[DataRequired()])


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)

        self.message = message
        self.payload = payload
        self.status_code = status_code or self.status_code

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.errorhandler(404)
def handle_page_not_found(error):
    print error.description
    return render_template('404.html', description=error.description), 404


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
            response = app.make_response(redirect(url_for('index')))
            response.set_cookie('token', user.token)
            return response
        else:
            return render_template('user/login.html', form=form, failed=True), 401

    return render_template('user/login.html', form=form, failed=False)


@app.route('/logout')
@login_required(admin=False)
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/')
@app.route('/<int:page>')
@login_required(admin=False)
def index(page=1):
    if current_user.first_time:
        current_user.first_time = False
        db.session.commit()
        return render_template('index/welcome.html', user=current_user)

    requests = db.session.query(AccessRequest).\
            join(Dataset).\
            join(Permission).\
            filter(Permission.owner == current_user).\
            all()

    return render_template('index/index.html', user=current_user, requests=requests)


@app.route('/settings')
@login_required(admin=True)
def admin():
    users = db.session.query(User).all()
    return render_template('user/admin.html', users=users)


@app.route('/token/generate')
@login_required(admin=False)
def generate_token():
    current_user.generate_token()
    return redirect('user/{}'.format(current_user.name))


@app.route('/token/revoke')
@login_required(admin=False)
def revoke_token():
    current_user.token = None
    db.session.commit()
    return redirect('user/{}'.format(current_user.name))


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
        user.generate_token()
        return redirect(url_for('admin'))

    return render_template('user/signup.html', form=form)


@app.route('/user/<name>')
@app.route('/user/<name>/<int:page>')
@login_required(admin=False)
def profile(name, page=1):
    user = db.session.query(User).filter(User.name == name).first()
    bookmark_count = db.session.query(Bookmark).\
        filter(Bookmark.user == user).count()
    collections_publicperms = Collection.query.join(Permission).\
                            filter(Permission.owner == user).\
                            filter(Permission.can_read == True)

    collections_directaccess = Collection.query.join(DirectAccess).\
                             filter(DirectAccess.user == current_user).\
                             filter(DirectAccess.can_read == True)
    collections = collections_directaccess.union(collections_publicperms)
    pagination = collections.paginate(page=page, per_page=8)
    return render_template('user/profile.html', user=user, pagination=pagination, bookmark_count=bookmark_count)


@app.route('/user/<name>/bookmarks')
def list_bookmarks(name):
    user = db.session.query(User).filter(User.name == name).first()
    return render_template('user/bookmarks.html', user=user)



@app.route('/create/<collection_name>', methods=['GET', 'POST'])
@login_required(admin=False)
def create_dataset(collection_name):
    form = CreateForm()
    collection = Collection.query.join(Permission).\
        filter(Collection.name == collection_name).\
        filter(Permission.owner == current_user).\
        first()

    if form.validate_on_submit():
        logic.create_dataset(models.SampleScan, form.name.data, current_user,
                collection, description=form.description.data)
        return redirect(url_for('index'))

    return render_template('dataset/create.html', form=form, collection=collection)


@app.route('/foo', methods=['GET', 'POST'])
@login_required(admin=False)
def create_collection():
    form = CreateCollectionForm()

    if form.validate_on_submit():
        logic.create_collection(form.name.data, current_user, form.description.data)
        return redirect(url_for('index'))

    return render_template('collection/create.html', form=form)


@app.route('/import', methods=['POST'])
@login_required(admin=False)
def import_submission():
    form = ImportForm()

    # FIXME: again this is not working
    # if form.validate_on_submit():
    #     pass
    template = request.form['template']

    # XXX: incredible danger zone!
    for entry in (e for e in os.listdir(template) if os.path.isdir(os.path.join(template, e))):
        path = os.path.join(template, entry)
        app.logger.info("Importing {}".format(entry))
        logic.import_sample_scan(entry, current_user, path)

    return redirect(url_for('index'))


@app.route('/update', methods=['POST'])
@login_required(admin=False)
def update():
    import csv

    # XXX: more danger zone!
    genuses = {x.name: x for x in db.session.query(Genus).all()}
    families = {x.name: x for x in db.session.query(Family).all()}
    orders = {x.name: x for x in db.session.query(Order).all()}
    scans = {x.name: x for x in db.session.query(SampleScan).all()}

    with open(request.form['csv'], 'rb') as f:
        reader = csv.reader(f)

        for name, _, genus, family, order in reader:
            if name in scans:
                scan = scans[name]

                if genus and not scan.genus:
                    if genus in genuses:
                        scan.genus = genuses[genus]
                    else:
                        g = Genus(name=genus)
                        db.session.add(g)
                        genuses[genus] = g
                        scan.genus = g

                if family and not scan.family:
                    if family in families:
                        scan.family = families[family]
                    else:
                        f = Family(name=family)
                        db.session.add(f)
                        families[family] = f
                        scan.family = f

                if order and not scan.order:
                    if order in orders:
                        scan.order = orders[order]
                    else:
                        o = Order(name=order)
                        db.session.add(o)
                        orders[order] = o
                        scan.order = o

    db.session.commit()
    return redirect(url_for('index'))


@app.route('/close/<int:dataset_id>')
@login_required(admin=False)
def close(dataset_id):
    dataset, permission = db.session.query (Dataset, Permission).\
        filter(Dataset.id == dataset_id).\
        filter(Permission.dataset_id == dataset_id).\
        filter(Permission.owner == current_user)

    if permission.count() > 0:
        dataset.closed = True
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/open/<int:dataset_id>')
@login_required(admin=False)
def open_dataset(dataset_id):
    dataset, permission = db.session.query (Dataset, Permission).\
        filter(Dataset.id == dataset_id).\
        filter(Permission.dataset_id == dataset_id).\
        filter(Permission.owner == current_user)

    if permission.count() > 0:
        dataset.closed = False
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/reindex')
@login_required(admin=True)
def reindex():
    es.indices.delete(index='datasets', ignore=[400, 404])
    es.indices.create(index='datasets')

    # # FIXME: make this a bulk operation
    for permission in Permission.query.filter(Permission.dataset_id != None).all():
        dataset = permission.dataset
        name = dataset.name
        tokenized = name.lower().replace('_', ' ')
        body = dict(name=name, tokenized=tokenized, owner=permission.owner.name,
                    description=dataset.description,
                    collection=dataset.collection.name)
        es.create(index='datasets', doc_type='dataset', body=body)

    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
@login_required(admin=False)
def complete_search():
    # form = SearchForm()
    # XXX: for some reason this does not validate?
    # if form.validate_on_submit():
    #     pass
    query = request.args['q']
    page = 1
    if 'page' in request.args:
        page = int(request.args['page'])
    # XXX: also search in description

    body = {'query': {'match': {'tokenized': {'query': query, 'fuzziness': 'AUTO', 'operator': 'and'}}}}
    hits = es.search(index='datasets', doc_type='dataset', body=body)
    names = [h['_source']['name'] for h in hits['hits']['hits']]

    datasets = Permission.query.join(Dataset).filter(Dataset.name.in_(names)).\
             filter(Permission.can_read == True)
    pagination = datasets.paginate(page=page, per_page=8)

    return render_template('base/search.html', pagination=pagination, query=query)

@app.route('/filter', methods = ['GET'])
@app.route('/filter/<int:page>', methods=['GET'])
def filter(page=1):
    samples = Permission.query.join(SampleScan).\
            filter(Permission.can_read == True)
    search_terms = {x: request.args[x] for x in ('genus', 'family', 'order') if x in request.args}

    # XXX: this is lame, please abstract somehow ...

    if 'genus' in search_terms:
        samples = samples.filter(SampleScan.genus_id == search_terms['genus'])

    if 'family' in search_terms:
        samples = samples.filter(SampleScan.family_id == search_terms['family'])

    if 'order' in search_terms:
        samples = samples.filter(SampleScan.order_id == search_terms['order'])

    pagination = samples.paginate(page=page, per_page=8)
    return render_template('index/filter.html', pagination=pagination, search_terms=search_terms)


@app.route('/share/<int:dataset_id>')
@app.route('/share/<int:dataset_id>/<int:user_id>')
@login_required(admin=False)
def share(dataset_id, user_id=None):
    if not user_id:
        users = db.session.query(User).filter(User.id != current_user.id).all()
        return render_template('dataset/share.html', users=users, dataset_id=dataset_id)

    user = db.session.query(User).filter(User.id == user_id).first()
    dataset, permission = db.session.query(Dataset,Permission).\
        filter(Permission.dataset_id == dataset_id).\
        filter(Permission.owner == user).\
        filter(Dataset.id == dataset_id).first()
    #TODO: Create Direct Access for users
    #if permission is not None:
    return redirect(url_for('index'))


@app.route('/process/<int:dataset_id>', methods=['POST'])
@login_required(admin=False)
def process(dataset_id):
    parent = Dataset.query.filter(Dataset.id == dataset_id).first()
    child = logic.create_dataset(models.Volume, request.form['name'], current_user, parent.collection, slices=request.form['outname'])

    flats = request.form['flats']
    darks = request.form['darks']
    projections = request.form['projections']
    output = request.form['outname']

    result = tasks.reconstruct.delay(current_user.token, child.id, parent.id, flats, darks, projections, output)

    db.session.add(models.Reconstruction(source=parent, destination=child, task_uuid=result.id,
                                         flats=flats, darks=darks, projections=projections, output=output))
    db.session.commit()

    return redirect(url_for('index'))


@app.route('/user/<name>/<collection_name>')
@login_required(admin=False)
def show_collection(name, collection_name):
    collection= Collection.query.\
        filter(Collection.name == collection_name).first()

    permission = Permission.query.\
        filter(Permission.collection == collection).\
        filter(Permission.can_read == True).first()

    if permission is None:
        direct_access = DirectAccess.query.\
                      filter(DirectAccess.collection == collection).\
                      filter(DirectAccess.user == current_user).\
                      filter(DirectAccess.can_read == True).first()
        if direct_access is None:
            return render_template('base/accessrequest.html', access_name='read',
                                   item = {'type':'collection',
                                           'name':collection_name,
                                           'description':collection.description,
                                           'id':collection.id})

    if len(collection.datasets) != 1 or current_user == permission.owner:
        return render_template('collection/list.html', name=name, collection=collection, owner=permission.owner)

    dataset = collection.datasets[0]
    return redirect(url_for('show_dataset', name=name, collection_name=collection_name, dataset_name=dataset.name))


@app.route('/user/<name>/<collection_name>/<dataset_name>')
@app.route('/user/<name>/<collection_name>/<dataset_name>/tree/<path:path>')
@login_required(admin=False)
def show_dataset(name, collection_name, dataset_name, path=''):
    collection = Collection.query.\
        filter(Collection.name == collection_name).first()

    if collection is None:
        abort(404, 'collection {} not found'.format(collection_name))

    dataset = Dataset.query.join(Collection).\
        filter(Collection.name == collection_name).\
        filter(Dataset.name == dataset_name).first()

    if dataset is None:
        abort(404, 'dataset {} not found'.format(dataset_name))

    permission = Permission.query.\
        filter(Permission.dataset == dataset).\
        filter(or_(Permission.can_read == True, Permission.owner==current_user)).\
               first()

    dataset_permissions = {}

    if permission is None:
        direct_access = DirectAccess.query.\
                      filter(DirectAccess.dataset == dataset).\
                      filter(DirectAccess.user == current_user).\
                      filter(DirectAccess.can_read == True).first()
        if direct_access is None:
            return render_template('base/accessrequest.html', access_name='read',
                                   user_name=name,
                                   dataset=dataset, collection=collection,
                                   item={'type':'dataset', 'name':dataset_name,
                                         'description':dataset.description,
                                         'id':dataset.id,})
        dataset_permissions = {'read': direct_access.can_read,
                               'interact': direct_access.can_interact,
                               'fork': direct_access.can_fork}
    else:
        dataset_permissions = {'read': permission.can_read,
                           'interact': permission.can_interact,
                           'fork': permission.can_fork}
    if path:
        filepath = os.path.join(dataset.path, path)

        if os.path.isfile(filepath):
            filename = os.path.basename(filepath)
            directory = os.path.dirname(filepath)

            return send_from_directory(directory, filename)

    # FIXME: check access rights
    # FIXME: scream if no dataset found

    parents = Dataset.query.join(Process.source).\
        filter(Process.destination_id == dataset.id).all()

    children = Dataset.query.join(Process.destination).\
        filter(Process.source_id == dataset.id).all()

    list_files = app.config['NOVA_ENABLE_FILE_LISTING']
    dirs = fs.get_dirs(dataset, path) if list_files else None
    files = sorted(fs.get_files(dataset, path)) if list_files else None

    params = dict(user_name=name, collection=collection, dataset=dataset,
                  parents=parents, children=children, path=path,
                  list_files=list_files, files=files, dirs=dirs, origin=[],
                  permissions=dataset_permissions)

    return render_template('dataset/detail.html', **params)


@app.route('/user/<name>/<collection_name>/<dataset_name>/requests/<int:request_id>')
@login_required(admin=False)
def access_request(name, collection_name, dataset_name, request_id):
    request = db.session.query(AccessRequest).\
       filter(AccessRequest.id == request_id).first()

    if request.dataset_id:
        owner = request.dataset.permissions[0].owner
        item = dict(type='dataset', name=request.dataset.name,
                id=request.dataset.id, description=request.dataset.description,
                url=url_for("show_dataset", name=owner.name,
                    collection_name=request.dataset.collection.name,
                    dataset_name=request.dataset.name))
    else:
        owner = request.collection.permissions[0].owner
        item = dict(type=collection, name=request.collection.name,
                id=request.collection.id, description=request.collection.description,
                url=url_for("show_collection", name=owner.name,
                    collection_name=request.dataset.collection.name))

    if owner == current_user:
        user_collections = db.session.query(Collection).join(Permission).\
                         filter(Permission.owner_id == request.user.id).count()
        return render_template('user/grantaccess.html', dataset=request.dataset, item=item, request=request)

    abort(401)


@app.route('/delete/<int:dataset_id>')
@login_required(admin=False)
def delete(dataset_id=None):
    dataset, permission = db.session.query (Dataset, Permission).\
        filter(Dataset.id == dataset_id).\
        filter(Permission.dataset_id == dataset_id).\
        filter(Permission.owner == current_user)
    #TODO: Add notifications for deletion to bookmarks and forks
    if permission.count () >0:
        dataset = dataset.first()
        path = fs.path_of(dataset)
        process = Process.query.filter(Process.destination_id == dataset_id).first()
        db.session.delete(process)
        db.session.delete(dataset)
        db.session.commit()
        app.logger.info("Would remove {}, however deletion is currently disabled".format(path))
    return redirect(url_for('index'))


@app.route('/upload/<int:dataset_id>', methods=['POST'])
def upload(dataset_id):
    user = users.check_token(request.args.get('token'))
    dataset = db.session.query(Dataset).\
            filter(Permission.owner == user).\
            filter(Permission.dataset_id == dataset_id).\
            filter(Dataset.id == dataset_id).first()

    if dataset is None:
        raise InvalidUsage('Dataset not found', status_code=404)

    if dataset.closed:
        return 'Dataset closed', 423

    f = io.BytesIO(request.data)
    memtar.extract_tar(f, fs.path_of(dataset))
    return ''


@app.route('/clone/<int:dataset_id>')
def clone(dataset_id):
    user = users.check_token(request.args.get('token'))
    dataset = db.session.query(Dataset).\
            filter(Dataset.id == dataset_id).first()
    if dataset is None:
        abort(404, 'Dataset not found')
    permission = db.session.query(Permission).\
            filter(Permission.dataset_id == dataset_id).\
            filter(Permission.can_fork == True)
    if permission.count() == 0:
        permission = db.session.query(Permission).\
            filter(Permission.collection_id == dataset.collection_id).\
            filter(Permission.can_fork == True)

    def generate():
        while True:
            data = fileobj.read(4096)

            if not data:
                break

            yield data
    if permission.count == 0:
        abort(500)
    fileobj = memtar.create_tar(fs.path_of(dataset))
    fileobj.seek(0)
    return Response(generate(), mimetype='application/gzip')
