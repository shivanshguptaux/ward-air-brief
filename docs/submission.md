# Submission

## Brief

VayuBrief Bhopal turns a ward's messy weekly air quality sheet into action. A ward officer, housing society or school pastes or uploads the sheet (any delimiter, mixed units, gaps) and picks who is asking, English or Hindi, and a simple or standard reading level. The code cleans the table, converts units and flags missing, impossible and stuck readings. Gemini writes the brief: a lead line, the likely hotspots and three ranked actions suited to that role, each citing its source rows, plus what changed since the last brief. Findings that rely on flagged data are marked low confidence. It also writes a printable internal note for staff and a phone-sized citizen advisory with lines for children, older adults and sensitive people. Try it: press "This week · Ward 31", then "Analyse sheet". Staff sign-in for the internal note: ravi.ward31 / bhopal-clean-air.

## GenAI services used and where

Gemini API via the google-genai SDK, in ai.py. Main model gemini-3.5-flash, with one retry on gemini-3.5-flash-lite on any API error, timeout or invalid reply, then an honest error (never a canned answer).
- ai.generate_civic_brief → _call_model: one structured call with a system instruction, a JSON response_schema, temperature 0.2 and a 20 s timeout. From the cleaned rows, flags and week-on-week change, it writes the trend, hotspots, role-specific ranked actions (each citing row IDs), the internal note and the citizen advisory in the chosen language and reading level.
- ai.validate_ai_schema checks the reply; logic.verify_citations drops findings citing rows the code didn't send.
User data is sent inside delimiters and treated as data. Numbers and AQI come from logic.py, not the model. Replies are cached for 15 minutes.
