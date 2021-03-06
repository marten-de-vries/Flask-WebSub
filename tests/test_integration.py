from flask import Flask
import pytest
import requests
from cachelib import SimpleCache

import os
import base64
from unittest.mock import Mock, call

from flask_websub.errors import SubscriberError, NotificationError
from flask_websub.subscriber import Subscriber, SQLite3TempSubscriberStorage, \
                                    SQLite3SubscriberStorage, \
                                    WerkzeugCacheTempSubscriberStorage
from flask_websub.hub import Hub, SQLite3HubStorage
from .utils import serve_app


def run_hub_app(celery, worker, https):
    app = Flask(__name__)
    app.config['PUBLISH_SUPPORTED'] = True

    hub = Hub(SQLite3HubStorage('hub.db'), celery, **app.config)
    worker.reload()

    app.register_blueprint(hub.build_blueprint(url_prefix='/hub'))
    with serve_app(app, port=5001, https=https):
        yield hub

    os.remove('hub.db')


@pytest.fixture
def https_hub(celery_session_app, celery_session_worker):
    # monkey-patch requests
    def new(*args, **kwargs):
        kwargs['verify'] = False
        return old(*args, **kwargs)
    old, requests.request = requests.request, new

    # suppress warning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    yield from run_hub_app(celery_session_app, celery_session_worker,
                           https=True)

    # de-monkey patch
    requests.request = old


@pytest.fixture
def hub(celery_session_app, celery_session_worker):
    yield from run_hub_app(celery_session_app, celery_session_worker,
                           https=False)


def subscriber_app(subscriber):
    app = Flask(__name__)
    app.register_blueprint(subscriber.build_blueprint(url_prefix='/callbacks'))

    with serve_app(app, port=5002):
        yield subscriber
    os.remove('subscriber.db')


@pytest.fixture
def subscriber():
    subscriber = Subscriber(SQLite3SubscriberStorage('subscriber.db'),
                            SQLite3TempSubscriberStorage('subscriber.db'))
    yield from subscriber_app(subscriber)


@pytest.fixture
def werkzeug_subscriber():
    subscriber = Subscriber(SQLite3SubscriberStorage('subscriber.db'),
                            WerkzeugCacheTempSubscriberStorage(SimpleCache()))
    yield from subscriber_app(subscriber)


def test_subscriber_error(subscriber):
    with pytest.raises(SubscriberError):
        subscriber.subscribe(topic_url='http://example.com',
                             # hub is not active, but the checks mean we don't
                             # get there anyway
                             hub_url='http://localhost:5001/hub',
                             # impossible
                             lease_seconds=-1)
    # nonexisting URL
    with pytest.raises(SubscriberError):
        subscriber.subscribe(topic_url='http://example.com',
                             hub_url='http://unexisting')

    # page exists, but is not a hub
    with pytest.raises(SubscriberError):
        subscriber.subscribe(topic_url='http://example.com',
                             hub_url='http://localhost:5002/ping')


def test_subscription_werkzeug(hub, werkzeug_subscriber):
    on_success = Mock()
    werkzeug_subscriber.add_success_handler(on_success)
    topic = 'http://example.com'
    id = werkzeug_subscriber.subscribe(topic_url=topic,
                                       hub_url='http://localhost:5001/hub')
    while not on_success.called:
        pass
    on_success.assert_called_with(topic, id, 'subscribe')


def test_unexisting_werkzeug(werkzeug_subscriber):
    resp = requests.get('http://localhost:5002/callbacks/unexisting', params={
        'hub.mode': 'subscribe',
    })
    assert resp.status_code == 404


def test_sub_notify_unsub(https_hub, subscriber):
    # subscribe
    on_success = Mock()
    subscriber.add_success_handler(on_success)
    topic = 'http://example.com'
    id = subscriber.subscribe(topic_url=topic,
                              hub_url='https://localhost:5001/hub')
    while not on_success.called:
        pass  # wait for the worker to finish
    on_success.assert_called_with(topic, id, 'subscribe')

    # send notification
    on_topic_change = Mock()
    subscriber.add_listener(on_topic_change)
    content = {
        'content': base64.b64encode(b'Hello World!').decode('ascii'),
        'headers': {
            'Link': ', '.join([
                '<http://example.com>; rel="self"',
                '<https://localhost:5001/hub>; rel="hub"',
            ])
        },
    }
    https_hub.send_change_notification.delay(topic, content).get()
    while not on_topic_change.called:  # pragma: no cover
        pass
    on_topic_change.assert_called_with(topic, id, b'Hello World!')

    # unsubscribe
    on_success = Mock()
    subscriber.add_success_handler(on_success)
    subscriber.unsubscribe(id)
    while not on_success.called:
        pass
    on_success.assert_called_with(topic, id, 'unsubscribe')


def test_validator(hub, subscriber):
    on_error = Mock()
    subscriber.add_error_handler(on_error)
    error = 'invalid URL'

    @hub.register_validator
    def validate(callback_url, topic_url, *args):
        if not topic_url.startswith('http://example.com'):
            return error

    topic = 'http://invalid.com'
    id = subscriber.subscribe(topic_url=topic,
                              hub_url='http://localhost:5001/hub')
    while not on_error.called:
        pass
    on_error.assert_called_with(topic, id, error)

    topic = 'http://example.com/abc'
    on_success = Mock()
    subscriber.add_success_handler(on_success)
    id = subscriber.subscribe(topic_url=topic,
                              hub_url='http://localhost:5001/hub')
    while not on_success.called:
        pass
    on_success.assert_called_with(topic, id, 'subscribe')


def test_renew(hub, subscriber):
    topic = 'http://example.com/def'
    on_success = Mock()
    subscriber.add_success_handler(on_success)
    id = subscriber.subscribe(topic_url=topic,
                              hub_url='http://localhost:5001/hub')
    while not on_success.called:
        pass
    subscriber.renew(id)
    while on_success.call_count != 2:
        pass

    # renew everything (because of the huge margin, and everything here means
    # our single subscription)
    subscriber.renew_close_to_expiration(margin_in_seconds=10000000000000)
    while on_success.call_count != 3:
        pass

    on_success.assert_has_calls([call(topic, id, 'subscribe'),
                                 call(topic, id, 'subscribe'),
                                 call(topic, id, 'subscribe')])


def test_renew_unexisting_id(subscriber):
    with pytest.raises(SubscriberError):
        subscriber.renew('unexisting')


def test_schedule_cleanup(hub):
    # long-term scheduling (does nothing in the time frame of this test)
    hub.schedule_cleanup(every_x_seconds=60 * 60 * 24)  # once a day


def test_hub_cleanup(hub):
    # cleanup (does nothing, but tests the path)
    hub.cleanup_expired_subscriptions.delay().get()


def test_hub_invalid_input(hub):
    with pytest.raises(NotificationError):
        hub.send_change_notification.delay('http://unexisting').get()
    with pytest.raises(NotificationError):
        # URL exists, but it does not have the right Link headers so sending
        # out a notification for it will (rightfully) fail.
        hub.send_change_notification.delay('http://localhost:5001/ping').get()


def test_subscriber_cleanup(subscriber):
    subscriber.cleanup()


def test_hub_manually(hub):
    resp = requests.post('http://localhost:5001/hub')
    assert resp.status_code == 400

    resp2 = requests.post('http://localhost:5001/hub', data={
        'hub.mode': 'unknown',
        'hub.topic': 'http://example.com',
        'hub.callback': 'http://unimportant/',
    })
    assert resp2.status_code == 400

    resp3 = requests.post('http://localhost:5001/hub', data={
        'hub.mode': 'subscribe',
        'hub.topic': 'http://example.com',
        'hub.callback': 'http://unimportant/',
        'hub.lease_seconds': 10000000000000000000  # out of bounds
    })
    assert resp3.status_code == 202

    resp4 = requests.post('http://localhost:5001/hub', data={
        'hub.mode': 'subscribe',
        'hub.topic': 'http://example.com',
        'hub.callback': 'http://unimportant/',
        'hub.lease_seconds': -10  # impossible
    })
    assert resp4.status_code == 400

    resp5 = requests.post('http://localhost:5001/hub', data={
        'hub.mode': 'subscribe',
        'hub.topic': 'http://example.com',
        'hub.callback': 'http://unimportant/',
        'hub.secret': 'X' * 1024,  # secret too big
    })
    assert resp5.status_code == 400

    resp6 = requests.post('http://localhost:5001/hub', data={
        'hub.mode': 'publish',
        # this page does not contain proper Links, so the publish action will
        # (eventually) fail.
        'hub.topic': 'http://localhost:5001/ping',
    })
    assert resp6.status_code == 202


def test_subscriber_manually(subscriber):
    resp = requests.get('http://localhost:5002/callbacks/unexisting')
    assert resp.status_code == 400

    resp2 = requests.get('http://localhost:5002/callbacks/unexisting', params={
        'hub.mode': 'subscribe',
    })
    assert resp2.status_code == 404

    resp3 = requests.post('http://localhost:5002/callbacks/unexisting')
    assert resp3.status_code == 404

    resp4 = requests.get('http://localhost:5002/callbacks/unexisting', {
        'hub.mode': 'denied',
    })
    assert resp4.status_code == 404
