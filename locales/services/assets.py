from utilities import ServiceLabs, ObjectNotFoundException
from locales import app
from locales.models import Country, State,Timezone,Street,District,City,Currency

db = app.db

CountryService = ServiceLabs.create_instance(Country, db)
StateService = ServiceLabs.create_instance(State, db)
CityService = ServiceLabs.create_instance(City, db)
DistrictService = ServiceLabs.create_instance(District, db)
StreetService = ServiceLabs.create_instance(Street, db)
CurrencyService = ServiceLabs.create_instance(Currency, db)
