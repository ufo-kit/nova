import sys
import getpass
from nova import app, db
from nova.models import User
from flask_script import Manager, Command, Option
from flask_migrate import MigrateCommand


class InitDatabaseCommand(Command):

    option_list = (
        Option('--name', dest='name', required=True),
        Option('--fullname', dest='fullname', required=True),
        Option('--email', dest='email', required=True),
    )

    def run(self, name, fullname, email):
        password = getpass.getpass("Password: ")
        repeated_password = getpass.getpass("Repeat password: ")

        if password != repeated_password:
            sys.exit("Passwords not matching.")

        db.create_all()
        db.session.add(User(name=name, fullname=fullname, email=email, is_admin=True, password=password))
        db.session.commit()


manager = Manager(app)
manager.add_command('initdb', InitDatabaseCommand)
manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()
