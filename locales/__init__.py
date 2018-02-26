# Imports
from flask import current_app as app
from sqlalchemy import exc
from sqlalchemy import event
from sqlalchemy.pool import Pool
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import scoped_session, sessionmaker

Session = scoped_session(sessionmaker())

session = Session()

# Logger
logger = app.logger

# Database
db = app.db

# Alembic
alembic = app.alembic

# API
api = app.api
cache = app.cache

moment = app.moment

# Connection pool disconnect handler. Brought about as a result of MYSQL!!!

@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    print "---------- In Ping Connection --------------"
    cursor = dbapi_connection.cursor()
    print "---------- Connection Cursor --------------", cursor
    try:
        cursor.execute("SELECT 1")
    except:
        # optional - dispose the whole pool
        # instead of invalidating one at a time
        # connection_proxy._pool.dispose()

        # raise DisconnectionError - pool will try
        # connecting again up to three times before raising.
        raise exc.DisconnectionError()
    cursor.close()


def register_api(cls, *urls, **kwargs):
    """ A simple pass through class to add entities to the api registry """
    kwargs["endpoint"] = getattr(cls, 'resource_name', kwargs.get("endpoint", None))
    app.api_registry.append((cls, urls, kwargs))


@app.teardown_request
def shutdown_session(exception=None):
    # print "------------- tearing down context now ---------"
    if exception:
        db.session.rollback()
        db.session.close()
        db.session.remove()
    db.session.close()
    db.session.remove()


@app.teardown_appcontext
def teardown_db(exception=None):
    # print "------------- tearing down app context now ---------"
    db.session.commit()
    db.session.close()
    db.session.remove()

