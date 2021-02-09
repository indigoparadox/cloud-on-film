#!/usr/bin/env python

import os
import unittest
from flask import Flask, current_app
from flask_testing import TestCase
from cloud_on_film import create_app, db
from cloud_on_film.models import Library, Folder, FileItem

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
        os.makedirs( os.path.join( self.lib_path, 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' ),
            exist_ok=True )
        self.rel_path = os.path.join(
            os.path.basename( os.path.dirname( self.file_path ) ),
            os.path.basename( self.file_path ) )
        current_app.logger.info(
            'running from path: {}'.format( self.file_path ) )
        current_app.logger.info( 'using {} as library path...'.format(
            self.lib_path ) )

        self.lib = Library(
            display_name='Testing Library',
            machine_name='testing_library',
            absolute_path=self.lib_path,
            auto_nsfw=True )
        db.session.add( self.lib )
        db.session.commit() # Commit to get library ID.
        current_app.logger.info( 'created library {} with ID {}'.format(
            self.lib.machine_name, self.lib.id ) )

        folder1 = Folder( library_id=self.lib.id, display_name='Foo Files 1' )
        db.session.add( folder1 )
        db.session.commit() # Commit to get folder1 ID.
        current_app.logger.info( 'created folder {} with ID {}'.format(
            folder1.display_name, folder1.id ) )

        folder2 = Folder(
            parent_id = folder1.id,
            library_id=self.lib.id,
            display_name='Foo Files 2' )
        db.session.add( folder2 )
        db.session.commit()
        current_app.logger.info( 'created folder {} with ID {}'.format(
            folder2.display_name, folder2.id ) )

        #tag1 = Tag( display_name='Testing Tag', owner_id=

    def tearDown( self ):
        db.session.remove()
        db.drop_all()

    def test_library_create( self ):
        current_app.logger.info( 'testing library creation...' )
        lib_test = Library.from_machine_name( 'testing_library' )
        assert( lib_test.machine_name == 'testing_library' )

    def test_library_enumerate_all( self ):
        current_app.logger.info( 'testing library_enumerate_all...' )
        libs = Library.enumerate_all()
        assert( 1 == len( libs ) )
        assert( 'testing_library' == libs[0].machine_name )
        assert( 'testing_library' == str( libs[0] ) )

    def test_folder_from_id( self ):
        folder_test = Folder.from_id( 1 )
        assert( folder_test.display_name == 'Foo Files 1' )
        assert( str( folder_test ) == 'Foo Files 1' )

    def test_folder_from_path( self ):
        current_app.logger.info( 'testing folder_from_path...' )
        folder_test = Folder.from_path( self.lib, 'Foo Files 1/Foo Files 2' )
        assert( folder_test.display_name == 'Foo Files 2' )
        assert( str( folder_test ) == 'Foo Files 2' )
        assert( folder_test.id == 2 )
        assert( folder_test.path == 'Foo Files 1/Foo Files 2' )
        assert( folder_test.path != 'xxx/Foo Files 2' )
        assert( folder_test.path != 'Foo Files 1/xxx' )

    def test_create_folder_from_path( self ):
        current_app.logger.info( 'testing creating via folder_from_path...' )
        folder_test = Folder.from_path( self.lib, 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' )
        assert( folder_test.path == 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' )
        assert( folder_test.display_name == 'Foo Files 4' )

    def test_file_from_path( self ):
        file1 = FileItem.from_path( self.lib.id, self.rel_path )
        assert( file1.display_name == 'test.py' )
        assert( file1.display_name != 'xxx.py' )
        assert( file1.filesize > 0 )

if '__main__' == __name__:
    unittest.main()

