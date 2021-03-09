
import os
import sys
import unittest
import re
from flask_testing import TestCase

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )
from tests.data_helper import DataHelper
from cloud_on_film import create_app, db
from cloud_on_film.models import SavedSearch

class TestLibraries( TestCase ):

    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_CHECK_DEFAULT = False
    WTF_CSRF_ENABLED = False
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

    def test_libraries_save_search( self ):

        res = self.client.post(
            '/save/search',
            data=dict(
                query='width=100',
                name='Width 100',
                save='save' ) )

        with self.client.session_transaction() as session:
            self.assertEqual( dict( session['_flashes'] ),
                {'message': 'Created search #1.'} )

        self.assertRedirects( res, '/search/saved/1' )

        search = db.session.query( SavedSearch ).first()
        self.assertEqual( 'Width 100', search.display_name )
        self.assertEqual( 'width=100', search.query )

    def test_libraries_delete_search( self ):

        search = SavedSearch( display_name='Width 100', query='width=100' )
        db.session.add( search )
        db.session.commit()
        search_id = search.id

        search = db.session.query( SavedSearch ) \
            .filter( SavedSearch.id == search_id ) \
            .first()
        self.assertIsNotNone( search )

        # Just get the form.
        res = self.client.get( '/delete/search/{}'.format( search_id ) )
        self.assertStatus( res, 200 )

        search = db.session.query( SavedSearch ) \
            .filter( SavedSearch.id == search_id ) \
            .first()
        self.assertIsNotNone( search )

        # Delete cancelled.
        res = self.client.post(
            '/delete/search/{}'.format( search_id ),
            data=dict( id=search_id ) )
        self.assertRedirects( res, '/' )

        # Delete OK'ed.
        res = self.client.post(
            '/delete/search/{}'.format( search_id ),
            data=dict( id=search_id, delete='Delete' ) )
        self.assertRedirects( res, '/' )

        #with self.client.session_transaction() as session:
        #    self.assertEqual( dict( session['_flashes'] ),
        #        {'message': 'Deleted search #1.'} )

        search = db.session.query( SavedSearch ) \
            .filter( SavedSearch.id == search_id ) \
            .first()
        self.assertIsNone( search )
