
import os
import sys
import unittest
import json
from flask_testing import TestCase
sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )
from tests.data_helper import DataHelper
from cloud_on_film import create_app, db

class TestRoutes( TestCase ):

    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_CHECK_DEFAULT = False

    def create_app( self ):
        return create_app( self )

    def setUp( self ):
        db.create_all()

        self.user_id = 0
        DataHelper.create_folders( self )
        DataHelper.create_libraries( self, db )
        DataHelper.create_data_folders( self, db )
        DataHelper.create_data_items( self, db )

    def tearDown( self ):
        db.session.remove()
        db.drop_all()

    def test_ajax_folder_id_path( self ):

        response = self.client.post(
            '/ajax/folder/id_path',
            data={'path':
            'testing_library/Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4'} )

        id_path = json.loads( response.data )
        self.assertEqual( id_path,
            ["library-1","folder-1","folder-2","folder-5","folder-6"] )
