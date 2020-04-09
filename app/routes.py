from os import environ
from datetime import datetime, timedelta
from pytz import utc

from app import app, db
from flask import request, jsonify

from pymongo import UpdateOne

from app.utils import adapter, format_date

@app.route('/excavator_operational', methods=['GET'])
def get_operational_status():
    """
    GET /excavator_operational - 
        this endpoint returns whether the machine is operational or not,
        based on the last query (scrape) of the BigCo asset manager.
        It will be a string that says either 'operational' or 'down'.
    """

    # This lambda is getting last(by timestamp) record from the DB
    last = lambda: db.dashboard_data.find_one({}, { "_id": 0, "status": 1, "ts": 1 }, sort=[('ts', -1)])

    try:
        # Parsing dashboard
        excavator_status = adapter.parse_dashboard(
            'https://corrux-challenge.azurewebsites.net/login',
            username=environ['BIGCO_USERNAME'], # Getting username and password from ENV variables 
            password=environ['BIGCO_PASSWORD']
        )[18:].lower()

        # Saving obtained data to DB
        db.dashboard_data.insert_one({
            'status': excavator_status,
            'ts': datetime.now().timestamp()
        })
    except adapter.DashboardUnreachable as e: 
        # Returning last record from DB and response code if Dashboard is Unreachable
        return jsonify({
            'last': last(),
            'e': 'Dashboard returned http code: %s' % e
        }), 523 # With 523 Code(Origin Is Unreachable)
    
    return last()['status'], 200

@app.route('/excavator_operating_hours_since_last_maintenance', methods=['GET'])
def operating_hours():
    """
    GET /excavator_operating_hours_since_last_maintenance -
        this endpoint returns how many operating hours ago (from now) the most recent maintenance was.
    """
    # This lambda is computing number of hours between 'most_recent_maintenance' from given obj and now
    compute_from_last = lambda last: format_date.compute_hours_since(last['most_recent_maintenance'])

    now = utc.localize(datetime.now())

    # Getting last saved record from stats
    if last := db.stats.find_one({}, sort=[('timestamp', -1)]):
        # Checking if last record isn't elder than 1 minute
        if (now - utc.localize(last['timestamp'])).seconds // 60 == 0:
            # If it's so, computing using last saved
            return compute_from_last(last)
    
    # Getting new stats from API
    client = adapter.BigCoAPIClient(
        'https://corrux-challenge.azurewebsites.net',
        username=environ['BIGCO_USERNAME'],
        password=environ['BIGCO_PASSWORD']
    )
    # If last is given: using its timestamp as start_date | else now minus 24 hours
    ts = last['timestamp'] if last else now - timedelta(hours=24)
    data = client.excavator_stats(ts, now) # Obtaining stats

    # Writting new data from API to DB using Update and upsert,
    # to insert only if not exist 
    requests = list(map(lambda rec: UpdateOne({'timestamp': rec['timestamp']}, {'$set': rec}, upsert=True), data))
    db.stats.bulk_write(requests, ordered=False)

    # Computing using last form obtained data
    return compute_from_last(data[-1])

@app.route('/excavator_average_fuel_rate_past_24h', methods=['GET'])
def fuel_rate():
    """
    GET /excavator_average_fuel_rate_past_24h
        this endpoint returns the average fuel rate.
    """
    # This lambda is computing fuel rate using given border-objects
    compute_fuel_rate = lambda first, last: str((last['cumulative_fuel_used'] - first['cumulative_fuel_used']) / (last['cumulative_hours_operated'] - first['cumulative_hours_operated']))

    now = utc.localize(datetime.now())
    prev = now - timedelta(hours=24)

    # Getting stats from last 24 hours
    pool = db.stats.find({
        "timestamp": {
            "$gte": prev,
            "$lte": now
        }
    })

    try:
        # Trying to get last record
        if last := pool[pool.count() - 1]:
            # Checking if last record isn't elder than 1 minute
            if (now - utc.localize(last['timestamp'])).seconds // 60 == 0:
                # If it's so, computing using last saved
                return compute_fuel_rate(pool[0], last), 200
    except IndexError: # If no stats is stored in DB
        last = None
    
    # Getting new stats from API
    client = adapter.BigCoAPIClient(
        'https://corrux-challenge.azurewebsites.net',
        username=environ['BIGCO_USERNAME'],
        password=environ['BIGCO_PASSWORD']
    )
    # If last is given using it as start_time | else gettings stats for last 24 hours from API
    ts = last['timestamp'] if last else prev
    data = client.excavator_stats(ts, now)

    # Writting new data from API to DB using Update and upsert,
    # to insert only if not exist 
    requests = list(map(lambda rec: UpdateOne({'timestamp': rec['timestamp']}, {'$set': rec}, upsert=True), data))
    db.stats.bulk_write(requests, ordered=False)
    
    return compute_fuel_rate(pool[0], data[-1]), 200

@app.route('/excavator_last_10_CAN_messages', methods=['GET'])
def last_10_can_msg():
    """
    GET /excavator_last_10_CAN_messages - 
        this endpoint simply returns the ten most recent CAN messages.
    """

    # This lambda returns last can messages limited by lim param as list, without mongo '_id' field
    get_last_objects = lambda lim: list(db.can_msgs.find({}, {"_id": 0}, sort=[('timestamp', -1)]).limit(lim))

    now = utc.localize(datetime.now())

    try:
        # Getting last CAN message
        if last := db.can_msgs.find_one({}, sort=[('timestamp', -1)]):
            # Checking if it isn't elder than 1 minute
            if (now - utc.localize(last['timestamp'])).seconds // 60 == 0:
                # If it's so, returning last 10 DB records
                return jsonify(get_last_objects(10))
    except IndexError:
        last = None

    # Obtaining messages from API
    client = adapter.BigCoAPIClient(
        'https://corrux-challenge.azurewebsites.net',
        username=environ['BIGCO_USERNAME'],
        password=environ['BIGCO_PASSWORD']
    )
    data = client.can_stream()
    # Writting new data from API to DB using Update and upsert,
    # to insert only if not exist 
    requests = list(map(lambda rec: UpdateOne({'timestamp': rec['timestamp'], 'id': rec['id']}, {'$set': rec}, upsert=True), data))
    db.can_msgs.bulk_write(requests, ordered=True)

    # Returning last 10 DB records
    return jsonify(get_last_objects(10))