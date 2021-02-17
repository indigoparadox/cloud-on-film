
from operator import add, sub
import os
import errno
import stat
import hashlib
import shutil
import importlib
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
from datetime import datetime
from collections import defaultdict

class HashEnum( Enum ):
    md5 = 1
    sha128 = 2
    sha256 = 3    

class StatusEnum( Enum ):
    missing = 1

class InvalidFolderException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.name = kwargs['name'] if 'name' in kwargs else None
        self.absolute_path = kwargs['absolute_path'] if 'absolute_path' in kwargs else None
        self.parent_id = kwargs['parent_id'] if 'parent_id' in kwargs else None
        self.library_id = kwargs['library_id']
        super().__init__( *args )

class LibraryRootException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.library_id = kwargs['library_id'] if 'library_id' in kwargs else None
        super().__init__( *args )

class LibraryPermissionsException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.library_id = kwargs['library_id'] if 'library_id' in kwargs else None
        super().__init__( *args )

class MaxDepthException( Exception ):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

class DBItemNotFoundException( Exception ):
    def __init__( self, *args, **kwargs ):
        #super().__init__( *args, **kwargs )
        self.absolute_path = kwargs['absolute_path'] if 'absolute_path' in kwargs else None
        self.folder = kwargs['folder'] if 'folder' in kwargs else None
        self.filename = kwargs['filename'] if 'filename' in kwargs else None

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

            elif isinstance( val, dict ):
                dict_out[key] = {}
                for dict_key in val:
                    if hasattr( val[dict_key], 'to_dict' ):
                        dict_out[key][dict_key] = val[dict_key].to_dict()

                        # Meta properties are a tuple with a redundant "key" and "val".
                        # Just keep the "val" if this arrangement is detected.
                        if isinstance( dict_out[key][dict_key], tuple ) and \
                        2 == len( dict_out[key][dict_key] ) and \
                        dict_key == dict_out[key][dict_key][0]:
                            dict_out[key][dict_key] = dict_out[key][dict_key][1]
                    else:
                        dict_out[key][dict_key] = val[dict_key]

            elif isinstance( val, Enum ):
                dict_out[key] = str( val )

            else:
                dict_out[key] = val

            #print( dict_out )

        return dict_out

class MetaPropertyMixin( object ):

    def __str__( self ):
        return self.value

    def __repr__( self ):
        return self.value

    def to_dict( self, *args, **kwargs ):
        return (self.key, self.value)

class UserMeta( db.Model, MetaPropertyMixin ):

    __tablename__ = 'user_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    user_id = db.Column( db.Integer, db.ForeignKey( 'users.id' ) )
    user = db.relationship( 'User', back_populates='meta' )

class User( db.Model, JSONItemMixin ):

    __tablename__ = 'users'

    id = db.Column( db.Integer, primary_key=True )
    email = db.Column(
        db.String( 128 ), index=True, unique=True, nullable=False )
    created = db.Column(
        db.DateTime, index=False, unique=False, nullable=False )
    libraries = db.relationship( 'Library', back_populates='owner' )
    meta = db.relationship( 'UserMeta', back_populates='user' )

class LibraryMeta( db.Model, MetaPropertyMixin ):

    __tablename__ = 'library_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    library_id = db.Column( db.Integer, db.ForeignKey( 'libraries.id' ) )
    library = db.relationship( 'Library',
        backref=db.backref(
            '_meta',
            collection_class=attribute_mapped_collection( 'key' ),
            lazy="joined",
            cascade="all, delete-orphan" ) )

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
    nsfw = db.Column(
        db.Boolean, index=False, unique=False, nullable=False )
    owner = db.relationship( 'User', back_populates='libraries' )
    owner_id = db.Column( db.Integer, db.ForeignKey( 'users.id' ) )
    meta = db.relationship( 'LibraryMeta', back_populates='library' )

    def __str__( self ):
        return self.machine_name

    def __repr__( self ):
        return self.machine_name

    @staticmethod
    def secure_query( user_id ):
        query = db.session.query( Library )

        if 0 <= user_id:
            query = query.filter( db.or_(
                Library.owner_id == user_id,
                Library.owner_id == None ) )

        return query

    @staticmethod
    def enumerate_all( user_id ):

        '''Return a list of all libraries (as defined by SQLA Library model.'''

        return Library.secure_query( user_id ).all()

items_tags = db.Table( 'items_tags', db.metadata,
    db.Column( 'items_id', db.Integer, db.ForeignKey( 'items.id' ) ),
    db.Column( 'tags_id', db.Integer, db.ForeignKey( 'tags.id' ) ) )

class TagMeta( db.Model, MetaPropertyMixin ):

    __tablename__ = 'tag_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    tag_id = db.Column( db.Integer, db.ForeignKey( 'tags.id' ) )
    tag = db.relationship( 'Tag',
        backref=db.backref(
            '_meta',
            collection_class=attribute_mapped_collection( 'key' ),
            lazy="joined",
            cascade="all, delete-orphan" ) )

class Tag( db.Model ):

    __tablename__ = 'tags'

    id = db.Column( db.Integer, primary_key=True )
    parent_id = db.Column( 
        db.Integer, db.ForeignKey( 'tags.id' ), nullable=True )
    parent = db.relationship( 'Tag', remote_side=[id] )
    name = db.Column(
        db.String( 64 ), index=True, unique=False, nullable=False )
    meta = db.relationship( 'TagMeta', back_populates='tag' )
    children = db.relationship( 'Tag', backref=db.backref(
        'tag_parent', remote_side=[id] ) )

    # Tags are a bit different than meta relationships at they're many-to-many.
    _items = db.relationship( 'Item', secondary=items_tags, back_populates='tags' )

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return self.name

    def to_dict( self, *args, **kwargs ):
        return self.path

    @property
    def path( self ):
        
        parent_list = []
        tag_iter = self

        # Traverse the folder's parents upwards.
        while isinstance( tag_iter, Tag ) and tag_iter.name:
            parent_list.insert( 0, tag_iter.name )
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
                .filter( Tag.name == path[0] ) \
                .filter( Tag.parent_id == tag_parent_id ) \
                .first()
            if not tag_iter:
                # Create the missing new tag.
                tag_iter = Tag( parent_id=tag_parent_id, name=path[0] )
                current_app.logger.info( 'creating new tag: {}'.format( tag_iter.path ) )
                db.session.add( tag_iter )
                db.session.commit()

            path.pop( 0 )
            tag_parent = tag_iter
        
        return tag_iter

    @staticmethod
    def enumerate_roots():
        return db.session.query( Tag ) \
            .filter( Tag.parent_id == None )

class FolderMeta( db.Model ):

    __tablename__ = 'folder_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    folder_id = db.Column( db.Integer, db.ForeignKey( 'folders.id' ) )
    folder = db.relationship( 'Folder',
        backref=db.backref(
            '_meta',
            collection_class=attribute_mapped_collection( 'key' ),
            lazy="joined",
            cascade="all, delete-orphan" ) )

class Folder( db.Model, JSONItemMixin ):

    __tablename__ = 'folders'

    id = db.Column( db.Integer, primary_key=True )
    items = db.relationship( 'Item', back_populates='folder' )
    parent_id = db.Column(
        db.Integer, db.ForeignKey( 'folders.id' ), nullable=True )
    parent = db.relationship( 'Folder', remote_side=[id] )
    #folder_parent = db.relationship( 'Folder', remote_side=[id] )
    library_id = db.Column( db.Integer, db.ForeignKey( 'libraries.id' ) )
    library = db.relationship( 'Library', back_populates='folders' )
    name = db.Column(
        db.String( 256 ), index=True, unique=False, nullable=False )
    meta = db.relationship( 'FolderMeta', back_populates='folder' )
    children = db.relationship( 'Folder', backref=db.backref(
        'folder_parent', remote_side=[id] ) )
    status = db.Column( db.Enum( StatusEnum ) )

    owner_id = db.column_property(
        db.select(
            [Library.owner_id],
            Library.id == library_id ).label( 'owner_id' ) )

    nsfw = db.column_property(
        db.select(
            [func.cast( Library.nsfw, db.Integer )],
            Library.id == library_id ).label( 'nsfw' ) )
        
    def __str__( self ):
        return self.name

    def __repr__( self ):
        return self.name

    @property
    def path( self, include_lib=False ):
        
        parent_list = []
        folder_iter = self

        # Traverse the folder's parents upwards.
        while isinstance( folder_iter, Folder ):
            parent_list.insert( 0, folder_iter.name )
            folder_iter = db.session.query( Folder ) \
                .filter( Folder.id == folder_iter.parent_id ) \
                .first()

        if include_lib:
            parent_list.insert( 0, self.library.machine_name )

        return '/'.join( parent_list )

    @property
    def absolute_path( self ):
        return '/'.join( [self.library.absolute_path, self.path] )

    @staticmethod
    def from_path( library_id, path, user_id ):

        # Do the fetching from scratch to ensure permissions.
        assert( isinstance( library_id, int ) )

        library = Library.secure_query( user_id ) \
            .filter( Library.id == library_id ) \
            .first()

        if not library:
            raise LibraryPermissionsException()

        if not path:
            raise LibraryRootException( library_id=library.id )

        path_right = path.split( '/' )
        path_left = []
        
        folder_iter = None
        parent = None

        #library_absolute_path = library.absolute_path

        while( len( path_right ) > 0 ):
            parent_id = None
            if folder_iter:
                parent_id = parent.id

            query = db.session.query( Folder ).filter(
                Folder.parent_id == parent_id,
                Folder.library_id == library.id,
                Folder.name == path_right[0] )
            folder_iter = query.first()

            # Use the parent's absolute path if available, otherwise use the library's.
            absolute_path = os.path.join( library.absolute_path, path_right[0] )
            if parent:
                absolute_path = os.path.join( parent.absolute_path, path_right[0] )
            
            if not os.path.exists( absolute_path ) and not folder_iter:
                # Folder does not exist on FS or in DB.
                raise InvalidFolderException( name=path[0], library_id=library.id, absolute_path=absolute_path )

            elif os.path.exists( absolute_path ) and not folder_iter:
                # Add folder to DB if it does exist.
                current_app.logger.info( 'creating missing DB entry for {} under {}...'.format( absolute_path, parent ) )
                
                # Assume we're under the root by default, but use parent if available.
                parent_id = None
                if parent:
                    parent_id = parent.id

                assert( library )
                folder_iter = Folder( parent_id=parent_id, library_id=library.id, name=path_right[0] )
                db.session.add( folder_iter )
                db.session.commit()
            path_left.append( path_right.pop( 0 ) )
            parent = folder_iter

        return folder_iter

    @staticmethod
    def secure_query( user_id ):
        query = db.session.query( Folder )
        
        if 0 <= user_id:
            query = query.filter( db.or_(
                None == Folder.owner_id,
                user_id == Folder.owner_id ) )

        return query
    
    @staticmethod
    def ensure_folder( folder_or_folder_id_or_path, user_id ):

        ''' Given a folder, folder ID, or folder path, return that folder
        model object. '''

        folder = None
        if isinstance( folder_or_folder_id_or_path, int ):
            folder = db.session.query( Folder ) \
                .filter( Folder.id == destination ) \
                .filter( Folder.owner_id == user_id ) \
                .first()
        elif isinstance( folder_or_folder_id_or_path, str ):
            folder = Folder.from_path( library, destination, user_id )
        elif isinstance( folder_or_folder_id_or_path, Folder ):
            folder = folder_or_folder_id_or_path

        if not folder:
            raise InvalidFolderException()

        return folder

class ItemMeta( db.Model, MetaPropertyMixin ):

    __tablename__ = 'item_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    item_id = db.Column( db.Integer, db.ForeignKey( 'items.id' ) )
    item = db.relationship( 'Item',
        backref=db.backref(
            '_meta',
            collection_class=attribute_mapped_collection( 'key' ),
            lazy="joined",
            cascade="all, delete-orphan" ) )

class Item( db.Model, JSONItemMixin ):

    __tablename__ = 'items'

    id = db.Column( db.Integer, primary_key=True )
    meta = association_proxy( '_meta', 'value',
        creator=lambda k, v: ItemMeta( key=k, value=v ) )
    folder_id = db.Column( db.Integer, db.ForeignKey( 'folders.id' ) )
    folder = db.relationship( 'Folder', back_populates='items' )
    tags = db.relationship(
        'Tag', secondary=items_tags, back_populates='_items' )
    name = db.Column(
        db.String( 256 ), index=True, unique=False, nullable=False )
    timestamp = db.Column(
        db.DateTime, index=False, unique=False, nullable=False )
    size = db.Column(
        db.Integer, index=False, unique=False, nullable=False )
    added = db.Column( db.DateTime, index=False, unique=False, nullable=False )
    hash = db.Column(
        db.String( 512 ), index=False, unique=False, nullable=False )
    hash_algo = db.Column( db.Integer, index=False, unique=False, nullable=False )
    status = db.Column( db.Enum( StatusEnum ) )

    owner_id = db.column_property(
        db.select(
            [Library.owner_id],
            db.and_(
                Library.id == Folder.library_id,
                Folder.id == folder_id ) ).label( 'owner_id' ) )

    nsfw = db.column_property(
        db.select(
            [func.cast( Library.nsfw, db.Integer )],
            db.and_(
                Library.id == Folder.library_id,
                Folder.id == folder_id ) ).label( 'nsfw' ) )

    library_id = db.column_property(
        db.select(
            [Library.id],
            db.and_(
                Library.id == Folder.library_id,
                Folder.id == folder_id ) ).label( 'library_id' ) )

    missing = db.case( [
            (status == 1, 1)
        ], else_=0 )

    # The plugin column should be allowed to be set by the subclass.
    # Items should be created as the subclass they are detected as.
    plugin= db.Column( db.String( 12 ), nullable=False )
    __mapper_args__ = {
        'polymorphic_identity': 'item',
        'polymorphic_on': plugin
    }

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return self.name

    def _check_tag_heir( self, tag ):
        if tag.parent and \
        not '' == tag.parent.name and \
        not self in tag.parent.files():
            current_app.logger.info( 'adding parent tag {} to {}...'.format( tag.parent.path, self.absolute_path ) )
            tag.parent._items.append( self )
        elif tag.parent:
            self._check_tag_heir( tag.parent )
    
    def fix_tags( self, append=[] ):

        # TODO

        for tag in append:
            self._tags.append( tag )

        for tag in self._tags:
            self._check_tag_heir( tag )
            
        return self._tags

    def move( self, library, destination, user_id ):
        
        if isinstance( destination, int ):
            destination = db.session.query( Folder ) \
                .filter( Folder.id == destination ) \
                .filter( Folder.owner_id == user_id ) \
                .first()
        elif isinstance( destination, str ):
            destination = Folder.from_path( library, destination, user_id )

        assert( isinstance( destination, Folder ) )

        shutil.move(
            self.absolute_path,
            os.path.join( destination.absolute_path, self.name ) )

        self.folder_id = destination.id
        db.session.commit()

    @property
    def path( self ):
        return '/'.join( [self.folder.path, self.name] )

    @property
    def absolute_path( self ):
        return '/'.join( [self.folder.absolute_path, self.name] )
    
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
    def from_path( library_id, relative_path, user_id ):
        # TODO: Check if exists on FS and create Item if so but not in DB.

        filename = os.path.basename( relative_path )
        
        # Get the folder from path so we're sure the folder is added to the DB before the file is.
        folder = Folder.from_path( library_id, os.path.dirname( relative_path ), user_id )
        item = Item.secure_query( user_id ) \
            .filter( Item.folder_id == folder.id ) \
            .filter( Item.name == os.path.basename( relative_path ) ) \
            .first()

        absolute_path = os.path.join( folder.absolute_path, filename )

        if not item and not os.path.exists( absolute_path ):
            raise FileNotFoundError( errno.ENOENT, os.strerror(errno.ENOENT), absolute_path )
        
        elif not item:
            # Toss it up to the plugin or situation to create an entry.
            raise DBItemNotFoundException(
                absolute_path=absolute_path, folder=folder, filename=filename )

        elif not os.path.exists( absolute_path ):
            # Item doesn't exist on FS even though it does on FS, so mark it missing.
            current_app.logger.warn( 'file missing: {}'.format( absolute_path ) )
            item.status = StatusEnum.missing
            db.session.commit()

        return item

    @staticmethod
    def secure_query( user_id ):

        poly = Plugin.polymorph()

        query = db.session.query( poly )
        
        if 0 <= user_id:
            query = query.filter( db.or_(
                None == Item.owner_id,
                user_id == Item.owner_id ) )

        return query

class FileExtension( db.Model ):

    __tablename__ = 'item_types'

    id = db.Column( db.Integer, primary_key=True )
    extension = db.Column(
        db.String( 12 ), index=True, unique=True, nullable=False )
    mime_type = db.Column(
        db.String( 128 ), index=False, unique=False, nullable=False )
    plugin_id = db.Column( db.Integer, db.ForeignKey( 'plugins.id' ) )
    plugin = db.relationship( 'Plugin',
        backref=db.backref(
            '_extensions',
            collection_class=attribute_mapped_collection( 'extension' ),
            lazy="joined",
            cascade="all, delete-orphan" ) )

class PluginMeta( db.Model, MetaPropertyMixin ):

    __tablename__ = 'plugin_meta'

    id = db.Column( db.Integer, primary_key=True )
    key = db.Column( db.String( 12 ), index=True, unique=False, nullable=False )
    value = \
        db.Column( db.String( 256 ), index=False, unique=False, nullable=True )
    plugin_id = db.Column( db.Integer, db.ForeignKey( 'plugins.id' ) )
    plugin = db.relationship( 'Plugin',
        backref=db.backref(
            '_meta',
            collection_class=attribute_mapped_collection( 'key' ),
            lazy="joined",
            cascade="all, delete-orphan" ) )

class Plugin( db.Model ):

    __tablename__ = 'plugins'

    id = db.Column( db.Integer, primary_key=True )
    machine_name = db.Column( db.String( 12 ), index=True, unique=True, nullable=False )
    display_name = db.Column( db.String( 128 ), index=False, unique=True, nullable=False )
    meta = association_proxy( '_meta', 'value',
        creator=lambda k, v: PluginMeta( key=k, value=v ) )
    enabled = db.Column(
        db.Boolean, index=False, unique=False, nullable=False )
    module_path = db.Column( db.String( 128 ), index=False, unique=True, nullable=False )
    model_name = db.Column( db.String( 128 ), index=False, unique=True, nullable=False )
    extensions = association_proxy( '_extensions', 'mime_type',
        creator=lambda k, v: FileExtension( extension=k, mime_type=v ) )

    @staticmethod
    def from_extension( extension ):
        return db.session.query( Plugin ) \
            .filter( extension in Plugin.extensions ) \
            .filter( Plugin.enabled == True ) \
            .first()

    @staticmethod
    def polymorph():

        plugins = db.session.query( Plugin ) \
            .filter( Plugin.enabled == True ) \
            .all()

        models = []
        for plugin in plugins:
            plugin_module = importlib.import_module( plugin.module_path )
            plugin_model = getattr( plugin_module, plugin.model_name )
            models.append( plugin_model )
        
        return db.with_polymorphic( Item, models )

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
