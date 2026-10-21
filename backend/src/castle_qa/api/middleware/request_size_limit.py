import json
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Protects the server from disk and memory exhaustion by rejecting oversized request bodies
    before Starlette spools them to temporary disk storage.
    """

    def __init__(self, app, max_request_size_bytes: int = 210 * 1024 * 1024):
        super().__init__(app)
        self.max_request_size_bytes = max_request_size_bytes
        self.max_mb = max_request_size_bytes // (1024 * 1024)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check Content-Length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length_int = int(content_length)
                if length_int < 0:
                    return Response(
                        status_code=400,
                        content=json.dumps({"detail": "Invalid Content-Length header (negative value)."}),
                        media_type="application/json",
                    )
                if length_int > self.max_request_size_bytes:
                    logger.warning(
                        "Rejecting request to %s: Content-Length %d exceeds limit of %d bytes",
                        request.url.path,
                        length_int,
                        self.max_request_size_bytes,
                    )
                    return Response(
                        status_code=413,
                        content=json.dumps(
                            {
                                "detail": f"Request payload too large ({length_int // (1024*1024)} MB). "
                                f"Maximum allowed request size is {self.max_mb} MB."
                            }
                        ),
                        media_type="application/json",
                    )
            except ValueError:
                pass

        # For chunked or streaming uploads where Content-Length may be absent,
        # count bytes dynamically in the receive channel
        bytes_received = 0
        original_receive = request._receive

        async def limited_receive():
            nonlocal bytes_received
            message = await original_receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > self.max_request_size_bytes:
                    logger.warning(
                        "Rejecting chunked request to %s: exceeded limit of %d bytes",
                        request.url.path,
                        self.max_request_size_bytes,
                    )
                    # Raising ValueError here will cause Starlette/FastAPI to terminate the connection
                    raise ValueError(
                        f"Request payload exceeded maximum allowed limit of {self.max_mb} MB."
                    )
            return message

        request._receive = limited_receive

        try:
            return await call_next(request)
        except ValueError as e:
            if "Request payload exceeded maximum allowed limit" in str(e):
                return Response(
                    status_code=413,
                    content=json.dumps({"detail": str(e)}),
                    media_type="application/json",
                )
            raise

