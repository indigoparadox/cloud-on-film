
import os
import sys
import unittest
import re
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
    ITEMS_PER_PAGE = 20
    SECRET_KEY = 'development'

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

    def test_libraries_root( self ):

        res = self.client.get( '/libraries/testing_library' )

        library_script_stanzas = [
            '<script src="/static/jquery.unveil2.min.js"></script>',
            '<script src="/static/featherlight.min.js"></script>',
            '<script src="/static/featherlight.gallery.min.js"></script>',
            '<script src="/static/libraries.js"></script>',
            '<script src="/static/field-tags.js"></script>',
            '<script src="/static/field-browser.js"></script>',
            '<script src="/static/edit-item.js"></script>',
            '<script src="/static/search.js"></script>',
            '<link rel="stylesheet" href="/static/featherlight.min.css" />',
            '<link rel="stylesheet" href="/static/featherlight.gallery.min.css" />',
            '<link rel="stylesheet" href="/static/gallery.css" />' ]

        for stanza in library_script_stanzas:
            stanza = re.escape( stanza )
            self.assertRegex( res.data.decode( 'utf-8' ), stanza )

    def test_ajax_folder_id_path( self ):

        res = self.client.post(
            '/ajax/folder/id_path',
            data={'path':
            'testing_library/Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4'} )

        id_path = json.loads( res.data )
        self.assertEqual( id_path,
            ["library-1","folder-1","folder-2","folder-5","folder-6"] )

    def test_ajax_html_search( self ):
        res = self.client.get(
            '/ajax/html/search' + \
            r'?query=%26%28%28rating%3D1%29%28nsfw%3D0%29%29' )

        items = json.loads( res.data )
        self.assertEqual( 1, len( items ) )

    def test_ajax_tags( self ):

        res = self.client.get( '/ajax/tags.json' )

        id_path = json.loads( res.data )
        self.assertEqual( id_path, [
            'IFDY',
            'IFDY/Test Tag 1',
            'IFDY/Test Tag 2',
            'IFDY/NSFW Test Tag 1',
            'IFDY/Test Tag 1/Sub Test Tag 3',
            'IFDY/Test Tag 2/Test Tag 1'] )
