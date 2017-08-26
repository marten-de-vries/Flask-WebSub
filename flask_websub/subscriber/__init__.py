from flask import url_for, current_app
import requests

import contextlib

from ..utils import uuid4, request_url, secret_too_big, A_DAY
from ..errors import SubscriberError

from .discovery import discover
from .blueprint import build_blueprint
from .events import EventMixin
from .storage import WerkzeugCacheTempSubscriberStorage, \
                     SQLite3TempSubscriberStorage, SQLite3SubscriberStorage

__all__ = ('Subscriber', 'discover', 'WerkzeugCacheTempSubscriberStorage',
           'SQLite3TempSubscriberStorage', 'SQLite3SubscriberStorage')

NO_SECRET_WITH_HTTP = ("Only specify a secret when using https. If you did "
                       "not pass one in yourself, disable AUTO_SET_SECRET.")
LEASE_SECONDS_INVALID = "lease_seconds should be a positive decimal integer"
INVALID_HUB_URL = "Invalid hub URL (subscribing failed)"
NOT_FOUND = "Could not find subscription: "
RENEW_FAILURE = "Could not renew subscription (%s, %s)"


class Subscriber(EventMixin):
    def __init__(self, storage, temp_storage, app, **opts):
        super().__init__()

        self.storage = storage
        self.temp_storage = temp_storage
        self.blueprint_name, blueprint = build_blueprint(self, **opts)
        app.register_blueprint(blueprint)

    def subscribe(self, **subscription_request):
        return self.subscribe_impl(mode='subscribe', **subscription_request)

    def subscribe_impl(self, callback_id=None, **request):
        # 5.1 Subscriber Sends Subscription Request
        endpoint = self.blueprint_name + '.subscription_confirmation'
        if not callback_id:
            callback_id = uuid4()
        callback_url = url_for(endpoint, callback_id=callback_id,
                               _external=True)
        args = {
            'hub.callback': callback_url,
            'hub.mode': request['mode'],
            'hub.topic': request['topic_url'],
        }
        try:
            args['hub.lease_seconds'] = request['lease_seconds']
        except KeyError:
            request['lease_seconds'] = None
        else:
            if request['lease_seconds'] <= 0:
                raise SubscriberError(LEASE_SECONDS_INVALID)
        add_secret_to_args(args, request, is_secure(request['hub_url']))
        # ten minutes should be enough time for the hub to answer. If the hub
        # didn't answer for so long, we can forget about the request.
        request['timeout'] = 10 * 60
        self.temp_storage[callback_id] = request
        try:
            response = safe_post_request(request['hub_url'], data=args)
            assert response.status_code == 202
        except requests.exceptions.RequestException as e:
            raise SubscriberError(INVALID_HUB_URL) from e
        except AssertionError as old_err:
            err = SubscriberError("Hub error - %s: %s" % (response.status_code,
                                                          response.content))
            raise err from old_err
        return callback_id

    def unsubscribe(self, callback_id):
        request = self.get_active_subscription(callback_id)
        request['mode'] = 'unsubscribe'
        self.subscribe_impl(callback_id, **request)

    def get_active_subscription(self, callback_id):
        try:
            subscription = self.storage[callback_id]
        except KeyError as e:
            raise SubscriberError(NOT_FOUND + callback_id)
        else:
            return subscription

    def renew(self, callback_id):
        return self.subscribe_impl(callback_id,
                                   **self.get_active_subscription(callback_id))

    def renew_close_to_expiration(self, margin_in_seconds=A_DAY):
        """This is a long-running method for any non-trivial usage of the
        subscriber module. It is recommended to run it in a celery task.

        """
        subscriptions = self.storage.close_to_expiration(margin_in_seconds)
        for subscription in subscriptions:
            try:
                self.subscribe_impl(**subscription)
            except SubscriberError as e:
                current_app.logger.warning(RENEW_FAILURE,
                                           subscription['topic_url'],
                                           subscription['callback_id'],
                                           exc_info=e)

    def cleanup(self):
        self.temp_storage.cleanup()


def is_secure(url):
    return url.startswith('https://')


def safe_post_request(url, **opts):
    if not is_secure(url):
        https_url = 'https' + url[len('http'):]
        with contextlib.suppress(requests.exceptions.RequestException):
            return request_url('POST', https_url, **opts)
    return request_url('POST', url, **opts)


def add_secret_to_args(args, request, hub_is_secure):
    # auto set secret (if safe to do so, the user didn't provide a secret,
    # and the functionality is not disabled)
    auto_set_secret = current_app.config.get('AUTO_SET_SECRET', True)
    if hub_is_secure and auto_set_secret:
        request.setdefault('secret', uuid4())
    else:
        request.setdefault('secret')

    if request['secret']:
        # check the invariant for using secrets
        if not hub_is_secure:
            raise SubscriberError(NO_SECRET_WITH_HTTP)
        if secret_too_big(request['secret']):
            raise SubscriberError("Secret is too big.")
        args['hub.secret'] = request['secret']
