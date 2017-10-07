Examples
========

To run the examples, first setup a celery broker. I myself did it this way:

.. code:: bash

  docker run -p 6379:6379 redis:alpine


Then, it's time to update server_example.py and client_example.py's SERVER_NAME
config variable. Simply set them to whatever hostname the server will have (it
can just be localhost).

I recommend installing the dependencies in a virtualenv:

.. code:: bash

  python3 -m venv venv # create the virtualenv
  source venv/bin/activate # activate the virtualenv
  pip install -e .[celery,redis] # install the dependencies

Finally, it's time to start the applications. Each line in a different
terminal (assuming the virtualenv is active in each):

.. code:: bash

  celery -A server_example.celery worker -l info
  ./server_example.py
  ./client_example.py
