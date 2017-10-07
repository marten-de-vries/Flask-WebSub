Flask-WebSub
-------------

An implementation of a WebSub hub, publisher and subscriber as a Flask
extension. The implementation is meant to be used as a library that can be
integrated in a larger application.

The components are split up into multiple packages, so you don't necessarily
have to use all three. It is for example possible to use the subscriber
implementation with an external hub. To learn to use this package, take a look
at the client_example.py (subscriber) and server_example.py (hub/publisher)
files. See the documentation for further information:
https://flask-websub.readthedocs.io/

Using the flask_websub.hub package requires celery.

For more about WebSub, see its specification: https://www.w3.org/TR/websub/
