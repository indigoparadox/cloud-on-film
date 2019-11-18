
from . import db

class User( db.Model ):

    __tablename__ = 'users'

    id = db.Column( db.Integer, primary_key=True )
    email = db.Column( db.String( 128 ), index=True, unique=True, nullable=False )
    created = db.Column( db.DateTime, index=False, unique=False, nullable=False )


pictures_tags = db.Table( 'pictures_tags', db.metadata,
    db.Column( 'pictures_id', db.Integer, db.ForeignKey( 'pictures.id' ) ),
    db.Column( 'tags_id', db.Integer, db.ForeignKey( 'tags.id' ) ) )


class Tag( db.Model ):

    __tablename__ = 'tags'

    id = db.Column( db.Integer, primary_key=True )
    parent_id = db.Column( db.Integer, unique=False, nullable=True )
    name = db.Column( db.String( 64 ), index=True, unique=False, nullable=False )
    owner_id = db.Column( db.Integer, db.ForeignKey( 'users.id' ) )
    picture_id = db.Column( db.Integer, db.ForeignKey( 'pictures.id' ) )
    pictures = db.relationship( 'Picture', secondary=pictures_tags, back_populates='tags' )


class Picture( db.Model ):

    __tablename__ = 'pictures'

    id = db.Column( db.Integer, primary_key=True )
    relative_path = db.Column( db.String( 256 ), index=True, unique=True, nullable=True )
    library_id = db.Column( db.Integer, db.ForeignKey( 'libraries.id' ) )
    tag_id = db.Column( db.Integer, db.ForeignKey( 'tags.id' ) )
    tags = db.relationship( 'Tag', secondary=pictures_tags, back_populates='pictures' )


class Library( db.Model ):

    __tablename__ = 'libraries'

    id = db.Column( db.Integer, primary_key=True )
    display_name = db.Column( db.String( 64 ), index=False, unique=True, nullable=False )
    machine_name = db.Column( db.String( 64 ), index=True, unique=True, nullable=False )
    absolute_path = db.Column( db.String( 256 ), index=True, unique=True, nullable=False )

