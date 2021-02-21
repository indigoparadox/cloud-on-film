
import os
import sys
sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )
import unittest
from flask import current_app
from flask_testing import TestCase
from data_helper import DataHelper
from cloud_on_film import create_app, db
from cloud_on_film.models import Library, Folder, Item, Tag
from cloud_on_film.importing import picture
from cloud_on_film.search import Searcher

class TestSearch( TestCase ):

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

    def test_search_eq( self ):

        DataHelper.create_data_items( self, db )

        search_test = Searcher( 'aspect=10' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        assert( 1 == len( res ) )
        assert( [10 == i.aspect for i in res] )

    def test_search_and( self ):

        DataHelper.create_data_items( self, db )

        search_test = Searcher( '&((rating=4)(nsfw=0))' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        assert( 1 == len( res ) )
        assert( [not i.nsfw for i in res] )
        assert( [4 == i.rating for i in res] )
        
    def test_search_gt( self ):

        DataHelper.create_data_items( self, db )

        search_test = Searcher( '(rating>1)' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        assert( 1 == len( res ) )
        assert( [1 < i.rating for i in res] )

    def test_search_gte( self ):

        DataHelper.create_data_items( self, db )

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

        assert( 2 == len( res ) )
        assert( [not i.nsfw for i in res] )
        assert( found_one and found_four )

    def test_search_like( self ):

        DataHelper.create_data_items( self, db )

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

        assert( found_ten and found_four )
        assert( 2 == len( res ) )

    def test_search_or( self ):

        DataHelper.create_data_items( self, db )

        search_test = Searcher( '|((width=100)(width=500))' )
        search_test.lexer.lex()
        search_test.lexer.dump()
        res = search_test.search( self.user_id ).all()

        assert( 2 == len( res ) )
        assert( [100 == i.width or 500 == i.width for i in res] )

        #assert( [4 == i.aspect for i in res] )
        #assert( [320 < i.width for i in res] )
