"""Gzip compression for text responses, using only the standard library."""

from __future__ import annotations

import gzip

from flask import Flask, Response, request

COMPRESSIBLE_TYPES = frozenset(
    {"text/html", "text/css", "text/javascript", "application/javascript", "application/json"}
)
MIN_SIZE_BYTES = 500
GZIP_LEVEL = 6


def gzip_response(response: Response) -> Response:
    """Gzip a successful text response when the client accepts gzip; leave anything else untouched."""
    if (
        "gzip" not in request.headers.get("Accept-Encoding", "").lower()
        or response.status_code != 200
        or response.mimetype not in COMPRESSIBLE_TYPES
        or "Content-Encoding" in response.headers
    ):
        return response
    response.direct_passthrough = False  # static files are streamed; read them so they can be compressed
    data = response.get_data()
    if len(data) < MIN_SIZE_BYTES:
        return response
    response.set_data(gzip.compress(data, compresslevel=GZIP_LEVEL))
    response.headers["Content-Encoding"] = "gzip"
    response.vary.add("Accept-Encoding")
    etag, _ = response.get_etag()
    if etag:
        response.set_etag(f"{etag}-gzip", weak=True)
    return response


def init_compression(app: Flask) -> None:
    """Register gzip compression on every response of the app."""
    app.after_request(gzip_response)
