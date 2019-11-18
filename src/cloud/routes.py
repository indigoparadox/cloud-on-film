
import logging 
from flask import Flask, render_template, request, current_app, flash
from sqlalchemy import exc
from .models import db, Library
from .forms import NewLibraryForm
from . import libraries

@current_app.cli.command( "update" )
def cloud_cli_update():
    libraries.update()

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
                absolute_path=form.absolute_path.data )
            db.session.add( lib )
            db.session.commit()
            flash( 'Library created.' )
        except exc.IntegrityError as e:
            logger.error( e )
            flash( e )
            db.session.rollback()

    return render_template( 'form_libraries_new.html', form=form )

@current_app.route( '/libraries' )
@current_app.route( '/libraries/<string:machine_name>' )
@current_app.route( '/libraries/<string:machine_name>/<path:relative_path>' )
def cloud_libraries( machine_name=None, relative_path=None ):

    logger = logging.getLogger( 'cloud.libraries' )

    if not machine_name and not relative_path:
        folders = libraries.enumerate()
    elif not relative_path:
        folders = libraries.enumerate_path( machine_name, relative_path )

    return render_template( 'libraries.html', folders=folders )

@current_app.route( '/' )
def cloud_root():
    return render_template( 'root.html' )

