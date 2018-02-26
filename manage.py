#! /usr/bin/env python

from flask_script import Manager
import os
import flask
from factories import create_app, initialize_api, initialize_blueprints
from flask_migrate import MigrateCommand

app = create_app('locales', 'config.TestConfig')

# Initializing script manager
manager = Manager(app)

logger = app.logger

@manager.command
def runserver():
    """ Start the server"""
    # with app2.app_context():
    from locales.views.public import www
    from locales import api
    from locales.resources import assets

    # Initialize the app blueprints
    initialize_blueprints(app, www)
    initialize_api(app, api)

    port = int(os.environ.get('PORT', 5500))
    app.run(host='0.0.0.0', port=port)

@manager.command
def install_assets(name):
    """ load startup data for a particular module """

    app = flask.current_app
    with app.app_context():
        from locales import db, models, logger
        from utilities import loader

        setup_dir = app.config.get("SETUP_DIR")  # Should be present in config

        filename = "%s.json" % name

        src = os.path.join(setup_dir, filename)
        logger.info(src)

        loader.load_data(models, db, src)

@manager.command
def alembic(action, message=""):
    """ alembic integration using Flask-Alembic. Should provide us with more control over migrations """

    from locales import alembic as _alembic

    if action == "migrate":
        app.logger.info("Generating migration")
        _alembic.revision(message)
        app.logger.info("Migration complete")

    elif action == "upgrade":
        app.logger.info("Executing upgrade")
        _alembic.upgrade()
        app.logger.info("Upgrade complete")

    elif action == 'update':
        app.logger.info("Executing upgrade")
        _alembic.upgrade()
        _alembic.revision("Generating migration")
        _alembic.upgrade()
        app.logger.info("Upgrade complete")



if __name__ == "__main__":
    manager.run()
