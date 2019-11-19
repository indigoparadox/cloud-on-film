
import logging 
import os
from .models import db, Library, Picture, Tag
import re

def update():

    logger = logging.getLogger( 'cloud.update' )
    
    for dirpath, dirnames, filenames in os.walk:
        for dirname in dirnames:
            logger.info( dirname )

def enumerate_libs():

    query = db.session.query( Library )
    return query.all()

def enumerate_path( machine_name, relative_path ):

    query = db.session.query( Picture ) \
        .join( Library, Picture.library ) \
        .filter( Library.machine_name == machine_name )

    return query.all()

def import_picture( picture ):

    logger = logging.getLogger( 'libraries.import.picture' )

    # Find matching library.
    relative_path = None
    library = None
    for lib in enumerate_libs():
        match = re.match(
            r'^{}\/(.*)'.format( lib.absolute_path ), picture['filename'] )
        if match:
            relative_path = match.groups()[0]
            library = lib
            break

    # Don't accept pictures not in a library.
    if not library:
        logger.warning( 'Unable to find library for: {}'.format(
            picture['filename'] ) )
        return

    #pic = Picture(
    #db.session.add( pic )
    #db.session.commit()

