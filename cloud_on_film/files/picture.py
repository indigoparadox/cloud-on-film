
import os
import stat
import errno
from datetime import datetime
from flask import current_app, url_for, render_template
from sqlalchemy import func
from sqlalchemy.ext.declarative import declared_attr
from PIL import Image
from cloud_on_film.models import \
    db, \
    Item, \
    ItemMeta, \
    DBItemNotFoundException, \
    Plugin

MACHINE_NAME = 'picture'

ASPECT_RATIO_FMT = {
    10: '16:10',
    9:  '16:9',
    4:  '4:3',
    1:  '1:1'
}

MAGIC_JPEG=b'\xff\xd8\xff'
MAGIC_GIF=b'\x47\x49\x46'
MAGIC_PNG=b'\x89\x50\x4e'

class ImageTypeException( Exception ):
    def __init__( self, *args, **kwargs ):
        self.image_type = \
            kwargs['image_type'] if 'image_type' in kwargs else \
            args[0] if 0 < len( args )  else \
            None
        super().__init__( *args, **kwargs )

class Picture( Item ):

    ''' Polymorph of Item class with additional functions and fields
    specifically for dealing with images. '''

    __mapper_args__ = {
        'polymorphic_identity': MACHINE_NAME
    }

    @declared_attr
    def width( self ):
        return db.column_property(
            db.select(
                [db.cast( ItemMeta.value, db.Integer )],
                db.and_(
                    ItemMeta.key == 'width',
                    ItemMeta.item_id == self.id ) ).label( 'width' ) )

    @declared_attr
    def height( self ):

        ''' Convenience access for meta['height']. '''

        return db.column_property(
            db.select(
                [db.cast( ItemMeta.value, db.Integer )],
                db.and_(
                    ItemMeta.key == 'height',
                    ItemMeta.item_id == self.id ) ).label( 'height' ) )

    @declared_attr
    def rating( self ):

        ''' Convenience access for meta['rating']. '''

        return db.column_property(
            db.case( [
                (db.select( [func.count( ItemMeta.value )],
                db.and_( # See if there's a meta['rating'] row.
                    ItemMeta.key == 'rating',
                    ItemMeta.item_id == self.id ) ).label( 'rating' ) == 1,
                (db.select( [db.cast( ItemMeta.value, db.Integer )],
                db.and_( # Return int( meta['rating'] ) if such a row exists.
                    ItemMeta.key == 'rating',
                    ItemMeta.item_id == self.id ) ).label( 'rating' )))
            ], else_=0 ) )

    @declared_attr
    def comment( self ):

        ''' Convenience access for meta['comment']. '''

        return db.column_property(
            db.case( [
                (db.select( [func.count( ItemMeta.value )],
                db.and_( # See if there's a meta['rating'] row.
                    ItemMeta.key == 'comment',
                    ItemMeta.item_id == self.id ) ).label( 'comment' ) != None,
                (db.select( [ItemMeta.value],
                db.and_( # Return int( meta['rating'] ) if such a row exists.
                    ItemMeta.key == 'comment',
                    ItemMeta.item_id == self.id ) ).label( 'comment' )))
            ], else_=None ) )

    @declared_attr
    def aspect( self ):

        ''' Convenience access for meta['aspect']. '''

        return db.column_property(
            db.case( [
                (16.0 * self.height.expression / self.width == 10.0, 10),
                (16.0 * self.height.expression / self.width == 9.0, 9),
                (4.0 * self.height.expression / self.width == 3.0, 4),
                (self.height.expression == self.width, 1),
            ], else_=0 ).label( 'aspect' ) )

    def to_dict( self, ignore_keys=None, max_depth=-1 ):
        dict_out = super().to_dict( ignore_keys, max_depth )

        status_out = 'ok'
        type_out = ''
        try:
            type_out = self.check_image_type()
        except ImageTypeException as e:
            status_out = 'error'
            type_out = e.image_type

        dict_out['check'] = {
            'status': status_out,
            'type': type_out
        }

        return dict_out

    def check_image_type( self ):

        ''' Compare the image's filename with its magic number and raise an
        ImageTypeException if they do not match. '''

        start_bytes = None
        try:
            with open( self.absolute_path, 'rb' ) as image_file_handle:
                start_bytes = image_file_handle.read( 3 )
        except FileNotFoundError as e:
            current_app.logger.error( 'while checking type: %s', e )
            raise ImageTypeException( 'missing' ) from e

        image_type = None
        if MAGIC_JPEG == start_bytes:
            image_type = 'image/jpeg'
            if not self.name.lower().endswith( '.jpeg' ) and \
            not self.name.lower().endswith( '.jpg' ):
                raise ImageTypeException( image_type )
        elif MAGIC_GIF == start_bytes:
            image_type = 'image/gif'
            if not self.name.lower().endswith( '.gif' ):
                raise ImageTypeException( image_type )
        elif MAGIC_PNG == start_bytes:
            image_type = 'image/png'
            if not self.name.lower().endswith( '.png' ):
                raise ImageTypeException( image_type )

        return image_type

    def open_image( self ):
        img_out = Image.open( self.absolute_path )
        if not img_out:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), self.absolute_path )
        return img_out

    def thumbnail_mime( self ):
        return 'image/jpeg'

    def thumbnail_path( self, size ):

        # Safety checks should be performed by the caller.
        if not os.path.exists( current_app.config['THUMBNAIL_PATH'] ):
            os.makedirs( current_app.config['THUMBNAIL_PATH'] )

        thumb_path = os.path.join(
            current_app.config['THUMBNAIL_PATH'],
            '{}_{}x{}.jpg'.format( self.hash, size[0], size[1] ) )

        if not os.path.exists( thumb_path ):
            with Image.open( self.absolute_path ) as im:
                try:
                    im.thumbnail( size, Image.LANCZOS )
                except OSError as e:
                    current_app.logger.warn(
                        'while generating thumbnail for %s: %s',
                        self.absolute_path, e )
                thumb = Image.new( 'RGB', size, (0, 0, 0) )
                thumb.paste( im,
                    (int( (size[0] - im.size[0]) / 2 ),
                    int( (size[1] - im.size[1]) / 2 )) )
                thumb.save( thumb_path, quality=75 )

        return thumb_path

    @staticmethod
    def from_path( lib, path, user_id ):

        picture = None
        try:
            picture = Item.from_path( lib, path, user_id )
        except DBItemNotFoundException as e:
            # Item doesn't exist in DB, but it does on FS, so add it to the DB.
            img_stat = os.stat( e.absolute_path )
            current_app.logger.info(
                'creating entry for file: {}'.format( e.absolute_path ) )
            picture = Picture(
                name=e.filename,
                folder_id=e.folder.id,
                timestamp=datetime.fromtimestamp( img_stat[stat.ST_MTIME] ),
                size=img_stat[stat.ST_SIZE],
                added=datetime.now(),
                hash=Picture.hash_file( e.absolute_path, 1 ),
                hash_algo=1 )
            db.session.add( picture )
            db.session.commit()

        if 'width' not in picture.meta or 'height' not in picture.meta:
            with Image.open( picture.absolute_path ) as im:
                print( im.size )
                picture.meta['width'] = im.size[0]
                picture.meta['height'] = im.size[1]
            db.session.commit()

            current_app.logger.info( 'found new image with size: {}x{}'.format(
                picture.width, picture.height
            ) )

        return picture

    def library_html( self ):

        self_dict = self.to_dict( ignore_keys=['folder', '_meta', '_tags'] )

        self_dict['classes'] = ''
        self_dict['fullsize_page'] = url_for( 'libraries.cloud_libraries',
            machine_name=self.folder.library.machine_name,
            relative_path=None ) + '/' + self.path
        self_dict['classes'] += ' nsfw' if self.nsfw else ''
        self_dict['aspect'] = \
            ASPECT_RATIO_FMT[self.aspect] if self.aspect else None
        self_dict['classes'] += ' wp-{}'.format(
            ASPECT_RATIO_FMT[self.aspect].replace( ':', 'x' ) ) if \
            self.aspect else ''
        self_dict['rating'] = int( self_dict['rating'] )
        self_dict['classes'] += ' rating-{}'.format( self.rating )

        # Format dict tags for display.
        if self_dict['tags'] is None:
            self_dict['tags'] = []
        for tag in self.tags:
            self_dict['classes'] += ' tag-{}'.format(
                tag.name.lower().replace( '/', '-' ).replace( ' ', '-' ) )

        html_out = render_template( 'file_card_picture.html.j2', **self_dict )
        return html_out

plugin = db.session.query( Plugin ) \
    .filter( Plugin.machine_name == MACHINE_NAME ) \
    .first()

if not plugin:
    plugin = Plugin(
        machine_name=MACHINE_NAME,
        display_name='Pictures',
        module_path='cloud_on_film.files.picture',
        model_name='Picture',
        enabled=True )
    db.session.add( plugin )
    db.session.commit()

    plugin.extensions['jpg'] = 'image/jpeg'
    plugin.extensions['jpeg'] = 'image/jpeg'
    plugin.extensions['gif'] = 'image/gif'
    plugin.extensions['png'] = 'image/png'
    plugin.extensions['bmp'] = 'image/bmp'
    plugin.extensions['ico'] = 'image/ico'

    db.session.commit()
