
from collections import namedtuple
from flask import render_template, url_for

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

    def __init__( self, form=None, **kwargs ):
        self.kwargs = {'form_{}'.format( k ): v for k, v in kwargs.items()}

        if hasattr( form, '_form_id' ) and not 'form_id' in self.kwargs:
            self.kwargs['form_id'] = form._form_id

        if hasattr( form, '_form_method' ) and not 'form_method' in self.kwargs:
            self.kwargs['form_method'] = form._form_method

        # Use callbacks as url_for() has troubles in early execution.
        if hasattr( form, '_include_scripts_callbacks' ) and not 'include_scripts' in self.kwargs:
            self.kwargs['include_scripts'] = [s() for s in form._include_scripts_callbacks]

        if hasattr( form, '_form_enctype' ) and not 'form_enctype' in self.kwargs:
            self.kwargs['form_enctype'] = form._form_enctype

        self.kwargs['form'] = form

class EditItemFormWidget( FormWidget ):

    ItemData = namedtuple( 'item_data', ['id', 'name', 'comment', 'tags', 'location'] )

    template_name = 'form_edit.html.j2'

    def __init__( self, item=None, form=None, **kwargs ):

        super().__init__( **kwargs )

        self.kwargs['include_scripts'] = [
            url_for( 'static', filename='typeahead.bundle.min.js' ),
            url_for( 'static', filename='bootstrap-tagsinput.min.js' ),
            url_for( 'static', filename='jstree.min.js' ),
            url_for( 'static', filename='edit-item.js' )
        ]

        self.kwargs['include_styles'] = [
            url_for( 'static', filename='bootstrap-tagsinput.css' ),
            url_for( 'static', filename='jstree/style.min.css' )
        ]

        if form:
            assert( RenameItemForm == type( form ) )
            self.kwargs['edit_form'] = form
        else:
            self.kwargs['edit_form'] = RenameItemForm()

        if item:
            self.kwargs['edit_form'].id.data = item.id
            self.kwargs['edit_form'].name.data = item.name
            self.kwargs['edit_form'].comment.data = item.comment
            self.kwargs['edit_form'].tags.data = ','.join( [t.path for t in item.tags] )
            self.kwargs['edit_form'].location.data = item.location

class EditBatchItemFormWidget( FormWidget ):

    template_name = 'form_edit_batch.html.j2'

    def __init__( self, items_list, **kwargs ):

        super().__init__( **kwargs )

        self.kwargs['edit_form'] = EditBatchItemForm(
            data={'items': [EditItemFormWidget.ItemData(
                i.id,
                i.name,
                i.comment,
                ','.join( [t.path for t in i.tags] ),
                i.location
                ) for i in items_list] } )

# endregion
