class FlaskWebSubError(Exception):
    """Base class for flask_websub errors"""


class StorageError(FlaskWebSubError):
    """Storage-related errors"""


class DiscoveryError(FlaskWebSubError):
    """For errors during canonical topic url and hub url discovery"""


class SubscriberError(FlaskWebSubError):
    """For errors while subscribing to a hub"""


class HubNotRespondingError(FlaskWebSubError):
    """For when a hub is not responding. Note that this error might be noticed
    very late, as it is only detected when the persistent state associated with
    the request is cleaned up. In the best case, it'll take an hour.

    """


class NotificationError(FlaskWebSubError):
    """Raised when the input of the send_change_notification task is invalid"""
