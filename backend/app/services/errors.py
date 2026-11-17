"""Domain errors shared by server information and health checks."""


class UnknownServer(LookupError):
    """The requested ID is not registered with this application."""
