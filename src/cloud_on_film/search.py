
from enum import Enum
from cloud_on_film.models import Item
from flask import current_app

class SearchSyntaxException( Exception ):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

class SearchExecuteException( Exception ):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

class SearchLexerParser( object ):

    class Op( Enum ):
        eq = 0
        neq = 1
        gt = 2
        lt = 3
        gte = 4
        lte = 5
        has = 6
        like = 7

    class Node( object ):
        def __init__( self ):
            self.parent = None

    class Compare( Node ):
        def __init__( self ):
            super().__init__()
            self.children = (None, None)
            self.op = None

        def __str__( self ):
            return 'COMPARE ({} {} {})'.format( self.children[0], str( self.op ), self.children[1] )

        def dump( self, depth=0 ):
            tab_str = ''.join( ['\t' for t in range( depth )] )
            print( '{}\t{} (D:{})'.format( tab_str, str( self ), depth ) )

    class Group( Node ):
        def __init__( self ):
            super().__init__()
            self.children = []

        def __str__( self ):
            return 'GROUP'

        def dump( self, depth=0 ):
            tab_str = ''.join( ['\t' for t in range( depth )] )
            print( '{}{} (D:{} C:{})'.format( tab_str, str( self ), depth, len( self.children ) ) )
            for t in self.children:
                t.dump( depth + 1 )

    class And( Group ):
        def __str__( self ):
            return 'AND'

    class Or( Group ):
        def __str__( self ):
            return 'OR'

    def __init__( self, query_str ):
        self.query_str = query_str
        self.root = SearchLexerParser.Group()
        self.last_attrib = None
        self.last_op = None
        self.last_value = None
        self.head = self.root

        # ctok = current_token
        self.ctok_value = ''
        self.ctok_type = None
        self.ctok_quotes = False

        self.pending_c = None

    def is_value_pending( self ):
        return '' != self.ctok_value and \
            None != self.ctok_type

    def lex( self ):
        for c in self.query_str:
            self._lex_c( c )

        # Button up any remaining tokens.
        self._append_ctok_value( None ) # Handle pending_c.
        if self.is_value_pending():
            self.push_token()

    def _lex_c( self, c ):

        if "'" == c or '"' == c:
            if not self.is_value_pending():
                self.ctok_type = str
                self.ctok_quotes = True

            elif str == self.ctok_type:
                self.push_token()

            else:
                raise SearchSyntaxException( 'invalid \'"\' or "\'" detected' )

        elif '%' == c:
            if None == self.last_attrib:
                raise SearchSyntaxException( 'invalid "%%" in attribute name' )

            else:
                # Don't overthink this. We'll just check if the value starts 
                # or ends with % on push to change the op to a LIKE.
                self._append_ctok_value( c )

        elif '&' == c:
            if str == self.ctok_type:
                self._append_ctok_value( c )

            elif not self.is_value_pending():
                self.push_and()

            else:
                raise SearchSyntaxException( 'stray "&" detected' )

        elif '=' == c:
            if str == self.ctok_type and self.ctok_quotes:
                self._append_ctok_value( c )

            elif '>' == self.pending_c:
                self.push_token()
                self.push_gte()
                self.pending_c = None

            elif '<' == self.pending_c:
                self.push_token()
                self.push_lte()
                self.pending_c = None

            elif str == self.ctok_type:
                if None != self.last_value:
                    raise SearchSyntaxException( 'stray "=" detected' )
                self.push_token()
                self.push_eq()

            else:
                raise SearchSyntaxException( 'stray "=" detected' )

        elif '>' == c:
            # Handle this under =
            self.pending_c = '>'

        elif '<' == c:
            # Handle this under =
            self.pending_c = '<'

        elif '(' == c:
            if str == self.ctok_type:
                self._append_ctok_value( c )
            
            elif '' == self.ctok_value:
                self.start_group()

            else:
                raise SearchSyntaxException( 'stray "("' )

        elif ')' == c:
            if str == self.ctok_type and self.ctok_quotes:
                self._append_ctok_value( c )
            
            elif '' != self.ctok_value and \
            str == self.ctok_type and \
            not self.ctok_quotes:
                self.push_token()
                self.end_group()

            elif '' != self.ctok_value and \
            None != self.ctok_type:
                self.push_token()
                self.end_group()

            elif isinstance( self.head, SearchLexerParser.Group ):
                self.end_group()

            #elif isinstance( self.head, SearchLexerParser.Compare ):
            #    self.end_group()
            #    pass

            else:
                raise SearchSyntaxException( 'stray ")"' )

        elif c.isdigit():
            if None == self.ctok_type:
                self.ctok_type = int

            self._append_ctok_value( c )

        elif c.isalpha():
            if None == self.ctok_type:
                self.ctok_type = str
            
            if str == self.ctok_type:
                self._append_ctok_value( c )
            else:
                raise SearchSyntaxException( 'attempted to add alpha char to int' )

    def _append_ctok_value( self, c ):
        if None != self.pending_c:
            self.ctok_value += self.pending_c
            self.pending_c = None
        if None != c:
            self.ctok_value += c

    def _push_group( self, group ):
        assert( isinstance( self.head, list ) or isinstance( self.head, SearchLexerParser.Group ) )
        group.parent = self.head
        if isinstance( self.head, list ):
            self.head.append( group )
        elif isinstance( self.head, SearchLexerParser.Group ):
            self.head.children.append( group )

    def start_group( self ):
        group = SearchLexerParser.Group()
        self._push_group( group )
        self.head = group

    def end_group( self ):
        self.head = self.head.parent

    def push_and( self ):
        group = SearchLexerParser.And()
        self._push_group( group )
        self.head = group

    def push_or( self ):
        group = SearchLexerParser.Or()
        self._push_group( group )
        self.head = group
    
    def push_like( self ):
        if SearchLexerParser.Op.eq and not self.last_op:
            raise SearchSyntaxException( 'invalid comparison to LIKE' )
        self.last_op = SearchLexerParser.Op.like

    def push_gt( self ):
        self.last_op = SearchLexerParser.Op.gt

    def push_lt( self ):
        self.last_op = SearchLexerParser.Op.lt

    def push_gte( self ):
        self.last_op = SearchLexerParser.Op.gte

    def push_lte( self ):
        self.last_op = SearchLexerParser.Op.lte
        
    def push_eq( self ):
        self.last_op = SearchLexerParser.Op.eq    
    
    def push_token( self ):

        # Change the OP to LIKE if we have a trailing %.
        if str == self.ctok_type and \
        (self.ctok_value.startswith( '%' ) or \
        self.ctok_value.endswith( '%' )):
            self.push_like()

        # Determine if we're assigning attrib or value.
        if None == self.last_attrib:
            assert( str == self.ctok_type )
            self.last_attrib = self.ctok_value

        elif None == self.last_value:
            self.last_value = self.ctok_type( self.ctok_value )

        elif None == self.last_op:
            raise SearchSyntaxException( 'missing operator' )
        
        if None != self.last_attrib and \
        None != self.last_value and \
        None != self.last_op:
            group = SearchLexerParser.Compare()
            group.parent = self.head
            group.op = self.last_op
            group.children = (self.last_attrib, self.last_value)
            assert( 2 == len( group.children ) )
            self.head.children.append( group )
            #self.head = group
            self.last_attrib = None
            self.last_value = None
            self.last_op = None

        self.ctok_type = None
        self.ctok_value = ''
        self.ctok_quotes = False

    def dump( self ):
        print( 'ROOT (D: 0 C:{})'.format( len( self.root.children ) ) )
        for t in self.root.children:
            t.dump( 1 )

class Searcher( object ):
    
    def __init__( self, query_str ):
        self.lexer = SearchLexerParser( query_str )

    def search( self, user_id, _tree_start=None, _query=None ):

        if not _query:
            _query = Item.secure_query( user_id )

        if not _tree_start:
            _tree_start = self.lexer.root

        for t in _tree_start.children:
            if isinstance( t, SearchLexerParser.Group ):
                current_app.logger.debug( 'search parser descending...' )
                _query = self.search( user_id, t, _query )
            elif isinstance( t, SearchLexerParser.Compare ):

                # TODO: Get plugin model or something.
                from cloud_on_film.files.picture import Picture

                if not hasattr( Picture, t.children[0] ):
                    raise SearchExecuteException( 'invalid attribute specified' )
                
                if SearchLexerParser.Op.eq == t.op:
                    _query = _query.filter( getattr( Picture, t.children[0] ) == t.children[1] )
                elif SearchLexerParser.Op.gt == t.op:
                    _query = _query.filter( getattr( Picture, t.children[0] ) > t.children[1] )
                elif SearchLexerParser.Op.lt == t.op:
                    _query = _query.filter( getattr( Picture, t.children[0] ) < t.children[1] )
                elif SearchLexerParser.Op.gte == t.op:
                    _query = _query.filter( getattr( Picture, t.children[0] ) >= t.children[1] )
                elif SearchLexerParser.Op.lte == t.op:
                    _query = _query.filter( getattr( Picture, t.children[0] ) <= t.children[1] )
                elif SearchLexerParser.Op.neq == t.op:
                    _query = _query.filter( getattr( Picture, t.children[0] ) != t.children[1] )
                elif SearchLexerParser.Op.gt.like == t.op:
                    _query = _query.filter( getattr( Picture, t.children[0] ).like( t.children[1] ) )

        return _query
