# from celery import Celery
# from celerytest import start_celery_worker
from flask import Flask
import pytest

from flask_websub.subscriber import Subscriber, SQLite3TempSubscriberStorage, \
                                    SQLite3SubscriberStorage
from flask_websub.hub import Hub, SQLite3HubStorage
from .utils import serve_app

# @pytest.fixture(scope='session')
# def celery():
#     celery = Celery('test_integration', broker='redis://localhost:6379')
#     worker = start_celery_worker(celery)
#     yield celery
#     worker.stop()
#
# @pytest.fixture(scope='session', autouse=True)
# def hub_server(celery):
#     app = Flask(__name__)
#
#     hub = Hub(SQLite3HubStorage(':memory:'), celery, **app.config)
#     app.register_blueprint(hub.build_blueprint(url_prefix='/hub'))
#
#     yield from serve_app(app, 5001)

@pytest.fixture(scope='session', autouse=True)
def subscriber_server():
    app = Flask(__name__)
    subscriber = Subscriber(SQLite3SubscriberStorage(':memory:'),
                            SQLite3TempSubscriberStorage(':memory:'))
    app.register_blueprint(subscriber.build_blueprint(url_prefix='/callbacks'))

    @subscriber.add_success_handler
    def on_success(topic_url, callback_id, mode):
        print("SUCCESS!", topic_url, callback_id, mode)


    @subscriber.add_error_handler
    def on_error(topic_url, callback_id, msg):
        print("ERROR!", topic_url, callback_id, msg)


    @subscriber.add_listener
    def on_topic_change(topic_url, callback_id, body):
        print('TOPIC CHANGED!', topic_url, callback_id, body)

    yield from serve_app(app, 5002)

def test_false():
    assert 'TODO'
