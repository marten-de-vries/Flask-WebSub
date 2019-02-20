from flask import abort
import requests

import contextlib
import hashlib
import hmac
import logging
import sqlite3
import uuid

INVALID_LEASE = "Invalid hub.lease_seconds (should be a positive integer)"
A_MINUTE = 60
A_DAY = A_MINUTE * 60 * 24


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


def request_url(config, *args, **kwargs):
    # 3 seconds seems reasonable even for slow/far away servers, as websub
    # requests should not do elaborate processing anyway.
    kwargs['timeout'] = config.get('REQUEST_TIMEOUT', 3)
    return requests.request(*args, **kwargs)


logger = logging.getLogger('flask_websub')


def warn(msg, exc_info):
    logger.warning(msg, exc_info=exc_info)


def calculate_hmac(algorithm, secret, data):
    hash = getattr(hashlib, algorithm)
    return hmac.new(secret.encode('UTF-8'), data, hash).hexdigest()


def get_content(config, topic_url):
    updated_content = request_url(config, 'GET', topic_url, stream=True)
    updated_content.raise_for_status()
    return updated_content


def secret_too_big(secret):
    # 200 bytes actually (not characters), but this is close enough as a
    # sanity check
    return len(secret) >= 200


class SQLite3StorageMixin:
    def __init__(self, path):
        """Path should be where you want to save the sqlite3 database."""

        self.path = path
        with self.connection() as connection:
            connection.execute(self.TABLE_SETUP_SQL)

    @contextlib.contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            # allow writing and reading simultaneously:
            with connection:
                connection.execute('PRAGMA journal_mode=wal')
                yield connection
        finally:
            connection.close()
