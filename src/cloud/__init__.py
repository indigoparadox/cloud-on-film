
import logging
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request
from .config import Config
uwsgi_present = False
try:
    import uwsgi
    uwsgi_present = True
except ImportError:
    logger = logging.getLogger( 'init.uwsgi' )
    uwsgi_present = False
    logger.warning( 'uwsgi not present; connection locking unavailable.' )

# Setup the database stuff.
db = SQLAlchemy()

def create_app():

    ''' App factory function. Call this from the runner/WSGI. '''

    app = Flask( __name__, instance_relative_config=False,
        static_folder='../static', template_folder='../templates' )

    # Load our hybrid YAML config.
    with app.open_instance_resource( 'config.yml', 'r' ) as config_f:
        cfg = Config( config_f )
        app.config.from_object( cfg )

    db.init_app( app )
    
    with app.app_context():
        from . import routes

        db.create_all()

        return app

