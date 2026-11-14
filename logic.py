"""Deterministic table parsing, unit normalisation, CPCB AQI calculation, and citation checks."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

# CPCB National Air Quality Index (NAQI) 24-hr breakpoints (in ug/m3)
# Format: (c_low, c_high, i_low, i_high)
PM25_BREAKPOINTS: list[tuple[Decimal, Decimal, int, int]] = [
    (Decimal(0), Decimal(30), 0, 50),
    (Decimal("30.001"), Decimal(60), 51, 100),
    (Decimal("60.001"), Decimal(90), 101, 200),
    (Decimal("90.001"), Decimal(120), 201, 300),
    (Decimal("120.001"), Decimal(250), 301, 400),
    (Decimal("250.001"), Decimal(999), 401, 500),
]

PM10_BREAKPOINTS: list[tuple[Decimal, Decimal, int, int]] = [
    (Decimal(0), Decimal(50), 0, 50),
    (Decimal("50.001"), Decimal(100), 51, 100),
    (Decimal("100.001"), Decimal(250), 101, 200),
    (Decimal("250.001"), Decimal(350), 201, 300),
    (Decimal("350.001"), Decimal(430), 301, 400),
    (Decimal("430.001"), Decimal(999), 401, 500),
]

STATION_ALIASES = {"station", "stationname", "stn", "location", "ward", "site", "area", "monitor"}
TIME_ALIASES = {"datetime", "date", "time", "timestamp", "hour", "recordedat", "period"}
PM25_ALIASES = {"pm25", "pm2.5", "pm2_5", "pm25ugm3", "finepm"}
PM10_ALIASES = {"pm10", "pm_10", "pm10ugm3", "coarsepm"}
UNIT_ALIASES = {"unit", "units", "uom", "scale"}
NOTES_ALIASES = {"notes", "note", "remarks", "remark", "comment", "observation", "status"}

INLINE_VALUE_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*(mg/m3|mg/m³|ug/m3|µg/m3|µg/m³|ppm)?\s*$",
    re.IGNORECASE,
)


def aqi_category_for_index(aqi: int | None) -> dict[str, str]:
    """Return CPCB category label and CSS token for an integer AQI value."""
    if aqi is None:
        return {"category": "Unverified", "token": "unverified"}
    if aqi <= 50:
        return {"category": "Good", "token": "good"}
    if aqi <= 100:
        return {"category": "Satisfactory", "token": "satisfactory"}
    if aqi <= 200:
        return {"category": "Moderate", "token": "moderate"}
    if aqi <= 300:
        return {"category": "Poor", "token": "poor"}
    if aqi <= 400:
        return {"category": "Very Poor", "token": "very-poor"}
    return {"category": "Severe", "token": "severe"}


def _sub_index(value: Decimal, breakpoints: list[tuple[Decimal, Decimal, int, int]]) -> int:
    """Calculate CPCB linear sub-index for a concentration in ug/m3."""
    for c_low, c_high, i_low, i_high in breakpoints:
        if value <= c_high:
            if c_high == c_low:
                return i_high
            ratio = (value - c_low) / (c_high - c_low)
            idx = Decimal(i_low) + ratio * Decimal(i_high - i_low)
            return max(0, min(500, int(idx.quantize(Decimal(1), rounding=ROUND_HALF_UP))))
    return 500


def compute_row_aqi(pm25: Decimal | None, pm10: Decimal | None) -> int | None:
    """Compute CPCB AQI as the worst sub-index of valid PM2.5 and PM10 readings."""
    sub_indices: list[int] = []
    if pm25 is not None:
        sub_indices.append(_sub_index(pm25, PM25_BREAKPOINTS))
    if pm10 is not None:
        sub_indices.append(_sub_index(pm10, PM10_BREAKPOINTS))
    if not sub_indices:
        return None
    return max(sub_indices)


def _normalise_header_key(raw_header: str) -> str:
    """Map messy column headers to canonical keys."""
    cleaned = re.sub(r"[^a-z0-9.]+", "", raw_header.strip().lower())
    if cleaned in STATION_ALIASES or "station" in cleaned or "location" in cleaned or "ward" in cleaned:
        return "station"
    if cleaned in TIME_ALIASES or "date" in cleaned or "time" in cleaned:
        return "timestamp"
    if cleaned in PM25_ALIASES or "2.5" in cleaned or "25" in cleaned:
        return "pm25"
    if cleaned in PM10_ALIASES or "pm10" in cleaned or "10" in cleaned:
        return "pm10"
    if cleaned in UNIT_ALIASES or "unit" in cleaned:
        return "unit"
    if cleaned in NOTES_ALIASES or "note" in cleaned or "remark" in cleaned:
        return "notes"
    return cleaned


def _normalise_timestamp(raw_ts: str) -> str:
    """Normalise common Indian/ISO timestamps where possible, keeping original if custom."""
    text = raw_ts.strip()
    if not text:
        return "Unspecified time"
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y/%m/%d %H:%M",
        "%d %b %Y %H:%M",
    ):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%d %b %H:%M")
        except ValueError:
            continue
    return text


def _parse_concentration(
    raw_val: str,
    row_unit: str,
    metric_label: str,
    row_id: int,
    station: str,
) -> tuple[Decimal | None, list[dict[str, Any]], bool]:
    """Parse and normalise a single PM concentration to ug/m3.

    Returns (valid_ugm3_or_None, flags, converted_from_mg).
    """
    flags: list[dict[str, Any]] = []
    text = (raw_val or "").strip()
    if not text or text.upper() in {"NA", "N/A", "NULL", "NONE", "-", "--", "ERR", "NAN"}:
        flags.append({
            "row_id": row_id,
            "station": station,
            "type": "missing",
            "metric": metric_label,
            "detail": f"Row {row_id} ({station}): {metric_label} reading is missing.",
        })
        return None, flags, False

    inline_unit = ""
    match = INLINE_VALUE_RE.match(text)
    if match:
        num_str = match.group(1)
        inline_unit = (match.group(2) or "").lower()
    else:
        num_str = text

    try:
        val = Decimal(num_str)
        if not val.is_finite():  # NaN, sNaN and Infinity cannot be compared or averaged
            raise InvalidOperation
    except InvalidOperation:
        flags.append({
            "row_id": row_id,
            "station": station,
            "type": "unparseable",
            "metric": metric_label,
            "detail": f"Row {row_id} ({station}): {metric_label} value '{text}' is not a valid number.",
        })
        return None, flags, False

    unit_norm = (inline_unit or row_unit or "ug/m3").strip().lower()
    converted = False
    if unit_norm in {"mg/m3", "mg/m³", "mg"}:
        val = (val * Decimal(1000)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        converted = True
        flags.append({
            "row_id": row_id,
            "station": station,
            "type": "unit_converted",
            "metric": metric_label,
            "detail": f"Row {row_id} ({station}): {metric_label} converted from mg/m³ to {val} µg/m³.",
        })
    elif unit_norm not in {"ug/m3", "µg/m3", "µg/m³", "ug", ""}:
        flags.append({
            "row_id": row_id,
            "station": station,
            "type": "wrong_unit",
            "metric": metric_label,
            "detail": f"Row {row_id} ({station}): Unrecognised unit '{row_unit}' on {metric_label}; excluded from valid average.",
        })
        return None, flags, False

    if val < Decimal(0):
        flags.append({
            "row_id": row_id,
            "station": station,
            "type": "negative",
            "metric": metric_label,
            "detail": f"Row {row_id} ({station}): Negative {metric_label} ({val} µg/m³) flagged as calibration error and excluded.",
        })
        return None, flags, converted

    if val > Decimal(999):
        flags.append({
            "row_id": row_id,
            "station": station,
            "type": "impossible_spike",
            "metric": metric_label,
            "detail": f"Row {row_id} ({station}): {metric_label} reading {val} µg/m³ exceeds CPCB 999 µg/m³ cap; flagged as sensor spike and excluded from average.",
        })
        return None, flags, converted

    return val.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), flags, converted


def parse_and_analyse_table(raw_table: str) -> dict[str, Any]:
    """Parse a messy CSV/TSV/semicolon table using csv.Sniffer and compute deterministic stats."""
    stream = io.StringIO(raw_table.strip())
    sample = raw_table[:1024]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(stream, dialect)
    all_rows = [r for r in reader if any(cell.strip() for cell in r)]
    if len(all_rows) < 2:
        raise ValueError("Table must include a header row and at least one data row.")

    raw_headers = all_rows[0]
    mapped_headers = [_normalise_header_key(h) for h in raw_headers]

    if "station" not in mapped_headers:
        mapped_headers[0] = "station"
    if "pm25" not in mapped_headers and "pm10" not in mapped_headers:
        raise ValueError(
            "Could not find a PM2.5 or PM10 column in the header row. "
            "Please include a column named PM2.5 or PM10."
        )

    cleaned_rows: list[dict[str, Any]] = []
    all_flags: list[dict[str, Any]] = []

    for idx, raw_cells in enumerate(all_rows[1:], start=1):
        row_dict: dict[str, str] = {}
        for col_i, key in enumerate(mapped_headers):
            val = raw_cells[col_i].strip() if col_i < len(raw_cells) else ""
            if key not in row_dict or not row_dict[key]:
                row_dict[key] = val

        station = row_dict.get("station", "").strip() or f"Station {idx}"
        timestamp = _normalise_timestamp(row_dict.get("timestamp", ""))
        raw_unit = row_dict.get("unit", "ug/m3").strip() or "ug/m3"
        notes = row_dict.get("notes", "").strip()

        pm25_val, pm25_flags, conv25 = (None, [], False)
        if "pm25" in mapped_headers:
            pm25_val, pm25_flags, conv25 = _parse_concentration(
                row_dict.get("pm25", ""), raw_unit, "PM2.5", idx, station
            )

        pm10_val, pm10_flags, conv10 = (None, [], False)
        if "pm10" in mapped_headers:
            pm10_val, pm10_flags, conv10 = _parse_concentration(
                row_dict.get("pm10", ""), raw_unit, "PM10", idx, station
            )

        row_flags = pm25_flags + pm10_flags
        all_flags.extend(row_flags)

        severe_flag_types = {
            f["type"] for f in row_flags if f["type"] != "unit_converted"
        }
        row_aqi = compute_row_aqi(pm25_val, pm10_val)
        cat_info = aqi_category_for_index(row_aqi)

        cleaned_rows.append({
            "row_id": idx,
            "station": station,
            "timestamp": timestamp,
            "pm25": float(pm25_val) if pm25_val is not None else None,
            "pm10": float(pm10_val) if pm10_val is not None else None,
            "raw_pm25": row_dict.get("pm25", ""),
            "raw_pm10": row_dict.get("pm10", ""),
            "unit_normalised": "µg/m³",
            "unit_converted": conv25 or conv10,
            "aqi": row_aqi,
            "aqi_category": cat_info["category"],
            "aqi_token": cat_info["token"],
            "notes": notes,
            "has_error_flag": bool(severe_flag_types),
            "flag_Wait_types": sorted(severe_flag_types),
            "flag_messages": [f["detail"] for f in row_flags],
        })

    # Detect flatlined sensors (4+ identical consecutive valid PM2.5 readings per station)
    rows_by_station: dict[str, list[dict[str, Any]]] = {}
    for row in cleaned_rows:
        rows_by_station.setdefault(row["station"], []).append(row)

    for station, s_rows in rows_by_station.items():
        streak: list[dict[str, Any]] = []
        last_val: float | None = None
        for r in s_rows:
            val = r["pm25"] if r["pm25"] is not None else r["pm10"]
            if val is not None and val == last_val:
                streak.append(r)
            else:
                if len(streak) >= 4:
                    _mark_flatline(station, streak, all_flags)
                streak = [r] if val is not None else []
                last_val = val
        if len(streak) >= 4:
            _mark_flatline(station, streak, all_flags)

    station_summaries = _build_station_summaries(rows_by_station)
    trust_summary = _build_trust_summary(cleaned_rows, all_flags, station_summaries)

    return {
        "rows": cleaned_rows,
        "flags": all_flags,
        "stations": station_summaries,
        "trust": trust_summary,
    }


def _mark_flatline(
    station: str,
    streak_rows: list[dict[str, Any]],
    all_flags: list[dict[str, Any]],
) -> None:
    """Flag a sequence of 4+ identical readings as a suspected flatlined sensor."""
    row_ids = [r["row_id"] for r in streak_rows]
    val = streak_rows[0]["pm25"] if streak_rows[0]["pm25"] is not None else streak_rows[0]["pm10"]
    msg = (
        f"Rows {', '.join(map(str, row_ids))} ({station}): "
        f"Identical reading ({val} µg/m³) repeated {len(streak_rows)} times in a row (possible stuck sensor)."
    )
    for r in streak_rows:
        r["has_error_flag"] = True
        r["flag_messages"].append(msg)
    all_flags.append({
        "row_id": row_ids[0],
        "row_ids": row_ids,
        "station": station,
        "type": "flatlined_sensor",
        "metric": "PM",
        "detail": msg,
    })


def _build_station_summaries(
    rows_by_station: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Aggregate deterministic mean, peak, AQI, and confidence per station."""
    summaries: list[dict[str, Any]] = []
    for station, s_rows in rows_by_station.items():
        pm25_vals = [Decimal(str(r["pm25"])) for r in s_rows if r["pm25"] is not None]
        pm10_vals = [Decimal(str(r["pm10"])) for r in s_rows if r["pm10"] is not None]

        mean_pm25 = (
            float((sum(pm25_vals) / Decimal(len(pm25_vals))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
            if pm25_vals
            else None
        )
        peak_pm25 = float(max(pm25_vals)) if pm25_vals else None
        mean_pm10 = (
            float((sum(pm10_vals) / Decimal(len(pm10_vals))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
            if pm10_vals
            else None
        )
        peak_pm10 = float(max(pm10_vals)) if pm10_vals else None

        station_aqi = compute_row_aqi(
            Decimal(str(mean_pm25)) if mean_pm25 is not None else None,
            Decimal(str(mean_pm10)) if mean_pm10 is not None else None,
        )
        cat_info = aqi_category_for_index(station_aqi)

        flagged_rows = [r["row_id"] for r in s_rows if r["has_error_flag"]]
        all_row_ids = [r["row_id"] for r in s_rows]

        # Station confidence is low if >= 30% of rows have anomalies/gaps or no valid readings
        confidence = (
            "low"
            if (not pm25_vals and not pm10_vals) or (len(flagged_rows) / len(s_rows) >= 0.3)
            else "high"
        )

        summaries.append({
            "station": station,
            "row_ids": all_row_ids,
            "flagged_row_ids": flagged_rows,
            "total_rows": len(s_rows),
            "mean_pm25": mean_pm25,
            "peak_pm25": peak_pm25,
            "mean_pm10": mean_pm10,
            "peak_pm10": peak_pm10,
            "aqi": station_aqi,
            "aqi_category": cat_info["category"],
            "aqi_token": cat_info["token"],
            "confidence": confidence,
        })

    summaries.sort(key=lambda s: (s["aqi"] is not None, s["aqi"] or 0), reverse=True)
    return summaries


def _build_trust_summary(
    cleaned_rows: list[dict[str, Any]],
    all_flags: list[dict[str, Any]],
    stations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarise overall dataset reliability for the Data Trust panel."""
    total_rows = len(cleaned_rows)
    error_rows = sum(1 for r in cleaned_rows if r["has_error_flag"])
    converted_rows = sum(1 for r in cleaned_rows if r["unit_converted"])
    overall_confidence = "low" if error_rows > 0 else "high"
    low_conf_stations = [s["station"] for s in stations if s["confidence"] == "low"]

    return {
        "total_rows": total_rows,
        "valid_rows": total_rows - error_rows,
        "flagged_rows_count": error_rows,
        "unit_converted_count": converted_rows,
        "overall_confidence": overall_confidence,
        "low_confidence_stations": low_conf_stations,
    }


def compute_delta(
    current_stations: list[dict[str, Any]],
    previous_brief: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare current station metrics with the previous brief stored in the signed session."""
    if not previous_brief or not previous_brief.get("stations"):
        return {
            "has_previous": False,
            "previous_timestamp": None,
            "summary_line": (
                "First brief in this session. Analyse another sheet next (or load "
                "'Example: Last week baseline' first, then 'Example: This week') to see station-by-station changes."
            ),
            "station_deltas": [
                {
                    "station": s["station"],
                    "direction": "new",
                    "arrow": "•",
                    "word": "new baseline",
                    "current_pm25": s["mean_pm25"],
                    "previous_pm25": None,
                    "pct_change": None,
                    "detail": f"{s['station']}: Baseline recorded at PM2.5 {s['mean_pm25'] or 'N/A'} µg/m³ (AQI {s['aqi'] or 'N/A'} {s['aqi_category']}).",
                }
                for s in current_stations
            ],
        }

    prev_by_name = {
        s["station"].strip().lower(): s for s in previous_brief.get("stations", [])
    }
    deltas: list[dict[str, Any]] = []

    for curr in current_stations:
        key = curr["station"].strip().lower()
        prev = prev_by_name.get(key)
        c_pm = curr.get("mean_pm25")
        p_pm = prev.get("mean_pm25") if prev else None

        if prev is None or c_pm is None or p_pm is None or p_pm == 0:
            deltas.append({
                "station": curr["station"],
                "direction": "new",
                "arrow": "•",
                "word": "new",
                "current_pm25": c_pm,
                "previous_pm25": p_pm,
                "pct_change": None,
                "detail": f"{curr['station']}: New station reading at PM2.5 {c_pm or 'N/A'} µg/m³.",
            })
            continue

        diff = round(c_pm - p_pm, 1)
        pct = round(((c_pm - p_pm) / p_pm) * 100)
        if abs(pct) <= 2:
            direction = "same"
            arrow = "→"
            word = "unchanged"
            detail = f"{curr['station']}: Unchanged at PM2.5 {c_pm} µg/m³ ({pct:+d}% vs last brief)."
        elif diff > 0:
            direction = "worse"
            arrow = "↑"
            word = "worse"
            detail = (
                f"{curr['station']} is worse: PM2.5 up {abs(pct)}% "
                f"(from {p_pm} to {c_pm} µg/m³, AQI {curr['aqi']} {curr['aqi_category']})."
            )
        else:
            direction = "worse" if False else "better"
            arrow = "↓"
            word = "better"
            detail = (
                f"{curr['station']} is better: PM2.5 down {abs(pct)}% "
                f"(from {p_pm} to {c_pm} µg/m³, AQI {curr['aqi']} {curr['aqi_category']})."
            )

        deltas.append({
            "station": curr["station"],
            "direction": direction,
            "arrow": arrow,
            "word": word,
            "current_pm25": c_pm,
            "previous_pm25": p_pm,
            "pct_change": pct,
            "detail": detail,
        })

    worst_delta = next((d for d in deltas if d["direction"] == "worse"), deltas[0] if deltas else None)
    summary_line = (
        worst_delta["detail"]
        if worst_delta
        else "Compared with the previous brief in this session."
    )

    return {
        "has_previous": True,
        "previous_timestamp": previous_brief.get("timestamp"),
        "summary_line": summary_line,
        "station_deltas": deltas,
    }


def build_session_snapshot(parsed: dict[str, Any], timestamp_str: str) -> dict[str, Any]:
    """Build a compact snapshot for the signed Flask cookie session."""
    return {
        "timestamp": timestamp_str,
        "stations": [
            {
                "station": s["station"],
                "mean_pm25": s["mean_pm25"],
                "aqi": s["aqi"],
                "aqi_category": s["aqi_category"],
            }
            for s in parsed.get("stations", [])
        ],
    }


def verify_citations(
    ai_output: dict[str, Any],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    """Validate every row_id cited by Gemini against parsed rows and enforce confidence flags."""
    rows_by_id = {r["row_id"]: r for r in parsed.get("rows", [])}
    valid_ids = set(rows_by_id.keys())
    flagged_ids = {r["row_id"] for r in parsed.get("rows", []) if r["has_error_flag"]}
    low_conf_stations = {
        s["station"].strip().lower()
        for s in parsed.get("stations", [])
        if s["confidence"] == "low"
    }

    verified_hotspots: list[dict[str, Any]] = []
    for h in ai_output.get("hotspots", []):
        cited = [rid for rid in h.get("row_ids", []) if rid in valid_ids]
        if not cited:
            continue
        loc_lower = str(h.get("location", "")).strip().lower()
        uses_flagged = any(rid in flagged_ids for rid in cited) or loc_lower in low_conf_stations
        confidence = "low" if uses_flagged or h.get("confidence") == "low" else "high"
        chips = [
            f"Row {rid} · {rows_by_id[rid]['station']}"
            for rid in cited
        ]
        verified_hotspots.append({
            **h,
            "row_ids": cited,
            "source_chips": chips,
            "confidence": confidence,
        })

    verified_actions: list[dict[str, Any]] = []
    for a in ai_output.get("actions", []):
        cited = [rid for rid in a.get("row_ids", []) if rid in valid_ids]
        if not cited:
            continue
        uses_flagged = any(rid in flagged_ids for rid in cited)
        confidence = "low" if uses_flagged or a.get("confidence") == "low" else "high"
        chips = [
            f"Row {rid} · {rows_by_id[rid]['station']}"
            for rid in cited
        ]
        verified_actions.append({
            **a,
            "row_ids": cited,
            "source_chips": chips,
            "confidence": confidence,
        })

    verified_actions.sort(key=lambda item: int(item.get("priority", 99)))

    return {
        **ai_output,
        "hotspots": verified_hotspots,
        "actions": verified_actions,
    }
