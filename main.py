"""Flask routes, security headers, structured request logging, and staff session auth."""

from __future__ import annotations

import json
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash, generate_password_hash

from ai import HONEST_ERROR_MESSAGE, AIAnalysisError, generate_civic_brief
from logic import (
    build_session_snapshot,
    compute_delta,
    parse_and_analyse_table,
    verify_citations,
)
from validation import (
    MAX_TABLE_CHARS,
    VALID_LANGUAGES,
    VALID_READING_LEVELS,
    VALID_ROLES,
    validate_analysis_input,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB cap
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

# Demo staff credentials for the internal briefing note (shown on the sign-in panel and README)
STAFF_DEMO_USERNAME = "ravi.ward31"
STAFF_DEMO_PASSWORD_DISPLAY = "bhopal-clean-air"
STAFF_PASSWORD_HASH = generate_password_hash(STAFF_DEMO_PASSWORD_DISPLAY)

# Rate limit: 20 requests per minute per IP on AI routes
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW_SEC = 60.0
_ip_requests: dict[str, deque[float]] = defaultdict(deque)

SAMPLE_DATA_PATH = Path(__file__).parent / "sample_data.json"


def _load_sample_data() -> dict[str, Any]:
    """Load example inputs and CPCB reference data from sample_data.json."""
    with SAMPLE_DATA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _check_rate_limit(ip: str) -> bool:
    """Return True if the IP is within the 20 req/min limit."""
    now = time.monotonic()
    bucket = _ip_requests[ip]
    while bucket and (now - bucket[0]) > RATE_LIMIT_WINDOW_SEC:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX:
        return False
    bucket.append(now)
    return True


def _client_ip() -> str:
    """Extract client IP safely behind Cloud Run proxy."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


@app.before_request
def _start_timer() -> None:
    request.environ["_start_t"] = time.monotonic()


@app.after_request
def _apply_headers_and_log(response: Response) -> Response:
    """Attach required security headers and emit one structured JSON log line per request."""
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "script-src 'self'; "
        "img-src 'self' data:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"

    start_t = request.environ.get("_start_t", time.monotonic())
    duration_ms = round((time.monotonic() - start_t) * 1000, 2)
    ai_meta = request.environ.get("_ai_meta", {})
    log_entry = {
        "severity": "INFO" if response.status_code < 400 else "WARNING",
        "route": request.path,
        "method": request.method,
        "status": response.status_code,
        "latency_ms": duration_ms,
        "model": ai_meta.get("model"),
        "cache_hit": ai_meta.get("cache_hit", False),
        "fallback_used": ai_meta.get("fallback_used", False),
    }
    print(json.dumps(log_entry), flush=True)
    return response


@app.errorhandler(RequestEntityTooLarge)
def _handle_too_large(_err: RequestEntityTooLarge) -> tuple[Response, int]:
    msg = "Uploaded file or request exceeds the 64 KB limit. Please upload a smaller CSV snippet."
    if request.accept_mimetypes.best == "application/json" or request.is_json:
        return jsonify({"ok": False, "error": msg}), 413
    return _render_workspace(general_error=msg), 413


def _render_workspace(
    *,
    form_values: dict[str, str] | None = None,
    field_errors: dict[str, str] | None = None,
    general_error: str | None = None,
    result: dict[str, Any] | None = None,
    login_error: str | None = None,
) -> str:
    """Render the main two-pane workspace template with current state."""
    samples = _load_sample_data()
    defaults = {
        "raw_table": "",
        "role": "ward_officer",
        "language": "en",
        "reading_level": "simple",
    }
    if form_values:
        defaults.update(form_values)

    return render_template(
        "index.html",
        examples=samples.get("examples", []),
        cpcb_categories=samples.get("cpcb_reference", {}).get("categories", []),
        roles=VALID_ROLES,
        languages=VALID_LANGUAGES,
        reading_levels=VALID_READING_LEVELS,
        max_table_chars=MAX_TABLE_CHARS,
        form=defaults,
        field_errors=field_errors or {},
        general_error=general_error,
        result=result,
        is_staff=bool(session.get("is_staff")),
        staff_demo_user=STAFF_DEMO_USERNAME,
        staff_demo_pass=STAFF_DEMO_PASSWORD_DISPLAY,
        login_error=login_error,
        has_previous_brief=bool(session.get("previous_brief")),
    )


@app.get("/health")
def health() -> tuple[Response, int]:
    """Cloud Run health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.get("/")
def index() -> str:
    """Render the empty workspace with example chips."""
    return _render_workspace()


@app.get("/samples/<sample_id>")
def get_sample(sample_id: str) -> tuple[Response, int]:
    """Return an example input dataset by ID for one-tap loading."""
    samples = _load_sample_data()
    for item in samples.get("examples", []):
        if item.get("id") == sample_id:
            return jsonify({"ok": True, "sample": item}), 200
    return jsonify({"ok": False, "error": "Example not found."}), 404


@app.post("/analyse")
def analyse() -> tuple[str | Response, int] | str:
    """Validate input, clean data, compare with previous session brief, and run Gemini."""
    if not _check_rate_limit(_client_ip()):
        msg = "Too many requests from this address. Please wait a minute and try again."
        return _render_workspace(general_error=msg), 429

    raw_table = request.form.get("raw_table", "")
    uploaded = request.files.get("csv_file")
    if uploaded and uploaded.filename and not raw_table.strip():
        try:
            raw_table = uploaded.read(64 * 1024).decode("utf-8-sig", errors="replace")
        except (OSError, UnicodeError):
            return _render_workspace(
                field_errors={"raw_table": "Could not read the uploaded CSV file as text."}
            ), 400

    cleaned_inputs, field_errors = validate_analysis_input(
        raw_table=raw_table,
        role=request.form.get("role", "ward_officer"),
        language=request.form.get("language", "en"),
        reading_level=request.form.get("reading_level", "simple"),
    )

    if field_errors:
        return _render_workspace(form_values=cleaned_inputs, field_errors=field_errors), 400

    try:
        parsed = parse_and_analyse_table(cleaned_inputs["raw_table"])
    except ValueError as exc:
        return _render_workspace(
            form_values=cleaned_inputs,
            field_errors={"raw_table": str(exc)},
        ), 400

    previous_brief = session.get("previous_brief")
    delta = compute_delta(parsed["stations"], previous_brief)

    try:
        ai_out = generate_civic_brief(
            parsed=parsed,
            delta=delta,
            role=cleaned_inputs["role"],
            language=cleaned_inputs["language"],
            reading_level=cleaned_inputs["reading_level"],
        )
        if isinstance(ai_out, tuple) and len(ai_out) == 2:
            raw_ai, ai_meta = ai_out
            request.environ["_ai_meta"] = ai_meta
        else:
            raw_ai = ai_out
        verified_ai = verify_citations(raw_ai, parsed)
        if not verified_ai.get("hotspots") or not verified_ai.get("actions"):
            raise AIAnalysisError(HONEST_ERROR_MESSAGE)
    except AIAnalysisError as exc:
        return _render_workspace(
            form_values=cleaned_inputs,
            general_error=str(exc) or HONEST_ERROR_MESSAGE,
        ), 503
    except (RuntimeError, ValueError, KeyError, TypeError):
        return _render_workspace(
            form_values=cleaned_inputs,
            general_error=HONEST_ERROR_MESSAGE,
        ), 503

    now_label = datetime.now(UTC).strftime("%d %b %Y %H:%M UTC")
    session["previous_brief"] = build_session_snapshot(parsed, now_label)

    result_bundle = {
        "generated_at": now_label,
        "role": cleaned_inputs["role"],
        "role_label": VALID_ROLES[cleaned_inputs["role"]],
        "language": cleaned_inputs["language"],
        "language_label": VALID_LANGUAGES[cleaned_inputs["language"]],
        "reading_level": cleaned_inputs["reading_level"],
        "reading_level_label": VALID_READING_LEVELS[cleaned_inputs["reading_level"]],
        "parsed": parsed,
        "delta": delta,
        "ai": verified_ai,
    }

    return _render_workspace(form_values=cleaned_inputs, result=result_bundle)


@app.post("/staff-login")
def staff_login() -> Response:
    """Verify staff credentials with werkzeug.security hash for the internal note."""
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if username == STAFF_DEMO_USERNAME and check_password_hash(STAFF_PASSWORD_HASH, password):
        session["is_staff"] = True
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": True, "is_staff": True})
        return redirect(url_for("index"))

    err_msg = "Invalid staff username or password. Use the demo credentials shown alongside the form."
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": False, "error": err_msg}), 401
    return Response(_render_workspace(login_error=err_msg), status=401)


@app.post("/staff-logout")
def staff_logout() -> Response:
    """Sign out of staff mode."""
    session.pop("is_staff", None)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "is_staff": False})
    return redirect(url_for("index"))
