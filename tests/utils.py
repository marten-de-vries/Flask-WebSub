import threading
import contextlib

from flask import request, url_for
import requests


@contextlib.contextmanager
def serve_app(app, port, https=False):
    opts = {'ssl_context': 'adhoc'} if https else {}
    app.config['PREFERRED_URL_SCHEME'] = 'https' if https else 'http'

    app.config['SERVER_NAME'] = 'localhost:' + str(port)

    @app.route('/ping')
    def ping():
        return 'pong'

    @app.route('/kill', methods=['POST'])
    def kill():
        request.environ['werkzeug.server.shutdown']()
        return 'bye'

    t = threading.Thread(target=lambda: app.run(port=port, **opts))
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
        requests.post(url_for('kill'), verify=False)
    t.join()
