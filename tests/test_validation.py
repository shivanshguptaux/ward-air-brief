"""Tests for validation.py: required fields, length limit, allowlists and wrong types."""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import SIMPLE_TABLE
from validation import MAX_TABLE_CHARS, validate_analysis_input


def _validate(**overrides: Any) -> tuple[dict[str, str], dict[str, str]]:
    fields: dict[str, Any] = {
        "raw_table": SIMPLE_TABLE,
        "role": "ward_officer",
        "language": "en",
        "reading_level": "simple",
    }
    fields.update(overrides)
    return validate_analysis_input(**fields)


def test_valid_input_passes_and_is_trimmed() -> None:
    cleaned, errors = _validate(raw_table=f"  {SIMPLE_TABLE}  ", role=" school ")
    assert errors == {}
    assert cleaned["raw_table"] == SIMPLE_TABLE.strip()
    assert cleaned["role"] == "school"


@pytest.mark.parametrize("role", ["ward_officer", "housing_society", "school"])
def test_every_role_is_accepted(role: str) -> None:
    assert _validate(role=role)[1] == {}


@pytest.mark.parametrize(("language", "level"), [("en", "simple"), ("hi", "standard")])
def test_languages_and_levels_are_accepted(language: str, level: str) -> None:
    assert _validate(language=language, reading_level=level)[1] == {}


@pytest.mark.parametrize("table", ["", "   ", None])
def test_missing_table_is_an_error(table: Any) -> None:
    _, errors = _validate(raw_table=table)
    assert "raw_table" in errors


def test_table_needs_a_data_row() -> None:
    _, errors = _validate(raw_table="Station,PM2.5")
    assert "header row" in errors["raw_table"]


def test_table_at_the_limit_is_accepted() -> None:
    table = ("Station,PM2.5\n" + "A,40\n" * 1000)[:MAX_TABLE_CHARS]
    assert len(table) == MAX_TABLE_CHARS
    assert "raw_table" not in _validate(raw_table=table)[1]


def test_table_over_the_limit_is_rejected() -> None:
    table = "Station,PM2.5\n" + "A,40\n" * 1000
    _, errors = _validate(raw_table=table)
    assert str(MAX_TABLE_CHARS) in errors["raw_table"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("role", "mayor"),
        ("role", ""),
        ("role", None),
        ("language", "fr"),
        ("language", 7),
        ("reading_level", "expert"),
        ("reading_level", ["simple"]),
    ],
)
def test_values_outside_the_allowlist_are_rejected(field: str, value: Any) -> None:
    cleaned, errors = _validate(**{field: value})
    assert field in errors
    # Cleaned values always fall back to a safe default
    assert cleaned["role"] in {"ward_officer", "housing_society", "school"}
    assert cleaned["language"] in {"en", "hi"}
    assert cleaned["reading_level"] in {"simple", "standard"}


def test_wrong_type_table_is_rejected_not_crashing() -> None:
    _, errors = _validate(raw_table=12345)
    assert "raw_table" in errors


def test_all_errors_are_reported_together() -> None:
    _, errors = validate_analysis_input("", "x", "y", "z")
    assert set(errors) == {"raw_table", "role", "language", "reading_level"}
