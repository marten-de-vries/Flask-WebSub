from flask_websub.subscriber import discover
from flask_websub.errors import DiscoveryError
from .utils import serve_app
import pytest
from flask import Flask, make_response

# app
HTML = '''
<!DOCTYPE html>
<html>
  <head>
    <link rel='hub' href='/hub'>
    <link rel='self' href='/resource'>
  </head>
</html>'''


@pytest.fixture(scope='module', autouse=True)
def flask_server():
    app = Flask(__name__)

    @app.route('/basic')
    def basic():
        r = make_response('Hello World!')
        r.headers['Link'] = '</hub>; rel="hub", </resource>; rel="self"'
        return r

    @app.route('/blank')
    def blank():
        return ''

    @app.route('/tags')
    def tags():
        return HTML

    with serve_app(app, port=5000):
        yield


def test_basic():
    assert discover('http://localhost:5000/basic') == {
        'hub_url': '/hub',
        'topic_url': '/resource'
    }


def test_blank():
    with pytest.raises(DiscoveryError):
        discover('http://localhost:5000/blank')


def test_tags():
    assert discover('http://localhost:5000/tags') == {
        'hub_url': '/hub',
        'topic_url': '/resource'
    }
