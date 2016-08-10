===============
Getting started
===============

Installation
============

The NOVA server and tools are written in Python using Flask and Celery. To start
quickly set up a virtual env and install all dependencies with::

    $ pip install -r requirements.txt


First steps
===========

Before starting the server you have to initialize the database with a user that
has administrative rights::

    $ python manage.py initdb --user <name> --fullname <name> --email <mail>

The script will ask for a password twice. Now start the server::

    $ python manage.py runserver

To allow server-side processing you also need to start a Celery instance from
the root directory using::

    $ celery -A nova.tasks worker

Remember that for this work you need to install a broker such as RabbitMQ or
Redis and configure that accordingly.

.. note:: 

    This is a setup for development, for deployment on a productive system ...
    wait for further information.
