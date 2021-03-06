
from enum import Enum

from cloud_on_film.models import Item, Tag
from . import db

#region exceptions

class SearchSyntaxException( Exception ):
    pass

class SearchExecuteException( Exception ):
    pass

#endregion

class SearchLexerParser( object ):

    ''' Given a query string, creates a parse tree to be translated
    into SQL by the searcher. '''

    class Op( Enum ):
        eq = 0
        neq = 1
        gt = 2
        lt = 3
        gte = 4
        lte = 5
        in_ = 6
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

    class Not( Group ):
        def __str__( self ):
            return 'NOT'

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

    def is_value_pending( self ):
        return '' != self.ctok_value and \
            None != self.ctok_type

    def lex( self ):
        skip = False
        for i in range( len( self.query_str ) ):
            if skip:
                skip = False
                continue

            c = self.query_str[i]

            if "'" == c or '"' == c:
                if not self.is_value_pending():
                    self.ctok_quotes = True

                elif self.ctok_quotes:
                    self.ctok_quotes = False

                else:
                    raise SearchSyntaxException( 'invalid \'"\' or "\'" detected' )

            elif '%' == c:
                if None == self.last_attrib:
                    raise SearchSyntaxException( 'invalid "%%" in attribute name' )

                else:
                    # Don't overthink this. We'll just check if the value starts
                    # or ends with % on push to change the op to a LIKE.
                    self.ctok_value += c

            elif '!' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

                elif not self.is_value_pending():
                    self.push_not()
                    if i + 1 < len( self.query_str ) and \
                    '(' == self.query_str[i + 1]:
                        skip = True # Skip redundant group.

                else:
                    raise SearchSyntaxException( 'stray "!" detected' )

            elif '&' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

                elif not self.is_value_pending():
                    self.push_and()
                    if i + 1 < len( self.query_str ) and \
                    '(' == self.query_str[i + 1]:
                        skip = True # Skip redundant group.

                else:
                    raise SearchSyntaxException( 'stray "&" detected' )

            elif '|' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

                elif not self.is_value_pending():
                    self.push_or()
                    if i + 1 < len( self.query_str ) and \
                    '(' == self.query_str[i + 1]:
                        skip = True # Skip redundant group.

                else:
                    raise SearchSyntaxException( 'stray "|" detected' )

            elif '=' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

                elif str == self.ctok_type:
                    if None != self.last_value:
                        raise SearchSyntaxException( 'stray "=" detected' )
                    self.push_token()
                    self.push_eq()

                else:
                    raise SearchSyntaxException( 'stray "=" detected' )

            elif '@' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

                elif str == self.ctok_type:
                    if None != self.last_value:
                        raise SearchSyntaxException( 'stray "@" detected' )
                    self.push_token()
                    self.push_in()

                else:
                    raise SearchSyntaxException( 'stray "@" detected' )

            elif ' ' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

            elif '>' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

                elif str == self.ctok_type and \
                None == self.last_attrib:
                    self.push_token()
                    if i + 1 < len( self.query_str ) and \
                    '=' == self.query_str[i + 1]:
                        # Is GTE (>=).
                        self.push_gte()
                        skip = True # Skip '='.
                    else:
                        # Is GT (>).
                        self.push_gt()

                else:
                    raise SearchSyntaxException( 'stray ">" detected' )

            elif '<' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

                elif str == self.ctok_type and \
                None == self.last_attrib:
                    self.push_token()
                    if i + 1 < len( self.query_str ) and \
                    '=' == self.query_str[i + 1]:
                        # Is LTE (<=).
                        self.push_lte()
                        skip = True # Skip '='.
                    else:
                        # Is LT (<).
                        self.push_lt()

                else:
                    raise SearchSyntaxException( 'stray "<" detected' )

            elif '(' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

                elif '' == self.ctok_value:
                    self.start_group()

                else:
                    raise SearchSyntaxException( 'stray "("' )

            elif ')' == c:
                if self.ctok_quotes:
                    self.ctok_value += c

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

                self.ctok_value += c

            elif c.isalpha():
                if None == self.ctok_type:
                    self.ctok_type = str

                if str == self.ctok_type:
                    self.ctok_value += c
                else:
                    raise SearchSyntaxException( 'attempted to add alpha char to int' )

        # Button up any remaining tokens.
        if self.is_value_pending():
            self.push_token()

    def _push_group( self, group ):
        assert( isinstance( self.head, SearchLexerParser.Group ) )
        group.parent = self.head
        self.head.children.append( group )

    def start_group( self ):
        group = SearchLexerParser.Group()
        self._push_group( group )
        self.head = group

    def end_group( self ):

        orphan = self.head
        parent = orphan.parent

        if isinstance( orphan, SearchLexerParser.Group ) and \
        isinstance( parent, SearchLexerParser.Group ) and \
        not isinstance( orphan, SearchLexerParser.Not ) and \
        1 == len( orphan.children ):
            # Remove this group with only one child.
            parent.children.remove( orphan )
            parent.children.append( orphan.children[0] )

        self.head = parent

    def push_and( self ):
        group = SearchLexerParser.And()
        self._push_group( group )
        self.head = group

    def push_or( self ):
        group = SearchLexerParser.Or()
        self._push_group( group )
        self.head = group

    def push_not( self ):
        group = SearchLexerParser.Not()
        self._push_group( group )
        self.head = group

    def push_like( self ):
        if SearchLexerParser.Op.eq and not self.last_op:
            raise SearchSyntaxException( 'invalid comparison to LIKE' )
        self.last_op = SearchLexerParser.Op.like

    def push_gt( self ):
        self.last_op = SearchLexerParser.Op.gt

    def push_in( self ):
        self.last_op = SearchLexerParser.Op.in_

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

    ''' Executes the search on the database using the tree created by
    the lexer. '''

    def __init__( self, query_str ):
        self.lexer = SearchLexerParser( query_str )

    def search( self, user_id, _tree_start=None, _query=None ):

        if not _query:
            _query = Item.secure_query( user_id )

        if not _tree_start:
            _tree_start = self.lexer.root

        if isinstance( _tree_start, SearchLexerParser.Group ):
            child_filter_list = []
            for c in _tree_start.children:
                child_filter_list.append( self.search( user_id, c, _query ) )

            filter_out = None
            if isinstance( _tree_start, SearchLexerParser.Or ):
                filter_out = db.or_( *child_filter_list )

            elif isinstance( _tree_start, SearchLexerParser.Not ):
                filter_out = db.not_( *child_filter_list )

            else:
                # If it's not an or then it's an and.
                filter_out = db.and_( *child_filter_list )

            if _tree_start.parent:
                return filter_out
            else:
                return _query.filter( filter_out )

        elif isinstance( _tree_start, SearchLexerParser.Compare ):

            # TODO: Get plugin model or something.
            from cloud_on_film.files.picture import Picture

            if SearchLexerParser.Op.in_ == _tree_start.op:
                # Special ops that use the attrib postfix.
                if not hasattr( Picture, _tree_start.children[1] ):
                    raise SearchExecuteException( 'invalid attribute "{}" specified'.format( _tree_start.children[1] ) )

            elif not hasattr( Picture, _tree_start.children[0] ):
                raise SearchExecuteException( 'invalid attribute "{}" specified'.format( _tree_start.children[0] ) )

            if SearchLexerParser.Op.eq == _tree_start.op:
                return (getattr( Picture, _tree_start.children[0] ) == _tree_start.children[1])
            elif SearchLexerParser.Op.gt == _tree_start.op:
                return (getattr( Picture, _tree_start.children[0] ) > _tree_start.children[1])
            elif SearchLexerParser.Op.lt == _tree_start.op:
                return (getattr( Picture, _tree_start.children[0] ) < _tree_start.children[1])
            elif SearchLexerParser.Op.gte == _tree_start.op:
                return (getattr( Picture, _tree_start.children[0] ) >= _tree_start.children[1])
            elif SearchLexerParser.Op.lte == _tree_start.op:
                return (getattr( Picture, _tree_start.children[0] ) <= _tree_start.children[1])
            elif SearchLexerParser.Op.neq == _tree_start.op:
                return (getattr( Picture, _tree_start.children[0] ) != _tree_start.children[1])
            elif SearchLexerParser.Op.like == _tree_start.op:
                return (getattr( Picture, _tree_start.children[0] ).like( _tree_start.children[1] ))
            elif SearchLexerParser.Op.in_ == _tree_start.op:
                #if 'tags' == _tree_start.children[1]:
                #    _tree_start.children = (Tag.from_path(_tree_start.children[1] ), 'tag_ids')
                return getattr( Picture, _tree_start.children[1] ).any( name=_tree_start.children[0] )

        return _query
