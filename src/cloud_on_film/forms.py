
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, BooleanField, HiddenField, TextAreaField
from wtforms.validators import DataRequired

class NewLibraryForm( FlaskForm ):

    # TODO: Disallow name "new"

    display_name = StringField( 'Display Name', validators=[DataRequired()] )
    machine_name = StringField( 'Machine Name', validators=[DataRequired()] )
    absolute_path = StringField( 'Absolute Path', validators=[DataRequired()] )
    nsfw = BooleanField( 'NSFW' )

class UploadLibraryForm( FlaskForm ):

    upload = FileField( 'Library Import File' )

class RenameItemForm( FlaskForm ):

    id = HiddenField( '' )
    name = StringField( 'Name', validators=[DataRequired()] )
    #nsfw = BooleanField( 'NSFW' )
    tags = StringField( 'Tags' )
    comment = TextAreaField( 'Comment' )
    location = HiddenField( '', validators=[DataRequired()] )

class SearchQueryForm( FlaskForm ):

    query = StringField( 'Search', validators=[DataRequired()] )
    page = HiddenField( '' )
