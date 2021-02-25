
import os
import sys
import unittest
import re
import json
from flask_testing import TestCase

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )
from tests.data_helper import DataHelper
from cloud_on_film import create_app, db

class TestAJAX( TestCase ):

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

        self.maxDiff = None

        self.user_id = 0
        DataHelper.create_folders( self )
        DataHelper.create_libraries( self, db )
        DataHelper.create_data_folders( self, db )
        DataHelper.create_data_items( self, db )

    def tearDown( self ):
        db.session.remove()
        db.drop_all()

    def test_ajax_get_item( self ):

        res = self.client.get( '/ajax/get/item/1' )

        item_data = json.loads( res.data )

        self.assertEqual( 2, len( item_data['_meta'] ) )
        self.assertEqual( 0, item_data['rating'] )

    def test_ajax_get_item_location( self ):

        res = self.client.get( '/ajax/get/item/1/location' )

        item_data = json.loads( res.data )

        self.assertEqual(
            'Testing Library/testing',
            item_data )

    def test_ajax_get_folder_machine_path( self ):

        res = self.client.get( '/ajax/get/machine_path/Testing Library/Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' )

        item_data = json.loads( res.data )

        self.assertEqual(
            ['testing_library', 1, 2, 5, 6], item_data )

    def test_ajax_get_folder_machine_path_jstree( self ):

        res = self.client.get( '/ajax/get/machine_path/Testing Library/Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4?format=jstree' )

        item_data = json.loads( res.data )

        self.assertEqual(
            ['library-1','folder-1', 'folder-2', 'folder-5', 'folder-6'], item_data )

    def test_ajax_get_library_machine_path( self ):

        res = self.client.get( '/ajax/get/machine_path/Testing Library' )

        item_data = json.loads( res.data )

        self.assertEqual(
            ['testing_library'], item_data )

    def test_ajax_html_search( self ):
        res = self.client.get(
            '/ajax/html/search' + \
            r'?query=%26%28%28rating%3D1%29%28nsfw%3D0%29%29' )

        items = json.loads( res.data )
        self.assertEqual( 1, len( items ) )

    def test_list_ajax_tags_show_empty( self ):

        res = self.client.get( '/ajax/list/tags?show_empty=true' )

        tag_list = json.loads( res.data )
        self.assertEqual( tag_list, [
            'IFDY',
            'IFDY/NSFW Test Tag 1',
            'IFDY/Test Tag 1/Sub Test Tag 3',
            'IFDY/Test Tag 1',
            'IFDY/Test Tag 2/Test Tag 1',
            'IFDY/Test Tag 2'] )

    def test_list_ajax_tags( self ):

        res = self.client.get( '/ajax/list/tags' )

        tag_list = json.loads( res.data )
        self.assertEqual( tag_list, [
            'IFDY/Test Tag 1/Sub Test Tag 3'] )

    def test_list_ajax_folders_base( self ):

        res = self.client.get( '/ajax/list/folders' )

        folders = json.loads( res.data )

        self.assertEqual( 
            folders, [
                {'id': 'root', 'parent': '#', 'text': 'root'},
                {'id': 'library-2', 'parent': 'root', 'text': 'NSFW Library'},
                {'id': 'library-1', 'parent': 'root', 'text': 'Testing Library'},
                {'children': False, 'id': 'folder-4', 'parent': 'library-2',
                    'text': 'foo_folder'},
                {'children': True, 'id': 'folder-1', 'parent': 'library-1',
                    'text': 'Foo Files 1'},
                {'children': False, 'id': 'folder-3', 'parent': 'library-1',
                    'text': 'testing'}] )

    def test_list_ajax_folders_sub( self ):

        res = self.client.get( '/ajax/list/folders?id=library-1' )

        folders = json.loads( res.data )

        self.assertEqual( 
            folders, [
                {'id': 'library-1', 'parent': 'root', 'text': 'Testing Library'},
                {'children': True, 'id': 'folder-1', 'parent': 'library-1',
                    'text': 'Foo Files 1'},
                {'children': False, 'id': 'folder-3', 'parent': 'library-1',
                    'text': 'testing'}
            ] )

    def test_list_ajax_folders_leaf( self ):

        res = self.client.get( '/ajax/list/folders?id=folder-3' )

        folders = json.loads( res.data )

        self.assertEqual( 
            folders, [
            ] )
