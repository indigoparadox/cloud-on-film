
from flask import current_app
from .models import db, Tag

def enumerate_tag_roots():

    query = db.session.query( Tag ) \
        .filter( Tag.parent_id == None )

    return query.all()

current_app.jinja_env.globals.update( enumerate_tag_roots=enumerate_tag_roots )
