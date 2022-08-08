import socket
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from config import Config
from flask_apscheduler import APScheduler
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_principal import Principal, Permission, RoleNeed, identity_loaded, UserNeed
import logging
from logging.handlers import RotatingFileHandler

import os


app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)  # SQL database
migrate = Migrate(app, db, render_as_batch=True)

login = LoginManager(app)
login.login_view = 'login'
bootstrap = Bootstrap(app)  # Style control
scheduler = APScheduler()
mail = Mail(app)
app.add_url_rule("/uploads/<name>", endpoint="download_file", build_only=True)
principals = Principal(app)

from app import routes, models, tasks, errors

celery = tasks.make_celery(app)
ip = (socket.gethostbyname(socket.gethostname()))


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user
    # Add the UserNeed to the identity
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.employee_id))

    # Assuming the User model has a list of roles, update the
    # identity with the roles that the user provides
    if hasattr(current_user, 'role'):
        # for role in current_user.role:
        identity.provides.add(RoleNeed(str(current_user.position)))

    admin_permission = Permission(RoleNeed('admin'))


if not app.debug:
    # ...

    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240,
                                       backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('App startup')