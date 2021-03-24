
import os
import logging
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request
from flask_wtf import CSRFProtect

# Setup the database stuff.
db = SQLAlchemy()

csrf = CSRFProtect()

def create_app( config=None ):

    ''' App factory function. Call this from the runner/WSGI. '''

    logging.basicConfig( level=logging.INFO )
    log_werkzeug = logging.getLogger( 'werkzeug' )
    log_werkzeug.setLevel( logging.ERROR )

    #logging.getLogger( 'sqlalchemy.engine' ).setLevel( logging.DEBUG )

    app = Flask( __name__, instance_relative_config=False,
        static_folder='static', template_folder='templates' )

    app.config['ITEMS_PER_PAGE'] = \
        int( os.getenv( 'COF_ITEMS_PER_PAGE' ) ) if \
        os.getenv( 'COF_ITEMS_PER_PAGE' ) else 20
    app.config['THUMBNAIL_PATH'] = \
        os.getenv( 'COF_THUMBNAIL_PATH' ) if \
        os.getenv( 'COF_THUMBNAIL_PATH' ) else '/tmp'
    app.config['SQLALCHEMY_QUERY_DEBUG'] = \
        os.getenv( 'SQLALCHEMY_QUERY_DEBUG' ) if \
        os.getenv( 'SQLALCHEMY_QUERY_DEBUG' ) else 'false'
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        os.getenv( 'SQLALCHEMY_DATABASE_URI' ) if \
        os.getenv( 'SQLALCHEMY_DATABASE_URI' ) else 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = \
        os.getenv( 'SECRET_KEY' ) if \
        os.getenv( 'SECRET_KEY' ) else 'development'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ALLOWED_PREVIEWS'] = [
        '160, 120',
        '360, 270',
        '230, 172'
    ]

    if config:
        app.config.from_object( config )

    db.init_app( app )

    csrf.init_app( app )

    with app.app_context():
        from . import routes
        from cloud_on_film.blueprints.ajax import ajax
        from cloud_on_film.blueprints.contents import contents

        db.create_all()

        app.register_blueprint( routes.libraries )
        app.register_blueprint( ajax )
        app.register_blueprint( contents )

        return app
