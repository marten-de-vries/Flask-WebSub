import abc
import contextlib
import sqlite3

from ..utils import now

__all__ = ('AbstractHubStorage', 'SQLite3HubStorage',)


class AbstractHubStorage(metaclass=abc.ABCMeta):
    """This abstract class formalizes the data model used by a hub.
    Implementations should take into account that methods can be called from
    different threads or even different processes.

    """
    @abc.abstractmethod
    def __delitem__(self, key):
        """A key consists of two components: (topic_url, callback_url).

        If the operation cannot be performed (e.g. because of there not being
        an item matching the key in the database), you may log an error. An
        exception should not be raised, though.

        """

    @abc.abstractmethod
    def __setitem__(self, key, value):
        """For key info, see __delitem__. value is a dict with the following
        properties:

        - expiration_time
        - secret

        """

    @abc.abstractmethod
    def get_callbacks(self, topic_url):
        """A generator function that should return tuples with the following
        values for each item in storage that has a matching topic_url:

        - callback_url
        - secret

        Note that expired objects should not be yielded.

        """


TABLE_SETUP_SQL = """
create table if not exists hub(
    topic_url text not null,
    callback_url text not null,
    expiration_time INTEGER not null,
    secret TEXT,
    PRIMARY KEY (topic_url, callback_url)
)
"""
DELITEM_SQL = "delete from hub where topic_url=? and callback_url=?"
SETITEM_SQL = """
insert into hub(topic_url, callback_url, expiration_time, secret)
values (?, ?, ?, ?)
"""
GET_CALLBACKS_SQL = """
select callback_url, secret from hub
where topic_url=? and expiration_time > ?
"""
CLEANUP_EXPIRED_SUBSCRIPTIONS_SQL = """
delete from hub where expiration_time <= ?
"""


class SQLite3HubStorage(AbstractHubStorage):
    def __init__(self, path):
        self.path = path
        with self.cursor() as cur:
            cur.execute(TABLE_SETUP_SQL)

    @contextlib.contextmanager
    def cursor(self):
        with sqlite3.connect(self.path) as connection:
            yield connection.cursor()

    def __delitem__(self, key):
        with self.cursor() as cur:
            cur.execute(DELITEM_SQL, key)

    def __setitem__(self, key, value):
        with self.cursor() as cur:
            cur.execute(SETITEM_SQL, key + (value['expiration_time'],
                                            value['secret']),)

    def get_callbacks(self, topic_url):
        with self.cursor() as cur:
            cur.execute(GET_CALLBACKS_SQL, (topic_url, now(),))
            while True:
                row = cur.fetchone()
                if not row:
                    break
                yield row

    def cleanup_expired_subscriptions(self):
        with self.cursor() as cur:
            cur.execute(CLEANUP_EXPIRED_SUBSCRIPTIONS_SQL, (now(),))
