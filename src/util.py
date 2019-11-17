
def get_config( app ):
    config = None
    with app.open_instance_resource( 'config.yml', 'r' ) as config_f:
        config = yaml.load( config_f )
    return config

