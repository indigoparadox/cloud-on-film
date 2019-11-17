#!/usr/bin/env python3

import logging 
import util
from flask import Flask, render_template, request
from database import db_session
uwsgi_present = False
try:
    import uwsgi
    uwsgi_present = True
except ImportError:
    uwsgi_present = False

app = Flask(__name__)
app.secret_key = 'development' # TODO: Change me.

@app.route( '/' )
def cloud_root():
    config = util.get_config()

    return render_template( 'root.html' )

@app.teardown_appcontext
def shutdown_session( exception=None ):
    db_session.remove()

if '__main__' == __name__:
    logging.basicConfig( level=logging.INFO )
    logger = logging.getLogger( 'main' )

    if not uwsgi_present:
        logger.warning( 'uwsgi not present; connection locking unavailable.' )

    app.run()

