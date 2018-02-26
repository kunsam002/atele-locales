
import os, pytz, json
from datetime import datetime, timedelta
from locales.models import *
from locales.services.assets import *
from locales import app, db, logger
from sqlalchemy import or_, and_

SETUP_DIR = app.config.get("SETUP_DIR") # Should be present in config


def start():
	""" Start the setup process """
	load_timezones()
	load_currencies()
	load_countries()
	load_states()
	load_cities()
