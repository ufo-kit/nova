import os
import re
import codecs
import os.path as op
from setuptools import setup, find_packages

init_path = op.join(op.dirname(__file__), 'nova/__init__.py')
init_content = codecs.open(init_path, encoding='utf-8').read()
__version__, = re.findall(r"__version__\W*=\W*'([^']+)'", init_content)

setup(
    name='nova',
    version=__version__,
    author='Matthias Vogelgesang',
    author_email='matthias.vogelgesang@kit.edu',
    url='http://github.com/ufo-kit/nova',
    license='LGPL',
    packages=find_packages(exclude=['*.tests']),
    scripts=['bin/nova'],
    exclude_package_data={'': ['README.rst']},
    description="NOVA data suite",
    install_requires=[
        'celery',
        'elasticsearch>=2.0.0,<3.0.0',
        'Flask-Admin',
        'Flask-Cache',
        'Flask-Login',
        'Flask-Migrate',
        'flask-restful',
        'Flask-SQLAlchemy',
        'flask-WTF',
        'jinja2',
        'passlib',
        'pyxdg',
        'requests',
        'SQLAlchemy-Utils',
        ],
)
