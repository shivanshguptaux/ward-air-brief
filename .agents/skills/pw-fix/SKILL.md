---
name: pw-fix
description: Find the root cause of an error and make the smallest fix. Use any time something breaks: a failing run, test, build, deploy or live URL.
---

Ask the owner for the full error if it was not pasted. Then:
1. Reproduce or locate it (for Cloud Run: `gcloud builds list --limit 3`, or the logs command in `AGENTS.md`).
2. State the root cause in two sentences.
3. Make the smallest fix, within your lane. Do not refactor anything else.
4. Re-run whatever failed and show it passing.
