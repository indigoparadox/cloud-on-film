
from flask_wtf import FlaskForm
from wtforms import \
    Field, \
    StringField as _StringField, \
    FileField as _FileField, \
    BooleanField as _BooleanField, \
    HiddenField as _HiddenField, \
    TextAreaField as _TextAreaField, \
    SubmitField as _SubmitField
from wtforms.validators import DataRequired, Optional
from markupsafe import Markup

class COFBaseFieldMixin( object ):
    def process_kwargs( self, kwargs ):
        self.dropdown = False
        if 'dropdown' in kwargs:
            if kwargs['dropdown']:
                self.dropdown = True 
            del kwargs['dropdown']
        return kwargs

class COFBaseFormMixin( object ):
    def has_dropdowns( self ):
        dropdowns = False
        for key in self._fields:
            if isinstance( self._fields[key], COFBaseFieldMixin ) \
            and self._fields[key].dropdown:
                dropdowns = True
        return dropdowns

class StringField( _StringField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super( _StringField, self ).__init__( *args, **kwargs )

class FileField( _FileField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super( _FileField, self ).__init__( *args, **kwargs )

class BooleanField( _BooleanField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super( _BooleanField, self ).__init__( *args, **kwargs )

class HiddenField( _HiddenField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super( _HiddenField, self ).__init__( *args, **kwargs )

class TextAreaField( _TextAreaField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super( _TextAreaField, self ).__init__( *args, **kwargs )

class SubmitField( _SubmitField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super( _SubmitField, self ).__init__( *args, **kwargs )

class DummyWidget(object):
    
    '''A convenience widget with no field and just a label.'''

    def __init__( self, html_tag='', prefix_label=True ):
        self.html_tag = html_tag
        self.prefix_label = prefix_label

    def __call__( self, field, **kwargs ):
        return ''

class LabelField( Field, COFBaseFieldMixin ):
    widget = DummyWidget()

    class DummyMeta( object ):
        def render_field( self, *args, **kwargs ):
            #return '<p class="{}">{}</p>'.format( args[1]['class_'], args[0]._label )
            return ''

    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        self.name = ''
        self.filters = []
        self._label = args[0]
        self.meta = LabelField.DummyMeta()
        super( Field, self ).__init__()

    def label( self ):
        return Markup( '<p>{}</p>'.format( self._label ) )

    def _value( self ):
        return None

    def default( self ):
        return ''

    def process_formdata( self, valuelist ):
        return None

class RequiredIf( object ):
    '''Validates field conditionally.
    Usage::
        login_method = StringField('', [AnyOf(['email', 'facebook'])])
        email = StringField('', [RequiredIf(login_method='email')])
        password = StringField('', [RequiredIf(login_method='email')])
        facebook_token = StringField('', [RequiredIf(login_method='facebook')])
    '''
    def __init__( self, *args, **kwargs ):
        self.conditions = kwargs
        self.message = 'No name provided for saved query.'

    def __call__( self, form, test_field ):
        for name, data in self.conditions.items():
            iter_field = form[name]
            if iter_field is None:
                raise Exception( 'no field named "{}"'.format( name ) )
            if iter_field.data == data and not test_field.data:
                DataRequired.__call__( self, form, test_field )
            Optional()( form, test_field )

class NewLibraryForm( FlaskForm, COFBaseFormMixin ):

    # TODO: Disallow name "new"

    display_name = StringField( 'Display Name', validators=[DataRequired()] )
    machine_name = StringField( 'Machine Name', validators=[DataRequired()] )
    absolute_path = StringField( 'Absolute Path', validators=[DataRequired()] )
    nsfw = BooleanField( 'NSFW' )
    delete = SubmitField( 'Create' )

class UploadLibraryForm( FlaskForm, COFBaseFormMixin ):

    upload = FileField( 'Library Import File' )

class RenameItemForm( FlaskForm, COFBaseFormMixin ):

    id = HiddenField( '' )
    name = StringField( 'Name', validators=[DataRequired()] )
    #nsfw = BooleanField( 'NSFW' )
    tags = StringField( 'Tags' )
    comment = TextAreaField( 'Comment' )
    location = HiddenField( '', validators=[DataRequired()] )

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
