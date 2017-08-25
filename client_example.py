#!/usr/bin/env python3

from flask import Flask, url_for
from flask_websub.subscriber import callbacks, subscribe, discover, \
                                    add_listener, add_error_handler, renew, \
                                    unsubscribe
from flask_websub.storage import set_storage, FileStorage

import sys

set_storage(FileStorage('client_data'))

app = Flask(__name__)
app.register_blueprint(callbacks, url_prefix='/callbacks')
app.config['SERVER_NAME'] = 'home.marten-de-vries.nl:8081'


@add_error_handler
def on_error(msg):
    print("ERROR!!!", msg)


@add_listener
def on_topic_change(topic_url, body):
    print('TOPIC CHANGED!!!', topic_url, body)


if len(sys.argv) == 2:
    url = sys.argv[1]
else:
    url = 'http://home.marten-de-vries.nl:8080/'


@app.route('/subscribe')
def subscribe_route():
    id = subscribe(**discover(url))
    return 'Subscribed. ' + url_for('renew_route', id=id, _external=True)


@app.route('/renew/<id>')
def renew_route(id):
    new_id = renew(id)
    return 'Renewed: ' + url_for('unsubscribe_route', id=new_id,
                                 _external=True)


@app.route('/unsubscribe/<id>')
def unsubscribe_route(id):
    unsubscribe(id)
    return 'Unsubscribed'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
