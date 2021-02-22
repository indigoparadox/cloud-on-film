
from collections import namedtuple
from flask import render_template

from cloud_on_film.forms import EditBatchItemForm, RenameItemForm

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

    def render( self ):

        kwargs = self.kwargs.copy()
        for widget in self.widgets:
            for key in widget.kwargs:
                if key in kwargs and \
                isinstance( kwargs[key], list ) and \
                isinstance( widget.kwargs[key], list ):
                    kwargs[key] += widget.kwargs[key]

                elif key in kwargs and \
                isinstance( kwargs[key], dict ) and \
                isinstance( widget.kwargs[key], dict ):
                    kwargs.update( widget.kwargs )

                elif key in widget.kwargs and \
                not key in kwargs:
                    kwargs[key] = widget.kwargs[key]

                else:
                    raise Exception( 'unreconcilable kwargs detected ({})'.format( key ) )

            if self.is_base:
                if not 'include_content' in kwargs:
                    kwargs['include_content'] = widget.template_name

        return render_template( self.template, **kwargs )

    def add_widget( self, widget ):
        self.widgets.append( widget )

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

        # Use callbacks as url_for() has troubles in early execution.
        if hasattr( form, '_include_scripts_callbacks' ) and \
        'include_scripts' not in self.kwargs:
            self.kwargs['include_scripts'] = \
                [s() for s in form._include_scripts_callbacks]

        if hasattr( form, '_include_styles_callbacks' ) and \
        'include_styles' not in self.kwargs:
            self.kwargs['include_styles'] = [s() for s in form._include_styles_callbacks]

        if hasattr( form, '_form_enctype' ) and 'form_enctype' not in self.kwargs:
            self.kwargs['form_enctype'] = form._form_enctype

        self.kwargs[self.form_pfx] = form

class EditItemFormWidget( FormWidget ):

    ItemData = namedtuple( 'item_data', ['id', 'name', 'comment', 'tags', 'location'] )

    template_name = 'form_edit.html.j2'

    def __init__( self, item=None, form=None, **kwargs ):

        self.kwargs = {}

        if form:
            assert( RenameItemForm == type( form ) )
        else:
            form = RenameItemForm()

        super().__init__( form, **kwargs )

        if item:
            self.kwargs[self.form_pfx].id.data = item.id
            self.kwargs[self.form_pfx].name.data = item.name
            self.kwargs[self.form_pfx].comment.data = item.comment
            self.kwargs[self.form_pfx].tags.data = ','.join( [t.path for t in item.tags] )
            self.kwargs[self.form_pfx].location.data = item.location

class EditBatchItemFormWidget( FormWidget ):

    template_name = 'form_edit_batch.html.j2'

    def __init__( self, items_list, form=None, **kwargs ):

        self.kwargs = {}

        if form:
            assert( EditBatchItemForm == type( form ) )
        else:
            form = EditBatchItemForm( data={'items': [EditItemFormWidget.ItemData(
                i.id,
                i.name,
                i.comment,
                ','.join( [t.path for t in i.tags] ),
                i.location
                ) for i in items_list] } )

        super().__init__( form, **kwargs )

# endregion
