---
name: pw-tests
description: Write pytest tests in tests/ only, with Gemini mocked. Use in the Claude Code lane after the first deploy, in parallel with the security and accessibility passes.
---

Write tests in `tests/` and pin `pytest==9.2.0` in `requirements-dev.txt`. Do not change app code; report bugs instead of fixing them. Make sure `pytest.ini` has `pythonpath = .`.

Cover:
- `logic.py`: every function, including empty, zero, very large and wrong-type inputs.
- `validation.py`: valid input, missing fields, over-length input, wrong types.
- Routes with Flask's test client: home renders, `/health`, the AI route happy path, 400 on bad input, 429 after the rate limit.
- `ai.py` with the client monkeypatched (no network): normal response, invalid JSON from the model, a failure that triggers the fallback, both failing giving the honest error (never a canned answer), no key giving the honest error, a finding with an unknown source being dropped.
- A prompt-injection input still returns schema-valid output and stays inside the delimiters.
- Security headers on responses.

Run `.venv/bin/pytest -q` and show the summary line.
