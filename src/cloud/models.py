
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
    userpic_id = db.Column( db.Integer, db.ForeignKey( 'pictures.id' ) )
    tags = db.relationship( 'Tag', back_populates='owner' )


pictures_tags = db.Table( 'pictures_tags', db.metadata,
    db.Column( 'pictures_id', db.Integer, db.ForeignKey( 'pictures.id' ) ),
    db.Column( 'tags_id', db.Integer, db.ForeignKey( 'tags.id' ) ) )


class Tag( db.Model ):

    __tablename__ = 'tags'

    id = db.Column( db.Integer, primary_key=True )
    parent_id = db.Column( db.Integer, unique=False, nullable=True )
    name = db.Column(
        db.String( 64 ), index=True, unique=False, nullable=False )
    owner = db.relationship( 'User', back_populates='tags' )
    owner_id = db.Column( db.Integer, db.ForeignKey( 'users.id' ) )
    picture_id = db.Column( db.Integer, db.ForeignKey( 'pictures.id' ) )
    pictures = db.relationship(
        'Picture', secondary=pictures_tags, back_populates='tags' )


class Picture( db.Model ):

    __tablename__ = 'pictures'

    id = db.Column( db.Integer, primary_key=True )
    folder_id = db.Column( db.Integer, db.ForeignKey( 'folders.id' ) )
    folder = db.relationship( 'Folder', back_populates='pictures' )
    tag_id = db.Column( db.Integer, db.ForeignKey( 'tags.id' ) )
    tags = db.relationship(
        'Tag', secondary=pictures_tags, back_populates='pictures' )
    display_name = db.Column(
        db.String( 256 ), index=True, unique=False, nullable=False )
    timestamp = db.Column(
        db.DateTime, index=False, unique=False, nullable=False )
    filesize = db.Column(
        db.Integer, index=False, unique=False, nullable=False )
    width = db.Column( db.Integer, index=False, unique=False, nullable=False )
    height = db.Column( db.Integer, index=False, unique=False, nullable=False )
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
    pictures = db.relationship( 'Picture', back_populates='folder' )
    parent_id = db.Column(
        db.Integer, db.ForeignKey( 'folders.id' ), nullable=True )
    parent = db.relationship( 'Folder', remote_side=[id] )
    library_id = db.Column( db.Integer, db.ForeignKey( 'libraries.id' ) )
    library = db.relationship( 'Library', back_populates='folders' )
    display_name = db.Column(
        db.String( 256 ), index=True, unique=True, nullable=False )


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


