from flask_websub.hub import Hub
from flask_websub.publisher import init_publisher, publisher
from flask import Flask, render_template_string
import pytest


@pytest.fixture
def app():
    app = Flask(__name__)
    init_publisher(app)
    yield app


def test_basic(app):
    @app.route('/resource')
    @publisher(self_url='/test', hub_url='/hub')
    def resource():
        return 'Hello World!'

    resp = app.test_client().get('/resource')
    assert '</test>; rel="self"' in resp.headers['Link']
    assert '</hub>; rel="hub"' in resp.headers['Link']


TEMPLATE = """{{ websub_self_url }} {{ websub_self_link }}
{{ websub_hub_url }} {{ websub_hub_link }}"""


def test_template(app):
    @app.route('/resource')
    @publisher(hub_url='/hub')
    def resource():
        return render_template_string(TEMPLATE)

    resp = app.test_client().get('/resource')
    assert resp.data.count(b'http://localhost/resource') == 2
    assert resp.data.count(b'/hub') == 2


def test_default_hub(app):
    # mess with the internals so it looks like no hub has been created yet -
    # even if it has been by another test.
    import flask_websub.hub.blueprint
    flask_websub.hub.blueprint.first_time = True
    # we don't need celery & storage to just construct the blueprint & find
    # the URL. So we just pass in None.
    hub = Hub(None, None, **app.config)
    app.register_blueprint(hub.build_blueprint(url_prefix='/hub'))

    @app.route('/resource')
    @publisher()
    def resource():
        return 'Hello World!'

    resp = app.test_client().get('/resource')
    assert '<http://localhost/hub>; rel="hub"' in resp.headers['Link']
    assert '<http://localhost/resource>; rel="self"' in resp.headers['Link']


def test_global_hub(app):
    app.config['HUB_URL'] = '/abc'

    @app.route('/resource')
    @publisher()
    def resource():
        return 'Hello World!'

    resp = app.test_client().get('/resource')
    assert '</abc>; rel="hub"' in resp.headers['Link']
