
import uuid
from flask.helpers import url_for
from flask.templating import render_template
from markupsafe import Markup
from wtforms.validators import DataRequired, Optional
from wtforms import \
    Field, \
    StringField as _StringField, \
    FileField as _FileField, \
    BooleanField as _BooleanField, \
    HiddenField as _HiddenField, \
    TextAreaField as _TextAreaField, \
    SubmitField as _SubmitField

class COFBaseFieldMixin( object ):
    def process_kwargs( self, kwargs ):

        self.dropdown = False
        if 'dropdown' in kwargs:
            if kwargs['dropdown']:
                self.dropdown = True 
            del kwargs['dropdown']

        self.url = ''
        if 'url_callback' in kwargs:
            self.url = kwargs['url_callback']()
            del kwargs['url_callback']
        elif 'url' in kwargs:
            self.url = kwargs['url']
            del kwargs['url']

        return kwargs

class COFBaseFormMixin( object ):

    errors = {}
    _form_action_callback = lambda s: '#'
    _form_group_class = ''
    _form_class = ''
    _form_id = ''
    _form_method = 'POST'
    _form_enctype = ''

    def has_dropdowns( self ):
        dropdowns = False
        for key in self._fields:
            if isinstance( self._fields[key], COFBaseFieldMixin ) \
            and self._fields[key].dropdown:
                dropdowns = True
        return dropdowns

    @property
    def form_id( self ):
        if hasattr( self, '_form_id' ):
            return self._form_id
        else:
            return None

    @property
    def form_mode( self ):
        if hasattr( self, '_form_mode' ):
            return self._form_mode
        else:
            return None

# region enhanced_fields

class StringField( _StringField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

class FileField( _FileField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

class BooleanField( _BooleanField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

class HiddenField( _HiddenField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

class TextAreaField( _TextAreaField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

class SubmitField( _SubmitField, COFBaseFieldMixin ):
    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

#endregion

#region widgets

class DummyWidget( object ):

    '''A convenience widget with no field and just a label.'''

    def __init__( self, html_tag='', prefix_label=True ):
        self.html_tag = html_tag
        self.prefix_label = prefix_label

    def __call__( self, field, **kwargs ):
        return ''

class ProgressWidget( object ):

    ''' A widget for displaying a progress bar using AJAX. '''

    def __call__( self, field, **kwargs ):
        return '''
<script type="text/javascript">
$().ready( function() {{
    updateProgress( "{update_url}" );
}} );
</script>
<div class="py-3">
   <div class="progress">
      <div id="thread-progress" class="progress-bar" role="progressbar" style="width: 0"></div>
   </div>
   <div id="current-filename"></div>
</div>
'''.format( update_url=field.url )

class BrowserWidget( object ):

    _include_scripts_callbacks = [
        lambda: (20, url_for( 'static', filename='jstree.min.js' )),
        lambda: (80, url_for( 'static', filename='field-browser.js' )) ]

    _include_styles_callbacks = [
        lambda: (10, url_for( 'static', filename='jstree/style.min.css' )) ]

    def __call__(self, field, **kwargs ):
        return render_template( 'field-tree.html.j2',
            field_name=field.name,
            field_data=field.data,
            browser_url=field.url,
            field_uuid=str( uuid.uuid1() ) )

class TagsWidget( object ):

    _include_scripts_callbacks = [
        lambda: (20, url_for( 'static', filename='typeahead.bundle.min.js' )),
        lambda: (25, url_for( 'static', filename='bootstrap-tagsinput.min.js' )),
        lambda: (80, url_for( 'static', filename='field-tags.js' )) ]

    _include_styles_callbacks = [
        lambda: (10, url_for( 'static', filename='bootstrap-tagsinput.css' )) ]

    def __call__(self, field, **kwargs ):
        return '''
<input type="text" data-role="tagsinput"
    'class="{classes}" id="{id}" name="{name}" value="{value}" />
<script type="text/javascript">
$().ready( function() {{
    $('#{id}').enableTags( "{tags_url}" );
}} );
</script>
'''.format(
            classes=kwargs['class_'] if 'class_' in kwargs else field.name,
            id=kwargs['id'] if 'id' in kwargs else field.name,
            name=field.name,
            value=field.data if hasattr( field, 'data' ) else '',
            tags_url=field.url )

#endregion

#region custom_fields

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
        super( LabelField, self ).__init__()

    def label( self ):
        return Markup( '<p>{}</p>'.format( self._label ) )

    def _value( self ):
        return None

    def default( self ):
        return ''

    def process_formdata( self, valuelist ):
        return None

class BrowserField( Field, COFBaseFieldMixin ):

    widget = BrowserWidget()

    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

    def _value( self ):
        return 'qqq'

    def default( self ):
        return 'xxx'

    def process_formdata( self, valuelist ):
        return 'rrr'

class ProgressField( Field, COFBaseFieldMixin ):

    widget = ProgressWidget()

    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

    def _value( self ):
        return None

    def default( self ):
        return 'xxx'

    def process_formdata( self, valuelist ):
        return None

class TagsField( Field, COFBaseFieldMixin ):

    widget = TagsWidget()

    def __init__( self, *args, **kwargs ):
        kwargs = self.process_kwargs( kwargs )
        super().__init__( *args, **kwargs )

    def _value( self ):
        return 'qqq'

    def default( self ):
        return 'xxx'

    def process_formdata( self, valuelist ):
        return 'rrr'

#endregion

#region validators

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

#endregion
