"""Public-safe categories of service failures shared across resources."""

from enum import Enum

from sqlalchemy.exc import TimeoutError


class UnknownServer(LookupError):
    """The requested ID is not registered with this application."""


class StorageFailure(Enum):
    UNCONFIGURED = "PostgreSQL storage has not been configured for this API."
    SCHEMA = "A required schema, table or column is missing. Check the migrations."
    TIMEOUT = "The database operation timed out."
    LOCK = "PostgreSQL could not acquire a required lock."
    CANCELED = "PostgreSQL canceled the operation before it completed."
    DATABASE = "PostgreSQL could not complete the requested storage operation."


class StorageUnavailable(Exception):
    """Carry only a fixed public reason across the persistence/HTTP boundary."""

    def __init__(self, reason: StorageFailure = StorageFailure.DATABASE):
        self.reason = reason

    @classmethod
    def from_database_error(cls, error):
        # SQLSTATE identifies known failures without including SQL, values or hosts.
        state = getattr(getattr(error, "orig", None), "sqlstate", None)
        if state in {"42P01", "42703", "3F000"}:
            return cls(StorageFailure.SCHEMA)
        if state == "55P03":
            return cls(StorageFailure.LOCK)
        if state == "57014":
            return cls(StorageFailure.CANCELED)
        if isinstance(error, TimeoutError):
            return cls(StorageFailure.TIMEOUT)
        return cls()
