#!/usr/bin/env python

from cloud import create_app

app = create_app()

if '__main__' == __name__:
    app.run()

