# Submission

## Public GitHub Repository Link

https://github.com/shivanshguptaux/ward-air-brief

## Deployed Prototype Link

https://vayubrief-64na6zdzrq-el.a.run.app

## Project Demo Video Submission

(to add)

## Describe the changes/updates made in the deployed version

VayuBrief Bhopal turns a ward's messy weekly air quality sheet into a traceable brief. Paste or upload a table (any delimiter, mixed units, gaps), pick who is asking (ward officer, housing society, school), English or Hindi, and a simple or standard reading level. The code cleans the table, converts mg/m³ to µg/m³, and flags missing, impossible and stuck readings. Gemini writes the lead line, hotspots and three ranked actions for that role, each citing its source rows; findings that rely on flagged data are marked low confidence. Results are in four tabs: Brief (with what changed since the last brief), Data trust, a printable internal note behind a staff sign-in, and a phone-sized citizen advisory with lines for children, older adults and sensitive people, which can be shared on WhatsApp in one tap. Accessible to WCAG 2.2 AA, 207 tests. Try: press "This week · Ward 31", then "Analyse sheet". Staff sign-in: ravi.ward31 / bhopal-clean-air.

## Changes since submission 1 (paste into "Describe the changes" for submission 2)

Security: HSTS and Permissions-Policy headers; session cookie is HttpOnly, Secure and SameSite=Lax; the rate limit uses the address Cloud Run sees, so a fake X-Forwarded-For cannot dodge it; prompt data escapes < and >, so pasted text cannot break out of its delimiters. Efficiency: one reused Gemini client, compact JSON prompt (fewer tokens), sample data loaded once at startup, static files cached for an hour, stale rate-limit entries pruned. Accessibility: every radio has an id and label, invalid groups get aria-invalid and a visible outline, the WhatsApp link announces it opens a new tab, higher placeholder contrast, aligned cards. Testing: 207 tests, 97% coverage, no network. New shorter link. Try: press "This week · Ward 31", then "Analyse sheet". Staff sign-in: ravi.ward31 / bhopal-clean-air.

## Mention the Gen AI services utilized in the submission, and where did you utilize it?

Gemini API via the google-genai SDK, in ai.py. Main model gemini-3.5-flash, with one retry on gemini-3.5-flash-lite on any API error, timeout or invalid reply, then an honest error (never a canned answer).
- ai.generate_civic_brief → _call_model: one structured call with a system instruction, a JSON response_schema, temperature 0.2 and a 20 s timeout. From the cleaned rows, flags and week-on-week change, it writes the trend, hotspots, role-specific ranked actions (each citing row IDs), the internal note and the citizen advisory in the chosen language and reading level.
- ai.validate_ai_schema checks the reply; logic.verify_citations drops findings citing rows the code didn't send.
User data is sent inside delimiters and treated as data. Numbers and AQI come from logic.py, not the model. Replies are cached for 15 minutes.
