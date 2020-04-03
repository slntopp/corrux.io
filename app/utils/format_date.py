from datetime import datetime
import pytz

template    = '%Y-%m-%d+%H:%M'
ts_template = '%Y-%m-%d %H:%M:%S'

def loads(date:str) -> datetime:
    return pytz.utc.localize(
        datetime.strptime(date, template)
    )

def dumps(date:datetime) -> str:
    return date.strftime(template)

def timestamp_loads(date:str) -> datetime:
    return pytz.utc.localize(
        datetime.strptime(date, ts_template)
    )