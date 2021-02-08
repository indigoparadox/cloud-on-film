
from flask import current_app
from sqlalchemy import or_
from .models import db, Tag

def enumerate_tag_roots():

    tagalias = db.aliased( Tag )
    query = db.session.query( Tag ) \
        .join( tagalias, Tag.parent ) \
        .filter( db.or_( Tag.parent_id == None,
            tagalias.display_name == '' ) )

    return query.all()

current_app.jinja_env.globals.update( enumerate_tag_roots=enumerate_tag_roots )
