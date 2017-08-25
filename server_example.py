#!/usr/bin/env python3

from flask import Flask, render_template, url_for
# The publisher and hub are combined in the same process because it's easier.
# There's no need to do so, though.
from flask_websub.publisher import publisher, init_publisher
from flask_websub.hub import Hub, SQLite3HubStorage
from flask_websub.utils import make_celery

app = Flask(__name__)
app.config['SERVER_NAME'] = 'home.marten-de-vries.nl:8080'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379'
app.config['PUBLISH_SUPPORTED'] = True  # not recommended, but nice for testing
celery = make_celery(app)

init_publisher(app)

hub = Hub(SQLite3HubStorage('server_data.sqlite3'))
hub.init(app, celery, url_prefix='/hub')


def validate_topic_existence(callback_url, topic_url):
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
