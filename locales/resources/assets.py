from locales.resources import BaseResource, ModelListField, ModelField
from locales import register_api
from locales.services.assets import *
from flask_restful import fields
from locales import logger


class CountryResource(BaseResource):
    resource_name = 'countries'
    service_class = CountryService
    resource_fields = {
        "code": fields.String,
        "name": fields.String,
        "slug": fields.String,
        "phone_code": fields.String
    }


register_api(CountryResource, '/countries/', '/countries/<int:id>/')
