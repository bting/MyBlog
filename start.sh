#!/bin/bash
source env/bin/activate
export FLASK_APP=blog.py
export FLASK_DEBUG=1
flask run
