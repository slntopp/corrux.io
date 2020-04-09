from os import environ

class Config(object):
    DEBUG = False

    # MONGO_URI = 'mongodb://mongo/corrux'
    MONGO_URI = environ['DB']
    CSRF_ENABLED = False

