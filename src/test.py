#!/usr/bin/env python

import os
import unittest
import json
import logging
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
        os.makedirs( os.path.join( self.lib_path, 'Foo Files 1/Foo Files 2/Foo Files 3/Foo Files 4' ),
            exist_ok=True )
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
            auto_nsfw=True )
        db.session.add( self.lib )
        db.session.commit() # Commit to get library ID.
        current_app.logger.debug( 'created library {} with ID {}'.format(
            self.lib.machine_name, self.lib.id ) )

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
        assert( 1 == len( libs ) )
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
        file1 = FileItem.from_path( self.lib.id, self.rel_path )
        assert( file1.display_name == 'test.py' )
        assert( file1.display_name != 'xxx.py' )
        assert( file1.filesize > 0 )

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

        #stmt = db.select( [FileMeta.key, FileMeta.value] ).select_from( FileItem.__table__.outerjoin( FileMeta.__table__ ) )
        #print( str( stmt ) )
        #for res in db.engine.execute( stmt ):
        #    print( res )

        #logging.getLogger( 'sqlalchemy.engine' ).setLevel( logging.DEBUG )

        #logging.getLogger( 'sqlalchemy.engine' ).setLevel( logging.ERROR )

        assert( tag_testing_img in file_test.tags() )
        assert( None != file_test )
        assert( 100 == int( file_test.meta['width'] ) )
        assert( 100 == int( file_test.meta['height'] ) )
        #assert( not file_test.aspect_16x10 )
        #print( 'aspect: {}'.format( file_test.aspect_16x10 ) )

        file_test = FileItem.from_path( self.lib, 'testing/random640x400.png' )

        assert( 640 == int( file_test.meta['width'] ) )
        assert( 400 == int( file_test.meta['height'] ) )
        #assert( file_test.aspect_16x10 )
        #print( 'aspect: {}'.format( file_test.aspect_16x10 ) )

        #print( 'width_col: {}'.format( file_test.width ) )

        '''print( 'zzz' )
        print( 'zzz' )
        print( db.session.query( FileItem ) \
            .filter( FileItem.aspect_16x10 == 10 ) )
        print( 'zzz' )
        print( 'zzz' )'''

        '''print( 'qzqzqz' )
        print( 'qzqzqz' )
        print( db.session.query( FileItem ) \
            .filter( FileItem.aspect_16x10 == 10 ) \
            .all() )
        print( 'qzqzqz' )
        print( 'qzqzqz' )'''
        
        print( 'zzz' )
        print( 'zzz' )
        print( db.session.query( FileItem ) \
            .filter( FileItem.width == 640 ) )
        print( 'zzz' )
        print( 'zzz' )

        print( 'qzqzqz' )
        print( 'qzqzqz' )
        print( db.session.query( FileItem ) \
            .filter( FileItem.width == 640 ) \
            .all() )
        print( 'qzqzqz' )
        print( 'qzqzqz' )

        print( 'width: {}'.format( db.session.query( FileItem ) \
            .filter( FileItem.width == 640 ).first().width ) )
        print( 'aspect: {}'.format( db.session.query( FileItem ) \
            .filter( FileItem.width == 640 ).first().aspect ) )

        print( 'found_by_aspect: {}'.format( db.session.query( FileItem ) \
            .filter( FileItem.aspect == 10.0 ) \
            .all() ) )
        print( 'found_by_aspect query: {}'.format( db.session.query( FileItem ) \
            .filter( FileItem.aspect == 10.0 ) \
             ) )

if '__main__' == __name__:
    unittest.main()

