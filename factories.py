"""
factories.py

@Author: Ogunmokun Olukunle

This module contains application factories.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from flask_restful import Api
import wtforms_json
# from flask_migrate import Migrate
from flask_cache import Cache
from flask_moment import Moment
from flask_alembic import Alembic

# Monkey patch wtforms to support json data
wtforms_json.init()


def initialize_api(app, api):
    """ Register all resources for the API """
    api.init_app(app=app)  # Initialize api first
    _resources = getattr(app, "api_registry", None)
    if _resources and isinstance(_resources, (list, tuple,)):
        for cls, args, kwargs in _resources:
            api.add_resource(cls, *args, **kwargs)


def initialize_blueprints(app, *blueprints):
    """
    Registers a set of blueprints to an application
    """
    for blueprint in blueprints:
        app.register_blueprint(blueprint)


def create_app(app_name, config_obj, with_api=True):
    """ Generates and configures the main shop application. All additional """
    # Launching application
    app = Flask(app_name)  # So the engine would recognize the root package

    # Load Configuration
    app.config.from_object(config_obj)

    # Initializing Database
    db = SQLAlchemy(app)
    app.db = db

    # migrate = Migrate(app, db)

    app.cache = Cache(app)

    # Initializing Alembic
    alembic = Alembic()
    alembic.init_app(app)
    app.alembic = alembic


    moment = Moment(app)
    app.moment = moment

    # Initializing the restful API
    if with_api:
        api = Api(app, prefix='/rest')
        app.api = api

    # Initialize Logging
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler("/var/log/locales/%s.log" % app.config.get("LOGFILE_NAME", app_name),
                                           maxBytes=500 * 1024)
        file_handler.setLevel(logging.INFO)
        from logging import Formatter
        file_handler.setFormatter(Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)

        # include an api_registry to the application
    app.api_registry = []  # a simple list holding the values to be registered

    return app
