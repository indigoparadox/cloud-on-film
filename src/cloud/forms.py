
from flask_wtf import FlaskForm
from wtforms import StringField, FileField
from wtforms.validators import DataRequired

class NewLibraryForm( FlaskForm ):

    # TODO: Disallow name "new"

    display_name = StringField( 'Display Name', validators=[DataRequired()] )
    machine_name = StringField( 'Machine Name', validators=[DataRequired()] )
    absolute_path = StringField( 'Absolute Path', validators=[DataRequired()] )

class UploadLibraryForm( FlaskForm ):

    upload = FileField( 'CSV File' )

