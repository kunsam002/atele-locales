"""
restful.py

@Author: Ogunmokun Olukunle

Extension Integration for Flask-Restful.

The classes in this module will be used to provide support for sqlalchemy and non-sqlalchemy integrations. Each base class should be
extended to implement specific functionality.

Requires flask-restful and sqlalchemny

"""
from datetime import datetime
import urlparse
import time
import urllib
import json

import dateutil.parser
from flask_restful import fields
from flask import request, g, make_response, url_for, current_app as app
from flask_restful import Resource, marshal, reqparse, abort
from sqlalchemy import asc, desc
from utilities.utils import DateJSONEncoder, encrypt_dict_to_string, decrypt_string_to_dict, copy_dict

from werkzeug.exceptions import HTTPException
# flask restful api object. Should be instantiated in the flask app
api = app.api
logger = app.logger


# custom status codes

NOT_YET_AVAILABLE_ERROR = 403
INTEGRITY_ERROR = 408
VALIDATION_FAILED = 409
ACTION_REQUIRED = 209


class ValidationFailed(HTTPException):
    """
    *34* `Validation Failed`
    Custom exception thrown when form validation fails.
    This is only useful when making REST api calls
    """

    name = "Validation Failed"
    code = VALIDATION_FAILED
    description = (
        '<p>Validation Failed</p>'
    )

    def __init__(self, data, description=None):
        """
        :param: data: A dictionary containing the field errors that occured
        :param: description: Optional description to send through
        """
        HTTPException.__init__(self)
        self.description = description
        self.data = data

    def get_response(self, environment):
        resp = super(ValidationFailed, self).get_response(environment)
        resp.status = "%s %s"(self.code, self.name.upper())
        return resp


class FurtherActionException(HTTPException):
    """
    *34* `Further Action Exception`
    Custom exception thrown when further action is required by the user.
    This is only useful when making REST api calls
    """

    name = "Further Action Required"
    code = ACTION_REQUIRED
    description = (
        '<p>Further Action Required</p>'
    )

    def __init__(self, data, description=None):
        """
        :param: data: A dictionary containing the field errors that occured
        :param: description: Optional description to send through
        """
        HTTPException.__init__(self)
        self.description = description
        self.data = data

    def get_response(self, environment):
        resp = super(FurtherActionException, self).get_response(environment)
        resp.status = "%s %s"(self.code, self.name.upper())
        return resp


# other exceptions to implement
# not found exception, also raised by the service layer
# authentication failed. This would be raised whenever authentication fails
# permission denied. The would occur when a user attempts to access unauthorized content


class IntegrityException(HTTPException):
    """
    *32* `Integrity Exception`
    Custom exception thrown when an attempt to save a resource fails.
    This is only useful when making REST api calls
    """

    name = "Integrity Exception"
    code = INTEGRITY_ERROR
    description = (
        '<p>Integrity Exception</p>'
    )

    def __init__(self, e):
        """
        param: e: parent exception to wrap and manipulate
        """
        print e
        HTTPException.__init__(self)
        self.data = e.data if hasattr(e, "data") else {}
        self.code = e.code if hasattr(e, "code") else INTEGRITY_ERROR
        bits = e.message.split("\n")
        if len(bits) > 1:
            self.data["error"] = bits[0]
            self.data["message"] = " ".join(bits[1:]).strip()
        else:
            self.data["message"] = " ".join(bits).strip()

    def get_response(self, environment):
        resp = super(IntegrityException, self).get_response(environment)
        resp.status = "%s %s"(self.code, self.name.upper())
        return resp


class ObjectNotFoundException(Exception):
    """ This exception is thrown when an object is queried by ID and not retrieved """

    def __init__(self, klass, obj_id):
        message = "%s: Object not found with id: %s" % (klass.__name__, obj_id)
        self.data = {"name": "ObjectNotFoundException", "message": message}
        self.status = 501
        super(ObjectNotFoundException, self).__init__(message)


class ActionDeniedException(Exception):
    """ This exception is thrown when an object is queried by ID and not retrieved """

    def __init__(self, klass, obj_id):
        message = "%s: Action denied on object id: %s" % (klass.__name__, obj_id)
        self.data = {"name": "ActionDeniedException", "message": message}
        self.status = 40
        super(ActionDeniedException, self).__init__(message)


class Timestamp(fields.Raw):
    def format(self, value):
        return value.isoformat()


class ModelField(fields.Raw):
    """ Custom field class to support embedding a model object within a resource reponse """

    def __init__(self, fields=None, exclude=[], extras=[], endpoint=None, **kwargs):
        super(ModelField, self).__init__(**kwargs)
        self.fields = fields
        self.endpoint = endpoint
        self.exclude = exclude
        self.extras = extras

    def format(self, value):
        """ Extract data as a dict from value object """
        return self.prepare(value)

    def prepare(self, value):
        """ Function to convert value into a dictionary for nesting """

        if isinstance(value, dict):
            data = value
        else:
            data = value.as_dict(include_only=self.fields, exclude=self.exclude, extras=self.extras)

        if self.endpoint:
            data["obj_id"] = data.get("id")  # add obj_id as key field

            # remove all unnecessary sections of the url
            uri = urlparse.urlparse(url_for(self.endpoint, **data))
            data["uri"] = urlparse.urlunparse(("", "", uri.path, "", "", ""))
            data.pop("obj_id")  # remove obj_id field

        return data


class ModelListField(ModelField):
    """ Extension class to support embedding iteratable properties within models """

    def __init__(self, _fields=None, exclude=[], extras=[], endpoint=None, **kwargs):
        """
        Field class to support sqlalchemy model list values in json serialization
        :param _fields: Fields to serialize
        :param exclude: Fields to exclude
        :param extras: Extra _fields to include in serialization
        :param endpoint: Endpoint name. If provided will include the URL property inside each object in the list
        :param kwargs: Extra arguments
        :return:
        """
        super(ModelListField, self).__init__(_fields, exclude, extras, endpoint, **kwargs)

    def format(self, values):
        """ Values should be an iteratable property """
        results = [self.prepare(value) for value in values]
        return results


def to_boolean(value):
    """
    Determine Falsy values for boolean.
    :param value: value representation of false
    :return:
    """

    #  lowercase the value if it comes as a string
    if isinstance(value, (str, unicode)):
        value = value.lower()

    if value in ['false', 'f', 'n', 'no', None, False]:
        return False
    else:
        return bool(value)


def to_date(value):
    """
    Parse a string representation of date into a date
    :param value: date in string format
    :return:
    """
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")


def to_datetime(value):
    try:
        return dateutil.parser.parse(value)
    except ValueError:
        raise ValueError("Unable to determine date or time from the values sent")


@api.representation('application/json')
def output_json(data, code, headers={}):
    """ Custom json output format to allow automatic date formatting with json """
    resp = make_response(json.dumps(data, cls=DateJSONEncoder), code)
    resp.headers.extend(headers)
    return resp


def empty_filter_parser():
    """ A utility function to return empty filter arguments when an implementation isn't available """
    return {}


def sort_func(asc_desc):
    """
    Returns the proper ordering function based on the key given

    :param asc_desc: Ascending or Descending, represented by `asc` or `desc`
    :returns: `sqlalchemy.asc` or `sqlalchemy.desc`
    :rtype: func
    """

    if asc_desc == "asc":
        return asc

    if asc_desc == "desc":
        return desc


def operator_func(query, service_class, op, name, value):
    """ Returns the query filtered according to the operator and property used.
        Values in use include:
            eq:  ==
            neq: !=
            gt:  >
            gte: >=
            lt: <
            lte: <=
            in: in_
            btw: between
    """
    if not isinstance(value, (list, tuple)):
        value = [value]

    if op == 'eq':
        return query.filter(getattr(service_class.model_class, name) == value[0])
    if op == 'neq':
        return query.filter(getattr(service_class.model_class, name) != value[0])
    if op == 'gt':
        return query.filter(getattr(service_class.model_class, name) > value[0])
    if op == 'gte':
        return query.filter(getattr(service_class.model_class, name) >= value[0])
    if op == 'lt':
        return query.filter(getattr(service_class.model_class, name) < value[0])
    if op == 'lte':
        return query.filter(getattr(service_class.model_class, name) <= value[0])
    if op == 'in':
        return query.filter(getattr(service_class.model_class, name).in_(value[0]))
    if op == 'btw':
        start, finish = None, None
        if value and len(value) > 1:
            start = value[0]
            finish = value[1]
        elif value:
            start = value[0]

        return query.filter(getattr(service_class.model_class, name).between(start, finish))


@app.errorhandler(VALIDATION_FAILED)
def form_validation_error(e):
    """ Error handler for custom form validation errors """
    return api.make_response(e.data, e.status)


@app.errorhandler(IntegrityException)
def integrity_exception_handler(e):
    """ Error handler for custom form validation errors """
    return api.make_response(e.data, e.status)


@app.errorhandler(ObjectNotFoundException)
def integrity_exception_handler(e):
    """ Error handler for custom form validation errors """
    return api.make_response(e.data, e.status)


@app.errorhandler(FurtherActionException)
def further_action_exception_handler(e):
    """ Error handler for custom form validation errors """
    return api.make_response(e.data, e.status)


class BaseResource(Resource):
    """
    Base resource class to control all REST API calls.
    """

    # Generic method decorators. Override where necessary
    method_decorators = []
    first_result_only = False  # return individual object rather than Array
    default_page_size = 20
    default_order_param = 'date_created'
    default_order_direction = 'desc'
    sub_resource = None
    validation_form = None
    resource_fields = None  # Implement this in subclass!
    resource_name = None  # A default name for the resource. This would be part of the meta information as well
    service_class = None
    pagers = [dict(name=str(v), value=v) for v in [5, 10, 20, 50, 100]]  # default number of items per page
    filters = []  # list of filters to show on each page. the values will be a list of dict of dicts
    # default sorters. can be overridden in any subclass
    searchable_fields = []
    sorters = [
        {
            "name": "ID",
            "value": "id"
        },
        {
            "name": "Name",
            "value": "name"
        },
        {
            "name": "Date Created",
            "value": "date_created"
        },
        {
            "name": "Last Updated",
            "value": "last_updated"
        }
    ]

    @property
    def output_fields(self):
        """ Property function to always generate a clean base value for output fields """
        return {
            'id': fields.Integer,
            'date_created': Timestamp,
            'last_updated': Timestamp,
        }

    def paging_parser(self):
        """
        Builds the parser to extract pagination information from the request

        :returns: a dict containing extracted values
        :rtype: dict
        """

        r_args = {"error_out": False}

        parser = reqparse.RequestParser()
        parser.add_argument('page', type=int, default=1, location='args')
        parser.add_argument('per_page', type=int, default=self.default_page_size, location='args')

        r_args.update(parser.parse_args())

        return r_args

    def sort_parser(self):
        """
        Builds the request parser for extracting sorting parameters from the request.

        :returns: a dict containing extracted values
        :rtype: dict

        """
        parser = reqparse.RequestParser()
        parser.add_argument("order_by", type=str, default=self.default_order_param, location='args')
        parser.add_argument("asc_desc", type=str, default=self.default_order_direction, location='args')

        return parser.parse_args()

    @staticmethod
    def search_parser():
        """
        Builds the request parser for extracting search parameters from the request.

        :returns: a dict containing extracted values
        :rtype: dict

        """
        parser = reqparse.RequestParser()
        parser.add_argument("query", type=str, location='args')
        parser.add_argument("id", type=str, location='args')

        return parser.parse_args()

    @staticmethod
    def operator_parser():
        """
        Determine the query operator tactic to use. The default value will be '==' or 'eq'. Possible values include:
        'eq', 'neq', 'gte', 'gt', 'lte', 'lt', 'btw'
        """

        parser = reqparse.RequestParser()
        parser.add_argument("op", type=str, location='args', default='eq')

        return parser.parse_args()

    @staticmethod
    def group_parser():

        parser = reqparse.RequestParser()
        parser.add_argument("group_ids", type=int, location='args', action='append')

        return parser.parse_args()

    def group_action_parser(self):

        parser = reqparse.RequestParser()
        parser.add_argument("action_name", type=str, location='args', default=None)

        return parser.parse_args()


    @staticmethod
    def search_filters():
        """default search filter. should be typically overwritten in subclass"""
        return {"match_all": {}}

    def search_query(self, search_q=None):
        """ Default search query. Should be typically overwritten in subclass"""
        if search_q:
            return {
                "multi_match": {
                    "query": search_q,
                    "type": "best_fields",
                    "fields": self.searchable_fields,
                    "operator": "and"
                }
            }

        else:
            return {
                "match_all": {}
            }

    @staticmethod
    def filter_parser():

        return empty_filter_parser()

    def is_permitted(self, obj=None, **kwargs):

        return obj

    def updated_form_data(self, attrs):

        return attrs

    def adjust_form_fields(self, form):

        return form

    def adjust_form_data(self, data):

        return data

    @staticmethod
    def prepare_errors(errors):

        _errors = {}
        for k, v in errors.items():
            _res = [str(z) for z in v]
            _errors[str(k)] = _res

        return _errors

    def validate(self, form_class, obj=None, adjust_func=None):

        if form_class is None:
            abort(405, status="Not Allowed", message="The data transmitted cannot be validated.")
        # converted to a patched version of wtforms
        form = form_class(obj=obj, csrf_enabled=False)

        if adjust_func:
            form = adjust_func(form)

        if form.validate():
            return self.updated_form_data(form.data), request.files
        else:
            raise ValidationFailed(data=self.prepare_errors(form.errors))

    def execute_query(self, resource_name, query, service_class, filter_args={}, sort_args={}, search_args={}, paging_args={},
                      resource_fields={}, operator_args={}, from_cache=True, **kwargs):

        resp = {"endpoint": resource_name}
        order_by, asc_desc = sort_args.get("order_by"), sort_args.get("asc_desc")
        page, per_page, error_out = paging_args.get("page"), paging_args.get("per_page"), paging_args.get("error_out")
        search_q = search_args.get("query")
        search_id = search_args.get("id")
        op = operator_args.get("op")

        # TODO implement permission check here
        self.is_permitted()

        # execute limit query:
        query = self.limit_query(query)

        # apply the query filters
        for name, value in filter_args.items():
            query = operator_func(query, service_class, op, name, value)

        # apply sorting
        _sort = sort_func(asc_desc)  # Extracts which sorting direction is required
        query = query.order_by(_sort(getattr(service_class.model_class, order_by)))

        if self.first_result_only:
            res = query.first()

            if not res:
                abort(404, status='Result not Found', message='')

            output_fields = self.output_fields

            output_fields.update(self.resource_fields)

            return marshal(res, output_fields), 200

        # execute the query and include paging
        paging = query.paginate(page, per_page, error_out)

        resp["order_by"] = order_by
        resp["asc_desc"] = asc_desc
        resp["page"] = paging.page
        resp["total"] = paging.total
        resp["pages"] = paging.pages
        resp["per_page"] = per_page
        resp["op"] = op
        resp["pagers"] = self.pagers
        resp["filters"] = self.filters
        resp["sorters"] = self.sorters

        # extract the request args and modify them for paging
        request_args = copy_dict(request.args, {})

        if paging.has_next:
            # build next page query parameters
            request_args["page"] = paging.next_num
            resp["next"] = paging.next_num
            resp["next_page"] = "%s%s" % ("?", urllib.urlencode(request_args))

        if paging.has_prev:
            # build previous page query parameters
            request_args["page"] = paging.prev_num
            resp["prev"] = paging.prev_num
            resp["prev_page"] = "%s%s" % ("?", urllib.urlencode(request_args))

        output_fields = self.output_fields

        _resource_fields = resource_fields or self.resource_fields

        output_fields.update(_resource_fields)

        resp["results"] = marshal(paging.items, output_fields)

        # TODO: Figure out how to handle exceptions so that it works out well

        return resp, 200

    def execute_get(self, obj_id, **kwargs):
        """ Execute a get query to retrieve an exact object by id."""

        output_fields = self.output_fields
        output_fields.update(self.resource_fields or {})
        obj = self.service_class.get(obj_id)

        obj = self.is_permitted(obj)  # check if you're permitted

        return marshal(obj, output_fields), 200

    def execute_group_action(self, obj_ids, attrs, files=None):
        """ Executes group actions by obj_ids """
        action_name = attrs.get("action_name", None)

        resp = None
        status = 201

        if action_name:
            action_func = getattr(self, "%s_group_action" % action_name, None)

            # if action_func exists, then pass the attrs
            if action_func:

                # inject validation here
                validation_form = getattr(self, "%s_validation_form" % action_name, None)
                adjust_func = getattr(self, "%s_adjust_form_fields" % action_name, None)

                if not validation_form:
                    abort(405, status="Not Authorized", message="The requested resource is not yet authorized for access")

                data, files = self.validate(validation_form, adjust_func=adjust_func)
                data = self.adjust_form_data(data)

                resp = action_func(obj_ids, data, files)

        return resp, status

    def limit_query(self, query):
        """
        Optionally filter the query by a particular property.
        This is useful in limiting the queries to only elements from a particular subset of the data.
        modifications on the query should be implemented here and the query object
        should be returned.

        :param query: the query to be executed

        :returns: query

        """

        return query

    def query(self):
        """ Define the query that loads data for your GET request. """
        return self.service_class.query

    def save(self, attrs, files=None):

        print "_____"
        print attrs

        obj = self.service_class.create(**attrs)

        print obj

        return obj

    def update(self, obj_id, attrs, files=None):
        """
        Updates information sent in by PUT request.
        This will be used along with self.validate(form_class, obj=None)
        The functionality is usually implemented in one of the service functions

        :param attrs: the data to be saved.
        """
        return self.service_class.update(obj_id, **attrs)

    def bulk_update(self, obj_ids, attrs, files=None):

        ignored_args = ["id", "date_created", "last_updated"]
        return self.service_class.update_by_ids(obj_ids, ignored_args=ignored_args, **attrs)

    def destroy(self, obj_id):
        """
        Deletes and object sent in by DELETE request.
        The functionality is usually implemented in one of the service functions

        :param obj_id: the id of the object to be deleted
        """

        return self.service_class.delete(obj_id)

    def delete_group_action(self, obj_ids, attrs, files=None):
        """
        Deletes objects sent in by DELETE request.
        The functionality is usually implemented in one of the service functions

        :param obj_ids: the list of ids for objects to be deleted
        """

        return self.service_class.delete_by_ids(ids=obj_ids)

    @staticmethod
    def current_user():
        """ Retrieves the current user of the api """
        return getattr(g, "user")

    @staticmethod
    def get_user_id():
        _user = getattr(g, "user", None)

        if not _user:
            abort(401, status="Invalid credentials", message="the user credentials provided is invalid for this resource")

        return _user.id

    def get(self, obj_id=None, resource_name=None):
        """
        Handle a get request based on the parameters
        """

        filter_args = self.filter_parser()
        paging_args = self.paging_parser()
        sort_args = self.sort_parser()
        search_args = self.search_parser()
        operator_args = self.operator_parser()
        resource_fields = self.resource_fields

        # Determine which query to execute based on parameters passed.

        if obj_id is None:
            # This is the bulk query method. If no obj_id is passed, then execute the collection request [execute_query]
            query = self.query()
            # execute the query and build the response.
            resp, status = self.execute_query(self.resource_name, query, self.service_class, filter_args, sort_args, search_args,
                                              paging_args, resource_fields, operator_args)

        elif obj_id is not None and resource_name is None:
            # This is an object get request. Based on obj_id, execute the get request [execute_get]
            resp, status = self.execute_get(obj_id)

        elif obj_id is not None and resource_name is not None:
            # This is a get sub-request based on the parent object by obj_id. execute the collection sub request [execute_query]

            sub_query_method = getattr(self, "%s_query" % resource_name.lower(), None)  # find the appropriate query
            sub_filter_parser = getattr(self, "%s_filter_parser" % resource_name.lower(), empty_filter_parser)  # find the filter parser
            sub_resource_fields = getattr(self, "%s_resource_fields" % resource_name.lower(), {})  # find the resource fields
            sub_service_class = getattr(self, "%s_service_class" % resource_name.lower(), None)  # find the resource fields

            if not sub_query_method or not sub_service_class:
                abort(404)
                # extract the sub_query, filter_args, parser_args, sort_args and execte the collection.

            sub_filter_args = sub_filter_parser()
            query = sub_query_method(obj_id)

            resp, status = self.execute_query(resource_name, query, sub_service_class, sub_filter_args, sort_args, search_args,
                                              paging_args, sub_resource_fields, operator_args)

        return resp, status

    def post(self, obj_id=None, resource_name=None):
        """ Execute a post request based on criteria given by the above parameters.
            If obj_id isn't passed. It implies a create function call. If there's an obj_id, it implies and update.
            if resource_name is passed, it implies a sub update method call
            It also contains logic for a bulk update
         """

        # extract bulk ids from the list to see how it works
        group_args = self.group_parser()
        obj_ids = group_args.get("group_ids", None)

        if obj_id is None and obj_ids is None:
            # when obj_id isn't passed, this executes the save function call
            self.is_permitted()  # check if you're permitted first
            attrs, files = self.validate(self.validation_form, adjust_func=self.adjust_form_fields)

            # update the form data using this interceptor. i.e inject a domain group id (merchant_id, courier_id etc.)
            attrs = self.adjust_form_data(attrs)

            try:
                res = self.save(attrs, files)  # execute save method [self.save()]
                output_fields = self.output_fields
                output_fields.update(self.resource_fields or {})

                return marshal(res, output_fields), 201
            except Exception, e:
                raise IntegrityException(e)

        elif obj_id is not None and resource_name is None:
            # when an obj_id is passed but resource_name doesn't exist, this implies an update method call
            obj = self.service_class.get(obj_id)
            obj = self.is_permitted(obj)  # check if you're permitted first
            attrs, files = self.validate(self.validation_form, obj=obj, adjust_func=self.adjust_form_fields)
            attrs = self.adjust_form_data(attrs)
            try:
                res = self.update(obj_id, attrs, files)  # execute update method [self.update()]
                output_fields = self.output_fields
                output_fields.update(self.resource_fields or {})

                return marshal(res, output_fields), 201
            except Exception, e:
                logger.error(e)
                raise IntegrityException(e)

        elif obj_id is not None and resource_name is not None:
            # when obj_id is passed along with a resource_name. this implies a do_method call.
            obj = self.service_class.get(obj_id)
            self.is_permitted(obj)  # check if you're permitted first

            adjust_func = getattr(self, "%s_adjust_form_fields" % resource_name, None)
            do_method = getattr(self, "do_%s" % resource_name, None)
            validation_form = getattr(self, "%s_validation_form" % resource_name, None)

            if do_method is None:
                abort(405, status="Not Authorized", message="The requested resource is not yet authorized for access")

            try:
                attrs = request.data or {}
                files = None

                # if there is a validation form, use it
                if validation_form:
                    attrs, files = self.validate(validation_form, obj, adjust_func=adjust_func)
                    attrs = self.adjust_form_data(attrs)

                res = do_method(obj_id, attrs, files)  # Functionality for saving data implemented here
                output_fields = self.output_fields
                output_fields.update(self.resource_fields or {})

                return marshal(res, output_fields), 201
            except Exception:
                raise

        elif obj_id is None and resource_name is None and obj_ids is not None:
            # attempting a bulk update. only occurs when bulk_ids values are present and there's not obj_id
            self.is_permitted()  # check if you're permitted first

            # cannot use validation form here, values will be derived from an update parser
            attrs = self.group_action_parser()
            files = None

            try:
                resp, status = self.execute_group_action(obj_ids, attrs, files)

                return resp, status
            except Exception, e:

                raise IntegrityException(e)

    def put(self, obj_id=None, resource_name=None):
        """ Put request will re-route to post request """
        return self.post(obj_id=obj_id, resource_name=resource_name)

    def delete(self, obj_id=None):
        """
        Handles deleting the resource entity. If the obj_id value isn't passed, then a bulk delete function is executed
        and requires values from bulk_ids retrieved via bulk_parser method
        """
        if obj_id is None:
            # the obj_id isn't sent, as such a bulk delete is requested
            group_args = self.group_parser()
            obj_ids = group_args.get("group_ids", [])
            attrs = self.group_action_parser()
            files = None
            try:

                resp = self.delete_group_action(obj_ids, attrs, files)
                return resp, 201
            except Exception, e:
                raise IntegrityException(e)
        else:
            # the obj_id sent, as such a single delete is requested
            obj = self.service_class.get(obj_id)
            self.is_permitted(obj)  # check if you're permitted
            try:
                resp = self.destroy(obj_id)  # Functionality for saving data implemented here

                return resp, 201
            except Exception, e:
                raise IntegrityException(e)
