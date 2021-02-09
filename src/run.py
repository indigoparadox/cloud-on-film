#!/usr/bin/env python

from cloud_on_film import create_app

app = create_app()

if '__main__' == __name__:
    app.run()
