from flask import abort, request, Blueprint, current_app

import hmac

from ..errors import SubscriberError
from ..storage import get_storage
from ..utils import warn, parse_lease_seconds, calculate_hmac, now, \
                    logging_race_condition

from .events import call_error_handlers, listeners

NOT_FOUND = "Could not found subscription with callback id '%s'"

callbacks = Blueprint('websub_callbacks', __name__)


@callbacks.route('/<callback_id>', methods=['GET'])
def subscription_confirmation(callback_id):
    mode = get_query_arg('hub.mode')
    try:
        subscription = get_storage()[callback_id, ]
    except KeyError as e:
        warn(NOT_FOUND % callback_id, e)
        abort(404)
    if mode == 'denied':
        return subscription_denied(callback_id, subscription)
    elif mode in ['subscribe', 'unsubscribe']:
        return confirm_subscription(callback_id, subscription)
    else:
        abort(400, "Invalid mode")


def get_query_arg(name):
    try:
        return request.args[name]
    except KeyError:
        abort(400, "Missing query argument: " + name)


def subscription_denied(callback_id, subscription):
    # 5.2 Subscription Validation

    # TODO: support Location header? It's a MAY, but a nice feature. Maybe
    # later, behind a config option.
    with logging_race_condition(callback_id):
        # cleanup
        del get_storage()[callback_id, ]
    reason = request.args.get('hub.reason', 'denied')
    call_error_handlers(subscription['topic_url'], SubscriberError(reason))
    return "'denied' acknowledged"


def confirm_subscription(callback_id, subscription):
    mode = get_query_arg('hub.mode')
    topic_url = get_query_arg('hub.topic')
    if mode != subscription['mode']:
        abort(404, "Mode does not match with last request")
    if topic_url != subscription['topic_url']:
        abort(404, "Topic url does not match")
    if mode == 'subscribe':
        lease = parse_lease_seconds(get_query_arg('hub.lease_seconds'))
        subscription['active'] = True
        subscription['expiration_time'] = now() + lease
        get_storage()[callback_id, ] = subscription
    else:  # unsubscribe
        with logging_race_condition(callback_id):
            del get_storage()[callback_id, ]
    return get_query_arg('hub.challenge'), 200


@callbacks.route('/<callback_id>', methods=['POST'])
def callback(callback_id):
    try:
        subscription = get_storage()[callback_id, ]
        assert subscription['active']
    except (KeyError, AssertionError):
        abort(404)
    # 1 MiB by default
    max_body_size = current_app.config.get('MAX_BODY_SIZE', 1024 * 1024)
    if request.content_length > max_body_size:
        abort(400, "Body too large")
    body = request.get_data()
    if body_is_valid(subscription, body):
        for callback in listeners:
            callback(subscription['topic_url'], body)
    return 'Content received'


def body_is_valid(subscription, body):
    if not subscription['secret']:
        return True
    try:
        algo, signature = request.headers['X-Hub-Signature'].split('=')
        expected_signature = calculate_hmac(algo, subscription['secret'], body)
    except KeyError as e:
        warn("X-Hub-Signature header expected but not set", e)
    except ValueError as e:
        warn("X-Hub-Signature header is invalid", e)
    except AttributeError as e:
        warn("Invalid algorithm in X-Hub-Signature", e)
    else:
        if hmac.compare_digest(signature, expected_signature):
            return True
    return False
