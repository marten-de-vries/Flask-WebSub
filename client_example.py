#!/usr/bin/env python3

from flask import Flask, url_for
from flask_websub.subscriber import Subscriber, SQLite3TempSubscriberStorage, \
                                    SQLite3SubscriberStorage, discover

import sys

app = Flask(__name__)
app.config['SERVER_NAME'] = 'home.marten-de-vries.nl:8081'

subscriber = Subscriber(SQLite3SubscriberStorage('client_data.sqlite3'),
                        SQLite3TempSubscriberStorage('client_data.sqlite3'),
                        app, url_prefix='/callbacks')


@subscriber.add_success_handler
def on_success(topic_url, callback_id, mode):
    print("SUCCESS!", topic_url, callback_id, mode)


@subscriber.add_error_handler
def on_error(topic_url, callback_id, msg):
    print("ERROR!", topic_url, callback_id, msg)


@subscriber.add_listener
def on_topic_change(topic_url, callback_id, body):
    print('TOPIC CHANGED!', topic_url, callback_id, body)


if len(sys.argv) == 2:
    url = sys.argv[1]
else:
    url = 'http://home.marten-de-vries.nl:8080/'


@app.route('/subscribe')
def subscribe_route():
    id = subscriber.subscribe(**discover(url))
    return 'Subscribed. ' + url_for('renew_route', id=id, _external=True)


@app.route('/renew/<id>')
def renew_route(id):
    new_id = subscriber.renew(id)
    return 'Renewed: ' + url_for('unsubscribe_route', id=new_id,
                                 _external=True)


@app.route('/unsubscribe/<id>')
def unsubscribe_route(id):
    subscriber.unsubscribe(id)
    return 'Unsubscribed: ' + url_for('cleanup_and_renew_all', _external=True)


@app.route('/cleanup_and_renew_all')
def cleanup_and_renew_all():
    subscriber.cleanup()
    # 100 days, to make sure every single subscription is renewed
    subscriber.renew_close_to_expiration(24 * 60 * 60 * 100)
    return 'Done!'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
