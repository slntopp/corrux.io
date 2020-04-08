import requests
from typing import Union
from datetime import datetime

from app.utils import format_date

class DashboardUnreachable(Exception):
    pass

def parse_dashboard(url: str, username: str, password: str) -> dict:

    """ Logins in Dashboard and returns as text(str) "Excavator Status: OPERATIONAL | DOWN"
    :param url: BigCo Dashboard URL
    :param username: Username
    :param password: Password

    :raises: DashboardUnreachable if Dashboard is Unreachable. This means that request has respond with not 200 status code
    """
    # As soon as /login route automatically redirects to main page(/status),
    # we don't need to do any additional "moves". So we're just sending:
    # POST /login with given credentials
    r = requests.post(
        url,
        {
            'email': username,
            'password': password
        }
    )

    if r.status_code != 200:
        raise DashboardUnreachable(r.status_code)
    return r.text

# BigCo API client class
class BigCoAPIClient:
    def __init__(self, endpoint: str, username: str, password: str):
        self.endpoint = endpoint
        self.auth = {
            "username":username,
            "password":password
        }

        self.build_session()

    def build_session(self) -> None:
        """ Obtains token from BigCo API """
        res = requests.post(
            self.endpoint + '/auth',
            json=self.auth
        )

        self.token = self.__validate_response__(res)['access_token']
        self.session = requests.Session()
        # Setting JWT Authorization header
        self.session.headers.update({
            'Authorization': 'JWT %s' % self.token
        })

    def excavator_stats(self, stime:datetime, etime:datetime) -> dict:
        """ Obtains Excavator Statistics from BigCo API
        :type stime: datetime.datetime
        :param stime: from what date to collect Excavator Stats (param: start_time)
    
        :type etime: datetime.datetime
        :param etime:datetime: till what date to collect Excavator Stats (param: end_time)
        """

        # Turning dates to BigCo timestamps format
        stime, etime = format_date.dumps(stime), format_date.dumps(etime)
        # Sending request
        res = self.__call__(
            'excavator_stats',
            params=[
                ('start_time',  stime),
                ('end_time',    etime)
            ]
        )
        # Converting timestamps from response to datetime.datetime
        def serialize(obj):
            obj['most_recent_maintenance'] = format_date.timestamp_loads(obj['most_recent_maintenance'])
            obj['timestamp'] = format_date.timestamp_loads(obj['timestamp'])
            return obj

        return list(map(lambda rec: serialize(rec), res))

    def can_stream(self) -> dict:
        """ Obtains last 50 CAN bus messages from BigCo API """
    
        # Converting timestamps from response to datetime.datetime
        def serialize(obj):
            obj['timestamp'] = format_date.timestamp_loads(obj['timestamp'])
            return obj
        
        return list(map(
            lambda rec: serialize(rec),
            self.__call__('can_stream') # Sending request
        ))


    def __call__(self, method:str, params:list=[], m:str='json') -> Union[dict, str]:
        """ Calling BigCo API methods
        :type method: str
        :param method: method name
    
        :type params: list
        :param params: List of tuples like [('key', 'value'), ...]
    
        :type m: str
        :param m: reponse payload getter-method name(json, text, etc.)
        """
        
        # Have to do it so, because "BigCo" API doesn't decode encoded symbols like start_time=2019-03-01%2B00%3A00
        params = "&".join("%s=%s" % (k,v) for k,v in params)
        res = self.session.get(
            self.endpoint + '/' + method,
            params=params
        )

        return self.__validate_response__(res, m)

    def __validate_response__(self, response, m:str='json') -> Union[str, dict, list]:
        """ Validates response
    
        :type response: requests.Response
        :param response: API Response
    
        :type m: str
        :param m: reponse payload getter-method name(json, text, etc.)
    
        :raises: BigCoAPIClient.BigCoAPI_Unauthorized, BigCoAPIClient.BigCoAPI_SomethingWentWrong
        """
        if response.status_code == 200:
            return getattr(response, m)()
        elif response.status_code == 401:
            raise BigCoAPIClient.BigCoAPI_Unauthorized()
        else:
            raise BigCoAPIClient.BigCoAPI_SomethingWentWrong()

    # Exceptions section
    class BigCoAPI_Unauthorized(Exception): # Unauthorized exception
        def __init__(self):
            super().__init__('Server returned 401 Forbidden. Check given credentials.')
    class BigCoAPI_SomethingWentWrong(Exception): # "Something went wrong" exception
        def __init__(self):
                super().__init__('Something went wrong, check provided data.')