
import logging 
from flask import Flask, render_template, request, current_app, flash, send_file, abort, redirect, url_for, jsonify
from sqlalchemy import exc
from .models import LibraryPermissionsException, StatusEnum, db, Library, Item, Folder, Tag, InvalidFolderException, LibraryRootException
from .forms import NewLibraryForm, UploadLibraryForm
from .importing import start_import_thread, threads
from werkzeug import secure_filename
import json
import os
import mimetypes
import io
import importlib
import re
from multiprocessing import Pool

current_app.jinja_env.globals.update( folder_from_path=Folder.from_path )
current_app.jinja_env.globals.update( library_enumerate_all=Library.enumerate_all )
current_app.jinja_env.globals.update( tag_enumerate_roots=Tag.enumerate_roots )

def url_self( **args ):
    return url_for( request.endpoint, **dict( request.view_args, **args ) )

current_app.jinja_env.globals.update( url_self=url_self )

@current_app.cli.command( "update" )
def cloud_cli_update():
    for library in db.session.query( Library ):
        library_absolute_path = library.absolute_path
        for dirpath, dirnames, filenames in os.walk( library_absolute_path ):
            relative_path = re.sub( '^{}'.format( library_absolute_path ), '', dirpath )
            try:
                assert( None != library )
                #print( 'lib_abs: ' + library.absolute_path )
                folder = Folder.from_path( library, relative_path )
                #print( folder )
            except InvalidFolderException as e:
                print( dirpath )
                print( relative_path )
                current_app.logger.error( e.absolute_path )
            except LibraryRootException as e:
                current_app.logger.error( 'root' )
            #for dirname in dirnames:
            #    current_app.logger.info( dirname )

def cloud_update_item_meta( item ):
    if not os.path.exists( item.absolute_path ):
        current_app.logger.warn( 'file missing: {}'.format( item.absolute_path ) )
        item.status = StatusEnum.missing
        return
    img = item.open_image()
    if img and \
    (item.width != int( img.size[0]  ) or \
    item.height != int( img.size[1] )):
        current_app.logger.info( 'updating metadata for {}, width={}, height={} (from {}, {})'.format(
            item.absolute_path, img.size[0], img.size[1], db_width, db_height ) )
        item.meta['width'] = img.size[0]
        item.meta['height'] = img.size[1]

@current_app.cli.command( "refresh" )
def cloud_cli_refresh():
    #with Pool( 5 ) as p:
    #    res = p.map( cloud_update_item_meta, db.session.query( Item ) )
    #    #db.session.commit()
    #    print( res )
    for item in db.session.query( Item ):
        cloud_update_item_meta( item )
    db.session.commit()

@current_app.route( '/callbacks/edit', methods=['POST'] )
def cloud_edit_filedata():

    pass

@current_app.route( '/preview/<int:file_id>' )
@current_app.route( '/preview/<int:file_id>/<int:width>/<int:height>' )
def cloud_plugin_preview( file_id, width=160, height=120 ):

    '''Generate a preview thumbnail to be called by a tag src attribute on gallery pages.'''

    current_uid = 0 # TODO: current_uid

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

    current_uid = 0 # TODO: current_uid
    
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

    current_uid = 0 # TODO: current_uid

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

    return render_template( 'form_libraries_new.html', form=form, current_uid=current_uid )

    if 'GET' == request.method:
        return render_template( 'form_libraries_uploading.html', id=id, uid=current_uid )
    elif 'POST' == request.method:
        return threads[id].progress

@current_app.route( '/libraries/upload', methods=['GET', 'POST'] )
@current_app.route( '/libraries/upload/<id>', methods=['GET', 'POST'] )
def cloud_libraries_upload( id='' ):

    current_uid = 0 # TODO: current_uid

    form = UploadLibraryForm( request.form )

    title = 'Upload Library Data'
    progress = 0
    
    if 'POST' == request.method and id:
        return jsonify( { 'filename': threads[id].filename,
            'progress': int( threads[id].progress ) } )
    elif 'POST' == request.method and form.validate_on_submit() and not id:
        pictures = \
            json.loads( request.files['upload'].read().decode( 'utf-8' ) )
        id = start_import_thread( pictures )
        return redirect( url_for( 'cloud_libraries_upload', id=id ) )
    elif 'GET' == request.method and id:
        try:
            title = 'Uploading thread #{}'.format( id )
            progress = int( threads[id].progress )
        except KeyError as e:
            return redirect( url_for( 'cloud_libraries_upload' ) )

    return render_template( 'form_libraries_upload.html',
        title=title, form=form, id=id, progress=progress, current_uid=current_uid )

@current_app.route( '/libraries/<string:machine_name>' )
@current_app.route( '/libraries/<string:machine_name>/<path:relative_path>' )
@current_app.route( '/libraries/<string:machine_name>/<path:relative_path>/<int:page>' )
def cloud_libraries( machine_name=None, relative_path=None, page=0 ):

    l_globals = {
        'library_name': machine_name,
        'title': os.path.basename(relative_path )
            if relative_path else machine_name,
        'categories': request.args.get( 'categories' )
            if request.args.get( 'categories' ) in ['tags', 'folders']
                else 'folders' }

    current_uid = 0; # TODO: current_uid

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
            'libraries.html', **l_globals, folders=folder.children,
            items=items, items_classes=' pictures', page=page, current_uid=current_uid,
            this_folder=folder )

    except LibraryRootException as e:
        # Show the root of the given library ID.
        return render_template(
            'libraries.html', **l_globals, folders=library.children, pictures=[], page=page,
            this_folder=None, current_uid=current_uid )

    except InvalidFolderException as e:

        # Try to see if this is a valid file and display it if so.
        file_item = Item.secure_query( current_uid ) \
            .filter( Item.folder_id == e.parent_id ) \
            .filter( Item.name == e.name ) \
            .first()

        if not file_item:
            abort( 404 )

        return render_template(
            'file_item.html', **l_globals, file_item=file_item, tag_list=json.dumps( tags ),
            current_uid=current_uid, page=page )

@current_app.route( '/ajax/item/<int:item_id>/save', methods=['POST'] )
def cloud_item_ajax_save( item_id ):

    current_uid = 0 # TODO: current_uid

    new_tags = request.form['tags'].split( ',' )

    #print( new_tags )
    #print( [Tag.from_path( t ) for t in new_tags] )

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == item_id ) \
        .first()
    
    if not item:
        abort( 403 )

    del item._tags[:]
    item.tags( append=[Tag.from_path( t ) for t in new_tags] )
    
    db.session.commit()

    return jsonify( item.to_dict( ignore_keys=['parent', 'folder'] ) )

@current_app.route( '/ajax/item/<int:item_id>/json', methods=['GET'] )
def cloud_item_ajax_json( item_id ):

    current_uid = 0 # TODO: current_uid

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == item_id ) \
        .first()

    if not item:
        abort( 403 )

    item_dict = item.to_dict( ignore_keys=['parent', 'folder'] )

    parents = []
    parent_iter = item.folder
    while parent_iter:
        parents.append( str( parent_iter.id ) )
        parent_iter = parent_iter.parent
    parents.reverse()
    parents.insert( 0, 'library-{}'.format( item.library_id ) )
    item_dict['parents'] = parents
        
    return jsonify( item_dict )

@current_app.route( '/ajax/html/items/<int:folder_id>/<int:page>', methods=['GET'] )
def cloud_items_ajax_json( folder_id, page ):

    # TODO: Determine current UID.
    current_uid = 0

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

    current_uid = 0 # TODO: current_uid

    folder_id = request.args.get( 'id' )
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
        folder_parent = query.filter( Folder.id == folder_id ).first()
        if not folder_parent:
            abort( 403 )
        folders = folder_parent.children
    else:
        # Get the tree started and iterate through the library's root folders.
        json_out += [{
            'id': 'root',
            'parent': '#',
            'text': 'root' # TODO: All libraries.
        }]
        libraries = Library.secure_query( current_uid ) \
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
                .all()

    json_out += [{
        'id': f.id,
        'parent': folder_id if folder_id else 'library-{}'.format( f.library_id ),
        'text': f.name,
        'children': True if 0 < len( f.children ) else False
    } for f in folders]

    #print( folder.to_dict( ignore_keys=['parent'], max_depth=2 ) )
 
    return jsonify( json_out )

@current_app.route( '/ajax/tags.json')
def cloud_tags_ajax():
    # TODO: Omit empty tags.
    tags = db.session.query( Tag ).filter( Tag.name != '' ).all()
    tag_list = [t.path for t in tags]
    return jsonify( tag_list )

@current_app.route( '/tags/<path:path>' )
def cloud_tags( path ):
    
    current_uid = 0 # TODO: current_uid
    
    # TODO: Omit empty tags.
    tag = Tag.from_path( path )

    items = Item.secure_query( current_uid ) \
        .filter( tag in Item.tags ) \
        .all()
    
    if not tag:
        abort( 404 )
    return render_template( 'libraries.html', pictures=items, 
        tag_roots=[tag.parent], this_tag=tag, current_uid=current_uid )

@current_app.route( '/ajax/search', methods=['GET'] ):
def cloud_items_ajax_search():
    pass

@current_app.route( '/' )
def cloud_root():
    current_uid = 0 # TODO: current_uid
    return render_template( 'root.html', current_uid=current_uid )
