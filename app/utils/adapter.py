import requests
from typing import Union
from datetime import datetime

from app.utils import format_date

class DashboardUnreachable(Exception):
    pass

def parse_dashboard(url: str, username: str, password: str) -> dict:
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

class BigCoAPIClient:
    def __init__(self, endpoint: str, username: str, password: str):
        self.endpoint = endpoint
        self.auth = {
            "username":username,
            "password":password
        }

        self.build_session()

    def build_session(self) -> None:
        res = requests.post(
            self.endpoint + '/auth',
            json=self.auth
        )

        self.token = self.__validate_response__(res)['access_token']
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': 'JWT %s' % self.token
        })

    def excavator_stats(self, stime:datetime, etime:datetime) -> dict:
        stime, etime = format_date.dumps(stime), format_date.dumps(etime)
        res = self.__call__(
            'excavator_stats',
            params=[
                ('start_time',  stime),
                ('end_time',    etime)
            ]
        )
        def serialize(obj):
            obj['most_recent_maintenance'] = format_date.timestamp_loads(obj['most_recent_maintenance'])
            obj['timestamp'] = format_date.timestamp_loads(obj['timestamp'])
            return obj

        return list(map(lambda rec: serialize(rec), res))

    def can_stream(self) -> dict:
        def serialize(obj):
            obj['timestamp'] = format_date.timestamp_loads(obj['timestamp'])
            return obj
        return list(map(
            lambda rec: serialize(rec),
            self.__call__('can_stream')
        ))


    def __call__(self, method:str, params:list=[], m:str='json') -> Union[dict, str]:
        params = "&".join("%s=%s" % (k,v) for k,v in params)
        res = self.session.get(
            self.endpoint + '/' + method,
            params=params
        )
        return self.__validate_response__(res, m)

    def __validate_response__(self, response, m:str='json'):
        if response.status_code == 200:
            return getattr(response, m)()
        elif response.status_code == 401:
            raise BigCoAPIClient.BigCoAPI_Unauthorized()
        else:
            raise BigCoAPIClient.BigCoAPI_SomethingWentWrong()

    # Exceptions
    class BigCoAPI_Unauthorized(Exception):
        def __init__(self):
            super().__init__('Server returned 401 Forbidden. Check given credentials.')
    class BigCoAPI_SomethingWentWrong(Exception):
        def __init__(self):
                super().__init__('Something went wrong, check provided data.')