
import yaml
from flask import current_app

def get_config():
    config = None
    with current_app.open_instance_resource( 'config.yml', 'r' ) as config_f:
        config = yaml.load( config_f )
    return config

