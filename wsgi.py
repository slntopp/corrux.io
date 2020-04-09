#!/usr/bin/env python3.8
from os import environ
from app import app

if __name__ == "__main__":
    app.run(host=environ['HOST'], port=environ['PORT'])