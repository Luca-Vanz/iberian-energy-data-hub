import sqlite3

from src.config import (
    DATABASE_PATH,
    IS_PUBLIC,
)


def get_database_connection():
    """
    Return a SQLite connection.

    In public mode the database is opened
    in read-only mode.
    """

    if IS_PUBLIC:

        database_uri = (
            f"file:{DATABASE_PATH.resolve().as_posix()}"
            "?mode=ro"
        )

        return sqlite3.connect(
            database_uri,
            uri=True,
        )


    return sqlite3.connect(
        DATABASE_PATH
    )