import os
from datetime import datetime, timedelta
import pytz

from app import app, db
from flask import request, jsonify

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
    print(db.stats.find())
    ts = datetime(1, 1, 1)
    if last := db.stats.find_one({}, sort=[('ts', -1)]):
        ts = format_date.timestamp_loads(last['timestamp'])
        if (pytz.utc.localize(datetime.now()) - ts).seconds // 60 == 0:
            pass # compute from object

    client = adapter.BigCoAPIClient(
        'https://corrux-challenge.azurewebsites.net',
        username=os.environ['BIGCO_USERNAME'],
        password=os.environ['BIGCO_PASSWORD']
    )


    # if:             db = [{a:0, b:0},{a:1, b:1},{a:2, b:2}]
    # update with:  data = [{a:0, b:1},{a:1, b:2},{a:2, b:3}]
    # so like -
    #  for i in range(db):
    #       where db[i].a == data[i].a: 
    #           db[i].b = data[i].b 
    db.stats.update_many(
        {'_id': { "$regex": "." }},
        client.excavator_stats(ts, datetime.now()),
        upsert=True
    )

    return '', 200