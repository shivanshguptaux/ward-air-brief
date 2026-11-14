# Submission

Fields in the order the form asks for them. Latest: submission 2.

## Public GitHub Repository Link

https://github.com/shivanshguptaux/ward-air-brief

## Deployed Prototype Link

https://vayubrief-64na6zdzrq-el.a.run.app

## Project Demo Video Submission

(to add)

## Describe the changes/updates made in the deployed version

Since submission 1 (93.75). Efficiency: Gemini runs with a low thinking level and a 2,048-token output cap (faster replies inside the 20 s timeout), one reused client, compact JSON prompt, sample data loaded once, static files cached for an hour, rate-limit entries pruned once a minute. Security: HSTS and Permissions-Policy headers; HttpOnly, Secure, SameSite=Lax session cookie; cross-site POSTs rejected; staff sign-in rate-limited; rate limit keyed on the address Cloud Run sees; prompt data escapes < and >. Accessibility: every radio has an id and label, invalid groups get aria-invalid and an outline, Hindi text is marked lang="hi", the WhatsApp link announces a new tab, higher placeholder contrast, aligned cards. Prompt: the lead line names the worst station, its figure and the likely cause. Testing: 218 tests, 97% coverage, no network. Shorter link. Try "This week · Ward 31", then "Analyse sheet". Staff sign-in: ravi.ward31 / bhopal-clean-air.

## Mention the Gen AI services utilized in the submission, and where did you utilize it?

Gemini API via the google-genai SDK, in ai.py. Main model gemini-3.5-flash, one retry on gemini-3.5-flash-lite on any API error, timeout or invalid reply, then an honest error (never a canned answer).
- ai.generate_civic_brief → _call_model: one structured call with a system instruction, JSON response_schema, temperature 0.2, low thinking level, 2,048-token cap and a 20 s timeout. From the cleaned rows, flags and week-on-week change it writes the lead line (worst station, figure, cause), trend, hotspots, role-specific ranked actions citing row IDs, the internal note and the citizen advisory in the chosen language and reading level.
- ai.validate_ai_schema checks the reply; logic.verify_citations drops findings citing rows the code didn't send.
User data sits inside delimiters with < and > escaped. Numbers and AQI come from logic.py. Replies are cached for 15 minutes.

## Brief (product description, if a form asks for one)

VayuBrief Bhopal turns a ward's messy weekly air quality sheet into a traceable brief. Paste or upload a table (any delimiter, mixed units, gaps), pick who is asking (ward officer, housing society, school), English or Hindi, and a simple or standard reading level. The code cleans the table, converts mg/m³ to µg/m³, and flags missing, impossible and stuck readings. Gemini writes the lead line, hotspots and three ranked actions for that role, each citing its source rows; findings that rely on flagged data are marked low confidence. Results are in four tabs: Brief (with what changed since the last brief), Data trust, a printable internal note behind a staff sign-in, and a phone-sized citizen advisory with lines for children, older adults and sensitive people, shared on WhatsApp in one tap. Try "This week · Ward 31", then "Analyse sheet". Staff sign-in: ravi.ward31 / bhopal-clean-air.
