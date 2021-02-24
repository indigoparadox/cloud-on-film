
import logging
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request
from flask_wtf import CSRFProtect
from .config import Config
uwsgi_present = False
try:
    import uwsgi
    uwsgi_present = True
except ImportError:
    uwsgi_present = False

# Setup the database stuff.
db = SQLAlchemy()

csrf = CSRFProtect()

def create_app( config=None ):

    logging.basicConfig( level=logging.INFO )
    log_werkzeug = logging.getLogger( 'werkzeug' )
    log_werkzeug.setLevel( logging.ERROR )

    #logging.getLogger( 'sqlalchemy.engine' ).setLevel( logging.DEBUG )

    ''' App factory function. Call this from the runner/WSGI. '''

    app = Flask( __name__, instance_relative_config=False,
        static_folder='../static', template_folder='../templates' )

    # Load our hybrid YAML config.
    if config:
        app.config.from_object( config )
    else:
        with app.open_instance_resource( 'config.yml', 'r' ) as config_f:
            cfg = Config( config_f )
            app.config.from_object( cfg )

    db.init_app( app )

    csrf.init_app( app )

    with app.app_context():
        from . import routes

        db.create_all()

        app.register_blueprint( routes.libraries )

        # TODO: Installer.
        import cloud_on_film.files.picture

        return app
