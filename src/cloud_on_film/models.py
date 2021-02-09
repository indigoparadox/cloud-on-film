
from . import db
from enum import Enum
from flask import current_app

class HashEnum( Enum ):
    md5 = 1
    sha128 = 2
    sha256 = 3

class InvalidFolderException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.display_name = kwargs['display_name'] if 'display_name' in kwargs else None
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
    item = db.relationship( 'FileItem', back_populates='meta' )

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
    meta = db.relationship( 'FileMeta', back_populates='item' )
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
    comment = db.Column( db.Text, index=False, unique=False, nullable=True )
    nsfw = db.Column( db.Boolean, index=True, unique=False, nullable=False )
    rating = db.Column( db.Integer, index=True, unique=False, nullable=True )

    def __str__( self ):
        return self.display_name

    def __repr__( self ):
        return self.display_name

    @property
    def path( self ):
        return '/'.join( [self.folder.path, self.display_name] )

    @property
    def absolute_path( self ):
        return '/'.join( [self.folder.absolute_path, self.display_name] )

    @staticmethod
    def from_id( file_id ):
        query = db.session.query( FileItem ) \
            .filter( FileItem.id == file_id )
        return query.first()

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
    def from_path( library_id, path ):
        if not path:
            raise LibraryRootException( library_id=library_id )

        if isinstance( library_id, Library ):
            library_id = library_id.id

        path = path.split( '/' )
        
        folder_iter = None
        while( len( path ) > 0 ):
            query = db.session.query( Folder ) \
                .filter( Folder.library_id == library_id, Folder.display_name == path[0] )
            folder_iter = query.first()
            if not folder_iter:
                raise InvalidFolderException( display_name=path[0], library_id=library_id )
            path.pop( 0 )

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
