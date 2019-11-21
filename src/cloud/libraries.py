
import logging 
import os
import stat
import hashlib
from .models import db, Library, FileItem, Tag, HashEnum, Folder, FileMeta
from PIL import Image
import re
from datetime import datetime
from flask import current_app, abort

class FileItemImportException( Exception ):
    pass

def update():

    logger = logging.getLogger( 'cloud.update' )
    
    for dirpath, dirnames, filenames in os.walk:
        for dirname in dirnames:
            logger.info( dirname )

def enumerate_libs():

    query = db.session.query( Library )

    return query.all()

current_app.jinja_env.globals.update( enumerate_libs=enumerate_libs )

def build_folder_path( folder_id ):
    
    parent_list = []

    # Traverse the folder's parents upwards.
    while isinstance( folder_id, int ):
        query = db.session.query( Folder ) \
            .filter( Folder.id == folder_id )
        folder = query.first()
        if folder:
            parent_list.insert( 0, folder.display_name )
            folder_id = folder.parent_id
        else:
            folder_id = None

    return '/'.join( parent_list )

current_app.jinja_env.globals.update( build_folder_path=build_folder_path )

def build_file_path( file_id, absolute_fs=False ):
    query = db.session.query( FileItem ) \
        .filter( FileItem.id == file_id )
    item = query.first()
    assert( None != item )

    file_path = os.path.join(
        build_folder_path( item.folder.id ),
        item.display_name )

    if absolute_fs:
        file_path = os.path.join( item.folder.library.absolute_path, file_path )

    return file_path

def get_path_folder_id( machine_name, relative_path ):

    parent_folder = None
    parent_folder_id = None
    library_id = None

    # Drill down through the path to the current folder.
    if relative_path:
        path_element_list = relative_path.split( '/' )
        for path_element_name in path_element_list:
            query = db.session.query( Folder ) \
                .filter( Folder.parent_id == parent_folder_id ) \
                .filter( Folder.display_name == path_element_name ) \
                .join( Library ) \
                .filter( Library.machine_name == machine_name )
            parent_folder = query.first()
            if not parent_folder:
                abort( 404 )
            parent_folder_id = parent_folder.id

    if parent_folder:
        return parent_folder.id
    else:
        return None

def enumerate_path_folders( machine_name, relative_path ):

    parent_folder_id = get_path_folder_id( machine_name, relative_path )

    # Build a list of folders inside of the current folder.
    query = db.session.query( Folder ) \
        .filter( Folder.parent_id == parent_folder_id )
    return query.all()
    
def enumerate_path_pictures( machine_name, relative_path ):

    parent_folder_id = get_path_folder_id( machine_name, relative_path )

    query = db.session.query( FileItem ) \
        .filter( FileItem.folder_id == parent_folder_id )
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
        raise FileItemImportException( 'Unable to find library for: {}'.format(
            picture['filename'] ) )

    # See if this picture's folder exists already.

    # Spelunk into folders starting from the library we found.
    folder_relative_path = os.path.dirname( relative_path )
    folder_path_list = folder_relative_path.split( '/' )
    parent_folder = None
    folder = None
    for subfolder in folder_path_list:
        query = db.session.query( Folder ) \
            .filter( Folder.display_name == subfolder )

        # Parent is either folder from the last iteration or NULL for the root.
        parent_folder_id = None
        if parent_folder:
            parent_folder_id = parent_folder.id
        query = query.filter( Folder.parent_id == parent_folder_id )

        folder = query.first()
        if None == folder:
            
            # Create the missing folder.
            new_folder = Folder(
                library_id=lib.id, parent_id=parent_folder_id,
                display_name=subfolder)
            db.session.add( new_folder )
            db.session.commit()

            if parent_folder:
                logger.info( 'Created folder {} under {}'.format(
                    subfolder, parent_folder.display_name ) )
            else:
                logger.info(
                    'Created folder {} under root'.format( subfolder ) )

            # Get the ID for the just-created folder.
            query = db.session.query( Folder ) \
                .filter( Folder.display_name == subfolder ) \
                .filter( Folder.parent_id == parent_folder_id )
            folder = query.first()

        assert( folder )
        parent_folder = folder

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
    db.session.commit()

    query = db.session.query( FileItem ) \
        .filter( FileItem.folder_id == folder.id ) \
        .filter( FileItem.display_name == display_name )
    pic = query.first()
    assert( None != pic )
    meta = FileMeta(
        item_id=pic.id, key='width', value=str( im.size[0] ) )
    db.session.add( meta )
    db.session.commit()

    meta = FileMeta(
        item_id=pic.id, key='height', value=str( im.size[1] ) )
    db.session.add( meta )
    db.session.commit()

    logger.info( 'Imported picture {} under {}'.format(
        display_name, folder.display_name ) )

