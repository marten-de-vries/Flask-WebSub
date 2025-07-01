import threading
import contextlib

from flask import url_for
from werkzeug.serving import make_server

import requests


@contextlib.contextmanager
def serve_app(app, port, https=False):
    opts = {'ssl_context': 'adhoc'} if https else {}
    app.config['PREFERRED_URL_SCHEME'] = 'https' if https else 'http'

    app.config['SERVER_NAME'] = 'localhost:' + str(port)

    @app.route('/ping')
    def ping():
        return 'pong'

    s = make_server("localhost", port, app, **opts)
    t = threading.Thread(target=s.serve_forever)
    t.start()

    with app.app_context():
        # block until the server is up
        def retry():
            try:
                requests.get(url_for('ping'), verify=False)
            except requests.ConnectionError:
                retry()
        retry()

        # run the tests
        yield

        # tear down the server
        s.shutdown()
    t.join()
