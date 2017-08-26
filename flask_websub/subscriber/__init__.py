from flask import url_for, current_app
import requests

import contextlib

from ..storage import get_storage
from ..utils import now, uuid4, request_url, is_expired, secret_too_big
from ..errors import SubscriberError, HubNotRespondingError

from .discovery import discover
from .blueprint import callbacks
from .events import add_listener, add_error_handler, call_error_handlers

__all__ = ('add_listener', 'add_error_handler', 'subscribe', 'unsubscribe',
           'renew_subscriptions_and_cleanup', 'discover', 'callbacks', 'renew')

NO_SECRET_WITH_HTTP = ("Only specify a secret when using https. If you did "
                       "not pass one in yourself, disable AUTO_SET_SECRET.")
CLEANED_INACTIVE_SUBSCRIPTION = "Cleaned up an expired inactive subscription"


def subscribe(**subscription_info):
    return subscribe_impl(mode='subscribe', **subscription_info)


def subscribe_impl(callback_id=None, **subscription):
    # 5.1 Subscriber Sends Subscription Request
    if not callback_id:
        callback_id = uuid4()
    args = {
        'hub.callback': url_for('websub_callbacks.subscription_confirmation',
                                callback_id=callback_id, _external=True),
        'hub.mode': subscription['mode'],
        'hub.topic': subscription['topic_url'],
    }
    with contextlib.suppress(KeyError):
        args['hub.lease_seconds'] = subscription['lease_seconds']
        if subscription['lease_seconds'] <= 0:
            raise SubscriberError("lease_seconds should be a positive integer")
    add_secret_to_args(args, subscription, is_secure(subscription['hub_url']))
    # one hour should be enough time for the hub to answer. If the hub
    # didn't answer for so long, we can forget about the request.
    subscription.update(expiration_time=now() + 60 * 60,
                        active=False)
    get_storage()[callback_id, ] = subscription
    try:
        response = safe_post_request(subscription['hub_url'], data=args)
        assert response.status_code == 202
    except requests.exceptions.RequestException as e:
        raise SubscriberError("Invalid hub URL (subscribing failed)") from e
    except AssertionError as old_err:
        err = SubscriberError("Hub error - %s: %s" % (response.status_code,
                                                      response.content))
        raise err from old_err
    return callback_id


def is_secure(url):
    return url.startswith('https://')


def add_secret_to_args(args, subscription, hub_is_secure):
    # auto set secret (if safe to do so, the user didn't provide a secret, and
    # the functionality is not disabled)
    auto_set_secret = current_app.config.get('AUTO_SET_SECRET', True)
    if hub_is_secure and auto_set_secret:
        subscription.setdefault('secret', uuid4())

    if 'secret' in subscription:
        # check the invariant for using secrets
        if not hub_is_secure:
            raise SubscriberError(NO_SECRET_WITH_HTTP)
        if secret_too_big(subscription['secret']):
            raise SubscriberError("Secret is too big.")
        args['hub.secret'] = subscription['secret']


def safe_post_request(url, **opts):
    if not is_secure(url):
        https_url = 'https' + url[len('http'):]
        with contextlib.suppress(requests.exceptions.RequestException):
            return request_url('POST', https_url, **opts)
    return request_url('POST', url, **opts)


def unsubscribe(callback_id):
    subscription = get_active_subscription(callback_id)
    subscription['mode'] = 'unsubscribe'
    subscribe_impl(callback_id, **subscription)


def get_active_subscription(callback_id):
    try:
        subscription = get_storage()[callback_id, ]
        assert subscription['active']
    except KeyError as e:
        raise SubscriberError("Could not find subscription: " + callback_id)
    except AssertionError as e:
        raise SubscriberError("That subscription is not active.")
    else:
        return subscription


def renew(callback_id):
    return subscribe_impl(callback_id, **get_active_subscription(callback_id))


def renew_subscriptions_and_cleanup(margin_in_seconds):
    store = get_storage()
    for (callback_id,), subscription in store.by_key():
        is_active = subscription['active']
        if is_active and is_expired(subscription, margin_in_seconds):
            subscribe_impl(callback_id, **subscription)
        elif not is_active and is_expired(subscription):
            error = HubNotRespondingError(CLEANED_INACTIVE_SUBSCRIPTION)
            call_error_handlers(subscription['topic_url'], error)
            del store[callback_id, ]
