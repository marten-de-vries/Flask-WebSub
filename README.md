Flask-WebSub
-------------

[![Build Status](https://dev.azure.com/marten-de-vries/Flask-WebSub/_apis/build/status/marten-de-vries.Flask-WebSub?branchName=master)](https://dev.azure.com/marten-de-vries/Flask-WebSub/_build/latest?definitionId=1&branchName=master)
[![Documentation](https://readthedocs.org/projects/flask-websub/badge/?version=latest)](https://flask-websub.readthedocs.io/)
[![PyPI version](https://badge.fury.io/py/Flask-WebSub.svg)](https://pypi.org/project/Flask-WebSub/)

An implementation of a WebSub hub, publisher and subscriber as a Flask
extension. The implementation is meant to be used as a library that can be
integrated in a larger application.

WebSub allows content providers to notify content subscribers of new content.
For example, a content provider could provide an RSS feed that a user (using
a web-based RSS reader) is interested in. Then the content provider could use
the publisher functionality of this package to advertise its support for
WebSub. The user's client can then subscribe to the feed using the subscriber
functionality of this extension. When the content provider publishes a blog
post, it notifies the so-called hub, which in turn notifies all subscribers.
You can either host your own hub (using the hub functionality of this package)
or depend upon one of the existing ones offered online. You can think of WebSub
as a standardized version of web hooks, that (due to mandatory resubscribing
every now and then) are more robust and support content integrity verification.

The components are split up into multiple packages, so you don't necessarily
have to use all three. It is for example possible to use the subscriber
implementation with an external hub. To learn to use this package, take a look
at the client_example.py (subscriber) and server_example.py (hub/publisher)
files. See the documentation for further information:
https://flask-websub.readthedocs.io/

Using the flask_websub.hub package requires celery.

For more about WebSub, which was previously named PubSubHubbub, see its specification: https://www.w3.org/TR/websub/
