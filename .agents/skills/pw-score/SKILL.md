---
name: pw-score
description: Run measured checks against the seven PromptWars scoring dimensions (tests and coverage, lint, security scans, secret scan, repo size, accessibility markup, README, live URL headers and speed) and report pass, warn or fail. Use before every submission, alongside /pw-audit. Read-only and costs no Gemini quota.
---

Do not edit any files in this skill. Report only.

1. Find the live URL: the `run.app` link in `README.md`, or
   `gcloud run services list --project pw-bhopal-1114 --region asia-south1 --format="value(URL)"`.
2. From the repo root run:
   `.venv/bin/python .agents/skills/pw-score/score.py LIVE_URL`
   (leave out `LIVE_URL` if nothing is deployed yet). Show the full output.
3. If you have a browser tool, open the live URL and check, by looking and by using the keyboard:
   - Tab through the golden path: every control is reachable, the focus ring is visible, the order makes sense.
   - At 360 px wide and at 200% zoom, nothing is cut off or needs sideways scrolling.
   - Load the example input and run it once (one real call): the loading and result text are announced (inside the `aria-live` region) and focus moves to the result.
   - Text contrast looks at least 4.5:1, and colour is never the only signal.
   Say what you saw for each.
4. End with:
   - A one-line verdict per dimension: Problem alignment, Code quality, Security, Efficiency, Testing, Accessibility, Google services.
   - Every FAIL first, then the 5 WARNs most likely to cost points. Each one gets the fix in one sentence, the lane that owns it (Antigravity for app files; Claude Code for `tests/`, `README.md`, `docs/`) and a time estimate.
   - Ignore SKIP lines unless asked.

The script never calls the AI route. Do not test real Gemini answers here.
