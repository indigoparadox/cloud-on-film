
import logging 
from flask import Flask, render_template, request, current_app, flash, send_file, abort, redirect, url_for, jsonify
from sqlalchemy import exc
from .models import db, Library, FileItem, Folder, Tag, InvalidFolderException, LibraryRootException
from .forms import NewLibraryForm, UploadLibraryForm
from .importing import start_import_thread, threads
from werkzeug import secure_filename
import json
import os
import mimetypes
import io
import importlib

current_app.jinja_env.globals.update( folder_from_path=Folder.from_path )
current_app.jinja_env.globals.update( library_enumerate_all=Library.enumerate_all )
current_app.jinja_env.globals.update( tag_enumerate_roots=Tag.enumerate_roots )

def url_self( **args ):
    return url_for( request.endpoint, **dict( request.view_args, **args ) )

current_app.jinja_env.globals.update( url_self=url_self )

@current_app.cli.command( "update" )
def cloud_cli_update():
    logger = logging.getLogger( 'cloud.update' )
    for dirpath, dirnames, filenames in os.walk:
        for dirname in dirnames:
            logger.info( dirname )

@current_app.route( '/callbacks/edit', methods=['POST'] )
def cloud_edit_filedata():

    pass

@current_app.route( '/preview/<int:file_id>' )
def cloud_plugin_preview( file_id ):

    '''Generate a preview thumbnail to be called by a tag src attribute on gallery pages.'''

    # TODO: Safety checks.

    item = FileItem.from_id( file_id )

    p = importlib.import_module(
        '.plugins.{}.files'.format( item.filetype ), 'cloud_on_film' )
    file_path = p.generate_thumbnail( file_id, (160, 120) )

    with open( file_path, 'rb' ) as pic_f:
        return send_file( io.BytesIO( pic_f.read() ),
            mimetypes.guess_type( file_path )[0] )

@current_app.route( '/fullsize/<int:file_id>' )
def cloud_plugin_fullsize( file_id ):

    logger = logging.getLogger( 'cloud.plugin.fullsize' )

    # TODO: Safety checks.

    item = FileItem.from_id( file_id )

    # TODO: Figure out display tag (img/audio/video/etc).
    #p = importlib.import_module(
    #    '.plugins.{}.files'.format( item.filetype ), 'cloud_on_film' )
    #file_path = p.generate_thumbnail( file_id, (160, 120) )

    file_type = mimetypes.guess_type( item.path )[0]
    
    logger.info( '{} mimetype: {}'.format( item.path, file_type ) )

    with open( item.absolute_path, 'rb' ) as pic_f:
        return send_file( io.BytesIO( pic_f.read() ), file_type )

@current_app.route( '/libraries/new', methods=['GET', 'POST'] )
def cloud_libraries_new():

    logger = logging.getLogger( 'cloud.library.new' )
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
            logger.error( e )
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

    logger = logging.getLogger( 'cloud.library.upload' )
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

    logger = logging.getLogger( 'cloud.libraries' )

    l_globals = {
        'library_name': machine_name,
        'title': os.path.basename(relative_path )
            if relative_path else machine_name,
        'categories': request.args.get( 'categories' )
            if request.args.get( 'categories' ) in ['tags', 'folders']
                else 'folders' }

    library = Library.from_machine_name( machine_name )
    if not library:
        abort( 404 )

    try:
        # Show a folder listing.
        folder = Folder.from_path( library.id, relative_path )
        return render_template(
            'libraries.html', **l_globals, folders=folder.children, pictures=folder.files,
            this_folder=folder )

    except LibraryRootException as e:
        # Show the root of the given library ID.
        return render_template(
            'libraries.html', **l_globals, folders=library.children, pictures=[],
            this_folder=None )

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
            'file_item.html', **l_globals, file_item=file_item )

@current_app.route( '/' )
def cloud_root():
    return render_template( 'root.html' )

