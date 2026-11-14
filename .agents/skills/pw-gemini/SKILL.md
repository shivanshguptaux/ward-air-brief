---
name: pw-gemini
description: Replace the stub in ai.py with real Gemini calls, fallback, honest error and cache, keeping the same schema. Use as the build step after styling.
---

Wire real Gemini into `ai.py`, following the "Gemini rules" in `AGENTS.md` exactly:
- Keep the same JSON schema so the UI does not change.
- `google-genai` client with `http_options=types.HttpOptions(timeout=20_000)`.
- `GenerateContentConfig(system_instruction=..., response_mime_type="application/json", response_schema=...)`; validate the parsed JSON before returning it.
- Primary model, then fallback model, then the honest error from `AGENTS.md`. Delete the stub and any demo mode: no canned answers on the live app.
- Every finding carries its source (row, field or fact ID); the code drops any finding whose source wasn't in the input.
- In-memory LRU cache, 15 minutes.
- One JSON log line per request: route, model, latency ms, cache hit, fallback used. No user text and no keys.

Test once with the real key, with the example input and with one messy input of your own. Then remove the key locally and confirm the honest error shows.
