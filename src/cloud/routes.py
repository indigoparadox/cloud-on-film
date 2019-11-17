
import logging 
from flask import Flask, render_template, request, current_app
from .database import db_session

@current_app.route( '/' )
def cloud_root():
    return render_template( 'root.html' )

@current_app.teardown_appcontext
def shutdown_session( exception=None ):
    db_session.remove()

