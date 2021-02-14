
from cloud_on_film.models import Item, db

PLUGIN_INFO = {}

def register_plugin( plugin, model, extensions ):
    PLUGIN_INFO[plugin] = {
        'model': model,
        'extensions': extensions
    }

def extension_model( extension ):
    for p in PLUGIN_INFO:
        if extension in PLUGIN_INFO[p]['extensions']:
            return PLUGIN_INFO[p]['model']
    return Item

def item_from_id( file_id ):
    poly = plugin_polymorph()
    return db.session.query( poly ) \
        .filter( Item.id == file_id ) \
        .first()

def item_from_path( library, path ):
    extension = path.split( '.' )[-1]
    return extension_model( extension ).from_path( library, path )

def plugin_polymorph():
    models = []
    for p in PLUGIN_INFO:
        models.append( PLUGIN_INFO[p]['model'] )
    return db.with_polymorphic( Item, models )
