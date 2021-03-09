
import os
import sys
from flask_testing import TestCase

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )
from tests.data_helper import DataHelper
from cloud_on_film import create_app, db
from cloud_on_film.search import Searcher

class TestSearch( TestCase ):

    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True

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

    def test_search_eq( self ):

        search_test = Searcher( 'aspect=10' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        self.assertEqual( 1, len( res ) )
        for item in res:
            self.assertEqual( 10, item.aspect )

    def test_search_and( self ):

        search_test = Searcher( '&((rating=4)(nsfw=0))' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        self.assertEqual( 1, len( res ) )
        for item in res:
            self.assertFalse( item.nsfw )
            self.assertEqual( 4, item.rating )
        
    def test_search_gt( self ):

        search_test = Searcher( '(rating>1)' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        self.assertEqual( 1, len( res ) )
        for item in res:
            self.assertLess( 1, item.rating )

    def test_search_gte( self ):

        search_test = Searcher( 'rating>=1' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        found_one = False
        found_four = False
        for i in res:
            if 4 == i.rating:
                found_four = True
            elif 1 == i.rating:
                found_one = True

        self.assertEqual( 2, len( res ) )
        self.assertTrue( found_one and found_four )

    def test_search_like( self ):

        search_test = Searcher( 'name=%random640%' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        found_ten = False
        found_four = False
        for i in res:
            if 4 == i.aspect:
                found_four = True
            elif 10 == i.aspect:
                found_ten = True

        self.assertTrue( found_ten and found_four )
        self.assertEqual( 2, len( res ) )

    def test_search_or( self ):

        search_test = Searcher( '|((width=100)(width=500))' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        self.assertEqual( 2, len( res ) )
        for item in res:
            self.assertIn( item.width, [100, 500] )

    def test_search_not( self ):

        search_test = Searcher( '!(width=500)' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        for item in res:
            self.assertNotEqual( 500, item.width )

    def test_search_in( self ):

        search_test = Searcher( '("Sub Test Tag 3"@tags)' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        #self.assertEqual( 1, len( res ) )
        self.assertEqual( ['random100x100.png'], [r.name for r in res] )
