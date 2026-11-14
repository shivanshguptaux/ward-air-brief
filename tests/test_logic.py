"""Tests for logic.py: parsing, units, flags, CPCB AQI, deltas, snapshots and citation checks."""

from __future__ import annotations

from decimal import Decimal

import pytest

import logic
from tests.conftest import SIMPLE_TABLE

# ---------- aqi_category_for_index ----------


@pytest.mark.parametrize(
    ("aqi", "category", "token"),
    [
        (None, "Unverified", "unverified"),
        (0, "Good", "good"),
        (50, "Good", "good"),
        (51, "Satisfactory", "satisfactory"),
        (100, "Satisfactory", "satisfactory"),
        (101, "Moderate", "moderate"),
        (200, "Moderate", "moderate"),
        (201, "Poor", "poor"),
        (300, "Poor", "poor"),
        (301, "Very Poor", "very-poor"),
        (400, "Very Poor", "very-poor"),
        (401, "Severe", "severe"),
        (10**9, "Severe", "severe"),
    ],
)
def test_aqi_category_boundaries(aqi: int | None, category: str, token: str) -> None:
    assert logic.aqi_category_for_index(aqi) == {"category": category, "token": token}


# ---------- _sub_index and compute_row_aqi ----------


@pytest.mark.parametrize(
    ("pm25", "expected"),
    [("0", 0), ("30", 50), ("60", 100), ("90", 200), ("120", 300), ("250", 400), ("999", 500)],
)
def test_pm25_breakpoints_match_cpcb(pm25: str, expected: int) -> None:
    assert logic.compute_row_aqi(Decimal(pm25), None) == expected


def test_sub_index_caps_very_large_values_at_500() -> None:
    assert logic._sub_index(Decimal(100000), logic.PM25_BREAKPOINTS) == 500


def test_sub_index_handles_zero_width_band() -> None:
    assert logic._sub_index(Decimal(5), [(Decimal(5), Decimal(5), 7, 9)]) == 9


def test_row_aqi_is_worst_of_pm25_and_pm10() -> None:
    # PM2.5 30 -> 50, PM10 350 -> 300: the worse one wins
    assert logic.compute_row_aqi(Decimal(30), Decimal(350)) == 300


def test_row_aqi_with_pm10_only() -> None:
    assert logic.compute_row_aqi(None, Decimal(100)) == 100


def test_row_aqi_with_no_readings_is_none() -> None:
    assert logic.compute_row_aqi(None, None) is None


def test_row_aqi_rejects_wrong_type() -> None:
    with pytest.raises(TypeError):
        logic.compute_row_aqi("30", None)  # type: ignore[arg-type]


# ---------- _normalise_header_key ----------


@pytest.mark.parametrize(
    ("header", "key"),
    [
        ("Station_Name", "station"),
        ("Location", "station"),
        ("Ward", "station"),
        ("Date_Time", "timestamp"),
        ("Time", "timestamp"),
        ("PM2.5", "pm25"),
        ("PM2_5", "pm25"),
        ("PM10", "pm10"),
        ("Unit", "unit"),
        ("Remarks", "notes"),
        ("Notes", "notes"),
        ("  Humidity  ", "humidity"),
    ],
)
def test_header_aliases(header: str, key: str) -> None:
    assert logic._normalise_header_key(header) == key


# ---------- _normalise_timestamp ----------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-11-11 08:00", "11 Nov 08:00"),
        ("2026-11-11 08:00:00", "11 Nov 08:00"),
        ("11/11/2026 18:00", "11 Nov 18:00"),
        ("11-11-2026 18:00", "11 Nov 18:00"),
        ("", "Unspecified time"),
        ("   ", "Unspecified time"),
        ("Monday morning", "Monday morning"),
    ],
)
def test_timestamp_normalisation(raw: str, expected: str) -> None:
    assert logic._normalise_timestamp(raw) == expected


# ---------- _parse_concentration ----------


def _parse(raw: str, unit: str = "ug/m3") -> tuple:
    return logic._parse_concentration(raw, unit, "PM2.5", 3, "TT Nagar")


@pytest.mark.parametrize("raw", ["", "  ", "NA", "n/a", "null", "-", "--", "ERR", "nan"])
def test_missing_values_are_flagged(raw: str) -> None:
    value, flags, converted = _parse(raw)
    assert value is None and not converted
    assert flags[0]["type"] == "missing"
    assert flags[0]["row_id"] == 3


def test_text_value_is_unparseable() -> None:
    value, flags, _ = _parse("high")
    assert value is None
    assert flags[0]["type"] == "unparseable"


def test_mg_per_m3_is_converted_to_ug() -> None:
    value, flags, converted = _parse("0.21", unit="mg/m3")
    assert value == Decimal("210.0")
    assert converted is True
    assert flags[0]["type"] == "unit_converted"


def test_inline_unit_overrides_row_unit() -> None:
    value, _, converted = _parse("0.192 mg/m3", unit="ug/m3")
    assert value == Decimal("192.0") and converted


def test_unknown_unit_is_excluded() -> None:
    value, flags, _ = _parse("40", unit="ppb")
    assert value is None
    assert flags[0]["type"] == "wrong_unit"


def test_negative_reading_is_excluded() -> None:
    value, flags, _ = _parse("-5")
    assert value is None
    assert flags[0]["type"] == "negative"


def test_reading_above_999_is_a_spike() -> None:
    value, flags, _ = _parse("1240")
    assert value is None
    assert flags[0]["type"] == "impossible_spike"


def test_exponent_notation_above_cap_is_a_spike() -> None:
    value, flags, _ = _parse("1e4")
    assert value is None and flags[0]["type"] == "impossible_spike"


@pytest.mark.parametrize(("raw", "expected"), [("0", Decimal("0.0")), ("999", Decimal("999.0")), ("12.345", Decimal("12.3"))])
def test_valid_readings_are_kept_and_rounded(raw: str, expected: Decimal) -> None:
    value, flags, _ = _parse(raw)
    assert value == expected
    assert flags == []


@pytest.mark.parametrize("raw", ["-nan", "sNaN"])
def test_nan_variants_are_flagged_not_crashing(raw: str) -> None:
    value, flags, _ = _parse(raw)
    assert value is None and flags


# ---------- parse_and_analyse_table ----------


@pytest.mark.parametrize(
    "table",
    ["", "Station,PM2.5", "\n\n", "Station,PM2.5\n,,\n"],
)
def test_table_without_data_rows_is_rejected(table: str) -> None:
    with pytest.raises(ValueError):
        logic.parse_and_analyse_table(table)


def test_table_without_pm_column_is_rejected() -> None:
    with pytest.raises(ValueError, match="PM2.5 or PM10"):
        logic.parse_and_analyse_table("Station,Humidity\nTT Nagar,40\n")


def test_table_rejects_wrong_type() -> None:
    with pytest.raises(AttributeError):
        logic.parse_and_analyse_table(None)  # type: ignore[arg-type]


def test_simple_comma_table() -> None:
    parsed = logic.parse_and_analyse_table(SIMPLE_TABLE)
    assert [r["row_id"] for r in parsed["rows"]] == [1, 2, 3]
    assert parsed["rows"][0]["station"] == "TT Nagar"
    assert parsed["rows"][0]["timestamp"] == "11 Nov 08:00"
    assert parsed["trust"]["flagged_rows_count"] == 0
    assert parsed["trust"]["overall_confidence"] == "high"


@pytest.mark.parametrize("sep", [";", "\t", "|"])
def test_other_delimiters_are_detected(sep: str) -> None:
    parsed = logic.parse_and_analyse_table(SIMPLE_TABLE.replace(",", sep))
    assert len(parsed["rows"]) == 3
    assert parsed["rows"][2]["pm25"] == 168.0


def test_messy_example_sheet_flags(week2_table: str) -> None:
    parsed = logic.parse_and_analyse_table(week2_table)
    trust = parsed["trust"]
    assert trust["total_rows"] == 13
    assert trust["flagged_rows_count"] == 6
    assert trust["unit_converted_count"] == 1
    types = {f["type"] for f in parsed["flags"]}
    assert {"missing", "impossible_spike", "flatlined_sensor", "unit_converted"} <= types
    # The 1240 spike is left out of averages, not silently kept
    row7 = parsed["rows"][6]
    assert row7["pm25"] is None and row7["has_error_flag"]


def test_stations_are_sorted_worst_first(week2_table: str) -> None:
    stations = logic.parse_and_analyse_table(week2_table)["stations"]
    aqis = [s["aqi"] for s in stations]
    assert aqis == sorted(aqis, reverse=True)
    assert stations[0]["station"] == "TT Nagar"


def test_four_identical_readings_flag_a_stuck_sensor() -> None:
    rows = "\n".join(f"Kolar,2026-11-11 0{h}:00,68,132,ug/m3" for h in range(4))
    parsed = logic.parse_and_analyse_table("Station,Time,PM2.5,PM10,Unit\n" + rows)
    assert all(r["has_error_flag"] for r in parsed["rows"])
    flat = [f for f in parsed["flags"] if f["type"] == "flatlined_sensor"]
    assert flat and flat[0]["row_ids"] == [1, 2, 3, 4]


def test_three_identical_readings_are_not_flagged() -> None:
    rows = "\n".join(f"Kolar,2026-11-11 0{h}:00,68,132,ug/m3" for h in range(3))
    parsed = logic.parse_and_analyse_table("Station,Time,PM2.5,PM10,Unit\n" + rows)
    assert not any(r["has_error_flag"] for r in parsed["rows"])


def test_missing_station_header_uses_first_column() -> None:
    parsed = logic.parse_and_analyse_table("Site code,PM2.5\nA1,40\n")
    assert parsed["rows"][0]["station"] == "A1"


def test_blank_station_cell_gets_a_placeholder() -> None:
    parsed = logic.parse_and_analyse_table("Station,PM2.5\n,40\n")
    assert parsed["rows"][0]["station"] == "Station 1"


def test_short_rows_are_padded_as_missing() -> None:
    parsed = logic.parse_and_analyse_table("Station,PM2.5,PM10\nTT Nagar,40\n")
    assert parsed["rows"][0]["pm10"] is None
    assert any(f["type"] == "missing" for f in parsed["flags"])


def test_very_large_table_is_handled() -> None:
    body = "\n".join(f"S{i % 5},2026-11-11 08:00,{40 + i % 50},{80 + i % 40},ug/m3" for i in range(2000))
    parsed = logic.parse_and_analyse_table("Station,Time,PM2.5,PM10,Unit\n" + body)
    assert parsed["trust"]["total_rows"] == 2000
    assert len(parsed["stations"]) == 5


def test_station_with_only_bad_readings_is_low_confidence_and_last() -> None:
    table = "Station,PM2.5\nGood St,40\nBroken St,NA\nBroken St,-3\n"
    stations = logic.parse_and_analyse_table(table)["stations"]
    assert stations[-1]["station"] == "Broken St"
    assert stations[-1]["aqi"] is None
    assert stations[-1]["confidence"] == "low"


# ---------- compute_delta ----------


def _station(name: str, pm: float | None, aqi: int | None = 300) -> dict:
    return {"station": name, "mean_pm25": pm, "aqi": aqi, "aqi_category": "Poor"}


@pytest.mark.parametrize("previous", [None, {}, {"stations": []}])
def test_first_brief_is_a_baseline(previous: dict | None) -> None:
    delta = logic.compute_delta([_station("TT Nagar", 200)], previous)
    assert delta["has_previous"] is False
    assert delta["station_deltas"][0]["direction"] == "new"


def test_delta_directions() -> None:
    previous = {
        "timestamp": "07 Nov",
        "stations": [_station("TT Nagar", 100), _station("Bhanpur", 200), _station("Kolar", 50), _station("Zero", 0)],
    }
    current = [_station("tt nagar ", 140), _station("Bhanpur", 150), _station("Kolar", 51), _station("Zero", 10), _station("New", 30)]
    delta = logic.compute_delta(current, previous)
    by_name = {d["station"].strip().lower(): d for d in delta["station_deltas"]}
    assert by_name["tt nagar"]["direction"] == "worse" and by_name["tt nagar"]["pct_change"] == 40
    assert by_name["bhanpur"]["direction"] == "better" and by_name["bhanpur"]["pct_change"] == -25
    assert by_name["kolar"]["direction"] == "same"
    assert by_name["zero"]["direction"] == "new"  # previous zero cannot give a percentage
    assert by_name["new"]["direction"] == "new"
    assert delta["has_previous"] is True
    assert delta["previous_timestamp"] == "07 Nov"
    assert "worse" in delta["summary_line"]


def test_delta_with_missing_current_value_is_new() -> None:
    delta = logic.compute_delta([_station("A", None)], {"stations": [_station("A", 100)]})
    assert delta["station_deltas"][0]["direction"] == "new"


# ---------- build_session_snapshot ----------


def test_session_snapshot_is_compact(week2_table: str) -> None:
    parsed = logic.parse_and_analyse_table(week2_table)
    snap = logic.build_session_snapshot(parsed, "14 Nov 2026 07:00 UTC")
    assert snap["timestamp"] == "14 Nov 2026 07:00 UTC"
    assert set(snap["stations"][0]) == {"station", "mean_pm25", "aqi", "aqi_category"}
    assert "rows" not in snap


def test_session_snapshot_of_empty_parse() -> None:
    assert logic.build_session_snapshot({}, "t") == {"timestamp": "t", "stations": []}


# ---------- verify_citations ----------


def _parsed_two_stations() -> dict:
    return logic.parse_and_analyse_table(
        "Station,PM2.5\nTT Nagar,200\nTT Nagar,210\nBhanpur,NA\nBhanpur,1500\n"
    )


def test_unknown_rows_are_removed_and_empty_findings_dropped() -> None:
    parsed = _parsed_two_stations()
    output = {
        "hotspots": [
            {"location": "TT Nagar", "confidence": "high", "row_ids": [1, 99]},
            {"location": "Ghost", "confidence": "high", "row_ids": [42]},
        ],
        "actions": [{"priority": 1, "confidence": "high", "row_ids": [77]}],
    }
    verified = logic.verify_citations(output, parsed)
    assert len(verified["hotspots"]) == 1
    assert verified["hotspots"][0]["row_ids"] == [1]
    assert verified["hotspots"][0]["source_chips"] == ["Row 1 · TT Nagar"]
    assert verified["actions"] == []


def test_findings_on_flagged_rows_become_low_confidence() -> None:
    parsed = _parsed_two_stations()
    output = {
        "hotspots": [{"location": "Bhanpur", "confidence": "high", "row_ids": [4]}],
        "actions": [{"priority": 1, "confidence": "high", "row_ids": [3]}],
    }
    verified = logic.verify_citations(output, parsed)
    assert verified["hotspots"][0]["confidence"] == "low"
    assert verified["actions"][0]["confidence"] == "low"


def test_hotspot_at_low_confidence_station_is_low_even_on_clean_rows() -> None:
    parsed = logic.parse_and_analyse_table("Station,PM2.5\nA,40\nA,NA\nA,NA\n")
    output = {"hotspots": [{"location": "a", "confidence": "high", "row_ids": [1]}], "actions": []}
    assert logic.verify_citations(output, parsed)["hotspots"][0]["confidence"] == "low"


def test_actions_are_sorted_by_priority_and_other_fields_kept() -> None:
    parsed = _parsed_two_stations()
    output = {
        "lead_line": "kept",
        "hotspots": [],
        "actions": [
            {"priority": 3, "confidence": "high", "row_ids": [1]},
            {"priority": 1, "confidence": "high", "row_ids": [2]},
        ],
    }
    verified = logic.verify_citations(output, parsed)
    assert [a["priority"] for a in verified["actions"]] == [1, 3]
    assert verified["lead_line"] == "kept"


def test_empty_ai_output_gives_empty_lists() -> None:
    verified = logic.verify_citations({}, _parsed_two_stations())
    assert verified["hotspots"] == [] and verified["actions"] == []


def test_infinity_is_unparseable_not_a_spike() -> None:
    value, flags, _ = _parse("Infinity")
    assert value is None
    assert flags[0]["type"] == "unparseable"


# ---------- build_whatsapp_share_url ----------

ADVISORY = {
    "headline": "Dusty air near TT Nagar & Bhanpur",
    "general_advice": "Keep windows closed after 6 pm.",
    "children": "Keep children indoors.",
    "older_adults": "Walk after 9 am.",
    "sensitive_groups": "Keep inhalers handy.",
}


def _share_text(url: str) -> str:
    from urllib.parse import parse_qs, urlparse

    parts = urlparse(url)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "wa.me", "/")
    return parse_qs(parts.query)["text"][0]


def test_whatsapp_link_carries_the_whole_english_advisory() -> None:
    text = _share_text(logic.build_whatsapp_share_url(ADVISORY, "en"))
    assert text.startswith("*Air Advisory · Bhopal: Dusty air near TT Nagar & Bhanpur*")
    for value in ADVISORY.values():
        assert value in text
    assert "*Children:*" in text and "*Sensitive groups:*" in text


def test_whatsapp_link_uses_hindi_labels() -> None:
    text = _share_text(logic.build_whatsapp_share_url(ADVISORY, "hi"))
    assert "वायु सलाह · भोपाल" in text
    assert "बच्चों के लिए" in text


def test_whatsapp_link_is_fully_encoded() -> None:
    url = logic.build_whatsapp_share_url(ADVISORY, "en")
    query = url.split("?text=", 1)[1]
    assert " " not in query and "&" not in query and "\n" not in query


def test_whatsapp_link_skips_empty_lines() -> None:
    text = _share_text(logic.build_whatsapp_share_url({"headline": "Only a headline"}, "en"))
    assert "Only a headline" in text
    assert "\n\n\n\n" not in text
