
import io
import mimetypes
from flask import Blueprint, abort, request, current_app, send_file
from cloud_on_film import db
from cloud_on_film.models import \
    Tag, Item, User, Folder, Library, LibraryRootException

contents = Blueprint( 'contents', __name__ )

@contents.route( '/contents/preview/<int:file_id>' )
def cloud_plugin_preview( file_id ):

    '''Generate a preview thumbnail to be called by a tag src attribute on gallery pages.'''

    width = int( request.args['width'] ) if 'width' in request.args else 160
    height = int( request.args['height'] ) if 'height' in request.args else 120

    current_uid = User.current_uid()

    allowed_resolutions = [
        tuple( [int( i ) for i in r.split( ',' )] )
            for r in current_app.config['ALLOWED_PREVIEWS']]

    if not (width, height) in allowed_resolutions:
        abort( 404 )

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == file_id ) \
        .first_or_404()

    file_path = item.thumbnail_path( (width, height) )

    with open( file_path, 'rb' ) as pic_f:
        return send_file( io.BytesIO( pic_f.read() ),
            item.thumbnail_mime() )

@contents.route( '/contents/fullsize/<int:file_id>' )
def cloud_plugin_fullsize( file_id ):

    current_uid = User.current_uid()

    item = Item.secure_query( current_uid ) \
        .filter( Item.id == file_id ) \
        .first_or_404()

    current_app.logger.debug( '{} mimetype: {}'.format(
        item.path, item.mime_type ) )

    file_path = item.absolute_path
    mime_type = item.mime_type if item.mime_type \
        else mimetypes.guess_type( file_path )

    with open( file_path, 'rb' ) as pic_f:
        return send_file( io.BytesIO( pic_f.read() ), mime_type )
