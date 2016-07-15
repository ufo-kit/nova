import os
from nova import __version__
from setuptools import setup, find_packages



setup(
    name='nova',
    version=__version__,
    author='Matthias Vogelgesang',
    author_email='matthias.vogelgesang@kit.edu',
    url='http://github.com/ufo-kit/nova',
    license='LGPL',
    packages=find_packages(exclude=['*.tests']),
    scripts=['bin/novactl', 'bin/nova'],
    exclude_package_data={'': ['README.rst']},
    description="NOVA data suite",
    install_requires=[
        'passlib',
        'sqlalchemy>=0.11',
        ],
    # long_description=open('README.rst').read(),
)
