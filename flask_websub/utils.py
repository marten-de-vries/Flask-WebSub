from flask import abort, current_app
from celery import Celery
import requests

import contextlib
import hashlib
import hmac
import time
import uuid

INVALID_LEASE = "Invalid hub.lease_seconds (should be a positive integer)"
RACE_CONDITION = ("Race condition. Subscription '%s' disappeared during this "
                  "request")


# Source: http://flask.pocoo.org/docs/0.12/patterns/celery/
def make_celery(app):
    celery = Celery(app.import_name,
                    backend=app.config.get('CELERY_RESULT_BACKEND'),
                    broker=app.config['CELERY_BROKER_URL'],)
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


def is_expired(subscription, margin_in_seconds=0):
    return subscription['expiration_time'] < now() + margin_in_seconds


def now():
    return int(round(time.time()))


def parse_lease_seconds(value):
    try:
        lease_seconds = int(value)
        assert lease_seconds > 0
    except (ValueError, AssertionError):
        abort(400, INVALID_LEASE)
    else:
        return lease_seconds


def uuid4():
    return str(uuid.uuid4())


def request_url(*args, **kwargs):
    # 3 seconds seems reasonable even for slow/far away servers, as websub
    # requests should not do elaborate processing anyway.
    kwargs['timeout'] = current_app.config.get('REQUEST_TIMEOUT', 3)
    return requests.request(*args, **kwargs)


def warn(msg, exc_info):
    current_app.logger.warning(msg, exc_info=exc_info)


def calculate_hmac(algorithm, secret, data):
    hash = getattr(hashlib, algorithm)
    return hmac.new(secret.encode('UTF-8'), data, hash).hexdigest()


def get_content(topic_url):
    updated_content = request_url('GET', topic_url, stream=True)
    updated_content.raise_for_status()
    return updated_content


@contextlib.contextmanager
def logging_race_condition(*key):
    try:
        yield
    except KeyError as e:
        warn(RACE_CONDITION % key, e)
