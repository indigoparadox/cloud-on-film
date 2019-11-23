
import logging
import re
import os
import stat
import hashlib
from datetime import datetime
from PIL import Image
from . import libraries
from .models import db, HashEnum, Folder, FileItem, Tag, FileMeta

class FileItemImportException( Exception ):
    pass

def path( rel_path, path_type=Folder, library_id=None ):

    logger = logging.getLogger( 'importing.path' )

    path_list = rel_path.split( '/' )

    parent = None
    item = None
    for subitem in path_list:
        query = db.session.query( path_type ) \
            .filter( path_type.display_name == subitem )

        # Parent is either folder from the last iteration or NULL for the root.
        parent_id = None
        if parent:
            parent_id = parent.id
        query = query.filter( path_type.parent_id == parent_id )

        item = query.first()
        if None == item:
            
            # Create the missing folder.
            new_item = path_type( parent_id=parent_id, display_name=subitem )
            if isinstance( new_item, Folder ):
                new_item.lbrary_id = library_id
            db.session.add( new_item )
            #db.session.commit()
            db.session.flush()
            db.session.refresh( new_item )

            if parent:
                logger.info( 'Created {} under {}'.format(
                    subitem, parent.display_name ) )
            else:
                logger.info(
                    'Created {} under root'.format( subitem ) )

            # Get the ID for the just-created folder.
            #query = db.session.query( path_type ) \
            #    .filter( path_type.display_name == subitem ) \
            #    .filter( path_type.parent_id == parent_id )
            #item = query.first()
            item = new_item

        assert( item )
        parent = item

    return item

def picture( picture ):

    logger = logging.getLogger( 'libraries.import.picture' )

    # Find matching library.
    relative_path = None
    library = None
    for lib in libraries.enumerate_libs():
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

    logger.info( 'Imported picture {} under {}'.format(
        display_name, folder.display_name ) )

