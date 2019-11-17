#!/usr/bin/env python

import logging
from cloud import create_app

app = create_app()

if '__main__' == __name__:
    logging.basicConfig( level=logging.INFO )
    logger = logging.getLogger( 'main' )

    app.run()

