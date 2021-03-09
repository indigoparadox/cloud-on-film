
import logging
import re
import os
import stat
import hashlib
import uuid
from flask import current_app
from datetime import datetime
from PIL import Image
from .models import InvalidFolderException, db, HashEnum, Folder, Item, Tag, Library
#from .files.picture import Picture
from threading import Thread

class ItemImportException( Exception ):
    pass

class ItemImportThread( Thread ):
    def __init__( self, pictures, app ):
        self.progress = 0
        self.filename = ''
        self.pictures = pictures
        self.app = app
        super().__init__()

    def run( self ):
        with self.app.app_context():
            self.logger = logging.getLogger(
                'importing.threads.' + str( self.ident ) )

            pictures_len = len( self.pictures )
            idx = 0
            for pic in self.pictures:
                self.progress = 100 * idx / pictures_len
                self.filename = pic['filename']
                try:
                    picture( pic )
                except ItemImportException as e:
                    self.logger.error( e )
                idx += 1

threads = {}

def start_import_thread( pictures ):
    id = uuid.uuid1()
    threads[id.hex] = ItemImportThread(
        pictures, current_app._get_current_object() )
    threads[id.hex].start()
    return id.hex

def picture( picture ):

    logger = logging.getLogger( 'libraries.import.picture' )

    current_uid = -1 # TODO: override current_uid

    # Find matching library.
    relative_path = None
    library = None
    for lib in Library.enumerate_all( -1 ):
        match = re.match(
            r'^{}\/(.*)'.format( lib.absolute_path ), picture['filename'] )
        if match:
            relative_path = match.groups()[0]
            library = lib
            print( relative_path )
            break

    # Don't accept pictures not in a library.
    if not library:
        raise ItemImportException( 'Unable to find library for: {}'.format(
            picture['filename'] ) )

    # See if this picture's folder exists already.

    # Spelunk into folders starting from the library we found.
    # Circumvent user checking.
    folder_relative_path = os.path.dirname( relative_path )
    try:
        folder = Folder.from_path( library.id, folder_relative_path, current_uid )
    except InvalidFolderException:
        raise ItemImportException( 'Folder does not exist: {}'.format(
            folder_relative_path ) )

    # See if the picture already exists.
    name = os.path.basename( picture['filename'] )
    query = db.session.query( Item ) \
        .filter( Item.folder_id == folder.id ) \
        .filter( Item.name == name )
    if None != query.first():
        raise ItemImportException(  'Item already exists: {}'.format(
            picture['filename'] ) )

    # Make sure the picture file exists.
    if not os.path.exists( picture['filename'] ):
        raise ItemImportException( 'Item file does not exist: {}'.format(
            picture['filename'] ) )

    with Image.open( picture['filename'] ) as im:
        if not im:
            raise ItemImportException( 'Unable to read picture: {}'.format(
                picture['filename'] ) )

        st = os.stat( picture['filename'] )

        from .files.picture import Picture
        pic = Picture(
            name=name,
            folder_id=folder.id,
            timestamp=datetime.fromtimestamp( st[stat.ST_MTIME] ),
            size=st[stat.ST_SIZE],
            added=datetime.fromtimestamp( picture['time_created'] ),
            hash=Item.hash_file( picture['filename'] ),
            hash_algo=1 )
        db.session.add( pic )
        db.session.flush()
        db.session.refresh( pic )

        pic.tags += [Tag.from_path( t ) for t in picture['tags']]

        if picture['comment']:
            pic.meta['comment'] = picture['comment']

        pic.meta['rating'] = picture['rating']
        pic.meta['width'] = picture['width']
        pic.meta['height'] = picture['height']

    db.session.commit()

    logger.debug( 'Imported picture {} under {}'.format(
        name, folder.name ) )

