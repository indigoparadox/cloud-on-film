
from operator import add, sub
import os
import errno
import stat
import hashlib
import shutil
from sqlalchemy import event, func
from sqlalchemy.orm import query
from sqlalchemy.inspection import inspect
from sqlalchemy.ext.hybrid import hybrid_property, Comparator
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.sql.sqltypes import Integer
from . import db
from enum import Enum
from flask import current_app
from PIL import Image
from datetime import datetime

class HashEnum( Enum ):
    md5 = 1
    sha128 = 2
    sha256 = 3    

class StatusEnum( Enum ):
    missing = 1

class MetaTypeEnum( Enum ):
    text = 0
    integer = 1

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

class LibraryPermissionsException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.library_id = kwargs['library_id']
        super().__init__( *args )

class MaxDepthException( Exception ):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

class MetaTransformer( Comparator ):
    def operate( self, op, other ):
        def transform( q ):
            cls = self.__clause_element__()
            print( 'qqq' )
            print( 'qqq' )
            print( cls )
            print( 'qqq' )
            print( 'qqq' )
            return q.join( FileMeta.item_id, cls.id )
        return transform

class MetaProperty( object ):

    def __init__( self, key, value=None ):
        self.key = key
        self.value = value
    
    @hybrid_property
    def value( self ):
        #return getattr( self, fieldname )
        return None

@event.listens_for( MetaProperty, 'mapper_configured', propagate=True )
def on_new_meta_property( mapper, cls ):
    pass

class JSONItemMixin( object ):

    def to_dict( self, ignore_keys=[], max_depth=-1 ):
        dict_out = {}

        if 0 == max_depth:
            raise MaxDepthException

        for key in inspect( self ).attrs.keys():
            if key in ignore_keys:
                continue

            val = getattr( self, key )

            if isinstance( val, list ):
                if 0 < len( val ) and \
                hasattr( val[0], 'to_dict' ):
                    try:
                        # Found a list of items.
                        if isinstance( val[0].to_dict(), tuple ) and \
                        len( val[0].to_dict() ) == 2:
                            # Translate list of tuples into a dict.
                            dict_out[key] = {}
                            for item in val:
                                tuple_out = item.to_dict( ignore_keys=ignore_keys, max_depth=(max_depth - 1) )
                                dict_out[key][tuple_out[0]] = tuple_out[1]

                        else:
                            # Just translate the list.
                            dict_out[key] = []
                            for item in val:
                                dict_out[key].append( item.to_dict( ignore_keys=ignore_keys, max_depth=(max_depth - 1) ) )

                    except MaxDepthException:
                        dict_out[key] = None
                else:
                    dict_out[key] = None

            elif isinstance( val, Enum ):
                dict_out[key] = str( val )

            else:
                dict_out[key] = val

            #print( dict_out )

        assert( not 'type' in dict_out )
        dict_out['type'] = str( type( self ) )

        return dict_out

#class UserMeta( db.Model ):
#    pass

class User( db.Model, JSONItemMixin ):

    __tablename__ = 'users'

    id = db.Column( db.Integer, primary_key=True )
    email = db.Column(
        db.String( 128 ), index=True, unique=True, nullable=False )
    created = db.Column(
        db.DateTime, index=False, unique=False, nullable=False )
    tags = db.relationship( 'Tag', back_populates='owner' )

class LibraryMeta( db.Model ):

    __tablename__ = 'library_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    item_id = db.Column( db.Integer, db.ForeignKey( 'libraries.id' ) )
    item = db.relationship( 'Library', back_populates='meta' )

    def to_dict( self, *args, **kwargs ):
        return (self.key, self.value)

class Library( db.Model, JSONItemMixin ):

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

    def is_accessible( self ):
        # TODO
        #print( self.machine_name )
        if self.machine_name == 'nosync':
            return False
        return True

    @staticmethod
    def from_machine_name( machine_name ):
        library = db.session.query( Library ) \
            .filter( Library.machine_name == machine_name ) \
            .first()

        if not library.is_accessible():
            raise LibraryPermissionsException( library_id=library.id )

        return library

    @staticmethod
    def from_id( id ):
        library = db.session.query( Library ) \
            .filter( Library.id == id ) \
            .first()

        if not library.is_accessible():
            raise LibraryPermissionsException( library_id=library.id )

        return library

    @staticmethod
    def enumerate_all():

        '''Return a list of all libraries (as defined by SQLA Library model.'''

        libraries = db.session.query( Library ).all()

        for library in libraries:
            if not library.is_accessible():
                libraries.remove( library )

        return libraries

class FileMeta( db.Model ):

    __tablename__ = 'file_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    item_id = db.Column( db.Integer, db.ForeignKey( 'files.id' ) )

    item = db.relationship( 'FileItem',
        backref=db.backref(
            '_meta',
            collection_class=attribute_mapped_collection( 'key' ),
            cascade="all, delete-orphan" ) )

    def __str__( self ):
        return self.value

    def __repr__( self ):
        return self.value

    def to_dict( self, *args, **kwargs ):
        return (self.key, self.value)

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

    def to_dict( self, *args, **kwargs ):
        return (self.key, self.value)

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
    _files = db.relationship(
        'FileItem', secondary=files_tags, back_populates='_tags' )
    meta = db.relationship( 'TagMeta', back_populates='item' )
    children = db.relationship( 'Tag', backref=db.backref(
        'tag_parent', remote_side=[id] ) )

    def __str__( self ):
        return self.display_name

    def __repr__( self ):
        return self.display_name

    def to_dict( self, *args, **kwargs ):
        return self.path

    def files( self ):
        return [f for f in self._files if f.folder.library.is_accessible()]

    @property
    def path( self ):
        
        parent_list = []
        tag_iter = self

        # Traverse the folder's parents upwards.
        while isinstance( tag_iter, Tag ) and tag_iter.display_name:
            parent_list.insert( 0, tag_iter.display_name )
            tag_iter = tag_iter.parent

        return '/'.join( parent_list )

    @staticmethod
    def from_path( path ):

        path = [''] + path.split( '/' )
        tag_iter = None
        tag_parent = None
        while 0 < len( path ):
            tag_parent_id = None
            if tag_parent:
                tag_parent_id = tag_parent.id

            tag_iter = db.session.query( Tag ) \
                .filter( Tag.display_name == path[0] ) \
                .filter( Tag.parent_id == tag_parent_id ) \
                .first()
            if not tag_iter:
                # Create the missing new tag.
                tag_iter = Tag( parent_id=tag_parent_id, display_name=path[0] )
                current_app.logger.info( 'creating new tag: {}'.format( tag_iter.path ) )
                db.session.add( tag_iter )
                db.session.commit()

            path.pop( 0 )
            tag_parent = tag_iter
        
        return tag_iter

    @staticmethod
    def enumerate_roots():

        tagalias = db.aliased( Tag )
        query = db.session.query( Tag ) \
            .join( tagalias, Tag.parent ) \
            .filter( db.or_( Tag.parent_id == None,
                tagalias.display_name == '' ) )

        return query.all()

class FolderMeta( db.Model ):

    __tablename__ = 'folder_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    item_id = db.Column( db.Integer, db.ForeignKey( 'folders.id' ) )
    item = db.relationship( 'Folder', back_populates='meta' )

    def to_dict( self, *args, **kwargs ):
        return (self.key, self.value)

class Folder( db.Model, JSONItemMixin ):

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
    status = db.Column( db.Enum( StatusEnum ) )
        
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
            parent_id = None
            if folder_iter:
                parent_id = parent.id

            query = db.session.query( Folder ).filter(
                Folder.parent_id == parent_id,
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

class FileItem( db.Model, JSONItemMixin ):

    __tablename__ = 'files'

    id = db.Column( db.Integer, primary_key=True )
    meta = association_proxy( '_meta', 'value',
        creator=lambda k, v: FileMeta( key=k, value=v ) )
    folder_id = db.Column( db.Integer, db.ForeignKey( 'folders.id' ) )
    folder = db.relationship( 'Folder', back_populates='files' )
    tag_id = db.Column( db.Integer, db.ForeignKey( 'tags.id' ) )
    _tags = db.relationship(
        'Tag', secondary=files_tags, back_populates='_files' )
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
    status = db.Column( db.Enum( StatusEnum ) )

    nsfw = db.column_property(
        db.select(
            [Library.auto_nsfw],
            db.and_(
                Library.id == Folder.library_id,
                Folder.id == folder_id ) ).label( 'nsfw' ) )

    width = db.column_property(
        db.select(
            [db.cast( FileMeta.value, db.Integer )],
            db.and_(
                FileMeta.item_id == id,
                FileMeta.key == 'width' ) ).label( 'width' ) )

    height = db.column_property(
        db.select(
            [db.cast( FileMeta.value, db.Integer )],
            db.and_(
                FileMeta.item_id == id,
                FileMeta.key == 'height' ) ).label( 'height' ) )

    aspect = db.column_property(
        db.case( [
            (16 * height.expression / width == 10, 10),
            (16 * height.expression / width == 9, 9),
            (4 * height.expression / width == 3, 4),
            (1 * height.expression / width == 1, 1)
        ], else_=0 ).label( 'aspect' ) )

    def __str__( self ):
        return self.display_name

    def __repr__( self ):
        return self.display_name

    def to_dict( self, *args, **kwargs ):
        dict_out = super().to_dict( *args, **kwargs )
        dict_out['tags'] = [t.to_dict( *args, **kwargs ) for t in self.tags()]
        del dict_out['_tags']
        dict_out['meta'] = dict_out['_meta']
        del dict_out['_meta']
        dict_out['nsfw'] = False
        if self.folder.library.auto_nsfw:
            dict_out['nsfw'] = True
        return dict_out

    def _check_tag_heir( self, tag ):
        if tag.parent and \
        not '' == tag.parent.display_name and \
        not self in tag.parent.files():
            current_app.logger.info( 'adding parent tag {} to {}...'.format( tag.parent.path, self.absolute_path ) )
            tag.parent._files.append( self )
        elif tag.parent:
            self._check_tag_heir( tag.parent )
    
    def tags( self, append=[] ):

        for tag in append:
            self._tags.append( tag )

        for tag in self._tags:
            self._check_tag_heir( tag )
            
        return self._tags

    def move( self, destination ):
        
        if isinstance( destination, int ):
            destination = Folder.from_id( destination )
        elif isinstance( destination, str ):
            destination = Folder.from_path( destination )

        assert( isinstance( destination, Folder ) )

        shutil.move(
            self.absolute_path,
            os.path.join( destination.absolute_path, self.display_name ) )

        self.folder_id = destination.id
        db.session.commit()

    def open_image( self ):
        im = Image.open( self.absolute_path )
        if not im:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), self.absolute_path )
        return im

    @property
    def path( self ):
        return '/'.join( [self.folder.path, self.display_name] )

    @property
    def absolute_path( self ):
        return '/'.join( [self.folder.absolute_path, self.display_name] )
    
    @staticmethod
    def hash_file( absolute_path, hash_algo=HashEnum.md5 ):
        # We don't need to bother with the folder, since this can just fail if the file doesn't really exist.
        absolute_path = os.path.join( absolute_path )
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
                filehash=FileItem.hash_file( absolute_path, HashEnum.md5 ),
                filehash_algo=HashEnum.md5,
                # TODO: Determine the file type dynamically.
                filetype='picture' )
            db.session.add( item )
            db.session.commit()

            with item.open_image() as im:
                item.meta['width'] = im.size[0]
                item.meta['height'] = im.size[1]
            db.session.commit()

            current_app.logger.info( 'found new image with size: {}x{}'.format(
                item.width, item.height
            ) )

        elif not os.path.exists( absolute_path ):
            # Item doesn't exist on FS even though it does on FS, so mark it missing.
            current_app.logger.warn( 'file missing: {}'.format( absolute_path ) )
            item.status = StatusEnum.missing
            db.session.commit()

        return item

class Plugin( db.Model ):

    __tablename__ = 'plugins'

    id = db.Column( db.Integer, primary_key=True )

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
