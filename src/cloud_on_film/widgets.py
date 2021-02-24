
from urllib.parse import quote
from collections import namedtuple
from flask import render_template
from flask.helpers import url_for
from wtforms.fields.core import Field
from wtforms.form import Form

from cloud_on_film.forms import EditBatchItemForm, EditItemForm, SaveSearchForm, SearchQueryForm

# region renderers

class WidgetRenderer( object ):

    ''' Provides a uniform means of gluing together forms/scripts/styles and
    ensuring they are included in the correct aread of the base template. '''

    def __init__( self, template='base.html.j2', **kwargs ):
        self.template = template
        self.kwargs = kwargs
        self.widgets = []

        self.is_base = False
        if 'base.html.j2' == template:
            self.is_base = True

    def add_kwarg( self, key, value, kwargs ):

        if key in kwargs and \
        isinstance( kwargs[key], list ) and \
        isinstance( value, list ):
            if key.startswith( 'include' ) and \
            0 < len( kwargs[key] ) and \
            isinstance( kwargs[key][0], tuple ):
                kwargs[key] += [w for w in value if w[1] not in [a[1] for a in kwargs[key]]]
            else:
                kwargs[key] += [w for w in value if w not in kwargs[key]]

        elif key in kwargs and \
        isinstance( kwargs[key], dict ) and \
        isinstance( value, dict ):
            kwargs.update( value )

        elif not key in kwargs:
            kwargs[key] = value

        else:
            raise Exception( 'unreconcilable kwargs detected ({})'.format( key ) )

        return kwargs

    def render_kwargs( self ):

        ''' Dynamically build a list of kwargs to pass to the template,
        based on renderer and widget properties. '''

        kwargs = self.kwargs.copy()
        for widget in self.widgets:
            for key in widget.kwargs:
                kwargs = self.add_kwarg( key, widget.kwargs[key], kwargs )

            if self.is_base:
                if not 'include_content' in kwargs:
                    kwargs['include_content'] = widget.template_name

        return kwargs

    def render( self ):

        kwargs = self.render_kwargs()

        if 'include_scripts' in kwargs:
            kwargs['include_scripts'] = sorted( kwargs['include_scripts'],
                key=lambda script: script[0] )
            kwargs['include_scripts'] = [s[1] for s in kwargs['include_scripts']]

        if 'include_styles' in kwargs:
            kwargs['include_styles'] = sorted( kwargs['include_styles'],
                key=lambda script: script[0] )
            kwargs['include_styles'] = [s[1] for s in kwargs['include_styles']]

        return render_template( self.template, **kwargs )

    def add_widget( self, widget ):
        self.widgets.append( widget )
        widget.on_added( self )

class LibraryRenderer( WidgetRenderer ):

    def __init__( self, **kwargs ):
        super().__init__( template='libraries.html.j2', **kwargs )

    def render_kwargs( self ):

        eif_id = EditItemForm._form_id.replace( '-', '_' )
        if eif_id not in self.kwargs:
            self.add_widget( EditItemFormWidget() )

        kwargs = super().render_kwargs()

        library_scripts = [
            (10, url_for( 'static', filename='jquery.unveil2.min.js' )),
            (10, url_for( 'static', filename='featherlight.min.js' )),
            (10, url_for( 'static', filename='featherlight.gallery.min.js' )),
            (90, url_for( 'static', filename='libraries.js' )),
            (90, url_for( 'static', filename='edit-item.js' )) ]

        kwargs = self.add_kwarg( 'include_scripts', library_scripts, kwargs )

        library_styles = [
            (10, url_for( 'static', filename='featherlight.min.css' )),
            (10, url_for( 'static', filename='featherlight.gallery.min.css' )),
            (90, url_for( 'static', filename='gallery.css' )) ]

        kwargs = self.add_kwarg( 'include_styles', library_styles, kwargs )

        return kwargs

# endregion

# region widgets

class FormWidget( object ):

    template_name = 'form_generic.html.j2'
    default_classes = "w-100"

    def __init__( self, form=None, **kwargs ):

        if not hasattr( self, 'kwargs' ):
            self.kwargs = {}

        # Try kwargs, form in order for form ID/prefix, else just use 'form'.
        self.form_id =  kwargs['id'] if 'id' in kwargs else \
            form._form_id if hasattr( form, '_form_id' ) else \
            'form'
        if 'form_pfx' in kwargs:
            self.form_pfx = kwargs['form_pfx']
            del kwargs['form_pfx']
        else:
            self.form_pfx = self.form_id.replace( '-', '_' )

        self.kwargs = {'form_{}'.format( k ): v for k, v in kwargs.items()}

        #if hasattr( form, '_form_id' ) and not 'form_id' in self.kwargs:
        self.kwargs[self.form_pfx + '_id'] = self.form_id

        if 'form_class' not in self.kwargs:
            self.kwargs[self.form_pfx + '_class'] = self.default_classes

        # Aggregate classes from form and kwargs.
        #if hasattr( form, '_form_class' ) and not 'form_class' in self.kwargs:
        #    self.kwargs[self.form_pfx + '_class'] = form._form_class
        if hasattr( form, '_form_class' ) and 'form_class' in self.kwargs:
            self.kwargs[self.form_pfx + '_class'] += form._form_class

        if hasattr( form, '_form_method' ) and 'form_method' not in self.kwargs:
            self.kwargs[self.form_pfx + '_method'] = form._form_method
        elif 'form_method' not in self.kwargs:
            self.kwargs[self.form_pfx + '_method'] = 'GET'

        self.add_form_scripts( form )

        if hasattr( form, '_include_styles_callbacks' ) and \
        'include_styles' not in self.kwargs:
            self.kwargs['include_styles'] = [s() for s in form._include_styles_callbacks]

        if hasattr( form, '_form_enctype' ) and 'form_enctype' not in self.kwargs:
            self.kwargs['form_enctype'] = form._form_enctype

        self.kwargs[self.form_pfx] = form
        self.form = form

    def add_form_scripts( self, form ):

        if 'include_scripts' not in self.kwargs:
            self.kwargs['include_scripts'] = []

        # Use callbacks as url_for() has troubles in early execution.
        if hasattr( form, '_include_scripts_callbacks' ):
            self.kwargs['include_scripts'] += \
                [s() for s in form._include_scripts_callbacks if s() not in self.kwargs['include_scripts']]

        if hasattr( form, '_fields' ):
            for field in form._fields:
                self.add_form_scripts( form._fields[field] )

        if hasattr( form, 'widget' ):
            self.add_form_scripts( form.widget )

    def on_added( self, renderer ):
        pass

class EditItemFormWidget( FormWidget ):

    template_name = 'form_edit.html.j2'

    def __init__( self, form=None, **kwargs ):
        if form:
            assert( EditItemForm == type( form ) )
        else:
            form = EditItemForm()

        super().__init__( form, **kwargs )

class EditBatchItemFormWidget( FormWidget ):

    template_name = 'form_edit_batch.html.j2'

    ItemData = namedtuple( 'item_data', ['id', 'name', 'comment', 'tags', 'location'] )

    def __init__( self, items_list, form=None, **kwargs ):

        self.kwargs = {}

        if form:
            assert( EditBatchItemForm == type( form ) )
        else:
            form = EditBatchItemForm( data={'items': [EditBatchItemFormWidget.ItemData(
                i.id,
                i.name,
                i.comment,
                ','.join( [t.path for t in i.tags] ),
                i.location
                ) for i in items_list] } )

        super().__init__( form, **kwargs )

class SearchFormWidget( FormWidget ):

    template_name = 'form_search.html.j2'

    def on_added( self, renderer ):
        if 'search_query' not in renderer.kwargs:
            renderer.kwargs['search_query'] = \
                quote( self.form.query.data ) if self.form.query.data else ''

class SavedSearchFormWidget( FormWidget ):

    template_name = 'form_search.html.j2'

# endregion
