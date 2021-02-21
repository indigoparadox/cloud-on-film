
import json
import os
import mimetypes
import io
from flask import \
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
    RenameItemForm, \
    SearchQueryForm, \
    SaveSearchForm, \
    SearchDeleteForm
from .importing import start_import_thread, threads
from .search import Searcher
from . import csrf

current_app.jinja_env.globals.update( user_current_uid=User.current_uid )
current_app.jinja_env.globals.update( folder_from_path=Folder.from_path )
current_app.jinja_env.globals.update( library_enumerate_all=Library.enumerate_all )
current_app.jinja_env.globals.update( tag_enumerate_roots=Tag.enumerate_roots )
current_app.jinja_env.globals.update( saved_search_enumerate_user=SavedSearch.enumerate_user )

def url_self( **args ):
    return url_for( request.endpoint, **dict( request.view_args, **args ) )

current_app.jinja_env.globals.update( url_self=url_self )

@current_app.route( '/preview/<int:file_id>' )
@current_app.route( '/preview/<int:file_id>/<int:width>/<int:height>' )
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

@current_app.route( '/fullsize/<int:file_id>' )
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

@current_app.route( '/libraries/new', methods=['GET', 'POST'] )
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

    return render_template( 'form_libraries_new.html.j2', form=form )

@current_app.route( '/libraries/upload', methods=['GET', 'POST'] )
@current_app.route( '/libraries/upload/<thread_id>', methods=['GET', 'POST'] )
def cloud_libraries_upload( thread_id='' ):

    form = UploadLibraryForm( request.form )

    title = 'Upload Library Data'
    progress = 0

    if 'POST' == request.method and thread_id:
        return jsonify( { 'filename': threads[thread_id].filename,
            'progress': int( threads[thread_id].progress ) } )

    elif 'POST' == request.method and \
    form.validate_on_submit() and not thread_id:
        pictures = \
            json.loads( request.files['upload'].read().decode( 'utf-8' ) )
        thread_id = start_import_thread( pictures )
        return redirect( url_for( 'cloud_libraries_upload', id=thread_id ) )

    elif 'GET' == request.method and thread_id:
        try:
            title = 'Uploading thread #{}'.format( thread_id )
            progress = int( threads[thread_id].progress )
        except KeyError:
            return redirect( url_for( 'cloud_libraries_upload' ) )

    return render_template( 'form_libraries_upload.html.j2',
        title=title, form=form, id=thread_id, progress=progress )

@current_app.route( '/libraries/<string:machine_name>' )
@current_app.route( '/libraries/<string:machine_name>/<path:relative_path>' )
@current_app.route( '/libraries/<string:machine_name>/<path:relative_path>/<int:page>' )
def cloud_libraries( machine_name=None, relative_path=None, page=0 ):

    rename_form = RenameItemForm( request.form )
    search_form = SearchQueryForm( request.form )

    l_globals = {
        'library_name': machine_name,
        'title': os.path.basename(relative_path )
            if relative_path else machine_name,
        'categories': request.args.get( 'categories' )
            if request.args.get( 'categories' ) in ['tags', 'folders']
                else 'folders' }

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

        offset = page * current_app.config['ITEMS_PER_PAGE']
        items = Item.secure_query( current_uid ) \
            .filter( Item.folder_id == folder.id ) \
            .order_by( Item.name ) \
            .offset( offset ) \
            .limit( current_app.config['ITEMS_PER_PAGE'] ) \
            .all()

        return render_template(
            'libraries.html.j2', **l_globals, folders=folder.children,
            items=items, items_classes=' pictures', page=page, current_uid=current_uid,
            this_folder=folder, rename_form=rename_form, search_form=search_form )

    except LibraryRootException as e:
        # Show the root of the given library ID.
        return render_template(
            'libraries.html.j2', **l_globals, folders=library.children,
            pictures=[], page=page, this_folder=None, current_uid=current_uid,
            rename_form=rename_form, search_form=search_form )

    except InvalidFolderException as e:

        # Try to see if this is a valid file and display it if so.
        file_item = Item.secure_query( current_uid ) \
            .filter( Item.folder_id == e.parent_id ) \
            .filter( Item.name == e.name ) \
            .first()

        if not file_item:
            abort( 404 )

        return render_template(
            'file_item.html.j2', **l_globals, file_item=file_item,
            page=page, rename_form=rename_form, search_form=search_form )


@current_app.route( '/search/save', methods=['POST'] )
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


        return redirect( url_for( 'cloud_items_search_saved', search_id=search.id ) )

    else:
        if save_search_form.search.data:
            for field, errors in save_search_form.errors.items():
                for error in errors:
                    flash( error, 'error')

        return redirect( url_for( 'cloud_items_search',
            name=save_search_form.name.data,
            query=save_search_form.query.data ) )

@current_app.route( '/search/delete/<int:search_id>', methods=['GET', 'POST'] )
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

        return redirect( url_for( 'cloud_root' ) )

@current_app.route( '/search/saved/<int:search_id>' )
def cloud_items_search_saved( search_id ):

    current_uid = User.current_uid()
    search = SavedSearch.secure_query( current_uid ) \
        .filter( SavedSearch.id == search_id ) \
        .first()

    if not search:
        abort( 404 )

    search_form = SearchQueryForm( request.args, csrf_enabled=False )
    save_search_form = SaveSearchForm( request.form )
    rename_form = RenameItemForm()

    page = int( request.args['page'] ) if 'page' in request.args else 0
    offset = page * current_app.config['ITEMS_PER_PAGE']
    limit = current_app.config['ITEMS_PER_PAGE']
    searcher = Searcher( search.query )
    searcher.lexer.lex()
    items = searcher.search( current_uid ) \
        .order_by( Item.name ) \
        .offset( offset ) \
        .limit( limit ) \
        .all()

    search_form.query.data = search.query
    save_search_form.query.data = search_form.query.data
    save_search_form.name.data = search.display_name

    return render_template(
        'libraries.html.j2', items=items, save_search_form=save_search_form,
        page=page, rename_form=rename_form, search_form=search_form )

@current_app.route( '/search' )
def cloud_items_search():

    current_uid = User.current_uid()

    search_form = SearchQueryForm( request.args, csrf_enabled=False )
    save_search_form = SaveSearchForm( request.form )
    rename_form = RenameItemForm( request.form )

    page = 0
    if (search_form.search.data or \
    save_search_form.save.data) and \
    (search_form.validate() or \
    save_search_form.validate()):
        page = int( search_form.page.data ) if search_form.page.data else 0
        query_str = search_form.query.data
        offset = page * current_app.config['ITEMS_PER_PAGE']
        limit = current_app.config['ITEMS_PER_PAGE']

        searcher = Searcher( query_str )
        searcher.lexer.lex()
        items = searcher.search( current_uid ) \
            .order_by( Item.name ) \
            .offset( offset ) \
            .limit( limit ) \
            .all()

        save_search_form.query.data = search_form.query.data

    else:
        if (search_form.search.data or \
        search_form.save.data):
            for field, errors in search_form.errors.items():
                for error in errors:
                    flash( error, 'error')
        items = []

    #return jsonify( [m.library_html() for m in query.all()] )

    return render_template(
        'libraries.html.j2', items=items, save_search_form=save_search_form,
        page=page, rename_form=rename_form, search_form=search_form )

@current_app.route( '/ajax/item/save', methods=['POST'] )
def cloud_item_ajax_save():

    current_uid = User.current_uid()

    save_form = RenameItemForm( request.form )
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
                return jsonify( {'submit_status': 'error', 'errors': ['Invalid save path specified.'] } )

    print( current_path.absolute_path )

    #db.session.commit()

    # Return the modified item.
    item_dict = item.to_dict( ignore_keys=['parent', 'folder'] )
    return jsonify( item_dict )

@current_app.route( '/ajax/item/<int:item_id>/json', methods=['GET'] )
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

@current_app.route( '/ajax/html/items/<int:folder_id>/<int:page>', methods=['GET'] )
def cloud_items_ajax_json( folder_id, page ):

    current_uid = User.current_uid()

    offset = page * current_app.config['ITEMS_PER_PAGE']

    items = Item.secure_query( current_uid ) \
        .filter( Item.folder_id == folder_id ) \
        .order_by( Item.name ) \
        .offset( offset ) \
        .limit( current_app.config['ITEMS_PER_PAGE'] ) \
        .all()

    #return jsonify( [i.to_dict( ignore_keys=['parent', 'folder'] ) for i in items] )
    return jsonify( [m.library_html() for m in items] )

@current_app.route( '/ajax/folders' )
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
            abort( 403 )
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
            abort( 403 )
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

    json_out += [{
        'id': 'folder-{}'.format( f.id ),
        'parent': 'folder-{}'.format( folder_id ) \
            if folder_id else 'library-{}'.format( f.library_id ),
        'text': f.name,
        'children': 0 < len( f.children )
    } for f in folders]

    return jsonify( json_out )

@current_app.route( '/ajax/tags.json')
def cloud_tags_ajax():
    # TODO: Omit empty tags.
    tags = db.session.query( Tag ).filter( Tag.name != '' ).all()
    tag_list = [t.path for t in tags]
    return jsonify( tag_list )

@current_app.route( '/tags/<path:path>' )
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

@current_app.route( '/ajax/html/search', methods=['GET'] )
def cloud_items_ajax_search():

    current_uid = User.current_uid()

    search_form = SearchQueryForm( request.args, csrf_enabled=False )

    if not search_form.validate():
        return jsonify( { 'submit_status': 'error', 'fields': search_form.errors } )

    page = int( search_form.page.data )
    query_str = search_form.query.data
    offset = page * current_app.config['ITEMS_PER_PAGE']
    limit = current_app.config['ITEMS_PER_PAGE']

    searcher = Searcher( query_str )
    searcher.lexer.lex()
    query = searcher.search( current_uid ) \
        .order_by( Item.name ) \
        .offset( offset ) \
        .limit( limit )

    return jsonify( [m.library_html() for m in query.all()] )

@current_app.route( '/' )
def cloud_root():
    return render_template( 'root.html.j2' )
