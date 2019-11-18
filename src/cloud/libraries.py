
import logging 
import os
from .models import db, Library, Picture

def update():

    logger = logging.getLogger( 'cloud.update' )
    
    for dirpath, dirnames, filenames in os.walk:
        for dirname in dirnames:
            logger.info( dirname )

def enumerate():

    query = db.session.query( Library )
    return query.all()

def enumerate_path( machine_name, relative_path ):

    query = db.session.query( Picture ) \
        .join( Library, Picture.library_id ) \
        .filter( Library.machine_name == machine_name )

    return query.all()

