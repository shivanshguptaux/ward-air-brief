"""Input validation for the Bhopal Air Quality Civic Intelligence workspace."""

from __future__ import annotations

from typing import Any

MAX_TABLE_CHARS: int = 2000

VALID_ROLES: dict[str, str] = {
    "ward_officer": "Ward officer",
    "housing_society": "Housing society",
    "school": "School principal",
}

VALID_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
}

VALID_READING_LEVELS: dict[str, str] = {
    "simple": "Simple (everyday words, no jargon)",
    "standard": "Standard (civic briefing)",
}


def validate_analysis_input(raw_table: Any, role: Any, language: Any, reading_level: Any) -> tuple[dict[str, str], dict[str, str]]:
    """Validate user inputs before parsing or calling Gemini. Returns (cleaned_inputs, field_errors)."""
    errors: dict[str, str] = {}
    raw_text = raw_table.strip() if isinstance(raw_table, str) else ""

    if not raw_text:
        errors["raw_table"] = "Paste an air quality table, upload a CSV file, or choose an Example sheet."
    elif len(raw_text) > MAX_TABLE_CHARS:
        errors["raw_table"] = (
            f"Table is {len(raw_text)} characters. Please keep pasted or uploaded tables "
            f"under {MAX_TABLE_CHARS} characters."
        )
    elif "\n" not in raw_text:
        errors["raw_table"] = "Include a header row and at least one data row."

    role_str = str(role or "").strip()
    if role_str not in VALID_ROLES:
        errors["role"] = "Choose who is asking (Ward officer, Housing society, or School)."

    lang_str = str(language or "").strip()
    if lang_str not in VALID_LANGUAGES:
        errors["language"] = "Choose a valid advisory language (English or Hindi)."

    level_str = str(reading_level or "").strip()
    if level_str not in VALID_READING_LEVELS:
        errors["reading_level"] = "Choose a reading level (Simple or Standard)."

    cleaned = {
        "raw_table": raw_text,
        "role": role_str if role_str in VALID_ROLES else "ward_officer",
        "language": lang_str if lang_str in VALID_LANGUAGES else "en",
        "reading_level": level_str if level_str in VALID_READING_LEVELS else "simple",
    }
    return cleaned, errors
