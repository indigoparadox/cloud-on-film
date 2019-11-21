
from . import db
from enum import Enum

class HashEnum( Enum ):
    md5 = 1
    sha128 = 2
    sha256 = 3


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


class Tag( db.Model ):

    __tablename__ = 'tags'

    id = db.Column( db.Integer, primary_key=True )
    parent_id = db.Column( db.Integer, unique=False, nullable=True )
    name = db.Column(
        db.String( 64 ), index=True, unique=False, nullable=False )
    owner = db.relationship( 'User', back_populates='tags' )
    owner_id = db.Column( db.Integer, db.ForeignKey( 'users.id' ) )
    file_id = db.Column( db.Integer, db.ForeignKey( 'files.id' ) )
    files = db.relationship(
        'FileItem', secondary=files_tags, back_populates='tags' )


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


class Folder( db.Model ):

    __tablename__ = 'folders'

    id = db.Column( db.Integer, primary_key=True )
    files = db.relationship( 'FileItem', back_populates='folder' )
    parent_id = db.Column(
        db.Integer, db.ForeignKey( 'folders.id' ), nullable=True )
    parent = db.relationship( 'Folder', remote_side=[id] )
    library_id = db.Column( db.Integer, db.ForeignKey( 'libraries.id' ) )
    library = db.relationship( 'Library', back_populates='folders' )
    display_name = db.Column(
        db.String( 256 ), index=True, unique=False, nullable=False )


class Plugin( db.Model ):

    __tablename__ = 'plugins'

    id = db.Column( db.Integer, primary_key=True )
    


class Library( db.Model ):

    __tablename__ = 'libraries'

    id = db.Column( db.Integer, primary_key=True )
    folders = db.relationship( 'Folder', back_populates='library' )
    display_name = db.Column(
        db.String( 64 ), index=False, unique=True, nullable=False )
    machine_name = db.Column(
        db.String( 64 ), index=True, unique=True, nullable=False )
    absolute_path = db.Column(
        db.String( 256 ), index=True, unique=True, nullable=False )


