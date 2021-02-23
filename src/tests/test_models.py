
import os
import sys
sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )
import unittest
import json
from flask import current_app
from flask_testing import TestCase
from tests.data_helper import DataHelper
from cloud_on_film import create_app, db
from cloud_on_film.models import Library, Folder, Item, Tag
from cloud_on_film.importing import picture
from cloud_on_film.search import Searcher

class TestModels( TestCase ):

    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True

    def create_app( self ):
        return create_app( self )

    def setUp( self ):
        db.create_all()

        self.user_id = 0 # TODO: current_uid
        DataHelper.create_folders( self )
        DataHelper.create_libraries( self, db )
        DataHelper.create_data_folders( self, db )

    def tearDown( self ):
        db.session.remove()
        db.drop_all()

    def test_library_create( self ):
        current_app.logger.debug( 'testing library creation...' )
        lib_test = Library.secure_query( self.user_id ) \
            .filter( Library.machine_name == 'testing_library' ) \
            .first()
        self.assertEqual( lib_test.machine_name, 'testing_library' )

    def test_library_enumerate_all( self ):
        current_app.logger.debug( 'testing library_enumerate_all...' )
        libs = Library.enumerate_all( self.user_id )
        self.assertEqual( 2, len( libs ) )
        self.assertEqual( 'testing_library', libs[0].machine_name )
        self.assertEqual( 'testing_library', str( libs[0] ) )

    def test_folder_from_path( self ):
        current_app.logger.debug( 'testing folder_from_path...' )
        folder_test = Folder.from_path(
            self.lib.id, 'Foo Files 1/Foo Files 2', self.user_id )
        self.assertEqual( folder_test.name, 'Foo Files 2' )
        self.assertEqual( str( folder_test ), 'Foo Files 2' )
        self.assertEqual( folder_test.id, 2 )
        self.assertEqual( folder_test.path, 'Foo Files 1/Foo Files 2' )
        self.assertNotEqual( folder_test.path, 'xxx/Foo Files 2' )
        self.assertNotEqual( folder_test.path, 'Foo Files 1/xxx' )

    def test_create_folder_from_path( self ):
        current_app.logger.debug( 'testing creating via folder_from_path...' )
        folder_test = Folder.from_path(
            self.lib.id, 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4',
            self.user_id )
        self.assertEqual(
            folder_test.path, 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' )
        self.assertEqual( folder_test.name, 'Foo Files 4' )

    def test_file_from_path( self ):

        from cloud_on_film.files.picture import Picture

        file1 = Picture.from_path(
            self.lib.id, 'testing/random320x240.png', self.user_id )
        self.assertEqual( file1.name, 'random320x240.png' )
        self.assertNotEqual( file1.name, 'xxx.py' )
        self.assertNotEqual( file1.name, 'xxx.png' )
        self.assertEqual( file1.size, 461998 )

    def test_item_tags( self ):

        DataHelper.create_data_items( self, db )

        from cloud_on_film.files.picture import Picture

        tag = Tag.from_path( 'IFDY/Test Tag 1/Sub Test Tag 3' )

        files_test = Item.secure_query( self.user_id ) \
            .filter( Picture.width == 100 ) \
            .all()

        self.assertEqual( 1, len( files_test ) )
        self.assertIn( tag, files_test[0].tags )

    def test_query_width( self ):

        DataHelper.create_data_items( self, db )

        from cloud_on_film.files.picture import Picture

        files_test = Item.secure_query( self.user_id ) \
            .filter( Picture.width == 100 ) \
            .all()

        self.assertEqual( 1, len( files_test ) )
        self.assertEqual( 'random100x100.png', files_test[0].name )
        self.assertEqual( 100, files_test[0].width )

    def test_import( self ):

        # Perform the import.
        pics_json = None
        with open( 'testing/test_import.json', 'r' ) as import_file:
            pics_json = json.loads( import_file.read() )
        for pic_json in pics_json:
            pic_json['filename'] = os.path.join(
                self.lib_path, pic_json['filename'] )
            picture( pic_json )

        # Test the results.
        tag_testing_img = Tag.from_path( 'Testing Imports/Testing Image' )

        from cloud_on_film.files.picture import Picture

        file_test = Item.secure_query( self.user_id ) \
            .filter( Picture.width == 100 ) \
            .first()

        self.assertIn( tag_testing_img, file_test.tags )
        self.assertEqual( 100, file_test.width )
        self.assertEqual( 100, file_test.height )
        self.assertEqual( 1, file_test.aspect )
        self.assertFalse( file_test.nsfw )
        self.assertEqual( 0, file_test.rating )

        file_test = Item.secure_query( self.user_id ) \
            .filter( Picture.width == 500 ) \
            .first()

        self.assertIn( tag_testing_img, file_test.tags )
        self.assertEqual( 500, file_test.width )
        self.assertEqual( 500, file_test.height )
        self.assertEqual( 1, file_test.aspect )
        self.assertFalse( file_test.nsfw )
        self.assertEqual( 3, file_test.rating )

        file_test = Item.secure_query( self.user_id ) \
            .filter( Picture.aspect == 10 ) \
            .first()

        self.assertNotIn( tag_testing_img, file_test.tags )
        self.assertEqual( 640, file_test.width )
        self.assertEqual( 400, file_test.height )
        self.assertEqual( 10, file_test.aspect )
        self.assertFalse( file_test.nsfw )
        self.assertEqual( 0, file_test.rating )

    def test_nsfw( self ):

        DataHelper.create_data_items( self, db )

        from cloud_on_film.files.picture import Picture

        file_test = Item.secure_query( self.user_id ) \
            .filter( Picture.nsfw == 1 ) \
            .first()

        self.assertTrue( file_test.nsfw )

    def test_aspect( self ):

        DataHelper.create_data_items( self, db )

        from cloud_on_film.files.picture import Picture

        file_test = Item.secure_query( self.user_id ) \
            .filter( Picture.aspect == 4 ) \
            .first()

        self.assertEqual( 4, file_test.aspect )
        self.assertEqual( 'random320x240.png', file_test.name )

        file_test = Item.secure_query( self.user_id ) \
            .filter( Picture.width == 100 ) \
            .first()

        self.assertEqual( 1, file_test.aspect )
        self.assertEqual( 'random100x100.png', file_test.name )

        file_test = Item.secure_query( self.user_id ) \
            .filter( Picture.aspect == 10 ) \
            .first()

        self.assertEqual( 10, file_test.aspect )
        self.assertEqual( 'random640x400.png', file_test.name )

    def test_rating( self ):

        DataHelper.create_data_items( self, db )

        from cloud_on_film.files.picture import Picture

        files_test = Item.secure_query( self.user_id ) \
            .filter( Picture.rating > 1 ) \
            .all()

        self.assertEqual( 1, len( files_test ) )
        self.assertEqual( 4, files_test[0].rating )
        self.assertEqual( 'random100x100.png', files_test[0].name )

        files_test = Item.secure_query( self.user_id ) \
            .filter( Picture.rating == 1 ) \
            .all()

        self.assertEqual( 1, len( files_test ) )
        self.assertEqual( 1, files_test[0].rating )
        self.assertEqual( 'random500x500.png', files_test[0].name )

if '__main__' == __name__:
    unittest.main()
