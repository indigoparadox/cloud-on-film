
@current_app.cli.command( "update" )
def cloud_cli_update():
    for library in db.session.query( Library ):
        library_absolute_path = library.absolute_path
        for dirpath, dirnames, filenames in os.walk( library_absolute_path ):
            relative_path = re.sub( '^{}'.format( library_absolute_path ), '', dirpath )
            try:
                assert( None != library )
                #print( 'lib_abs: ' + library.absolute_path )
                folder = Folder.from_path( library, relative_path )
                #print( folder )
            except InvalidFolderException as e:
                print( dirpath )
                print( relative_path )
                current_app.logger.error( e.absolute_path )
            except LibraryRootException as e:
                current_app.logger.error( 'root' )
            #for dirname in dirnames:
            #    current_app.logger.info( dirname )

def cloud_update_item_meta( item ):
    if not os.path.exists( item.absolute_path ):
        current_app.logger.warn( 'file missing: {}'.format( item.absolute_path ) )
        item.status = StatusEnum.missing
        return
    img = item.open_image()
    if img and \
    (item.width != int( img.size[0]  ) or \
    item.height != int( img.size[1] )):
        current_app.logger.info( 'updating metadata for {}, width={}, height={} (from {}, {})'.format(
            item.absolute_path, img.size[0], img.size[1], db_width, db_height ) )
        item.meta['width'] = img.size[0]
        item.meta['height'] = img.size[1]

@current_app.cli.command( "refresh" )
def cloud_cli_refresh():
    #with Pool( 5 ) as p:
    #    res = p.map( cloud_update_item_meta, db.session.query( Item ) )
    #    #db.session.commit()
    #    print( res )
    for item in db.session.query( Item ):
        cloud_update_item_meta( item )
    db.session.commit()