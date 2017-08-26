import functools

from .blueprint import build_blueprint, A_DAY
from .tasks import make_request_retrying, send_change_notification, \
                   subscribe, unsubscribe
from .storage import SQLite3HubStorage

__all__ = ('Hub', 'SQLite3HubStorage')


class Hub:
    """The user interface to this module. The constructor requires a storage
    object, a flask app and a celery object. The last can be (but does not have
    to be) created using `flask_websub.utils.make_celery(app)``. Any further
    options passed in to the constructor are passed onto the
    app.register_blueprint() function when the single route of the hub is
    registered. This makes it possible to e.g. change the location of the
    endpoint by setting the url_prefix keyword argument.

    User-facing properties have doc strings. Other properties should be
    considered implementation details.

    """
    def __init__(self, storage, app, celery, **opts):
        self.validators = []
        self.storage = storage

        app.register_blueprint(build_blueprint(self, **opts))

        def task_with_hub(f, **opts):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                return f(self, *args, **kwargs)
            return celery.task(**opts)(wrapper)

        # tasks for internal use:
        self.subscribe = task_with_hub(subscribe)
        self.unsubscribe = task_with_hub(unsubscribe)

        max_attempts = app.config.get('MAX_ATTEMPTS', 10)
        make_req = task_with_hub(make_request_retrying, bind=True,
                                 max_retries=max_attempts)
        self.make_request_retrying = make_req

        # user facing tasks:
        self.send_change_notification = task_with_hub(send_change_notification)
        self.send_change_notification.__doc__ = """
        Allows you to notify subscribers of a change to a `topic_url`. This
        is a celery task, so you probably will actually want to call
        hub.send_change_notification.delay(topic_url, updated_content). The
        last argument is optional. If passed in, it should be an object with
        two properties: `headers` (dict-like), and `content` (a byte string).
        If left out, the updated content will be fetched from the topic url
        directly.

        """.lstrip()

        @celery.task
        def cleanup():
            self.storage.cleanup_expired_subscriptions()
        self.cleanup_expired_subscriptions = cleanup
        self.cleanup_expired_subscriptions.__doc__ = """
        Removes any expired subscriptions from the backing data store. It
        takes no arguments, and is a celery task.

        """.lstrip()

        def schedule_cleanup(every_x_seconds=A_DAY):
            celery.add_periodic_task(every_x_seconds,
                                     self.cleanup_expired_subscriptions.s())
        self.schedule_cleanup = schedule_cleanup
        self.schedule_cleanup.__doc__ = """
        schedule_cleanup(every_x_seconds=A_DAY): schedules the celery task
        `cleanup_expired_subscriptions` as a recurring event, the frequency of
        which is determined by its parameter. This is not a celery task itself
        (as the cleanup is only scheduled), and is a convenience function.

        """.lstrip()

    def register_validator(self, f):
        """Register `f` as a validation function for subscription requests. It
        gets a callback_url and topic_url as its arguments, and should return
        None if the validation succeeded, or a string describing the problem
        otherwise.

        """
        self.validators.append(f)
