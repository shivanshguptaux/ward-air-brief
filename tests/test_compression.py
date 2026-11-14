"""Tests for compression.py: gzip on text responses, nothing else touched."""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

import main
from tests.conftest import SIMPLE_TABLE

GZIP = {"Accept-Encoding": "gzip, deflate, br"}
STATIC = Path(main.__file__).parent / "static"


def test_page_is_gzipped_when_the_browser_accepts_it(client) -> None:
    response = client.get("/", headers=GZIP)
    assert response.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in response.headers["Vary"]
    body = response.get_data()
    assert int(response.headers["Content-Length"]) == len(body)
    page = gzip.decompress(body).decode("utf-8")
    assert "Your brief will appear here" in page
    assert len(body) < len(page.encode("utf-8")) / 2


def test_page_is_plain_without_accept_encoding(client) -> None:
    response = client.get("/")
    assert "Content-Encoding" not in response.headers
    assert "Your brief will appear here" in response.get_data(as_text=True)


@pytest.mark.parametrize("name", ["styles.css", "app.js"])
def test_static_text_files_are_gzipped_intact(client, name: str) -> None:
    response = client.get(f"/static/{name}", headers=GZIP)
    assert response.status_code == 200
    assert response.headers["Content-Encoding"] == "gzip"
    assert gzip.decompress(response.get_data()) == (STATIC / name).read_bytes()
    assert response.headers["Cache-Control"] == "public, max-age=3600"
    assert response.headers["ETag"].startswith('W/"')
    response.close()


def test_small_json_is_left_alone(client) -> None:
    response = client.get("/health", headers=GZIP)
    assert "Content-Encoding" not in response.headers
    assert response.get_json() == {"status": "ok"}


def test_error_pages_are_left_alone(client) -> None:
    response = client.get("/does-not-exist", headers=GZIP)
    assert response.status_code == 404
    assert "Content-Encoding" not in response.headers


def test_non_text_files_are_left_alone(client) -> None:
    response = client.get("/static/icon-512.svg", headers=GZIP)
    assert "Content-Encoding" not in response.headers
    response.close()


def test_security_headers_survive_compression(client) -> None:
    response = client.get("/", headers=GZIP)
    assert response.headers["Content-Encoding"] == "gzip"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")


def test_analysis_result_is_gzipped(client, fake_gemini) -> None:
    fake_gemini()
    data = {"raw_table": SIMPLE_TABLE, "role": "ward_officer", "language": "en", "reading_level": "simple"}
    response = client.post("/analyse", data=data, headers=GZIP)
    assert response.status_code == 200
    assert "TT Nagar is the hotspot" in gzip.decompress(response.get_data()).decode("utf-8")
