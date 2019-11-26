
import logging 
import os
import stat
import hashlib
from .models import db, Library, FileItem, Tag, HashEnum, Folder, FileMeta
import re
from datetime import datetime
from flask import current_app, abort
from sqlalchemy import or_

class InvalidFolderException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.display_name = kwargs['display_name']
        self.parent_id = kwargs['parent_id']
        super().__init__( *args )

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
                raise InvalidFolderException(
                    parent_id=parent_folder_id,
                    display_name=path_element_name )
            parent_folder_id = parent_folder.id

    if parent_folder:
        return parent_folder.id
    else:
        return None

def enumerate_path_folders( machine_name, relative_path ):

    parent_folder_id = get_path_folder_id( machine_name, relative_path )

    # Build a list of folders inside of the current folder.
    query = db.session.query( Folder ) \
        .filter( Folder.parent_id == parent_folder_id ) \
        .order_by( Folder.display_name.asc() )
    folders = query.all()

    return folders
    
def enumerate_path_pictures( machine_name, relative_path ):

    parent_folder_id = get_path_folder_id( machine_name, relative_path )

    query = db.session.query( FileItem ) \
        .filter( FileItem.folder_id == parent_folder_id ) \
        .order_by( FileItem.display_name.asc() )
    return query.all()
