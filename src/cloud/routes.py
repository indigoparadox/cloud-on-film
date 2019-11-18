
import logging 
from flask import Flask, render_template, request, current_app
from .models import db

@current_app.route( '/' )
def cloud_root():
    return render_template( 'root.html' )

