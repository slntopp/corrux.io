import os
from datetime import datetime, timedelta
import pytz

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
            username=os.environ['BIGCO_USERNAME'],
            password=os.environ['BIGCO_PASSWORD']
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

    if last := db.stats.find_one({}, sort=[('timestamp', -1)]):
        if (pytz.utc.localize(datetime.now()) - pytz.utc.localize(last['timestamp'])).seconds // 60 == 0:
            return compute_from_last(last)
    
    client = adapter.BigCoAPIClient(
        'https://corrux-challenge.azurewebsites.net',
        username=os.environ['BIGCO_USERNAME'],
        password=os.environ['BIGCO_PASSWORD']
    )
    ts = last['timestamp'] if last else pytz.utc.localize(datetime(1, 1, 1))
    data = client.excavator_stats(ts, datetime.now())

    requests = list(map(lambda rec: UpdateOne({'timestamp': rec['timestamp']}, {'$set': rec}, upsert=True), data))
    db.stats.bulk_write(requests, ordered=False)

    return compute_from_last(data[-1])

@app.route('/excavator_average_fuel_rate_past_24h', methods=['GET'])
def fuel_rate():

    # обновлять данные из API

    first = db.stats.find_one({
        "timestamp": {
            "$gte": pytz.utc.localize(datetime(2019, 3, 1, 0, 0))
        }
    })
    last  = db.stats.find_one({
        "timestamp": {
            "$lte": pytz.utc.localize(datetime(2020, 3, 2, 0, 0))
        }
    }, sort = [('timestamp', -1)])

    print(first, last)

    fuel_used       = last['cumulative_fuel_used'] - first['cumulative_fuel_used']
    hours_operated  = last['cumulative_hours_operated'] - first['cumulative_hours_operated']

    print(fuel_used, ' / ', hours_operated, ' => ', fuel_used / hours_operated)

    return '', 200