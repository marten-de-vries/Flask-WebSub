Flask-WebSub
-------------

An implementation of a WebSub hub, publisher and subscriber based on Flask. The
implementation is meant to be used as a library that can be integrated in a
larger application.

The components are split up into multiple packages, so you don't necessarily
have to use all three. It is for example possible to use the subscriber
implementation with an external hub.

If you do use both the publisher and hub package, you benefit from
autodiscovery of the hub url.

Using the flask_websub.hub package requires celery.

For more about websub, see its specification: https://www.w3.org/TR/websub/
