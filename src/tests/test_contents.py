
import os
import sys
import unittest
import re
import json
from io import BytesIO
from flask_testing import TestCase
from PIL import Image

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )
from tests.data_helper import DataHelper
from cloud_on_film import create_app, db
from cloud_on_film.models import SavedSearch

class TestContents( TestCase ):

    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_CHECK_DEFAULT = False
    WTF_CSRF_ENABLED = False
    ITEMS_PER_PAGE = 20
    SECRET_KEY = 'development'
    ALLOWED_PREVIEWS = [
        '320, 240'
    ]
    THUMBNAIL_PATH = '/tmp/cof_test_thumb'

    def create_app( self ):
        return create_app( self )

    def setUp( self ):
        db.create_all()

        self.maxDiff = None

        self.user_id = 0
        DataHelper.create_folders( self )
        DataHelper.create_libraries( self, db )
        DataHelper.create_data_folders( self, db )
        DataHelper.create_data_items( self, db )

    def tearDown( self ):
        db.session.remove()
        db.drop_all()

    def test_contents_preview( self ):

        res = self.client.get( '/contents/preview/2?width=320&height=240' )

        self.assertStatus( res, 200 )

        for header in res.headers:
            if 'Content-Type' == header[0]:
                self.assertEqual( header[1], 'image/jpeg' )
            elif 'Content-Length' == header[0]:
                self.assertEqual( header[1], '8756' )

        res_buf = BytesIO()
        res_buf.write( res.data )

        image = Image.open( res_buf )

        self.assertEqual( 320, image.width )
        self.assertEqual( 240, image.height )

    def test_contents_fullsize( self ):

        res = self.client.get( '/contents/fullsize/2' )

        self.assertStatus( res, 200 )

        for header in res.headers:
            if 'Content-Type' == header[0]:
                self.assertEqual( header[1], 'image/jpeg' )
            elif 'Content-Length' == header[0]:
                self.assertEqual( header[1], '60380' )

        res_buf = BytesIO()
        res_buf.write( res.data )

        image = Image.open( res_buf )

        self.assertEqual( 100, image.width )
        self.assertEqual( 100, image.height )
        