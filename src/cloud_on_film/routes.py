
import json
import os
import mimetypes
import io
import uuid
from flask import \
    Blueprint, \
    render_template, \
    request, \
    current_app, \
    flash, \
    send_file, \
    abort, \
    redirect, \
    url_for, \
    jsonify
from sqlalchemy import exc

from .models import \
    db, \
    Library, \
    Item, \
    Folder, \
    Tag, \
    InvalidFolderException, \
    LibraryRootException, \
    SavedSearch, \
    User
from .forms import \
    NewLibraryForm, \
    UploadLibraryForm, \
    SearchQueryForm, \
    SaveSearchForm, \
    EditItemForm, \
    SearchDeleteForm

from .importing import start_import_thread, threads
from .search import Searcher
from .widgets import \
    EditBatchItemFormWidget, \
    FormRenderer, \
    FormWidget, \
    LibraryRenderer, \
    SearchFormWidget, \
    SavedSearchFormWidget, WidgetRenderer
from . import csrf

libraries = Blueprint( 'libraries', __name__ )

libraries.add_app_template_global( lambda: str( uuid.uuid1() ), name='uuid' )
libraries.add_app_template_global( User.current_uid, name='user_current_uid' )
libraries.add_app_template_global( Folder.from_path, name='folder_from_path' )
libraries.add_app_template_global( Library.enumerate_all, name='library_enumerate_all' )
libraries.add_app_template_global( Tag.enumerate_roots, name='tag_enumerate_roots' )
libraries.add_app_template_global( SavedSearch.enumerate_user, name='saved_search_enumerate_user' )

def url_self( **args ):
    return url_for( request.endpoint, **dict( request.view_args, **args ) )

current_app.jinja_env.globals.update( url_self=url_self )

# region preview

@libraries.route( '/preview/<int:file_id>' )
@libraries.route( '/preview/<int:file_id>/<int:width>/<int:height>' )
def cloud_plugin_preview( file_id, width=160, height=120 ):

    '''Generate a preview thumbnail to be called by a tag src attribute on gallery pages.'''

    current_uid = User.current_uid()

    allowed_resolutions = [
        tuple( [int( i ) for i in r.split( ',' )] )
            for r in current_app.config['ALLOWED_PREVIEWS']]

    if not (width, height) in allowed_resolutions:
        abort( 404 )

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == file_id ).first()

    # Safety checks.
    if not item:
        abort( 403 )

    #p = importlib.import_module(
    #    '.plugins.{}.files'.format( item.filetype ), 'cloud_on_film' )
    #file_path = p.generate_thumbnail( file_id, (160, 120) )

    file_path = item.thumbnail_path( (width, height) )

    with open( file_path, 'rb' ) as pic_f:
        return send_file( io.BytesIO( pic_f.read() ),
            mimetypes.guess_type( file_path )[0] )

@libraries.route( '/fullsize/<int:file_id>' )
def cloud_plugin_fullsize( file_id ):

    current_uid = User.current_uid()

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == file_id ).first()

    # Safety checks.
    if not item:
        abort( 403 )

    # TODO: Figure out display tag (img/audio/video/etc).
    #p = importlib.import_module(
    #    '.plugins.{}.files'.format( item.filetype ), 'cloud_on_film' )
    #file_path = p.generate_thumbnail( file_id, (160, 120) )

    file_type = mimetypes.guess_type( item.path )[0]

    current_app.logger.debug( '{} mimetype: {}'.format( item.path, file_type ) )

    with open( item.absolute_path, 'rb' ) as pic_f:
        return send_file( io.BytesIO( pic_f.read() ), file_type )

# endregion

# region library

@libraries.route( '/libraries/new', methods=['GET', 'POST'] )
def cloud_libraries_new():

    form = NewLibraryForm( request.form )

    if 'POST' == request.method and form.validate():

        try:
            # Try to create the libary.
            lib = Library(
                display_name=form.display_name.data,
                machine_name=form.machine_name.data,
                absolute_path=form.absolute_path.data,
                nsfw=form.nsfw.data )
            db.session.add( lib )
            db.session.commit()
            flash( 'Library created.' )
        except exc.IntegrityError as e:
            current_app.logger.error( e )
            flash( e )
            db.session.rollback()

    form_widget = FormWidget( form=form, id='form-library-new', method='POST' )
    render = FormRenderer( form_widget, title='New Library' )
    
    return render.render()

@libraries.route( '/libraries/upload', methods=['GET', 'POST'] )
@libraries.route( '/libraries/upload/<thread_id>', methods=['GET', 'POST'] )
def cloud_libraries_upload( thread_id='' ):

    title = 'Upload Library Data'
    progress = 0
    form = None

    if 'POST' == request.method:

        form = UploadLibraryForm( request.form )
        if form.validate_on_submit():
            pictures = \
                json.loads( request.files['upload'].read().decode( 'utf-8' ) )
            thread_id = start_import_thread( pictures )
            return redirect(
                url_for( 'libraries.cloud_libraries_upload' ) + '?thread_id=thread_id' )

    elif 'GET' == request.method:
        thread_id = int( request.args['thread_id'] ) \
            if 'thread_id' in request.args else None
        form = UploadLibraryForm()
        form.progress.url = \
            url_for( 'libraries.cloud_ajax_libraries_upload' ) + \
            '?thread_id=' + str( thread_id )
        
        title = 'Uploading thread #{}'.format( thread_id )
        # XXX: DEBUG
        if 999 == thread_id:
            progress = 33
        else:
            progress = threads[thread_id].progress if thread_id in threads else 0

    form_widget = FormWidget( form=form, form_pfx='form' )
    render = FormRenderer( form_widget, title=title, progress=progress )

    return render.render()

@libraries.route( '/libraries/<string:machine_name>', methods=['GET'] )
@libraries.route( '/libraries/<string:machine_name>/<path:relative_path>', methods=['GET'] )
def cloud_libraries( machine_name=None, relative_path=None ):

    page = int( request.args['page'] ) if 'page' in request.args and request.args['page'] else 0
    offset = page * current_app.config['ITEMS_PER_PAGE']

    renderer = LibraryRenderer( page=page )

    # These forms will never be handled by this route, so they don't need
    # to collect POSTs.
    search_form = SearchQueryForm()
    search_widget = SearchFormWidget( form=search_form )
    renderer.add_widget( search_widget )

    current_uid = User.current_uid()

    library = Library.secure_query( current_uid ) \
        .filter( Library.machine_name == machine_name ) \
        .first()

    if not library:
        abort( 404 )

    try:
        # Show a folder listing.
        folder = Folder.from_path( library.id, relative_path, current_uid )

        if not folder:
            abort( 404 )

        items = Item.secure_query( current_uid ) \
            .filter( Item.folder_id == folder.id ) \
            .order_by( Item.name ) \
            .offset( offset ) \
            .limit( current_app.config['ITEMS_PER_PAGE'] ) \
            .all()

        renderer.kwargs['this_folder'] = folder
        renderer.kwargs['items'] = items
        renderer.kwargs['folders'] = folder.children

        return renderer.render()

    except LibraryRootException as e:
        # Show the root of the given library ID.

        items = Item.secure_query( current_uid ) \
            .filter( Item.folder_id == None ) \
            .order_by( Item.name ) \
            .offset( offset ) \
            .limit( current_app.config['ITEMS_PER_PAGE'] ) \
            .all()

        renderer.kwargs['items'] = items
        renderer.kwargs['folders'] = library.children

        return renderer.render()

    except InvalidFolderException as e:

        # Try to see if this is a valid file and display it if so.

        file_item = Item.secure_query( current_uid ) \
            .filter( Item.folder_id == e.parent_id ) \
            .filter( Item.name == e.name ) \
            .first()

        if not file_item:
            abort( 404 )

        # TODO: Individual file display.
        return render_template(
            'file_item.html.j2', file_item=file_item,
            page=page, edit_form=edit_form, search_form=search_form )

# endregion

# region search

@libraries.route( '/search/save', methods=['POST'] )
def cloud_items_search_save():

    current_uid = User.current_uid()

    save_search_form = SaveSearchForm( request.form )

    if save_search_form.validate():

        search = SavedSearch.secure_query( current_uid ) \
            .filter( SavedSearch.display_name == save_search_form.name.data ) \
            .first()

        if search:
            search.query = save_search_form.query.data
            db.session.commit()
            flash( 'Updated search #{}.'.format( search.id ) )

        else:

            search = SavedSearch(
                owner_id=current_uid,
                display_name=save_search_form.name.data,
                query=save_search_form.query.data )
            db.session.add( search )
            db.session.commit()
            flash( 'Created search #{}.'.format( search.id ) )


        return redirect( url_for( 'libraries.cloud_items_search_saved', search_id=search.id ) )

    else:
        if save_search_form.query.data:
            for field, errors in save_search_form.errors.items():
                for error in errors:
                    flash( error, 'error')

        return redirect( url_for( 'libraries.cloud_items_search',
            name=save_search_form.name.data,
            query=save_search_form.query.data ) )

@libraries.route( '/search/delete/<int:search_id>', methods=['GET', 'POST'] )
def cloud_items_search_delete( search_id ):

    search = SavedSearch.secure_query( User.current_uid() ) \
        .filter( SavedSearch.id == search_id ) \
        .first()

    if not search:
        abort( 404 )

    if 'GET' == request.method:
        delete = SearchDeleteForm( request.args )
        return render_template( 'form_search_delete.html.j2', search=search,
            delete=delete )

    elif 'POST' == request.method:
        delete = SearchDeleteForm( request.form )
        if not delete.validate():
            abort( 404 )

        db.session.delete( search )
        db.session.commit()

        return redirect( url_for( 'libraries.cloud_root' ) )

@libraries.route( '/search/saved/<int:search_id>' )
def cloud_items_search_saved( search_id ):

    search_form = SearchQueryForm( request.args )
    save_search_form = SaveSearchForm( request.form )

    current_uid = User.current_uid()
    search = SavedSearch.secure_query( current_uid ) \
        .filter( SavedSearch.id == search_id ) \
        .first()

    if not search:
        abort( 404 )

    page = int( request.args['page'] ) \
        if 'page' in request.args and request.args['page'] else 0
    offset = page * current_app.config['ITEMS_PER_PAGE']
    limit = current_app.config['ITEMS_PER_PAGE']
    searcher = Searcher( search.query )
    searcher.lexer.lex()
    items = searcher.search( current_uid ) \
        .order_by( Item.name ) \
        .offset( offset ) \
        .limit( limit ) \
        .all()

    renderer = LibraryRenderer( items=items, page=page )

    search_form.query.data = search.query
    save_search_form.query.data = search_form.query.data
    save_search_form.name.data = search.display_name

    save_search_widget = SavedSearchFormWidget( form=save_search_form )
    renderer.add_widget( save_search_widget )

    search_widget = SearchFormWidget( form=search_form )
    renderer.add_widget( search_widget )

    return renderer.render()

@libraries.route( '/search', methods=['GET'] )
def cloud_items_search():

    page = int( request.args['page'] ) \
        if 'page' in request.args and request.args['page'] else 0
    offset = page * current_app.config['ITEMS_PER_PAGE']

    current_uid = User.current_uid()

    save_search_form = SaveSearchForm( request.args, csrf_enabled=False )
    search_form = SearchQueryForm( request.args )

    renderer = LibraryRenderer( page=page )

    search_form_widget = SearchFormWidget( search_form )
    renderer.add_widget( search_form_widget )

    save_search_form_widget = SavedSearchFormWidget( save_search_form )
    renderer.add_widget( save_search_form_widget )

    if search_form.validate():
        query_str = search_form.query.data

        searcher = Searcher( query_str )
        searcher.lexer.lex()
        items = searcher.search( current_uid ) \
            .order_by( Item.name ) \
            .offset( offset ) \
            .limit( current_app.config['ITEMS_PER_PAGE'] ) \
            .all()

        search_form.query.data = search_form.query.data

        renderer.kwargs['items'] = items

    else:
        for field, errors in search_form.errors.items():
            for error in errors:
                flash( error, 'error')

    return renderer.render()

# endregion

# region ajax_json

@libraries.route( '/ajax/item/save', methods=['POST'] )
def cloud_item_ajax_save():

    current_uid = User.current_uid()

    save_form = EditItemForm( request.form )
    if not save_form.validate():
        return jsonify( { 'submit_status': 'error', 'fields': save_form.errors } )

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == save_form.id.data ) \
        .first()
    if not item:
        abort( 403 )

    # Translate tags data.
    new_tags = request.form['tags'].split( ',' )
    item.tags = [Tag.from_path( t ) for t in new_tags]

    # Translate location data.
    new_location = request.form['location'].split( '/' )
    current_path = None
    for path_id in new_location:
        if path_id.startswith( 'library-' ):
            library_id = path_id.split( '-' )[1]
            current_path = Library.secure_query( current_uid ) \
                .filter( Library.id == library_id ) \
                .first()
        elif path_id.startswith( 'folder-' ):
            folder_id = path_id.split( '-' )[1]
            if isinstance( current_path, Library ):
                current_path = Folder.secure_query( current_uid ) \
                    .filter( Folder.id == folder_id ) \
                    .filter( Folder.library_id == current_path.id ) \
                    .first()
            elif isinstance( current_path, Folder ):
                current_path = Folder.secure_query( current_uid ) \
                    .filter( Folder.id == folder_id ) \
                    .filter( Folder.parent_id == current_path.id ) \
                    .first()
            else:
                return jsonify(
                    {'submit_status': 'error', 'errors':
                        ['Invalid save path specified.'] } )

    #db.session.commit()

    # Return the modified item.
    item_dict = item.to_dict( ignore_keys=['parent', 'folder'] )
    return jsonify( item_dict )

@libraries.route( '/ajax/item/<int:item_id>/json', methods=['GET'] )
def cloud_item_ajax_json( item_id ):

    current_uid = User.current_uid()

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == item_id ) \
        .first()

    if not item:
        abort( 403 )

    item_dict = item.to_dict( ignore_keys=['parent', 'folder'] )

    parents = []
    parent_iter = item.folder
    while parent_iter:
        parents.append( 'folder-{}'.format( parent_iter.id ) )
        parent_iter = parent_iter.parent
    parents.reverse()
    parents.insert( 0, 'library-{}'.format( item.library_id ) )
    item_dict['parents'] = parents

    return jsonify( item_dict )

@current_app.route( '/ajax/libraries/upload', methods=['GET'] )
def cloud_ajax_libraries_upload():

    thread_id = int( request.args['thread_id'] ) if 'thread_id' in request.args else None

    if not thread_id:
        abort( 404 )

    if 999 == thread_id:
        progress = 33
    else:
        progress = threads[thread_id].progress if thread_id in threads else 0
    
    return jsonify( {'progress': progress} )

@libraries.route( '/ajax/folders' )
def cloud_folders_ajax():

    current_uid = User.current_uid()

    folder_id = request.args.get( 'id' )
    if folder_id.startswith( 'folder-' ):
        folder_id = folder_id.split( '-' )[1]
    if None != folder_id:
        try:
            folder_id = None if '#' == folder_id else int( folder_id )
        except ValueError as e:
            abort( 404 )

    json_out = []
    folders = []
    query = Folder.secure_query( current_uid )
    if folder_id:
        # The tree already has this folder, so iterate through its children.
        folder_parent = query \
            .filter( Folder.id == folder_id ) \
            .order_by( Folder.name ) \
            .first()
        if not folder_parent:
            abort( 404 )
        folders = folder_parent.children
    else:
        # Get the tree started and iterate through the library's root folders.
        json_out += [{
            'id': 'root',
            'parent': '#',
            'text': 'root'
        }]
        libraries = Library.secure_query( current_uid ) \
            .order_by( Library.display_name ) \
            .all()
        if 0 == len( libraries ):
            abort( 404 )
        for library in libraries:
            json_out.append(
                {
                    'id': 'library-{}'.format( library.id ),
                    'parent': 'root',
                    'text': library.display_name
                }
            )
            folders += query.filter( Folder.parent_id == None ) \
                .filter( Folder.library_id == library.id ) \
                .order_by( Folder.name ) \
                .all()

    # Convert all the folders on the list to a format palatable to jsTree.
    json_out += [{
        'id': 'folder-{}'.format( f.id ),
        'parent': 'folder-{}'.format( folder_id ) \
            if folder_id else 'library-{}'.format( f.library_id ),
        'text': f.name,
        'children': 0 < len( f.children )
    } for f in folders]

    return jsonify( json_out )

@libraries.route( '/ajax/folder/id_path', methods=['POST'] )
def cloud_ajax_folder_id_path():

    ''' Given a relative path starting with a Library machine_name,
    return a list of numeric IDs starting with that' Library's ID. '''

    path = request.form['path']
    library = None

    if path:
        path = path.split( '/' )
        library_name = path[0]
        path.pop( 0 )
        path = '/'.join( path )

        library = Library.secure_query( User.current_uid() ) \
            .filter( Library.machine_name == library_name ) \
            .first()
    else:
        library = Library.secure_query( User.current_uid() ) \
            .first()

    if not library:
        abort( 404 )

    try:
        # A path was provided, so try to find the DB folder for it.
        folder = Folder.from_path( library.id, path, User.current_uid() )

        if not folder:
            abort( 404 )

    except LibraryRootException:
        # No parent folder exists.
        folder = None

    # Build the path by iterating upwards from the found folder.
    # Skip if no fullder due to LibraryRootException above.
    id_path = []
    while folder:
        id_path.insert( 0, 'folder-{}'.format( folder.id ) )
        folder = folder.parent
    id_path.insert( 0, 'library-{}'.format( library.id ) )

    return jsonify( id_path )

@libraries.route( '/ajax/tags.json' )
def cloud_tags_ajax():
    # TODO: Omit empty tags.
    tags = db.session.query( Tag ).filter( Tag.name != '' ).all()
    tag_list = [t.path for t in tags]
    return jsonify( tag_list )

@libraries.route( '/tags/<path:path>' )
def cloud_tags( path ):

    current_uid = User.current_uid()

    # TODO: Omit empty tags.
    tag = Tag.from_path( path )

    items = Item.secure_query( current_uid ) \
        .filter( tag in Item.tags ) \
        .all()

    if not tag:
        abort( 404 )

    return render_template( 'libraries.html.j2', pictures=items,
        tag_roots=[tag.parent], this_tag=tag )

@current_app.route( '/ajax/search/delete', methods=['POST'] )
def cloud_items_ajax_search_delete():

    delete = SearchDeleteForm( request.form )

    if not delete.validate():
        return jsonify( { 'submit_status': 'error', 'fields': delete.errors } )

    search = SavedSearch.secure_query( User.current_uid() ) \
        .filter( SavedSearch.id == delete.id.data ) \
        .first()

    if not search:
        return jsonify( {
            'submit_status': 'error',
            'message': 'Specified search not found.' } )

    db.session.delete( search )
    db.session.commit()

    return jsonify( { 'submit_status': 'success' } )

# endregion

# region ajax_html

@libraries.route( '/ajax/html/items/<int:folder_id>/<int:page>', methods=['GET'] )
def cloud_items_ajax_json( folder_id, page ):

    offset = page * current_app.config['ITEMS_PER_PAGE']

    items = Item.secure_query( User.current_uid() ) \
        .filter( Item.folder_id == folder_id ) \
        .order_by( Item.name ) \
        .offset( offset ) \
        .limit( current_app.config['ITEMS_PER_PAGE'] ) \
        .all()

    #return jsonify( [i.to_dict( ignore_keys=['parent', 'folder'] ) for i in items] )
    return jsonify( [m.library_html() for m in items] )

@libraries.route( '/ajax/html/search', methods=['GET'] )
def cloud_items_ajax_search():

    search_form = SearchQueryForm( request.args, csrf_enabled=False )

    if not search_form.validate():
        return jsonify( { 'submit_status': 'error', 'fields': search_form.errors } )

    page = 0
    try:
        page = int( search_form.page.data )
    except ValueError:
        pass

    query_str = search_form.query.data
    offset = page * current_app.config['ITEMS_PER_PAGE']

    searcher = Searcher( query_str )
    searcher.lexer.lex()
    query = searcher.search( User.current_uid() ) \
        .order_by( Item.name ) \
        .offset( offset ) \
        .limit( current_app.config['ITEMS_PER_PAGE'] )

    return jsonify( [m.library_html() for m in query.all()] )

@libraries.route( '/ajax/html/batch', methods=['GET'] )
def cloud_items_ajax_batch():

    item_ids = [int( i.split( '-' )[-1] ) for i in request.args['item_ids'].split( ',' )]

    #edit_form = EditBatchItemForm()

    #page = int( search_form.page.data )
    #offset = page * current_app.config['ITEMS_PER_PAGE']
    limit = current_app.config['ITEMS_PER_PAGE']
    render = WidgetRenderer( template_name='form_edit_batch.html.j2' )

    items = Item.secure_query( User.current_uid() ) \
        .filter( Item.id.in_( item_ids ) ) \
        .limit( limit ) \
        .all()

    render.add_widget( EditBatchItemFormWidget( items ) )

    return render.render()

# endregion

@libraries.route( '/' )
def cloud_root():
    return render_template( 'root.html.j2' )
