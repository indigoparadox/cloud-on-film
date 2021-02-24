
from flask import Blueprint, jsonify, abort, request
from cloud_on_film import db
from cloud_on_film.models import Tag, Item, User, Folder, Library, items_tags

ajax = Blueprint( 'ajax', __name__ )

# region helpers

def jsonify_error( msg, form=None ):

    ''' Helper function to return errors in a usable format. '''

    err_out = { 'submit_status': 'error', 'message': msg }

    if form:
        err_out['fields'] = form.errors

    return jsonify( err_out )

# endregions

# region routes

@ajax.route( '/ajax/tags' )
def tags():

    ''' Return a list of ACCESSIBLE tags. '''

    current_uid = User.current_uid()
    tag_query = db.session.query( Tag ) \
            .filter( Tag.name != '' )

    if not 'show_empty' in request.args or \
    request.args.get( 'show_empty' ) != 'true':
        tag_query = tag_query \
            .filter( Tag._items.any() )

    tag_query = tag_query.order_by( Tag.name )

    tag_list =  tag_query.all()

    return jsonify( [t.path for t in tag_list] )

@ajax.route( '/ajax/folders' )
def folders():

    ''' Return a list of folders beneat the folder with ?id= ID, or under
    the roots of all ACCESSIBLE top-level libraries otherwise. Returns in
    a format usable by jsTree. '''

    current_uid = User.current_uid()

    # Maintain at least a string so tests below work.
    folder_or_lib_id = request.args.get( 'id' ) if 'id' in request.args else ''

    # Setup for the minor differentiation between folders and libraries.
    comparator = Folder if folder_or_lib_id.startswith( 'folder-' ) else \
        Library
    json_out = []
    folders_out = []

    folder_or_lib_id = int( folder_or_lib_id ) if \
            folder_or_lib_id.isnumeric() else \
        folder_or_lib_id.split( '-' )[1] if \
            2 == len( folder_or_lib_id.split( '-' ) ) else \
        None

    # Fetch the requested nodes. Start with siblings for continuity.
    if Folder == comparator:
        # The tree already has this folder, so iterate through its children.
        folders_out += Folder.secure_query( User.current_uid() ) \
        .filter( db.or_(
            Folder.parent_id == folder_or_lib_id
        ) ) \
        .order_by( Folder.name ) \
        .all()
        
    else:
        libraries_query = Library.secure_query( current_uid ) \
            .order_by( Library.display_name )

        # Get the tree started and iterate through the library's root folders.
        if folder_or_lib_id:
            libraries_query = \
                libraries_query.filter( Library.id == folder_or_lib_id )
        else:
            json_out += [{
                'id': 'root',
                'parent': '#',
                'text': 'root'
            }]
        libraries = libraries_query.all()

        if 0 == len( libraries ):
            abort( 404 )

        for library in libraries:
            json_out.append( {
                'id': 'library-{}'.format( library.id ),
                'parent': 'root',
                'text': library.display_name
            } )
            folders_out += Folder.secure_query( User.current_uid() ) \
                .filter( Folder.parent_id == None ) \
                .filter( Folder.library_id == library.id ) \
                .order_by( Folder.name ) \
                .all()

    # Convert all the folders on the list to a format palatable to jsTree.
    json_out += [{
        'id': 'folder-{}'.format( f.id ),
        'parent': 'folder-{}'.format( f.parent.id ) if f.parent else \
            'library-{}'.format( f.library_id ),
        'text': f.name,
        'children': 0 < len( f.children )
    } for f in folders_out]

    return jsonify( json_out )

# endregion

# region handlers

@ajax.errorhandler( 403 )
@ajax.errorhandler( 404 )
def error_404( ex ):
    return jsonify_error( str( ex ) )

# endregion
