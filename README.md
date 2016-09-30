### Server

1. Install Flask and dependencies

        $ pip install -r requirements.txt

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


### Client

1. Log in and generate a token
2. Use the token to initialize a directory

        $ cd path/to/dataset
        $ nova init --token 1.xyz --remote http://localhost:5000

3. Push the data to the remote

        $ nova push
