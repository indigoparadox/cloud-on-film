#!/usr/bin/env python

import os
import unittest
import json
import logging
import shutil
from flask import Flask, current_app
from flask_testing import TestCase
from cloud_on_film import create_app, db
from cloud_on_film.models import Library, Folder, FileItem, Tag, FileMeta
from cloud_on_film.importing import picture

class TestLibrary( TestCase ):

    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True

    def create_app( self ):
        return create_app( self )

    def setUp( self ):
        db.create_all()

        self.file_path = os.path.realpath( __file__ )
        self.lib_path = os.path.dirname( os.path.dirname( self.file_path ) )
        self.nsfw_lib_path = '/tmp/testing_nsfw_lib'
        os.makedirs( os.path.join( self.lib_path, 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' ),
            exist_ok=True )
        os.makedirs( self.nsfw_lib_path + '/foo_folder', exist_ok=True )
        shutil.copy2( '../testing/random640x480.png', self.nsfw_lib_path + '/foo_folder/' )
        self.rel_path = os.path.join(
            os.path.basename( os.path.dirname( self.file_path ) ),
            os.path.basename( self.file_path ) )
        current_app.logger.debug(
            'running from path: {}'.format( self.file_path ) )
        current_app.logger.debug( 'using {} as library path...'.format(
            self.lib_path ) )

        self.lib = Library(
            display_name='Testing Library',
            machine_name='testing_library',
            absolute_path=self.lib_path,
            auto_nsfw=False )
        db.session.add( self.lib )
        db.session.commit() # Commit to get library ID.
        current_app.logger.debug( 'created library {} with ID {}'.format(
            self.lib.machine_name, self.lib.id ) )

        self.nsfw_lib = Library(
            display_name='NSFW Library',
            machine_name='nsfw_library',
            absolute_path=self.nsfw_lib_path,
            auto_nsfw=True )
        db.session.add( self.nsfw_lib )
        db.session.commit() # Commit to get library ID.
        current_app.logger.debug( 'created library {} with ID {}'.format(
            self.nsfw_lib.machine_name, self.nsfw_lib.id ) )

        folder1 = Folder( library_id=self.lib.id, display_name='Foo Files 1' )
        db.session.add( folder1 )
        db.session.commit() # Commit to get folder1 ID.
        current_app.logger.debug( 'created folder {} with ID {}'.format(
            folder1.display_name, folder1.id ) )

        folder2 = Folder(
            parent_id = folder1.id,
            library_id=self.lib.id,
            display_name='Foo Files 2' )
        db.session.add( folder2 )
        db.session.commit()
        current_app.logger.debug( 'created folder {} with ID {}'.format(
            folder2.display_name, folder2.id ) )

        tag_root = Tag( display_name='' )
        db.session.add( tag_root )
        db.session.commit()

        tag_ifdy = Tag( display_name='IFDY', parent_id = tag_root.id )
        db.session.add( tag_ifdy )
        db.session.commit()

        tag_test_1 = Tag( display_name='Test Tag 1', parent_id = tag_ifdy.id )
        db.session.add( tag_test_1 )
        tag_test_2 = Tag( display_name='Test Tag 2', parent_id = tag_ifdy.id )
        db.session.add( tag_test_2 )
        tag_nsfw_test_1 = Tag( display_name='NSFW Test Tag 1',
            parent_id = tag_root.id )
        db.session.add( tag_nsfw_test_1 )
        db.session.commit()

        tag_sub_test_3 = Tag(
            display_name='Sub Test Tag 3', parent_id = tag_test_1.id )
        db.session.add( tag_sub_test_3 )
        tag_test_alt_1 = Tag(
            display_name='Test Tag 1', parent_id = tag_test_2.id )
        db.session.add( tag_test_alt_1 )
        db.session.commit()

    def tearDown( self ):
        db.session.remove()
        db.drop_all()

    def test_library_create( self ):
        current_app.logger.debug( 'testing library creation...' )
        lib_test = Library.from_machine_name( 'testing_library' )
        assert( lib_test.machine_name == 'testing_library' )

    def test_library_enumerate_all( self ):
        current_app.logger.debug( 'testing library_enumerate_all...' )
        libs = Library.enumerate_all()
        assert( 2 == len( libs ) )
        assert( 'testing_library' == libs[0].machine_name )
        assert( 'testing_library' == str( libs[0] ) )

    def test_folder_from_id( self ):
        folder_test = Folder.from_id( 1 )
        assert( folder_test.display_name == 'Foo Files 1' )
        assert( str( folder_test ) == 'Foo Files 1' )

    def test_folder_from_path( self ):
        current_app.logger.debug( 'testing folder_from_path...' )
        folder_test = Folder.from_path( self.lib, 'Foo Files 1/Foo Files 2' )
        assert( folder_test.display_name == 'Foo Files 2' )
        assert( str( folder_test ) == 'Foo Files 2' )
        assert( folder_test.id == 2 )
        assert( folder_test.path == 'Foo Files 1/Foo Files 2' )
        assert( folder_test.path != 'xxx/Foo Files 2' )
        assert( folder_test.path != 'Foo Files 1/xxx' )

    def test_create_folder_from_path( self ):
        current_app.logger.debug( 'testing creating via folder_from_path...' )
        folder_test = Folder.from_path( self.lib, 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' )
        assert( folder_test.path == 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' )
        assert( folder_test.display_name == 'Foo Files 4' )

    def test_file_from_path( self ):
        file1 = FileItem.from_path( self.lib.id, 'testing/random320x240.png' )
        assert( file1.display_name == 'random320x240.png' )
        assert( file1.display_name != 'xxx.py' )
        assert( file1.display_name != 'xxx.png' )
        assert( file1.filesize == 461998 )

    def test_tag_from_path( self ):
        tag = Tag.from_path( 'IFDY/Test Tag 1/Sub Test Tag 3' )

    def test_import( self ):
        # Perform the import.
        pics_json = None
        with open( '../testing/test_import.json', 'r' ) as import_file:
            pics_json = json.loads( import_file.read() )
        for pic_json in pics_json:
            pic_json['filename'] = os.path.join(
                self.lib_path, pic_json['filename'] )
            picture( pic_json )

        # Test the results.
        file_test = FileItem.from_path( self.lib, 'testing/random100x100.png' )
        tag_testing_img = Tag.from_path( 'Testing Imports/Testing Image' )

        assert( tag_testing_img in file_test.tags() )
        assert( None != file_test )
        assert( 100 == file_test.width )
        assert( 100 == file_test.height )
        assert( file_test.aspect == 1 )
        assert( not file_test.nsfw )

        file_test = FileItem.from_path( self.lib, 'testing/random640x400.png' )

        assert( 640 == file_test.width )
        assert( 400 == file_test.height )
        assert( file_test.aspect == 10 )
        assert( not file_test.nsfw )

    def test_nsfw( self ):

        file_test = FileItem.from_path( self.lib, 'testing/random500x500.png' )

        file_test = FileItem.from_path(
            self.nsfw_lib, 'foo_folder/random640x480.png' )
        assert( file_test.nsfw )
        assert( 640 == file_test.width )
        assert( 480 == file_test.height )
        assert( file_test.aspect == 4 )

if '__main__' == __name__:
    unittest.main()

