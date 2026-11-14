---
name: pw-secure
description: Security pass on the app without changing behaviour or looks. Use after the first deploy.
---

Apply the "Security" line of the quality bar in `AGENTS.md`: input validation with clear 400 messages, `MAX_CONTENT_LENGTH`, autoescape, `textContent` in JS, the security headers, a per-IP rate limit on AI routes returning a friendly 429, no stack traces, debug off.

Move any inline script into `static/` so the CSP holds. Finish any template or static change before minute 130, when Claude Code takes those folders. List the changes in one short list.
