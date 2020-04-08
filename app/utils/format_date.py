from datetime import datetime, timedelta
from pytz import utc

# API timestamp basic template
template    = '%Y-%m-%d+%H:%M'
# API timestamp with seconds template
ts_template = '%Y-%m-%d %H:%M:%S'

def loads(date:str) -> datetime:
    """ Loads date from string(timestamp) to datetime.datetime object
    :type date:str
    :param date: date as string
    """
    return utc.localize(
        datetime.strptime(date, template)
    )

def dumps(date:datetime) -> str:
    """ Saves date from datetime.datetime to string
    :type date:datetime:
    :param date: date as datetime.datetime object
    """
    return date.strftime(template)

def timestamp_loads(date:str) -> datetime:
    """ Loads date from string(timestamp with seconds) to datetime.datetime
    :type date:str
    :param date: timestamp as string
    """
    return utc.localize(
        datetime.strptime(date, ts_template)
    )

def compute_hours_since(of:datetime, to:datetime=datetime.now()) -> str:
    """ Calculates number of hours between of and to
    :type of: datetime.datetime
    :param of: from what point to calculate
    
    :type to:datetime.datetime
    :param to: to what point to calculate
    """

    # Dates can be offset-naive and offset-aware
    # and its impossible to substract dates with different types 
    if not to.tzinfo and not of.tzinfo: # If both are offset-aware(not offset-naive)
        diff = to - of
    elif to.tzinfo: # If to is offset-aware
        diff = to - utc.localize(of)
    elif of.tzinfo: # If of is offset-aware
        diff = utc.localize(to) - of
    else: # If both are offset-naive
        diff = utc.localize(to) - utc.localize(of)

    return str(
        int(
            diff.total_seconds() // 60 // 60
        )
    )