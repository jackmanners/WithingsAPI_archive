import os
from os.path import exists

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = 'SECRET KEY'
    SECURITY_PASSWORD_SALT = 'the_shire'  # Default: 'my_precious_two'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'local_database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    SEND_FILE_MAX_AGE_DEFAULT = 0
    UPLOAD_FOLDER = 'app/uploads'
    ALLOWED_EXTENSIONS = {'json', 'zip'}
    CELERY_BROKER_URL = 'redis://localhost:6379',
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'

    """
    Email Stuff:
    This works specifically with Outlook emails. If using a different host to 
    send emails, make sure to update the mail server/port.
    """
    MAIL_SERVER = 'smtp.office365.com'
    MAIL_PORT = 587
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or \
        "MAIL_USERNAME_HERE"
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or \
        "MAIL_PASSWORD_HERE"                       
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    withings_CLIENT_ID = os.environ.get('withings_CLIENT_ID') or \
        'CLIENT_ID_HERE'
    withings_CUSTOMER_SECRET = os.environ.get('withings_CUSTOMER_SECRET') or \
        'CLIENT_ID_HERE'
    withings_STATE = "Unknown"  # I'm honestly unsure what this is intended to be for, 
                                # but it is returned in the authentication request. In 
                                # our current API we are using it to track the participant
                                # that is being authenticated, but it is unused here. 
    withings_ACCOUNT_URL = "https://account.withings.com"
    withings_WBSAPI_URL = "https://wbsapi.withings.net"

    # Make the callback URL https://localhost/5000 for testing (and make 
    # sure this is changed in your Withings app settings as well)
    withings_CALLBACK_URI = os.environ.get('withings_CALLBACK_URI') or \
        "CALLBACK_URL_HERE"

    fitbit_CLIENT_ID = "not used"
    fitbit_CLIENT_SECRET = "not used"
