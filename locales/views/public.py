"""
public.py

@Author: Ogunmokun, Olukunle

The public views
"""

from flask import Blueprint, render_template, abort, redirect, \
    flash, url_for, request, session, g, make_response, current_app
from _socket import gethostbyname, gethostname
from locales import db, logger, app
from locales.models import *
from sqlalchemy import asc, desc, or_, and_, func
import time
import json
import urllib
import base64
import requests
import os
import sys
import random
import pprint
import cgi
from datetime import datetime

www = Blueprint('public', __name__)


@www.context_processor
def main_context():
    """ Include some basic assets in the startup page """
    today = datetime.today()
    current_ip = gethostbyname(gethostname())
    return locals()

@www.route('/<string:path>/')
@www.route('/')
def index(path=None):
    country = Country.query.first()
    return render_template("public/index.html", **locals())

