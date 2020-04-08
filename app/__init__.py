from flask import Flask
import asyncio
import json
from bson.objectid import ObjectId
from flask_pymongo import PyMongo
from datetime import datetime

class JSONEncoder(json.JSONEncoder):
    ''' extend json-encoder class '''

    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return str(o)
        return json.JSONEncoder.default(self, o)

app = Flask(__name__)

app.config.from_object('app.conf.Config')
mongo = PyMongo(app)
db = mongo.db.corrux

app.json_encoder = JSONEncoder

from app import routes