
import os
import random
import logging
import tempfile
import stat
from datetime import datetime

import numpy
from PIL import Image
from faker import Faker
from faker.providers import BaseProvider

from cloud_on_film.models import Library, Folder

PICTURE_SIZES = [
    (100, 100),
    (500, 500),
    (320, 240),
    (640, 480),
    (640, 400)
]

class FakeLibrary( BaseProvider ):

    def __init__( self, generator ):
        super().__init__( generator )

        self.fake = Faker()

        self.logger = logging.getLogger( 'fake.library' )

        self.picture_sizes = PICTURE_SIZES.copy()

    def display_name( self, lmin, lmax ):
        return ' '.join( [w.capitalize() \
            for w in self.fake.words( random.randint( lmin, lmax ) )] )

    def random_image( self, width, height ) -> Image:
        image_array = numpy.random.rand( width, height, 3 ) * 255
        image_out = Image.fromarray( image_array.astype( 'uint8' ) ).convert( 'RGB' )
        return image_out

    def picture( self, dbc, folder : Folder ):
        if not self.picture_sizes:
            self.picture_sizes = PICTURE_SIZES.copy()
        sz = random.choice( self.picture_sizes )
        self.picture_sizes.remove( sz )
        picture_img = self.random_image( *sz )
        picture_name = self.display_name( 2, 6 ) + '.jpg'
        picture_path = os.path.join( folder.absolute_path, picture_name )
        picture_img.save( picture_path )
        picture_date = datetime.fromtimestamp( random.randrange( 100000, 1000000 ) )
        picture_stat = os.stat( picture_path )

        from cloud_on_film.files.picture import Picture

        rating_out = random.randint( 0, 4 )
        picture_out = Picture(
            name=picture_name,
            width=sz[0],
            height=sz[1],
            rating=rating_out,
            folder_id=folder.id,
            timestamp=datetime.fromtimestamp( picture_stat[stat.ST_MTIME] ),
            size=picture_stat[stat.ST_SIZE],
            added=datetime.now(),
            hash=Picture.hash_file( picture_path, 1 ),
            hash_algo=1 )

        dbc.session.add( picture_out )
        dbc.session.commit()

        self.logger.info( 'created picture %s', picture_name )

        return {picture_name: {
            'type': 'picture',
            'width': sz[0],
            'height': sz[1],
            'rating': rating_out
        } }

    def folder(
        self,
        dbc,
        children_ct : int = 0,
        parent : Folder = None,
        library : Library = None,
        depth : int = 0
    ):
        folder_args = {}

        self.logger.info( 'depth: %d, children: %d', depth, children_ct )

        absolute_path : str
        if parent:
            folder_args['parent_id'] = parent.id
            folder_args['library_id'] = parent.library_id
            absolute_path = parent.absolute_path
        elif library:
            folder_args['library_id'] = library.id
            absolute_path = library.absolute_path

        folder_name = None
        folder_path = None
        while not folder_name:
            try:
                folder_name = self.display_name( 3, 5 )
                folder_path = os.path.join( absolute_path, folder_name )
                os.makedirs( folder_path )
            except (OSError, IOError) as exc:
                self.logger.error( 'error creating %s: %s', folder_path, exc )
                folder_name = None
                folder_path = None

        folder_args['name'] = folder_name

        folder_out = Folder( **folder_args )

        dbc.session.add( folder_out )
        dbc.session.commit()

        dict_out = {folder_name: {
            'id': folder_out.id,
            'children': {},
            'type': 'folder'
        } }
        for i in range( children_ct ):
            dict_out[folder_name]['children'].update( self.picture(
                dbc=dbc,
                folder=folder_out
            ) )

        for i in range( children_ct ):
            dict_out[folder_name]['children'].update( self.folder(
                dbc=dbc,
                children_ct=children_ct - random.randint( 1, 2 ),
                parent=folder_out,
                library=library,
                depth=depth + 1
            ) )

        self.logger.info( 'created folder %s', folder_name )

        return dict_out

    def library( self, dbc, root_path, children_ct=0 ):

        library_name = self.display_name( 2, 4 )
        nsfw_out = (random.randint( 0, 100 ) > 75)
        library_out = Library(
            display_name=library_name,
            machine_name=library_name.lower().replace( ' ', '_' ),
            absolute_path=os.path.join( root_path, library_name ),
            nsfw=nsfw_out
        )
        dbc.session.add( library_out )
        dbc.session.commit()

        if not children_ct:
            children_ct = random.randint( 1, 3 )

        dict_out = {library_name: {
            'children': {},
            'nsfw': nsfw_out,
            'absolute_path': os.path.join( root_path, library_name )
        } }
        for i in range( children_ct ):
            dict_out[library_name]['children'].update( self.folder(
                dbc=dbc,
                children_ct=children_ct - random.randint( 1, 2 ),
                parent=None,
                library=library_out
            ) )

        return dict_out
