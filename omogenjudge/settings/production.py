from omogenjudge.settings.base import *  # noqa

import toml
import os

CONFIG_FILE_PATH = os.environ.get("OMOGEN_CONFIG_FILE_PATH") or "/etc/omogen/web.toml"
with open(CONFIG_FILE_PATH, "r") as f:
    config = toml.load(f)

DEBUG=True

SECRET_KEY = config['web']['secret_key']

MAILJET_API_KEY = config['email']['mailjet_api_key']
MAILJET_API_SECRET = config['email']['mailjet_api_secret']

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
#SECURE_HSTS_SECONDS = 31536000
#SECURE_SSL_REDIRECT = True

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'omogenjudge',
        'USER': 'omogenjudge',
        'PASSWORD': config['database']['password'],
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
STATICFILES_DIRS = [
    config['staticfiles']['dir']
]

if "oauth" in config:
    OAUTH_DETAILS = config["oauth"]
