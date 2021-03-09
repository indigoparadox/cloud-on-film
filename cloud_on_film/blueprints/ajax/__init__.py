
from flask import Blueprint, jsonify, abort, request
from cloud_on_film import db
from cloud_on_film.forms import EditItemForm
from cloud_on_film.models import \
    Tag, Item, User, Folder, Library, LibraryRootException

ajax = Blueprint( 'ajax', __name__ )

# region helpers

def jsonify_error( msg, form=None ):

    ''' Helper function to return errors in a usable format. '''

    err_out = { 'submit_status': 'error', 'message': msg }

    if form:
        err_out['fields'] = form.errors

    return jsonify( err_out )

# endregions

# region list

@ajax.route( '/ajax/list/tags' )
def list_tags():

    ''' Return a list of ACCESSIBLE tags. '''

    tag_query = db.session.query( Tag )

    if not 'show_empty' in request.args or \
    request.args.get( 'show_empty' ) != 'true':
        tag_query = tag_query \
            .filter( Tag._items.any() )

    tag_query = tag_query.order_by( Tag.name )

    tag_list =  tag_query.all()

    return jsonify( [t.path for t in tag_list] )

@ajax.route( '/ajax/list/folders' )
def list_folders():

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

# region get

@ajax.route( '/ajax/get/machine_path/<string:library_name>' )
@ajax.route( '/ajax/get/machine_path/<string:library_name>/<path:relative_path>', methods=['GET'] )
def get_machine_path( library_name, relative_path=None ):

    ''' Given a relative path starting with a Library machine_name,
    return a list of numeric IDs starting with that' Library's ID. '''

    library = Library.secure_query( User.current_uid() ) \
        .filter( Library.display_name == library_name ) \
        .first_or_404()

    try:
        # A path was provided, so try to find the DB folder for it.
        folder = Folder.from_path( library.id, relative_path, User.current_uid() )

    except LibraryRootException:
        # No parent folder exists.
        folder = None

    path_out = folder.machine_path if folder else [library.machine_name]
    if 'format' in request.args and request.args.get( 'format' ) == 'jstree':
        path_out = ['library-{}'.format( library.id )]
        if folder:
            first = True
            for id_iter in folder.machine_path:
                if first:
                    # Skip library machine name (prefilled w/ library ID above).
                    first = False
                else:
                    path_out.append( 'folder-{}'.format( id_iter ) )

    return jsonify( path_out )

@ajax.route( '/ajax/get/item/<int:item_id>', methods=['GET'] )
@ajax.route( '/ajax/get/item/<int:item_id>/<string:attribute>', methods=['GET'] )
def get_item( item_id, attribute=None ):

    item = Item.secure_query( User.current_uid() ) \
        .filter( Item.id == item_id ) \
        .first_or_404()

    if attribute and hasattr( item, attribute ):
        return jsonify( getattr( item, attribute ) )
    elif not attribute:
        item_dict = item.to_dict( ignore_keys=['parent', 'folder'] )
        return jsonify( item_dict )

# endregion

# region save

@ajax.route( '/ajax/item/save', methods=['POST'] )
def cloud_item_ajax_save():

    current_uid = User.current_uid()

    save_form = EditItemForm( request.form )
    if not save_form.validate():
        return jsonify( { 'submit_status': 'error', 'fields': save_form.errors } )

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == save_form.id.data ) \
        .first()
    if not item:
        abort( 403 )

    # Translate tags data.
    new_tags = request.form['tags'].split( ',' )
    item.tags = [Tag.from_path( t ) for t in new_tags]

    # Translate location data.
    new_location = request.form['location'].split( '/' )
    current_path = None
    for path_id in new_location:
        if path_id.startswith( 'library-' ):
            library_id = path_id.split( '-' )[1]
            current_path = Library.secure_query( current_uid ) \
                .filter( Library.id == library_id ) \
                .first()
        elif path_id.startswith( 'folder-' ):
            folder_id = path_id.split( '-' )[1]
            if isinstance( current_path, Library ):
                current_path = Folder.secure_query( current_uid ) \
                    .filter( Folder.id == folder_id ) \
                    .filter( Folder.library_id == current_path.id ) \
                    .first()
            elif isinstance( current_path, Folder ):
                current_path = Folder.secure_query( current_uid ) \
                    .filter( Folder.id == folder_id ) \
                    .filter( Folder.parent_id == current_path.id ) \
                    .first()
            else:
                return jsonify(
                    {'submit_status': 'error', 'errors':
                        ['Invalid save path specified.'] } )

    #db.session.commit()

    # Return the modified item.
    item_dict = item.to_dict( ignore_keys=['parent', 'folder'] )
    return jsonify( item_dict )

# endregion

# region handlers

@ajax.errorhandler( 403 )
@ajax.errorhandler( 404 )
def error_404( ex ):
    return jsonify_error( str( ex ) )

# endregion
