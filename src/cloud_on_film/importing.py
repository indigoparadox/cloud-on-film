
import logging
import re
import os
import stat
import hashlib
import uuid
from flask import current_app
from datetime import datetime
from PIL import Image
from .models import db, HashEnum, Folder, FileItem, Tag, FileMeta, Library
from threading import Thread

class FileItemImportException( Exception ):
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
                except FileItemImportException as e:
                    self.logger.error( e )
                idx += 1

threads = {}

def start_import_thread( pictures ):
    id = uuid.uuid1()
    threads[id.hex] = ItemImportThread(
        pictures, current_app._get_current_object() )
    threads[id.hex].start()
    return id.hex

def path( path_list, path_type=Folder, library_id=None, parent=None ):

    logger = logging.getLogger( 'importing.path' )

    if not path_list:
        # No list left! We're done!
        return parent
    elif isinstance( path_list, str ):
        path_list = path_list.split( '/' )

    assert( isinstance( path_list, list ) )
    assert( len( path_list ) > 0 )

    # See if the item we're to create exists already.
    display_name = path_list.pop( 0 )
    query = db.session.query( path_type ) \
        .filter( path_type.display_name == display_name ) \
        .filter( path_type.parent_id == 
            (parent.id if parent else None) )
    item = query.first()
    if None == item:
        
        # Create the missing item.
        if path_type == Folder:
            assert( library_id )
            item = path_type( 
                library_id=library_id,
                parent_id=parent.id if parent else None,
                display_name=display_name )
        else:
            item = path_type(
                parent_id=parent.id if parent else None,
                display_name=display_name )
        db.session.add( item )
        db.session.flush()
        db.session.refresh( item )

        logger.debug( 'Created {} {} under {}'.format(
            path_type.__name__, display_name,
            parent.display_name if parent else 'root' ) )
        
    assert( item )
    if parent:
        assert( item.parent_id == parent.id )
    else:
        assert( item.parent_id == None )

    # Recurse into the next item.
    return path( path_list, path_type, library_id, item )

def picture( picture ):

    logger = logging.getLogger( 'libraries.import.picture' )

    # Find matching library.
    relative_path = None
    library = None
    for lib in Library.enumerate_all():
        match = re.match(
            r'^{}\/(.*)'.format( lib.absolute_path ), picture['filename'] )
        if match:
            relative_path = match.groups()[0]
            library = lib
            break

    # Don't accept pictures not in a library.
    if not library:
        raise FileItemImportException( 'Unable to find library for: {}'.format(
            picture['filename'] ) )

    # See if this picture's folder exists already.

    # Spelunk into folders starting from the library we found.
    folder_relative_path = os.path.dirname( relative_path )
    folder = path( folder_relative_path, library_id=lib.id )

    tags = []
    for tag_path in picture['tags']:
        tags.append( path( tag_path, path_type=Tag ) )

    # See if the picture already exists.
    display_name = os.path.basename( picture['filename'] )
    query = db.session.query( FileItem ) \
        .filter( FileItem.folder_id == folder.id ) \
        .filter( FileItem.display_name == display_name )
    if None != query.first():
        raise FileItemImportException(  'FileItem already exists: {}'.format(
            picture['filename'] ) )

    # Make sure the picture file exists.
    if not os.path.exists( picture['filename'] ):
        raise FileItemImportException( 'FileItem file does not exist: {}'.format(
            picture['filename'] ) )

    im = Image.open( picture['filename'] )
    if not im:
        raise FileItemImportException( 'Unable to read picture: {}'.format(
            picture['filename'] ) )

    ha = hashlib.md5()
    with open( picture['filename'], 'rb' ) as picture_f:
        buf = picture_f.read( 4096 )
        while 0 < len( buf ):
            ha.update( buf )
            buf = picture_f.read( 4096 )

    st = os.stat( picture['filename'] )

    pic = FileItem(
        display_name=display_name,
        folder_id=folder.id,
        timestamp=datetime.fromtimestamp( st[stat.ST_MTIME] ),
        filesize=st[stat.ST_SIZE],
        added=datetime.fromtimestamp( picture['time_created'] ),
        filehash=ha.hexdigest(),
        filehash_algo=HashEnum.md5,
        filetype='picture',
        comment=picture['comment'],
        rating=picture['rating'],
        nsfw=False )
    db.session.add( pic )
    #db.session.commit()
    db.session.flush()
    db.session.refresh( pic )

    #query = db.session.query( FileItem ) \
    #    .filter( FileItem.folder_id == folder.id ) \
    #    .filter( FileItem.display_name == display_name )
    #pic = query.first()
    assert( None != pic )
    meta = FileMeta(
        item_id=pic.id, key='width', value=str( im.size[0] ) )
    db.session.add( meta )
    #db.session.commit()

    meta = FileMeta(
        item_id=pic.id, key='height', value=str( im.size[1] ) )
    db.session.add( meta )
    #db.session.commit()

    for tag in tags:
        tag.files.append( pic )
    
    db.session.commit()

    logger.debug( 'Imported picture {} under {}'.format(
        display_name, folder.display_name ) )

