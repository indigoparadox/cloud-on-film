
from flask import current_app
from ... import libraries
from ...models import db, Library, FileItem
import os
from PIL import Image

def generate_thumbnail( file_id, size ):

    # TODO: Safety checks.
    item = FileItem.from_id( file_id )

    #width = 0
    #height = 0
    #for m in item.meta:
    #    if 'width' == m.key:
    #        width = int( m.value )
    #    elif 'height' == m.key:
    #        height = int( m.value )

    #assert( width > 0 and height > 0 )

    if not os.path.exists( current_app.config['THUMBNAIL_PATH'] ):
        os.makedirs( current_app.config['THUMBNAIL_PATH'] )

    thumb_path = os.path.join(
        current_app.config['THUMBNAIL_PATH'],
        '{}_{}x{}.jpg'.format( item.filehash, size[0], size[1] ) )

    #file_path = libraries.build_file_path( file_id, absolute_fs=True )

    if not os.path.exists( thumb_path ):
        im = Image.open( item.absolute_path )
        im.thumbnail( size, Image.ANTIALIAS )
        thumb = Image.new( 'RGB', size, (0, 0, 0) )
        thumb.paste( im,
            (int( (size[0] - im.size[0]) / 2 ),
            int( (size[1] - im.size[1]) / 2 )) )
        thumb.save( thumb_path, quality=75 )

    return thumb_path

