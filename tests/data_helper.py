
import os
import sys
import shutil

from flask import current_app

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

from cloud_on_film.models import Library, Folder,Tag

class DataHelper( object ):

    @staticmethod
    def create_folders( test_class ):

        test_class.file_path = os.path.realpath( __file__ )
        test_class.lib_root_path = os.path.join(
            os.path.dirname( os.path.dirname( test_class.file_path ) ), 'testdata' )
        test_class.lib_path = os.path.join( test_class.lib_root_path, 'library1' )
        test_class.nsfw_lib_path = os.path.join( test_class.lib_root_path, 'library2' )
        test_class.rel_path = os.path.join(
            os.path.basename( os.path.dirname( test_class.file_path ) ),
            os.path.basename( test_class.file_path ) )

    @staticmethod
    def create_libraries( test_class, db ):

        #current_app.logger.debug(
        #    'running from path: {}'.format( self.file_path ) )
        #current_app.logger.debug( 'using {} as library path...'.format(
        #    self.lib_path ) )

        test_class.lib = Library(
            display_name='Testing Library',
            machine_name='testing_library',
            absolute_path=test_class.lib_path,
            nsfw=False )
        db.session.add( test_class.lib )
        db.session.commit() # Commit to get library ID.
        current_app.logger.debug( 'created library {} with ID {}'.format(
            test_class.lib.machine_name, test_class.lib.id ) )

        test_class.nsfw_lib = Library(
            display_name='NSFW Library',
            machine_name='nsfw_library',
            absolute_path=test_class.nsfw_lib_path,
            nsfw=True )
        db.session.add( test_class.nsfw_lib )
        db.session.commit() # Commit to get library ID.
        current_app.logger.debug( 'created library {} with ID {}'.format(
            test_class.nsfw_lib.machine_name, test_class.nsfw_lib.id ) )

    @staticmethod
    def create_data_folders( test_class, db ):

        subfolder1 = Folder( library_id=test_class.lib.id, name='subfolder1' )
        db.session.add( subfolder1 )
        db.session.commit() # Commit to get folder1 ID.
        current_app.logger.debug( 'created folder {} with ID {}'.format(
            subfolder1.name, subfolder1.id ) )

        subfolder2 = Folder( library_id=test_class.lib.id, name='subfolder2' )
        db.session.add( subfolder2 )
        db.session.commit() # Commit to get folder1 ID.
        current_app.logger.debug( 'created folder {} with ID {}'.format(
            subfolder2.name, subfolder2.id ) )

        subfolder3 = Folder(
            parent_id = subfolder2.id,
            library_id=test_class.lib.id,
            name='subfolder3' )
        db.session.add( subfolder3 )
        db.session.commit()
        current_app.logger.debug( 'created folder {} with ID {}'.format(
            subfolder3.name, subfolder3.id ) )

    @staticmethod
    def create_data_items( test_class, db ):

        tag_ifdy = Tag( name='IFDY', parent_id = None )
        db.session.add( tag_ifdy )
        db.session.commit()

        tag_test_1 = Tag( name='Test Tag 1', parent_id = tag_ifdy.id )
        db.session.add( tag_test_1 )
        db.session.commit()

        tag_test_2 = Tag( name='Test Tag 2', parent_id = tag_ifdy.id )
        db.session.add( tag_test_2 )
        db.session.commit()

        tag_nsfw_test_1 = Tag( name='NSFW Test Tag 1',
            parent_id = tag_ifdy.id )
        db.session.add( tag_nsfw_test_1 )
        db.session.commit()

        tag_sub_test_3 = Tag(
            name='Sub Test Tag 3', parent_id = tag_test_1.id )
        db.session.add( tag_sub_test_3 )
        db.session.commit()

        tag_test_alt_1 = Tag(
            name='Test Tag 1', parent_id = tag_test_2.id )
        db.session.add( tag_test_alt_1 )
        db.session.commit()

        from cloud_on_film.files.picture import Picture

        file_test = Picture.from_path(
            test_class.lib.id, 'subfolder2/subfolder3/random320x240.png', test_class.user_id )

        file_test = Picture.from_path(
            test_class.lib.id, 'subfolder1/random100x100.png', test_class.user_id )
        file_test.meta['rating'] = 4
        file_test.tags.append( tag_sub_test_3 )

        file_test = Picture.from_path(
            test_class.nsfw_lib.id, 'subfolder1/random500x500.png', test_class.user_id )
        file_test.meta['rating'] = 1

        file_test = Picture.from_path(
            test_class.nsfw_lib.id, 'subfolder2/random640x400.png', test_class.user_id )

        file_test = Picture.from_path(
            test_class.nsfw_lib.id, 'subfolder2/random640x480.png', test_class.user_id )

        db.session.commit()
