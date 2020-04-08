from datetime import datetime, timedelta
from pytz import utc

template    = '%Y-%m-%d+%H:%M'
ts_template = '%Y-%m-%d %H:%M:%S'

def loads(date:str) -> datetime:
    return utc.localize(
        datetime.strptime(date, template)
    )

def dumps(date:datetime) -> str:
    return date.strftime(template)

def timestamp_loads(date:str) -> datetime:
    return utc.localize(
        datetime.strptime(date, ts_template)
    )

def compute_hours_since(dt:datetime) -> int:
    try:
        return str(
            int(
                (
                    utc.localize(datetime.now()) - utc.localize(dt)
                ).total_seconds() / 60 // 60
            )
        )
    except ValueError:
        return str(
            int(
                (
                    utc.localize(datetime.now()) - dt
                ).total_seconds() / 60 // 60
            )
        )