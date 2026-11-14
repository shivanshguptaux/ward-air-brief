---
name: pw-build
description: Build the full golden path end to end with a stubbed Gemini response and sample data. Use as build step 1, after the plan is approved.
---

Build step 1 of the approved plan:
- Create the files in `AGENTS.md`'s structure, plus `requirements.txt` (pinned versions from `AGENTS.md`), `Procfile` (`web: gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 60 main:app`) and `/health`.
- `ai.py` returns a hard-coded response that matches the JSON schema exactly. It is temporary: `/pw-gemini` deletes it before the first deploy.
- `sample_data.json` holds example **inputs**, labelled "Example", that load into the form with one tap. Never stored results.
- Every state exists: empty (with 2 or 3 example chips), loading, result, error with retry.
- If the owner attached a paper sketch, follow its screens, order and layout. Use the copy in `BRIEF.md`, not placeholder text.
- Basic layout only; styling comes next.

Run it with `.venv/bin/flask --app main run --port 8080`, tell the owner the URL, and stop.
