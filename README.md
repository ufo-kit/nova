### Server

1. Install nova and its dependencies

        $ python setup.py install

2. Install frontend dependencies

        $ bower install

3. Edit the default configuration and store the location

        $ cp nova.cfg.example nova.cfg
        $ export NOVA_SETTINGS=$(pwd)/nova.cfg

4. Create database and initial admin user

        $ python manage.py initdb --name john --fullname "John Doe" --email "jd@jd.com"

5. Run the server

        $ python manage.py runserver

If you run from source make sure to upgrade the database with when pulling

    $ python manage.py db upgrade


### Dependencies

All Python dependencies are listed in the `setup.py`. Full-text search requires
a running [ElasticSearch](https://www.elastic.co) server (2.4.3 on Ubuntu
16.04). Moreover, to be able to view thumbnails and 3D client visualization of
synchrotron imaging data, you will have to run the
[nova-thumbnail-server](https://github.com/ufo-kit/nova-wave-server/) and
[nova-wave-server](https://github.com/ufo-kit/nova-thumbnail-server) and make
them accessible by this server process.
