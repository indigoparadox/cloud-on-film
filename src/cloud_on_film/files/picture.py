
import os
import stat
from flask import current_app, url_for
from sqlalchemy import func
from sqlalchemy.ext.declarative import declared_attr
from cloud_on_film.models import db, Item, ItemMeta, Library, Folder, DBItemNotFoundException
from cloud_on_film.plugins import register_plugin
from PIL import Image
from datetime import datetime

PLUGIN = 'picture'

ASPECT_RATIO_FMT = {
    10: '16:10',
    9:  '16:9',
    4:  '4:3',
    1:  '1:1'
}

class Picture( Item ):

    __mapper_args__ = {
        'polymorphic_identity': PLUGIN
    }

    @declared_attr
    def width( cls ):
        return db.column_property(
            db.select(
                [db.cast( ItemMeta.value, db.Integer )],
                db.and_(
                    ItemMeta.key == 'width',
                    ItemMeta.item_id == cls.id ) ).label( 'width' ) )

    @declared_attr
    def height( cls ):
        return db.column_property(
            db.select(
                [db.cast( ItemMeta.value, db.Integer )],
                db.and_(
                    ItemMeta.key == 'height',
                    ItemMeta.item_id == cls.id ) ).label( 'height' ) )

    @declared_attr
    def rating( cls ):
        return db.column_property(
            db.case( [
                (db.select( [func.count( ItemMeta.value )],
                db.and_( # See if there's a meta['rating'] row.
                    ItemMeta.key == 'rating',
                    ItemMeta.item_id == cls.id ) ).label( 'rating' ) == 1,
                (db.select( [db.cast( ItemMeta.value, db.Integer )],
                db.and_( # Return int( meta['rating'] ) if such a row exists.
                    ItemMeta.key == 'rating',
                    ItemMeta.item_id == cls.id ) ).label( 'rating' )))
            ], else_=0 ) )

    @declared_attr
    def comment( cls ):
        return db.column_property(
            db.case( [
                (db.select( [func.count( ItemMeta.value )],
                db.and_( # See if there's a meta['rating'] row.
                    ItemMeta.key == 'comment',
                    ItemMeta.item_id == cls.id ) ).label( 'comment' ) != None,
                (db.select( [ItemMeta.value],
                db.and_( # Return int( meta['rating'] ) if such a row exists.
                    ItemMeta.key == 'comment',
                    ItemMeta.item_id == cls.id ) ).label( 'comment' )))
            ], else_=None ) )

    @declared_attr
    def aspect( cls ):
        return db.column_property(
            db.case( [
                (16 * cls.height.expression / cls.width == 10, 10),
                (16 * cls.height.expression / cls.width == 9, 9),
                (4 * cls.height.expression / cls.width == 3, 4),
                (1 * cls.height.expression / cls.width == 1, 1)
            ], else_=0 ).label( 'aspect' ) )

    def open_image( self ):
        im = Image.open( self.absolute_path )
        if not im:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), self.absolute_path )
        return im

    def thumbnail_path( self, size ):

        # Safety checks should be performed by the caller.
        if not os.path.exists( current_app.config['THUMBNAIL_PATH'] ):
            os.makedirs( current_app.config['THUMBNAIL_PATH'] )

        thumb_path = os.path.join(
            current_app.config['THUMBNAIL_PATH'],
            '{}_{}x{}.jpg'.format( self.hash, size[0], size[1] ) )

        if not os.path.exists( thumb_path ):
            with Image.open( self.absolute_path ) as im:
                im.thumbnail( size, Image.ANTIALIAS )
                thumb = Image.new( 'RGB', size, (0, 0, 0) )
                thumb.paste( im,
                    (int( (size[0] - im.size[0]) / 2 ),
                    int( (size[1] - im.size[1]) / 2 )) )
                thumb.save( thumb_path, quality=75 )

        return thumb_path

    @staticmethod
    def from_path( lib, path ):

        picture = None
        try:
            picture = Item.from_path( lib, path )
        except DBItemNotFoundException as e:
            # Item doesn't exist in DB, but it does on FS, so add it to the DB.
            st = os.stat( e.absolute_path )
            current_app.logger.info( 'creating entry for file: {}'.format( e.absolute_path ) )
            picture = Picture(
                name=e.filename,
                folder_id=e.folder.id,
                timestamp=datetime.fromtimestamp( st[stat.ST_MTIME] ),
                size=st[stat.ST_SIZE],
                added=datetime.now(),
                hash=Picture.hash_file( e.absolute_path, 1 ),
                hash_algo=1 )
            db.session.add( picture )
            db.session.commit()

        meta_test = False
        try:
            meta_test = picture.meta['width']
            meta_test = picture.meta['height']
        except KeyError as e:
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

        self_dict['comment'] = self.comment if self.comment else ''
        self_dict['preview'] = url_for( 'cloud_plugin_preview', file_id=self.id )
        self_dict['fullsize_page'] = url_for( 'cloud_libraries',
            machine_name=self.folder.library.machine_name,
            relative_path=None ) + '/' + self.path
        self_dict['fullsize'] = url_for( 'cloud_plugin_fullsize', file_id=self.id )
        self_dict['nsfw'] = '<small class="text-bright nsfw">NSFW</small>' if self.nsfw else ''
        self_dict['aspect'] = '<small class="text-bright aspect-ratio">{}</small>'.format( ASPECT_RATIO_FMT[self.aspect] ) if self.aspect else ''
        self_dict['rating'] = '<small class="rating">' + \
            ''.join( ['<a href="#" class="star-on star-{}"'.format( i ) for i in range( self.rating )] ) + \
            ''.join( ['<a href="#" class="star-off star-{}"></a>'.format( i ) for i in range( 5 - self.rating )] ) + \
            '</small>'

        html_out = '''
<div class="col-md-2 col-sm-4 coll-xs-6 px-0 card bg-secondary">

    <div class="px-0 py-0 libraries-thumbnail-wrapper" data-src="{preview}">
        <a href="{fullsize_page}" class="thumbnail"
            data-fullsize="{fullsize}">
            <noscript>
                <img
                    class="img-responsive libraries-thumbnail"
                    src="{preview}"
                    alt="{name}" />
            </noscript>
        </a>
    </div> <!-- /libraries-thumbnail-wrapper -->

    <form action="{{ url_for( 'cloud_edit_filedata' ) }}" method="POST"
        class="container-fluid d-flex flex-column flex-grow-1">

        <div class="card-body container-fluid d-flex flex-column flex-grow-1 w-100 px-0">

            <!-- body text -->
            <h3 class="card-title d-flex flex-column">{name}</h3>
            <p class="card-text d-flex flex-column flex-grow-1">
                {comment}
            </p>

            <!-- button bar -->
            <div class="d-flex flex-column">
                {nsfw}
                {aspect}
                <a href="#" onclick="return renameItem( {id} );">Edit</a>
                {rating}
            </div>

        </div> <!-- /card-body -->

    </form>
</div> <!-- /card -->

'''.format( **self_dict )
        return html_out

register_plugin( plugin='picture', model=Picture, extensions=['jpg', 'jpeg', 'gif', 'png', 'bmp', 'ico'] )
