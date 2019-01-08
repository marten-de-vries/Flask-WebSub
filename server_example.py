#!/usr/bin/env python3
# server_example.py

from flask import Flask, render_template, url_for
# The publisher and hub are combined in the same process because it's easier.
# There's no need to do so, though.
from flask_websub.publisher import publisher, init_publisher
from flask_websub.hub import Hub, SQLite3HubStorage
from celery import Celery

# app & celery
app = Flask(__name__)
app.config['SERVER_NAME'] = 'localhost:8080'
celery = Celery('server_example', broker='redis://localhost:6379')

# initialise publisher
init_publisher(app)

# initialise hub
#
# PUBLISH_SUPPORTED is not recommended in production, as it just accepts any
# link without validation, but it's but nice for testing.
app.config['PUBLISH_SUPPORTED'] = True
# we could also have passed in just PUBLISH_SUPPORTED, but this is probably a
# nice pattern for your app:
hub = Hub(SQLite3HubStorage('server_data.sqlite3'), celery, **app.config)
app.register_blueprint(hub.build_blueprint(url_prefix='/hub'))


def validate_topic_existence(callback_url, topic_url, *args):
    with app.app_context():
        if topic_url.startswith('https://websub.rocks/'):
            return  # pass validation
        if topic_url != url_for('topic', _external=True):
            return "Topic not allowed"


hub.register_validator(validate_topic_existence)
hub.schedule_cleanup()  # cleanup expired subscriptions once a day, by default


@app.before_first_request
def cleanup():
    # or just cleanup manually at some point
    hub.cleanup_expired_subscriptions.delay()


@app.route('/')
@publisher()
def topic():
    return render_template('server_example.html')


@app.route('/update_now')
def update_now():
    hub.send_change_notification.delay(url_for('topic', _external=True))
    return "Notification send!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
