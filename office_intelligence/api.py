"""ASGI application entrypoint for local and hosted deployments."""

from app import asgi_app as app

__all__ = ["app"]
