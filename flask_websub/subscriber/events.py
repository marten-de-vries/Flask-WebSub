listeners = set()
error_handlers = set()


def add_listener(f):
    listeners.add(f)


def call_listeners(topic_url, body):
    call_all(listeners, topic_url, body)


def add_error_handler(f):
    error_handlers.add(f)


def call_error_handlers(topic_url, error):
    call_all(error_handlers, topic_url, error)


def call_all(funcs, *args):
    for func in funcs:
        func(*args)
