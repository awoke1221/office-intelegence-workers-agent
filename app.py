"""Compatibility entrypoints for both legacy WSGI and modern ASGI hosting."""

from __future__ import annotations

import importlib
import json
import os
from typing import Any, Awaitable, Callable, Dict, Optional

from a2wsgi import ASGIMiddleware


class LazyApplication:
	"""Keep health checks lightweight and load the full API on demand."""

	def __init__(self) -> None:
		self._application: Optional[Callable[..., Awaitable[Any]]] = None

	async def __call__(self, scope: Dict[str, Any], receive: Callable[..., Awaitable[Any]], send: Callable[..., Awaitable[Any]]) -> None:
		if scope["type"] == "lifespan":
			await self._handle_lifespan(receive, send)
			return

		path = scope.get("path", "")
		if isinstance(path, bytes):
			path = path.decode("utf-8", errors="replace")

		if scope["type"] == "http" and path in ("/health", "/health/live", "/health/ready"):
			checks = {
				"shared_secret": bool(os.environ.get("OFFICE_INTELLIGENCE_SHARED_SECRET")),
				"allowed_origins": bool(os.environ.get("OFFICE_INTELLIGENCE_ALLOWED_ORIGINS")),
				"llm_provider": os.environ.get("LLM_PROVIDER", "deepseek").lower() != "mock",
			}
			ready = all(checks.values())
			payload = {"status": "ready" if ready else "not_ready", "service": "office-intelligence", "check": "readiness", "checks": checks}
			if path != "/health/ready":
				payload = {"status": "ok", "service": "office-intelligence", "check": "liveness"}
			body = json.dumps(payload).encode("utf-8")
			await send({
				"type": "http.response.start",
				"status": 200 if path != "/health/ready" or ready else 503,
				"headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))],
			})
			await send({"type": "http.response.body", "body": body})
			return

		if self._application is None:
			self._application = importlib.import_module("backend_api").app
		await self._application(scope, receive, send)

	async def _handle_lifespan(self, receive: Callable[..., Awaitable[Any]], send: Callable[..., Awaitable[Any]]) -> None:
		while True:
			message = await receive()
			if message["type"] == "lifespan.startup":
				await send({"type": "lifespan.startup.complete"})
			elif message["type"] == "lifespan.shutdown":
				await send({"type": "lifespan.shutdown.complete"})
				return


asgi_app = LazyApplication()
_backend_wsgi = ASGIMiddleware(asgi_app)


def app(environ: Dict[str, Any], start_response: Callable[..., Any]):
	"""Serve Render's legacy synchronous probes without starting the backend."""
	path = environ.get("PATH_INFO", "/")
	if path in ("/", "/health"):
		body = json.dumps({"status": "ok"}).encode("utf-8")
		start_response("200 OK", [
			("Content-Type", "application/json"),
			("Content-Length", str(len(body))),
		])
		return [body]
	return _backend_wsgi(environ, start_response)

__all__ = ["app", "asgi_app"]
