import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager

from config import settings

_pool: ThreadedConnectionPool | None = None


def init_pool():
    global _pool
    _pool = ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        dsn=settings.database_url,
    )


def close_pool():
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None


@contextmanager
def get_connection():
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SET search_path = ag_catalog, public;")
            cur.execute("LOAD 'age';")
        yield conn
    finally:
        _pool.putconn(conn)
