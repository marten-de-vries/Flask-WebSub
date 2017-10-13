Examples
========

To run the example below, first start a celery broker. For example like this:

.. code:: bash

  docker run -p 6379:6379 redis:alpine


Then, it is time to install the dependencies. We use a ``virtualenv`` to
isolate them from the rest of the system:

.. code:: bash

  python3 -m venv venv # create the virtualenv
  source venv/bin/activate # activate the virtualenv
  pip install Flask-WebSub[celery,redis] # install the dependencies

Now our environment is set up, we can actually create a server and client file:

.. literalinclude:: ../server_example.py

.. literalinclude:: ../client_example.py

.. literalinclude:: ../templates/server_example.html
   :language: html

Don't forget to update ``server_example.py`` and ``client_example.py``'s
``SERVER_NAME`` config variable when creating those files. Simply set them to
whatever hostname the server will have (it can just be localhost).

Finally, it's time to start the applications. Each line in a different
terminal (assuming the virtualenv is active in each):

.. code:: bash

  celery -A server_example.celery worker -l info  # starts the celery worker
  ./server_example.py  # runs the server flask application
  ./client_example.py  # runs the client flask application

You can now see the page the hub publishes by navigating to the root url of
the hub server (port 8080). As it's a static page, you can simulate updating it
by navingating to ``/update_now``. Of course, for this to do something, you
need to subscribe to the URL. The subscriber server (as defined in
``client_example.py``, port 8081) offers a ``/subscribe`` endpoint to help you
with this. It will also tell you other URLs you can visit to control the
subscription side of the process.
