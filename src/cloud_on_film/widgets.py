
import uuid
from urllib.parse import quote
from collections import namedtuple
from flask import render_template, render_template_string
from flask.helpers import url_for

from cloud_on_film.forms import EditBatchItemForm, EditItemForm, SaveSearchForm, SearchQueryForm

class WidgetRenderException( Exception ):
    pass

# region renderers

class WidgetRenderer( object ):

    ''' Provides a uniform means of gluing together forms/scripts/styles and
    ensuring they are included in the correct aread of the base template. '''

    template_name = None
    template_string = None

    def __init__( self, **kwargs ):
        if 'template_name' in kwargs:
            self.template_name = kwargs['template_name']
        elif 'template_string' in kwargs:
            self.template_string = kwargs['template_string']
        self.kwargs = kwargs
        self.widgets = []

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
            raise WidgetRenderException(
                'unreconcilable kwargs detected ({})'.format( key ) )

        return kwargs

    def render_kwargs( self, **kwargs ):

        ''' Dynamically build a list of kwargs to pass to the template,
        based on renderer and widget properties. '''

        if not kwargs:
            kwargs = self.kwargs.copy()

        for widget in self.widgets:
            for key in widget.kwargs:
                kwargs = self.add_kwarg( key, widget.kwargs[key], kwargs )

            #if self.is_base:
            #    if not 'include_content' in kwargs:
            #        kwargs['include_content'] = widget.template_name

        if 'include_scripts' in kwargs:
            kwargs['include_scripts'] = sorted( kwargs['include_scripts'],
                key=lambda script: script[0] )
            kwargs['include_scripts'] = [s[1] for s in kwargs['include_scripts']]

        if 'include_styles' in kwargs:
            kwargs['include_styles'] = sorted( kwargs['include_styles'],
                key=lambda script: script[0] )
            kwargs['include_styles'] = [s[1] for s in kwargs['include_styles']]

        return kwargs

    def render( self, **kwargs ):

        if not kwargs:
            kwargs = self.render_kwargs()

        if 'template_name' in kwargs and kwargs['template_name']:
            return render_template( kwargs['template_name'], **kwargs )
        elif 'template_string' in kwargs and kwargs['template_string']:
            return render_template_string( kwargs['template_string'], **kwargs )
        else:
            raise Exception( 'no template specified' )

    def add_widget( self, widget ):
        self.widgets.append( widget )
        widget.on_added( self )

class FormRenderer( WidgetRenderer ):

    def __init__( self, form_widget, use_base=True, **kwargs ):

        self.use_base = use_base

        super().__init__( **kwargs )

        self.add_widget( form_widget )
        self.form = form_widget

    def render( self, **kwargs ):

        form_key = self.form.form_pfx

        template_string = r"{% from 'macros.html.j2' import show_form %}" + \
            r"{{ show_form( " + form_key + r" ) }}"

        if not kwargs:
            kwargs = self.render_kwargs()

        if self.use_base:
            kwargs['template_name'] = 'base.html.j2'
            kwargs['content'] = render_template_string(
                template_string, **kwargs )

        return super().render( **kwargs )

class LibraryRenderer( WidgetRenderer ):

    def __init__( self, **kwargs ):
        super().__init__( template_name='libraries.html.j2', **kwargs )

    def render_kwargs( self, **kwargs ):

        eif_id = EditItemForm._form_id.replace( '-', '_' )
        if eif_id not in self.kwargs:
            self.add_widget( EditItemFormWidget( EditItemForm() ) )

        kwargs = self.kwargs.copy()

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

        kwargs = super().render_kwargs( **kwargs )

        return kwargs

# endregion

# region widgets

class FormWidget( object ):

    template_name = None
    default_classes = "w-100"
    form_type = None

    def __init__( self, form=None, **kwargs ):

        if not hasattr( self, 'kwargs' ):
            self.kwargs = {}

        if self.form_type:
            if form:
                assert( isinstance( form, self.form_type ) )

        # Try kwargs, form in order for form ID/prefix, else just use 'form'.
        self.form_id = kwargs['id'] if 'id' in kwargs else \
            form._form_id if hasattr( form, '_form_id' ) else \
            'form'
        if 'form_pfx' in kwargs:
            self.form_pfx = kwargs['form_pfx']
            del kwargs['form_pfx']
        else:
            self.form_pfx = self.form_id.replace( '-', '_' )

        self.add_form_scripts( form )

        if hasattr( form, '_include_styles_callbacks' ) and \
        'include_styles' not in self.kwargs:
            self.kwargs['include_styles'] = [s() for s in form._include_styles_callbacks]

        #if hasattr( form, '_form_enctype' ) and 'form_enctype' not in self.kwargs:
        #    self.kwargs['form_enctype'] = form._form_enctype

        self.kwargs[self.form_pfx] = form
        self.form = form

    def add_form_scripts( self, form ):

        if 'include_scripts' not in self.kwargs:
            self.kwargs['include_scripts'] = []

        # Use callbacks as url_for() has troubles in early execution.
        if hasattr( form, '_include_scripts_callbacks' ):
            self.kwargs['include_scripts'] += \
                [s() for s in form._include_scripts_callbacks \
                    if s() not in self.kwargs['include_scripts']]

        if hasattr( form, '_fields' ):
            for field in form._fields:
                self.add_form_scripts( form._fields[field] )

        if hasattr( form, 'widget' ):
            self.add_form_scripts( form.widget )

    def on_added( self, renderer ):
        pass

class EditItemFormWidget( FormWidget ):

    template_name = 'form_edit.html.j2'
    form_type = EditItemForm

class EditBatchItemFormWidget( FormWidget ):

    template_name = 'form_edit_batch.html.j2'
    form_type = EditBatchItemForm

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
    form_type = SearchQueryForm

    def on_added( self, renderer ):
        self.form._form_group_class = 'form-group h-50 d-flex'
        self.form._form_class = 'form-inline'
        if 'search_query' not in renderer.kwargs:
            renderer.kwargs['search_query'] = \
                quote( self.form.query.data ) if self.form.query.data else ''

class SavedSearchFormWidget( FormWidget ):

    template_name = 'form_search.html.j2'
    form_type = SaveSearchForm

# endregion
