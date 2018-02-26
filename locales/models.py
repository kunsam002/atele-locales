from _socket import gethostbyname, gethostname
import json
import sys
import os
import re
from datetime import datetime
from pprint import pprint
# from utilities.utils import slugify
from sqlalchemy import func, event
from sqlalchemy import inspect, UniqueConstraint, desc
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property, Comparator
from sqlalchemy.orm import dynamic
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
import inspect as pyinspect
from locales import db, logger, app
from unicodedata import normalize

_slugify_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


def slugify(text, delim=u'-'):
    """
    Generates an ASCII-only slug.

    :param text: The string/text to be slugified
    :param: delim: the separator between words.

    :returns: slugified text
    :rtype: unicode
    """

    result = []
    for word in _slugify_punct_re.split(text.lower()):
        # ensured the unicode(word) because str broke the code
        word = normalize('NFKD', unicode(word)).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))

def get_model_from_table_name(tablename):
    """ return the Model class for a given __tablename__ """

    _models = [args[1] for args in globals().items() if pyinspect.isclass(args[
                                                                              1]) and issubclass(args[1], db.Model)]

    for _m in _models:
        try:
            if _m.__tablename__ == tablename:
                return _m
        except:
            raise

    return None

def slugify_from_name(context):
    """
	An sqlalchemy processor that works with default and onupdate
	field parameters to automatically slugify the name parameters in the model
	"""
    return slugify(context.current_parameters['name'])



class AppMixin(object):
    """ Mixin class for general attributes and functions """

    @property
    def pk(self):
        """ generic way to retrieve the identity of a model object """
        pk_name = inspect(self.__class__).primary_key[0].name
        return getattr(self, pk_name)

    @classmethod
    def primary_key(cls):
        """ generic way to retrieve the identity of a model object """
        pk_name = inspect(cls).primary_key[0].name
        return getattr(cls, pk_name)

    @declared_attr
    def date_created(cls):
        return db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @declared_attr
    def last_updated(cls):
        return db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    def as_dict(self, include_only=None, exclude=["is_deleted"], extras=["pk"], child=None, child_include=[]):
        """ Retrieve all values of this model as a dictionary """
        data = inspect(self)

        if include_only is None:
            include_only = data.attrs.keys() + extras

        else:
            include_only = include_only + extras

        _dict = dict([(k, getattr(self, k)) for k in include_only if isinstance(getattr(self, k),
                                                                                (hybrid_property, InstrumentedAttribute,
                                                                                 InstrumentedList,
                                                                                 dynamic.AppenderMixin)) is False and k not in exclude])

        for key, obj in _dict.items():
            if isinstance(obj, db.Model):
                _dict[key] = obj.as_dict()

            if isinstance(obj, (list, tuple)):
                items = []
                for item in obj:
                    inspect_item = inspect(item)
                    items.append(
                        dict([(k, getattr(item, k)) for k in inspect_item.attrs.keys() + extras if
                              k not in exclude and hasattr(item, k)]))

                for item in items:
                    obj = item.get(child)
                    if obj:
                        item[child] = obj.as_dict(extras=child_include)
        return _dict

    def level_dict(self, include_only=None, exclude=["is_deleted"], extras=[], child=None, child_include=[]):
        data = self.as_dict(include_only=include_only, exclude=exclude, extras=extras, child=child,
                            child_include=child_include)
        for key, value in data.items():
            if type(data.get(key)) == dict:
                data.pop(key)
        return data


class Timezone(AppMixin, db.Model):
    code = db.Column(db.String(200), primary_key=True, nullable=False, index=True, unique=True)
    name = db.Column(db.String(200))
    offset = db.Column(db.String(200))  # UTC time

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<Timezone %r>' % self.name


class Country(AppMixin, db.Model):
    code = db.Column(db.String(200), nullable=False, index=True, unique=True, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True, unique=True)
    slug = db.Column(db.String(200), nullable=False, default=slugify_from_name)
    phone_code = db.Column(db.String)
    enabled = db.Column(db.Boolean, default=False)
    requires_post_code = db.Column(db.Boolean, default=False)

    timezone_code = db.Column(db.String(200), db.ForeignKey('timezone.code'), nullable=True)
    timezone = db.relationship("Timezone", foreign_keys="Country.timezone_code")


    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<Country %r>' % self.name


class State(AppMixin, db.Model):
    code = db.Column(db.String(200), nullable=False, index=True, unique=True, primary_key=True)
    name = db.Column(db.String(200), index=True)
    slug = db.Column(db.String(200), nullable=False, default=slugify_from_name)

    country_code = db.Column(db.String(200), db.ForeignKey('country.code'), nullable=False)

    country = db.relationship("Country", foreign_keys="State.country_code")

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<State %r>' % self.name


class City(AppMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    zipcode = db.Column(db.String(200))
    slug = db.Column(db.String(200), nullable=False, default=slugify_from_name)
    state_code = db.Column(db.String(200), db.ForeignKey('state.code'), nullable=False)
    state = db.relationship("State", foreign_keys="City.state_code")

    country_code = db.Column(db.String(200), db.ForeignKey('country.code'), nullable=False)
    country = db.relationship("Country", foreign_keys="City.country_code")

    # __table_args__ = (
    #     UniqueConstraint("slug", "state_code", "country_code"),
    # )

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<State %r>' % self.name


class Currency(AppMixin, db.Model):
    code = db.Column(db.String(200), nullable=False, index=True, primary_key=True)
    name = db.Column(db.String(200))
    enabled = db.Column(db.Boolean, default=False)
    symbol = db.Column(db.String(200))
    payment_code = db.Column(db.String(200))

    def __unicode__(self):
        return "%s (%s)" % (self.name.title(), self.code)

    def __repr__(self):
        return '<Currency %r>' % self.name


class District(AppMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    code = db.Column(db.String(200))
    slug = db.Column(db.String(200), nullable=False, default=slugify_from_name)

    state_code = db.Column(db.String(200), db.ForeignKey('state.code'), nullable=False)
    state = db.relationship('State', foreign_keys="District.state_code")

    country_code = db.Column(db.String(200), db.ForeignKey('country.code'), nullable=False)
    country = db.relationship('Country', foreign_keys="District.country_code")

    city_id = db.Column(db.Integer, db.ForeignKey('city.id', ondelete="SET NULL"), nullable=False)
    city = db.relationship('City', foreign_keys="District.city_id")

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<State %r>' % self.name


class Street(AppMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200))
    code = db.Column(db.String(200))

    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    city = db.relationship('City', foreign_keys="Street.city_id")

    district_id = db.Column(db.Integer, db.ForeignKey('district.id'), nullable=True)
    district = db.relationship('District', foreign_keys="Street.district_id")

    state_code = db.Column(db.String(200), db.ForeignKey('state.code'), nullable=False)
    state = db.relationship('State', foreign_keys="Street.state_code")

    country_code = db.Column(db.String(200), db.ForeignKey('country.code'), nullable=False)
    country = db.relationship('Country', foreign_keys="Street.country_code")

    def __unicode__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

