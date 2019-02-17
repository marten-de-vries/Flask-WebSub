class FlaskWebSubError(Exception):
    """Base class for flask_websub errors"""


class DiscoveryError(FlaskWebSubError):
    """For errors during canonical topic url and hub url discovery"""


class SubscriberError(FlaskWebSubError):
    """For errors while subscribing to a hub"""


class NotificationError(FlaskWebSubError):
    """Raised when the input of the send_change_notification task is invalid"""
