"""Shared fixtures: Flask test client, a fake Gemini client, sample tables and AI payloads.

No test makes a network call. Gemini is replaced by FakeClient via ai._get_client.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

import ai
import main

PRIMARY = "gemini-3.5-flash"
FALLBACK = "gemini-3.5-flash-lite"

SIMPLE_TABLE = (
    "Station,Date_Time,PM2.5,PM10,Unit,Notes\n"
    "TT Nagar,2026-11-11 08:00,192,318,ug/m3,Road digging\n"
    "TT Nagar,2026-11-11 12:00,210,340,ug/m3,Traffic\n"
    "Bhanpur,2026-11-11 08:00,168,275,ug/m3,Landfill\n"
)


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test with an empty AI cache, an empty rate limiter and fixed model names."""
    ai.clear_ai_cache()
    main._ip_requests.clear()
    monkeypatch.setenv("GEMINI_MODEL", PRIMARY)
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", FALLBACK)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture()
def client():
    """Flask test client."""
    main.app.config.update(TESTING=True)
    with main.app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def week2_table() -> str:
    """The messy 'This week' example sheet the demo uses."""
    examples = main._load_sample_data()["examples"]
    return next(e["raw_table"] for e in examples if e["id"] == "week2")


@pytest.fixture()
def week1_table() -> str:
    """The 'Last week' baseline example sheet."""
    examples = main._load_sample_data()["examples"]
    return next(e["raw_table"] for e in examples if e["id"] == "week1")


def make_ai_payload(hotspot_rows: list[int] | None = None, action_rows: list[int] | None = None) -> dict[str, Any]:
    """Build a schema-valid Gemini response citing the given row IDs."""
    hotspot_rows = [1, 2] if hotspot_rows is None else hotspot_rows
    action_rows = [1] if action_rows is None else action_rows
    return {
        "lead_line": "TT Nagar is the hotspot: PM2.5 averages 201 µg/m³, likely construction dust.",
        "trend_summary": "Readings rise through the day at TT Nagar.",
        "hotspots": [
            {
                "location": "TT Nagar",
                "summary": "Highest average PM2.5 in the ward.",
                "likely_cause": "Road digging dust.",
                "confidence": "high",
                "row_ids": hotspot_rows,
            }
        ],
        "actions": [
            {
                "priority": 2,
                "who": "Sanitation squad",
                "what": "Check night waste burning.",
                "by_when": "Tonight",
                "confidence": "high",
                "row_ids": action_rows,
            },
            {
                "priority": 1,
                "who": "Water tanker crew",
                "what": "Sprinkle water on dug roads.",
                "by_when": "Today 16:00",
                "confidence": "high",
                "row_ids": action_rows,
            },
        ],
        "since_last_brief_narrative": "First brief, so this is the baseline.",
        "internal_note": {
            "subject": "Ward 31 air brief",
            "situation_summary": "TT Nagar is worst.",
            "operational_directives": ["Sprinkle water", "Patrol at night"],
            "monitoring_gaps_note": "No gaps.",
        },
        "citizen_advisory": {
            "headline": "Dusty air near TT Nagar tonight",
            "general_advice": "Keep windows closed in the evening.",
            "children": "Keep children indoors after 6 pm.",
            "older_adults": "Walk after 9 am.",
            "sensitive_groups": "Keep inhalers handy.",
        },
    }


class FakeModels:
    """Stands in for client.models; each model name maps to response text or an exception."""

    def __init__(self, behaviours: dict[str, Any]) -> None:
        self.behaviours = behaviours
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, model: str, contents: str, config: Any) -> SimpleNamespace:
        """Record the call, then return the scripted text or raise the scripted error."""
        self.calls.append({"model": model, "contents": contents, "config": config})
        behaviour = self.behaviours.get(model, RuntimeError(f"unexpected model {model}"))
        if isinstance(behaviour, BaseException):
            raise behaviour
        return SimpleNamespace(text=behaviour)


class FakeClient:
    """Minimal google-genai client replacement."""

    def __init__(self, behaviours: dict[str, Any]) -> None:
        self.models = FakeModels(behaviours)


@pytest.fixture()
def fake_gemini(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeClient]:
    """Install a FakeClient and an API key. Pass text or an exception for each model."""

    def install(primary: Any = None, fallback: Any = None, with_key: bool = True) -> FakeClient:
        if primary is None:
            primary = json.dumps(make_ai_payload())
        if fallback is None:
            fallback = RuntimeError("fallback should not be called")
        fake = FakeClient({PRIMARY: primary, FALLBACK: fallback})
        if with_key:
            monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
        monkeypatch.setattr(ai, "_get_client", lambda api_key: fake)
        return fake

    return install
