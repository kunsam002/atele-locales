# Configuration module

import os


class Config(object):
    """
	Base configuration class. Subclasses should include configurations for
	testing, development and production environments

	"""

    DEBUG = True
    SECRET_KEY = '\x91c~\xc0-\xe3\'f\xe19PAE\x93\xe8\x91`utu"\xd0\xb6\x01l/\x0c\xed\\\xbd]Hoe\x99lkcalese\xf8'
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_POOL_RECYCLE = 1 * 60 * 60

    ADMIN_EMAILS = ["kunle@atele.org"]

    FLASK_ASSETS_USE_S3 = False
    USE_S3 = False
    USE_S3_DEBUG = DEBUG
    ASSETS_DEBUG = True
    S3_USE_HTTPS = False

    LOGFILE_NAME = "atele-locales"

    ADMIN_USERNAME = "atele-locales"
    ADMIN_PASSWORD = "atele-locales"
    ADMIN_EMAIL = "kunle@atele.org"
    ADMIN_FULL_NAME = "Atele Locales"

    # Facebook, Twitter and Google Plus handles
    SOCIAL_LINKS = {"facebook": "", "twitter": "", "google": "",
                    "instagram": "", "pinterest": ""}

    # ReCaptcha Keys
    RECAPTCHA_PUB_KEY = "6LeC-OgSAAAAAOjhuihbl6ks-NxZ9jzcv7X4kG9M"
    RECAPTCHA_PRIV_KEY = "6LeC-OgSAAAAANbUdjXj_YTCHbocDQ48-bRRFYTr"

    # redis
    CACHE_TYPE = 'simple'




class TestConfig(Config):
    """ Configuration class for site development environment """

    DEBUG = True

    SQLALCHEMY_DATABASE_URI = 'postgres://postgres:postgres@localhost/locales'

    DATABASE = SQLALCHEMY_DATABASE_URI
    SETUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'setup')
    MAX_RETRY_COUNT = 3


    LOGIN_VIEW = '.login'


class LiveConfig(Config):
    """ Configuration class for site development environment """

    DEBUG = True

    SQLALCHEMY_DATABASE_URI = 'postgres://btwwaokaqviewj:4aa94f239810bb1291643b0b45c4fc64b7ae135ea336d65088632a39af5af078@ec2-54-228-181-43.eu-west-1.compute.amazonaws.com:5432/dcg8g5q4b7np52'

    DATABASE = SQLALCHEMY_DATABASE_URI
    SETUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'setup')
    MAX_RETRY_COUNT = 3


    LOGIN_VIEW = '.login'
