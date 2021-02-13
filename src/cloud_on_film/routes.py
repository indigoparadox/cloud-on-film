
import logging 
from flask import Flask, render_template, request, current_app, flash, send_file, abort, redirect, url_for, jsonify
from sqlalchemy import exc
from .models import LibraryPermissionsException, StatusEnum, db, Library, FileItem, Folder, Tag, InvalidFolderException, LibraryRootException
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
                folder = Folder().from_path( library, relative_path )
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
    #    res = p.map( cloud_update_item_meta, db.session.query( FileItem ) )
    #    #db.session.commit()
    #    print( res )
    for item in db.session.query( FileItem ):
        cloud_update_item_meta( item )
    db.session.commit()

@current_app.route( '/callbacks/edit', methods=['POST'] )
def cloud_edit_filedata():

    pass

@current_app.route( '/preview/<int:file_id>' )
def cloud_plugin_preview( file_id ):

    '''Generate a preview thumbnail to be called by a tag src attribute on gallery pages.'''

    item = FileItem.from_id( file_id )

    # Safety checks.
    if not item.folder.library.is_accessible():
        abort( 403 )

    p = importlib.import_module(
        '.plugins.{}.files'.format( item.filetype ), 'cloud_on_film' )
    file_path = p.generate_thumbnail( file_id, (160, 120) )

    with open( file_path, 'rb' ) as pic_f:
        return send_file( io.BytesIO( pic_f.read() ),
            mimetypes.guess_type( file_path )[0] )

@current_app.route( '/fullsize/<int:file_id>' )
def cloud_plugin_fullsize( file_id ):

    item = FileItem.from_id( file_id )

    # Safety checks.
    if not item.folder.library.is_accessible():
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
                auto_nsfw=form.auto_nsfw.data )
            db.session.add( lib )
            db.session.commit()
            flash( 'Library created.' )
        except exc.IntegrityError as e:
            current_app.logger.error( e )
            flash( e )
            db.session.rollback()

    return render_template( 'form_libraries_new.html', form=form )

    if 'GET' == request.method:
        return render_template( 'form_libraries_uploading.html', id=id )
    elif 'POST' == request.method:
        return threads[id].progress

@current_app.route( '/libraries/upload', methods=['GET', 'POST'] )
@current_app.route( '/libraries/upload/<id>', methods=['GET', 'POST'] )
def cloud_libraries_upload( id='' ):

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
        title=title, form=form, id=id, progress=progress )

@current_app.route( '/libraries/<string:machine_name>' )
@current_app.route( '/libraries/<string:machine_name>/<path:relative_path>' )
def cloud_libraries( machine_name=None, relative_path=None ):

    l_globals = {
        'library_name': machine_name,
        'title': os.path.basename(relative_path )
            if relative_path else machine_name,
        'categories': request.args.get( 'categories' )
            if request.args.get( 'categories' ) in ['tags', 'folders']
                else 'folders' }

    try:
        library = Library.from_machine_name( machine_name )
    except LibraryPermissionsException as e:
        abort( 403 )
    if not library:
        abort( 404 )

    tags = [t.display_name for t in db.session.query( Tag ).filter( Tag.display_name != '' ).all()]
    
    try:
        # Show a folder listing.
        folder = Folder.from_path( library.id, relative_path )
        return render_template(
            'libraries.html', **l_globals, folders=folder.children, pictures=folder.files,
            this_folder=folder, tag_list=json.dumps( tags ) )

    except LibraryRootException as e:
        # Show the root of the given library ID.
        return render_template(
            'libraries.html', **l_globals, folders=library.children, pictures=[],
            this_folder=None, tag_list=json.dumps( tags ) )

    except InvalidFolderException as e:

        # Try to see if this is a valid file and display it if so.
        query = db.session.query( FileItem ) \
            .filter( FileItem.folder_id == e.parent_id ) \
            .filter( FileItem.display_name == e.display_name )
        file_item = query.first()
        if not file_item:
            # File not found.
            abort( 404 )
        elif file_item.folder.library.machine_name != machine_name:
            # Wrong library.
            abort( 403 )

        return render_template(
            'file_item.html', **l_globals, file_item=file_item, tag_list=json.dumps( tags ) )

@current_app.route( '/ajax/items/<int:item_id>/save', methods=['POST'] )
def cloud_item_ajax_save( item_id ):
    new_tags = request.form['tags'].split( ',' )

    #print( new_tags )
    #print( [Tag.from_path( t ) for t in new_tags] )

    item = db.session.query( FileItem ) \
        .filter( FileItem.id == item_id ) \
        .first()
    del item._tags[:]
    item.tags( append=[Tag.from_path( t ) for t in new_tags] )
    
    db.session.commit()

    return jsonify( item.to_dict( ignore_keys=['parent', 'folder'] ) )

@current_app.route( '/ajax/items/<int:item_id>/json', methods=['GET'] )
def cloud_item_ajax_json( item_id ):
    item = db.session.query( FileItem ) \
        .filter( FileItem.id == item_id ) \
        .first()
        
    return jsonify( item.to_dict( ignore_keys=['parent', 'folder'] ) )

@current_app.route( '/ajax/folders' )
@current_app.route( '/ajax/folders/<int:folder_id>' )
def cloud_folders_ajax( folder_id=None ):

    folder = db.session.query( Folder )
    if folder_id:
        folder = folder.filter( Folder.id == folder_id )
    folder = folder.first()

    print( folder.to_dict( ignore_keys=['parent'], max_depth=2 ) )

    return jsonify( folder.to_dict( ignore_keys=['parent', 'folder_parent', 'library'], max_depth=2 ) )

@current_app.route( '/ajax/tags.json')
def cloud_tags_ajax():
    tags = db.session.query( Tag ).filter( Tag.display_name != '' ).all()
    tag_list = [t.path for t in tags]
    return jsonify( tag_list )

@current_app.route( '/tags/<path:path>' )
def cloud_tags( path ):
    tag = Tag.from_path( path )
    if not tag:
        abort( 404 )
    return render_template( 'libraries.html', pictures=tag.files(), tag_roots=[tag.parent], this_tag=tag )

@current_app.route( '/' )
def cloud_root():
    return render_template( 'root.html' )

