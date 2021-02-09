
import os
import errno
import stat
import hashlib
from sqlalchemy.orm import query
from . import db
from enum import Enum
from flask import current_app
from PIL import Image
from datetime import datetime

class HashEnum( Enum ):
    md5 = 1
    sha128 = 2
    sha256 = 3

class InvalidFolderException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.display_name = kwargs['display_name'] if 'display_name' in kwargs else None
        self.absolute_path = kwargs['absolute_path'] if 'absolute_path' in kwargs else None
        self.parent_id = kwargs['parent_id'] if 'parent_id' in kwargs else None
        self.library_id = kwargs['library_id']
        super().__init__( *args )

class LibraryRootException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.library_id = kwargs['library_id']
        super().__init__( *args )

class User( db.Model ):

    __tablename__ = 'users'

    id = db.Column( db.Integer, primary_key=True )
    email = db.Column(
        db.String( 128 ), index=True, unique=True, nullable=False )
    created = db.Column(
        db.DateTime, index=False, unique=False, nullable=False )
    tags = db.relationship( 'Tag', back_populates='owner' )

class FileMeta( db.Model ):

    __tablename__ = 'file_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    item_id = db.Column( db.Integer, db.ForeignKey( 'files.id' ) )
    item = db.relationship( 'FileItem', back_populates='_meta' )

files_tags = db.Table( 'files_tags', db.metadata,
    db.Column( 'files_id', db.Integer, db.ForeignKey( 'files.id' ) ),
    db.Column( 'tags_id', db.Integer, db.ForeignKey( 'tags.id' ) ) )

class TagMeta( db.Model ):

    __tablename__ = 'tag_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    item_id = db.Column( db.Integer, db.ForeignKey( 'tags.id' ) )
    item = db.relationship( 'Tag', back_populates='meta' )

    @staticmethod
    def store_aspect( item ):

        def calc_gcd( a, b ):
            if 0 == b:
                return a
            return calc_gcd( b, a % b )

        width = int( item.meta( 'width' ) )
        height = int( item.meta( 'height' ) )
        aspect_r = calc_gcd( width, height )
        aspect_w = int( width / aspect_r )
        aspect_h = int( height / aspect_r )

        if 10 == aspect_h and 16 == aspect_w:
            item.meta( 'aspect', '16x10' )
        elif 9 == aspect_h and 16 == aspect_w:
            item.meta( 'aspect', '16x9' )
        elif 3 == aspect_h and 4 == aspect_w:
            item.meta( 'aspect', '4x3' )

    @staticmethod
    def store_width( item ):
        # TODO
        pass

class Tag( db.Model ):

    __tablename__ = 'tags'

    id = db.Column( db.Integer, primary_key=True )
    parent_id = db.Column( 
        db.Integer, db.ForeignKey( 'tags.id' ), nullable=True )
    parent = db.relationship( 'Tag', remote_side=[id] )
    #tag_parent = db.relationship( 'Tag', remote_side=[id] )
    display_name = db.Column(
        db.String( 64 ), index=True, unique=False, nullable=False )
    owner = db.relationship( 'User', back_populates='tags' )
    owner_id = db.Column( db.Integer, db.ForeignKey( 'users.id' ) )
    file_id = db.Column( db.Integer, db.ForeignKey( 'files.id' ) )
    files = db.relationship(
        'FileItem', secondary=files_tags, back_populates='tags' )
    meta = db.relationship( 'TagMeta', back_populates='item' )
    children = db.relationship( 'Tag', backref=db.backref(
        'tag_parent', remote_side=[id] ) )

    def __str__( self ):
        return self.display_name

    def __repr__( self ):
        return self.display_name

    @staticmethod
    def enumerate_roots():

        tagalias = db.aliased( Tag )
        query = db.session.query( Tag ) \
            .join( tagalias, Tag.parent ) \
            .filter( db.or_( Tag.parent_id == None,
                tagalias.display_name == '' ) )

        return query.all()

class FileItem( db.Model ):

    __tablename__ = 'files'

    id = db.Column( db.Integer, primary_key=True )
    _meta = db.relationship( 'FileMeta', back_populates='item' )
    folder_id = db.Column( db.Integer, db.ForeignKey( 'folders.id' ) )
    folder = db.relationship( 'Folder', back_populates='files' )
    tag_id = db.Column( db.Integer, db.ForeignKey( 'tags.id' ) )
    tags = db.relationship(
        'Tag', secondary=files_tags, back_populates='files' )
    display_name = db.Column(
        db.String( 256 ), index=True, unique=False, nullable=False )
    filetype= db.Column(
        db.String( 12 ), index=True, unique=False, nullable=True )
    timestamp = db.Column(
        db.DateTime, index=False, unique=False, nullable=False )
    filesize = db.Column(
        db.Integer, index=False, unique=False, nullable=False )
    added = db.Column( db.DateTime, index=False, unique=False, nullable=False )
    filehash = db.Column(
        db.String( 512 ), index=False, unique=False, nullable=False )
    filehash_algo = db.Column(
        db.Enum( HashEnum ), index=False, unique=False, nullable=False )
    nsfw = db.Column( db.Boolean, index=True, unique=False, nullable=False )

    def __str__( self ):
        return self.display_name

    def __repr__( self ):
        return self.display_name

    def meta( self, key, value=None, default=None ):

        ''' Get a piece of FileItem metadata, or set it if value != None. '''

        query = db.session.query( FileMeta ) \
            .filter( FileMeta.item_id == self.id ) \
            .filter( FileMeta.key == key )
        all = query.all()
        if value and 0 < len( all ):
            # Create a new metadata item.
            all[0].value = value
            db.session.commit()

        elif value and 0 >= len( query.all() ):
            # Create a new metadata item.
            meta = FileMeta( key=key, value=value, item_id=self.id )
            db.session.add( meta )
            db.session.commit()

        elif 0 < len( all ) and not value:
            return all[0].value

        else:
            return default

    def meta_int( self, key, default=None ):
        return int( self.meta( key, default=default ) )

    def open_image( self ):
        im = Image.open( self.absolute_path )
        if not im:
            raise FileNotFoundError( errno.ENOENT, os.strerror(errno.ENOENT), self.absolute_path )
        return im

    @property
    def path( self ):
        return '/'.join( [self.folder.path, self.display_name] )

    @property
    def absolute_path( self ):
        return '/'.join( [self.folder.absolute_path, self.display_name] )
    
    @staticmethod
    def hash_file( library_id, relative_path, hash_algo=HashEnum.md5 ):
        if not isinstance( library_id, Library ):
            library_id = Library.from_id( library_id )

        # We don't need to bother with the folder, since this can just fail if the file doesn't really exist.
        absolute_path = os.path.join( library_id.absolute_path, relative_path )
        ha = hashlib.md5()
        with open( absolute_path, 'rb' ) as file_f:
            buf = file_f.read( 4096 )
            while 0 < len( buf ):
                ha.update( buf )
                buf = file_f.read( 4096 )
        return ha.hexdigest()

    @staticmethod
    def from_id( file_id ):
        query = db.session.query( FileItem ) \
            .filter( FileItem.id == file_id )
        return query.first()

    @staticmethod
    def from_path( library_id, relative_path ):
        # TODO: Check if exists on FS and create FileItem if so but not in DB.

        filename = os.path.basename( relative_path )
        
        # Get the folder from path so we're sure the folder is added to the DB before the file is.
        folder = Folder.from_path( library_id, os.path.dirname( relative_path ) )
        item = db.session.query( FileItem ) \
            .filter( FileItem.folder_id == folder.id ) \
            .filter( FileItem.display_name == os.path.basename( relative_path ) ) \
            .first()

        absolute_path = os.path.join( folder.absolute_path, filename )

        if not item and not os.path.exists( absolute_path ):
            raise FileNotFoundError( errno.ENOENT, os.strerror(errno.ENOENT), absolute_path )
        
        elif not item:
            # Item doesn't exist in DB, but it does on FS, so add it to the DB.
            st = os.stat( absolute_path )
            current_app.logger.info( 'creating entry for file: {}'.format( absolute_path ) )
            item = FileItem(
                display_name=filename,
                folder_id=folder.id,
                timestamp=datetime.fromtimestamp( st[stat.ST_MTIME] ),
                filesize=st[stat.ST_SIZE],
                added=datetime.now(),
                filehash=FileItem.hash_file( library_id, relative_path, HashEnum.md5 ),
                filehash_algo=HashEnum.md5,
                # TODO: Determine the file type dynamically.
                filetype='picture',
                nsfw=False )
            db.session.add( item )
            db.session.commit()

        return item

class FolderMeta( db.Model ):

    __tablename__ = 'folder_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    item_id = db.Column( db.Integer, db.ForeignKey( 'folders.id' ) )
    item = db.relationship( 'Folder', back_populates='meta' )

class Folder( db.Model ):

    __tablename__ = 'folders'

    id = db.Column( db.Integer, primary_key=True )
    files = db.relationship( 'FileItem', back_populates='folder' )
    parent_id = db.Column(
        db.Integer, db.ForeignKey( 'folders.id' ), nullable=True )
    parent = db.relationship( 'Folder', remote_side=[id] )
    #folder_parent = db.relationship( 'Folder', remote_side=[id] )
    library_id = db.Column( db.Integer, db.ForeignKey( 'libraries.id' ) )
    library = db.relationship( 'Library', back_populates='folders' )
    display_name = db.Column(
        db.String( 256 ), index=True, unique=False, nullable=False )
    meta = db.relationship( 'FolderMeta', back_populates='item' )
    children = db.relationship( 'Folder', backref=db.backref(
        'folder_parent', remote_side=[id] ) )
        
    def __str__( self ):
        return self.display_name

    def __repr__( self ):
        return self.display_name

    @property
    def path( self, include_lib=False ):
        
        parent_list = []
        folder_iter = self

        # Traverse the folder's parents upwards.
        while isinstance( folder_iter, Folder ):
            parent_list.insert( 0, folder_iter.display_name )
            folder_iter = Folder.from_id( folder_iter.parent_id )

        if include_lib:
            parent_list.insert( 0, self.library.machine_name )

        return '/'.join( parent_list )

    @property
    def absolute_path( self ):
        return '/'.join( [self.library.absolute_path, self.path] )

    @staticmethod
    def from_path( library, path ):
        if not isinstance( library, Library ):
            library = Library.from_id( library )

        if not path:
            raise LibraryRootException( library_id=library.id )

        path_right = path.split( '/' )
        path_left = []
        
        folder_iter = None
        parent = None

        library_absolute_path = library.absolute_path

        while( len( path_right ) > 0 ):
            query = db.session.query( Folder ).filter(
                Folder.library_id == library.id,
                Folder.display_name == path_right[0] )
            folder_iter = query.first()
            
            #print( 'path_right[0]: ' + path_right[0] )
            #print( 'folder_iter: ' + str( folder_iter ) )
            #print( 'parent: ' + str( parent ) )

            # Use the parent's absolute path if available, otherwise use the library's.
            absolute_path = os.path.join( library.absolute_path, path_right[0] )
            if parent:
                absolute_path = os.path.join( parent.absolute_path, path_right[0] )
            
            #print( 'abs_path: ' + absolute_path )
            if not os.path.exists( absolute_path ) and not folder_iter:
                # Folder does not exist on FS or in DB.
                raise InvalidFolderException( display_name=path[0], library_id=library.id, absolute_path=absolute_path )
            elif os.path.exists( absolute_path ) and not folder_iter:
                # Add folder to DB if it does exist.
                current_app.logger.info( 'creating missing DB entry for {} under {}...'.format( absolute_path, parent ) )
                
                # Assume we're under the root by default, but use parent if available.
                parent_id = None
                if parent:
                    parent_id = parent.id

                assert( library )
                folder_iter = Folder( parent_id=parent_id, library_id=library.id, display_name=path_right[0] )
                db.session.add( folder_iter )
                db.session.commit()
            path_left.append( path_right.pop( 0 ) )
            parent = folder_iter

        return folder_iter

    @staticmethod
    def from_id( folder_id ):
        query = db.session.query( Folder ) \
            .filter( Folder.id == folder_id )
        return query.first()

class Plugin( db.Model ):

    __tablename__ = 'plugins'

    id = db.Column( db.Integer, primary_key=True )

class LibraryMeta( db.Model ):

    __tablename__ = 'library_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    item_id = db.Column( db.Integer, db.ForeignKey( 'libraries.id' ) )
    item = db.relationship( 'Library', back_populates='meta' )

class Library( db.Model ):

    __tablename__ = 'libraries'

    id = db.Column( db.Integer, primary_key=True )
    folders = db.relationship( 'Folder', back_populates='library' )
    children = db.relationship( 'Folder', primaryjoin='and_(Library.id == Folder.library_id, Folder.parent_id == None)' )
    display_name = db.Column(
        db.String( 64 ), index=False, unique=True, nullable=False )
    machine_name = db.Column(
        db.String( 64 ), index=True, unique=True, nullable=False )
    absolute_path = db.Column(
        db.String( 256 ), index=True, unique=True, nullable=False )
    auto_nsfw = db.Column(
        db.Boolean, index=False, unique=False, nullable=False )
    meta = db.relationship( 'LibraryMeta', back_populates='item' )

    def __str__( self ):
        return self.machine_name

    def __repr__( self ):
        return self.machine_name

    @staticmethod
    def from_machine_name( machine_name ):
        query = db.session.query( Library ) \
            .filter( Library.machine_name == machine_name )
        return query.first()

    @staticmethod
    def from_id( id ):
        query = db.session.query( Library ) \
            .filter( Library.id == id )
        return query.first()

    @staticmethod
    def enumerate_all():

        '''Return a list of all libraries (as defined by SQLA Library model.'''

        query = db.session.query( Library )
        return query.all()

class WorkerSemaphore( db.Model ):

    __tablename__ = "db_semaphores"

    id = db.Column( db.String( 64 ), primary_key=True )
    # Timestamp stored as integer for simpler math later.
    timestamp = \
        db.Column( db.Integer, index=False, unique=False, nullable=False )
    progress = \
        db.Column( db.Integer, index=False, unique=False, nullable=False )
    note = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
