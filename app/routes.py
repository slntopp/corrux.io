from os import environ
from datetime import datetime, timedelta
from pytz import utc

from app import app, db
from flask import request, jsonify

from pymongo import UpdateOne

from app.utils import adapter, format_date

@app.route('/excavator_operational', methods=['GET'])
def get_operational_status():
    last = lambda: db.dashboard_data.find_one({}, { "_id": 0, "status": 1, "ts": 1 }, sort=[('ts', -1)])

    try:
        excavator_status = adapter.parse_dashboard(
            'https://corrux-challenge.azurewebsites.net/login',
            username=environ['BIGCO_USERNAME'],
            password=environ['BIGCO_PASSWORD']
        )[18:].lower()

        db.dashboard_data.insert_one({
            'status': excavator_status,
            'ts': datetime.now().timestamp()
        })
    except adapter.DashboardUnreachable as e:
        return jsonify({
            'last': last(),
            'e': 'Dashboard returned http code: %s' % e
        }), 523 # Origin Is Unreachable
    
    return (last(), 200)

@app.route('/excavator_operating_hours_since_last_maintenance', methods=['GET'])
def operating_hours():
    compute_from_last = lambda last: format_date.compute_hours_since(last['most_recent_maintenance'])

    now = utc.localize(datetime.now())

    if last := db.stats.find_one({}, sort=[('timestamp', -1)]):
        if (now - utc.localize(last['timestamp'])).seconds // 60 == 0:
            return compute_from_last(last)
    
    client = adapter.BigCoAPIClient(
        'https://corrux-challenge.azurewebsites.net',
        username=environ['BIGCO_USERNAME'],
        password=environ['BIGCO_PASSWORD']
    )
    ts = last['timestamp'] if last else now - timedelta(hours=24)
    data = client.excavator_stats(ts, now)

    requests = list(map(lambda rec: UpdateOne({'timestamp': rec['timestamp']}, {'$set': rec}, upsert=True), data))
    db.stats.bulk_write(requests, ordered=False)

    return compute_from_last(data[-1])

@app.route('/excavator_average_fuel_rate_past_24h', methods=['GET'])
def fuel_rate():

    compute_fuel_rate = lambda first, last: str((last['cumulative_fuel_used'] - first['cumulative_fuel_used']) / (last['cumulative_hours_operated'] - first['cumulative_hours_operated']))

    now = utc.localize(datetime.now())
    prev = now - timedelta(hours=24)

    pool = db.stats.find({
        "timestamp": {
            "$gte": prev,
            "$lte": now
        }
    })

    try:
        if last := pool[pool.count() - 1]:
            if (now - utc.localize(last['timestamp'])).seconds // 60 == 0:
                return compute_fuel_rate(pool[0], last), 200
    except IndexError:
        last = None
    
    client = adapter.BigCoAPIClient(
        'https://corrux-challenge.azurewebsites.net',
        username=environ['BIGCO_USERNAME'],
        password=environ['BIGCO_PASSWORD']
    )
    ts = last['timestamp'] if last else prev
    data = client.excavator_stats(ts, now)

    requests = list(map(lambda rec: UpdateOne({'timestamp': rec['timestamp']}, {'$set': rec}, upsert=True), data))
    db.stats.bulk_write(requests, ordered=False)
    
    return compute_fuel_rate(pool[0], data[-1]), 200

@app.route('/excavator_last_10_CAN_messages', methods=['GET'])
def last_10_can_msg():
    
    get_last_objects = lambda lim: list(db.can_msgs.find({}, {"_id": 0}, sort=[('timestamp', -1)]).limit(lim))

    now = utc.localize(datetime.now())

    try:
        if last := db.can_msgs.find_one({}, sort=[('timestamp', -1)]):
            if (now - utc.localize(last['timestamp'])).seconds // 60 == 0:
                return jsonify(get_last_objects(10))
    except IndexError:
        last = None

    client = adapter.BigCoAPIClient(
        'https://corrux-challenge.azurewebsites.net',
        username=environ['BIGCO_USERNAME'],
        password=environ['BIGCO_PASSWORD']
    )
    data = client.can_stream()
    requests = list(map(lambda rec: UpdateOne({'timestamp': rec['timestamp'], 'id': rec['id']}, {'$set': rec}, upsert=True), data))
    db.can_msgs.bulk_write(requests, ordered=True)

    return jsonify(get_last_objects(10))