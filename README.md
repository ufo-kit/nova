## Installation

1. Install Flask and dependencies

        $ pip install -r requirements

2. Install the `nova` binary

        $ python setup.py install

3. Install frontend dependencies

        $ bower install

4. Create database and initial admin user

        $ python manage.py initdb --name john --fullname "John Doe" --email "jd@jd.com"

5. Run the server

        $ python manage.py runserver

If you run from source make sure to upgrade the database with

    $ python manage.py db upgrade
