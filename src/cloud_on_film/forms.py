
from flask import url_for
from flask_wtf import FlaskForm
from wtforms import \
    StringField as _StringField, \
    FileField as _FileField, \
    BooleanField as _BooleanField, \
    HiddenField as _HiddenField, \
    TextAreaField as _TextAreaField, \
    SubmitField as _SubmitField, \
    FormField, \
    FieldList
from wtforms.validators import DataRequired

from .fields import \
    StringField, \
    FileField, \
    BooleanField, \
    HiddenField, \
    TextAreaField, \
    SubmitField, \
    LabelField, \
    ProgressField, \
    COFBaseFormMixin

class NewLibraryForm( FlaskForm, COFBaseFormMixin ):

    # TODO: Disallow name "new"

    _form_id = 'form-library-new'
    _form_mode = 'POST'

    display_name = StringField( 'Display Name', validators=[DataRequired()] )
    machine_name = StringField( 'Machine Name', validators=[DataRequired()] )
    absolute_path = StringField( 'Absolute Path', validators=[DataRequired()] )
    nsfw = BooleanField( 'NSFW' )
    delete = SubmitField( 'Create' )

class UploadLibraryForm( FlaskForm, COFBaseFormMixin ):

    _form_id = 'form-library-upload'
    _form_mode = 'POST'
    _include_scripts_callbacks = [lambda: url_for( 'static', filename='field-progress.js')]
    _form_enctype = 'multipart/form-data'
    
    upload = FileField( 'Library Import File' )
    progress = ProgressField( 'Upload Progress' )
    submit = SubmitField( 'Submit' )

class RenameItemForm( FlaskForm, COFBaseFormMixin ):

    id = HiddenField( '' )
    name = StringField( 'Name', validators=[DataRequired()] )
    #nsfw = BooleanField( 'NSFW' )
    tags = StringField( 'Tags' )
    location = StringField( 'Location', validators=[DataRequired()] )
    comment = TextAreaField( 'Comment' )

class EditBatchItemForm( FlaskForm, COFBaseFormMixin ):

    items = FieldList( FormField( RenameItemForm ) )

class SaveSearchForm( FlaskForm, COFBaseFormMixin ):

    query = _StringField( 'Search String', validators=[DataRequired()] )
    name = StringField( 'Search Name', validators=[DataRequired()] )
    save = SubmitField( 'Save Search' )
    
class SearchQueryForm( FlaskForm, COFBaseFormMixin ):

    query = _StringField( '', validators=[DataRequired()] )
    search = SubmitField( 'Search' )
    #save_as = StringField( 'Query Name', dropdown=True, validators=[RequiredIf( save=True )] )
    #save = SubmitField( 'Save', dropdown=True )
    page = HiddenField( '' )

class SearchDeleteForm( FlaskForm, COFBaseFormMixin ):
    
    id = HiddenField( '' )
    prompt = LabelField( 'Are you sure you wish to delete this saved search? This action cannot be undone.')
    delete = SubmitField( 'Delete' )
