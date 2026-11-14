# VayuBrief Bhopal

Turn a messy ward air quality sheet into a traceable brief, ranked local actions, an internal note and a citizen advisory in English or Hindi.

**Live:** https://vayubrief-64na6zdzrq-el.a.run.app

**Try it in 30 seconds**
1. Open the live URL and press **This week · Ward 31**, then **Analyse sheet**.
2. Read the lead line, then press any **Row** chip to jump to the reading it came from in **Data trust**.
3. Open **Internal note** and press **Sign in** (demo account `ravi.ward31` / `bhopal-clean-air`, already filled in). Open **Citizen advisory** for the resident card and press **Share on WhatsApp** to send it.

To see **Since last brief**, analyse **Last week · Ward 31** first, then **This week · Ward 31**.

## The problem

> Develop an AI-driven civic intelligence solution that enables local authorities, housing societies, and ward-level teams to turn raw air quality data into actionable local interventions. The solution must leverage Generative AI as a core component to interpret pasted or uploaded data tables, including messy ones with inconsistent formats, units, or missing readings, and summarize trends and likely hotspots in plain language. It should recommend prioritized local actions suited to who is asking, since a ward officer, a housing society, and a school can each do different things. Every finding should be traceable to the underlying data, with data gaps and unreliable readings clearly flagged. The assistant should compare each new brief with the previous one to show what changed, and generate both an internal briefing note and a citizen advisory in multiple languages, written for different reading levels, with extra care for children, older adults, and people sensitive to poor air.

Ravi, an assistant engineer for one Bhopal ward, gets a messy sheet from three monitors every Monday and has about 15 minutes before the ward review to decide what to do. The sheet has gaps and impossible readings, and most of the residents he must warn don't understand AQI.

**Why this matters**
- Only 270 of India's 562 live monitoring stations gave stable data in 2025 ([ThePrint](https://theprint.in/environment/indian-districts-air-quality-monitoring-station-airvoice/2893284)).
- Delhi's municipal corporation spent 17% of its clean air funds in five years ([Tribune](https://www.tribuneindia.com/news/delhi/as-national-capital-chokes-mcd-sat-on-clean-air-funds)).
- Bhopal spent ₹195 crore of ₹242 crore under NCAP and is still 6th in the clean air survey ([Free Press Journal](https://www.freepressjournal.in/bhopal/clean-air-survey-despite-190-crore-spend-bhopal-stuck-at-6th-rank)).
- 93% of Delhi residents don't understand AQI ([India TV](https://www.indiatvnews.com/news/india-93-per-cent-delhiites-don-t-know-what-aqi-means-survey-499958)); only 10% of the urban poor know the terms AQI or PM2.5 ([Business Standard](https://www.business-standard.com/india-news/air-pollution-related-terminologies-awareness-low-among-urban-poor-study-124040700353_1.html)).

## What it does

1. **Paste or upload** the sheet, and choose who is asking (ward officer, housing society, school), the language and the reading level.
2. **The code cleans and flags.** It detects the delimiter, converts mg/m³ to µg/m³, and flags missing, negative, above-999 and stuck readings. Gemini then writes the brief from the cleaned rows and cites a row for every finding.
3. **Ravi gets four tabs:** **Brief** (lead line, stations, hotspots, ranked actions, since last brief), **Data trust** (every flag and the cleaned table), **Internal note** (staff only, printable on A4) and **Citizen advisory** (a phone-sized card with lines for children, older adults and sensitive people, shared to WhatsApp in one tap).

## How it works

```
form → validation.py → logic.parse_and_analyse_table → logic.compute_delta → ai.generate_civic_brief (Gemini) → logic.verify_citations → templates/index.html
```

**The AI decides, the code computes.** Gemini writes the language and makes the judgement calls: trend, likely causes, which actions fit the role, the note and the advisory. Everything numeric is plain Python in `logic.py`: parsing with `csv.Sniffer`, unit conversion, CPCB AQI per reading and per station, data flags, the change since the last brief and the WhatsApp share link (`build_whatsapp_share_url`, a plain `wa.me` link with no API or tracking). `verify_citations` drops any finding that cites a row the code didn't send, and forces low confidence on findings that rely on flagged rows. If nothing survives, the user sees an honest error instead of an unsupported brief.

**Fallback chain** (`ai.generate_civic_brief`)
1. Identical request in the last 15 minutes: served from the in-memory LRU cache (64 entries).
2. `GEMINI_MODEL` (default `gemini-3.5-flash`): system instruction, JSON `response_schema`, temperature 0.2, low thinking level, 2,048-token output cap, 20 second timeout. If the model rejects the thinking setting, the same call is retried once without it. The reply is checked by `validate_ai_schema`.
3. On any API error, timeout or invalid reply: one retry on `GEMINI_FALLBACK_MODEL` (default `gemini-3.5-flash-lite`).
4. If both fail, or there is no key: "The analysis couldn't run right now", with the safe next step. The app never shows a canned or reassuring answer.

## Google services used

| Service | What for | Where |
|---|---|---|
| Gemini API (`google-genai`) | Writes the brief, ranked actions, internal note and citizen advisory | `ai.py` (`_call_model`, `generate_civic_brief`) |
| Cloud Run | Hosts the app with gunicorn, max 2 instances | `Procfile`, deploy command below |
| Cloud Build | Builds the container from source on each deploy | `gcloud run deploy --source .` |
| Secret Manager | `GEMINI_API_KEY` and `FLASK_SECRET_KEY`, never in code | `--set-secrets` in the deploy command |
| Cloud Logging | One structured JSON line per request on stdout: route, status, latency, model, cache hit, fallback used. No user text, no keys | `main.py` (`_apply_headers_and_log`) |
| Google Fonts | Inter, plus Noto Sans Devanagari for Hindi | `templates/index.html` |

## Evaluation notes

| Area | What was done | Evidence |
|---|---|---|
| Problem statement alignment | Every ask in the challenge maps to one visible feature: messy input, flags, role-based actions, row citations, since last brief, note, bilingual advisory at two reading levels, care groups; a lead line that names the worst station, its figure and the likely cause; the advisory goes to residents through WhatsApp, where they already are | `BRIEF.md`, `templates/index.html`, `logic.py` |
| Code quality | Routes, AI, deterministic logic, validation and compression in separate modules, each under 300 lines; type hints and docstrings throughout; design system fully tokenised | `main.py`, `ai.py`, `logic.py`, `validation.py`, `static/styles.css` |
| Security | Allowlisted role, language and level; 2,000-character table limit; 64 KB request cap; Jinja autoescape; `textContent` only in JS; CSP, HSTS, nosniff, referrer, frame and permissions headers; cross-site POSTs rejected by an `Origin` check; 20 requests a minute per IP on `/analyse` and on staff sign-in, keyed on the address Cloud Run sees so it cannot be spoofed; hashed staff password; signed `HttpOnly`, `Secure`, `SameSite=Lax` session cookie; secrets in Secret Manager; user data in delimiters with `<` and `>` escaped, treated as data by the system instruction | `validation.py`, `main.py`, `ai.py`, `static/app.js` |
| Efficiency | 15-minute LRU cache; one reused Gemini client; low thinking level and a 2,048-token output cap; compact JSON prompt (no indentation); 20 second timeout; sample data loaded once at startup; static files cached for an hour; HTML, CSS, JS and JSON gzipped (`compression.py`, standard library only); stale rate-limit entries pruned once a minute; no build step, one small CSS and JS file | `ai.py`, `main.py`, `compression.py`, `static/` |
| Testing | 227 pytest cases, no network (Gemini replaced by a fake client), 97% line coverage of app code: parsing, units, flags, AQI boundaries, deltas, citation checks, validation, every route, fallback and honest error, cache, schema checks, prompt injection, rate limit, sign-in, security headers including HSTS, cross-site POST rejection, sign-in rate limit, thinking and output caps, radio labels, invalid states and Hindi language tags. Includes regression tests for two bugs the suite found and that were then fixed | `tests/` |
| Accessibility | WCAG 2.2 AA: skip link, landmarks, one h1, fieldsets with legends, hints and errors tied with `aria-describedby`, `aria-invalid`, `aria-live` status, focus moves to the brief or the first error, ARIA tabs with arrow keys, AQI always colour plus word plus number, Hindi text marked `lang="hi"`, 3:1 control borders, reduced motion, works at 360 px | `templates/index.html`, `static/styles.css`, `static/app.js` |
| Google services | Gemini, Cloud Run, Cloud Build, Secret Manager, Cloud Logging, Google Fonts | table above |

## Run locally

```bash
uv venv .venv --python 3.13 && uv pip install --python .venv -r requirements.txt -r requirements-dev.txt
```

```bash
GEMINI_API_KEY="$(gcloud secrets versions access latest --secret=gemini-api-key-free --project pw-bhopal-1114)" .venv/bin/flask --app main run --port 8080
```

Open http://localhost:8080. Health check: `/health`. Without a key the app still runs and shows the honest error on analysis.

## Tests

```bash
.venv/bin/pytest -q
```

The suite makes no network calls and uses no Gemini quota: `tests/conftest.py` swaps the Gemini client for a fake that returns scripted replies or errors.

| File | Covers |
|---|---|
| `tests/test_logic.py` | CPCB breakpoints and category boundaries, header aliases, timestamps, mg→µg conversion, missing, negative, above-999 and stuck readings, delimiters, a 2,000-row table, deltas, session snapshot, citation checks, the WhatsApp share link |
| `tests/test_validation.py` | Valid input, missing fields, the 2,000-character limit, allowlists, wrong types |
| `tests/test_ai.py` | Request shape, fallback on 429, 503, timeout or invalid JSON, honest error when both fail or no key, cache hits, expiry and eviction, schema rejection, injection staying inside delimiters (user text cannot close a tag) |
| `tests/test_compression.py` | Gzip on the page, CSS, JS and analysis result; plain responses without `Accept-Encoding`; small JSON, errors and SVG left alone; security headers kept |
| `tests/test_routes.py` | Home, health, samples, 404, the analyse happy path and comparison, CSV upload, 400s, 413, 503 honest error, dropped citations, rate limit, staff sign-in, security headers |

## Deploy

```bash
gcloud run deploy vayubrief --source . --project pw-bhopal-1114 --region asia-south1 --allow-unauthenticated --max-instances 2 --set-secrets GEMINI_API_KEY=gemini-api-key-free:latest,FLASK_SECRET_KEY=flask-secret-key:latest --set-env-vars GEMINI_MODEL=gemini-3.5-flash,GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite
```

```bash
gcloud run services logs read vayubrief --project pw-bhopal-1114 --region asia-south1 --limit 50
```

## Honest limits

- AQI per reading applies CPCB's 24-hour breakpoints to single readings, so it is indicative, not the official daily AQI.
- Only the previous brief is kept, in the signed session cookie, so "since last brief" compares one step back and is per browser.
- The staff sign-in is one shared demo account that guards the internal note. It is not user management.
- English and Hindi only. Gemini writes the Hindi, and no native speaker has reviewed it.
- The free-tier key allows about 20 Gemini requests a day; after that, users see the honest error.
- The cache and the rate limit live in memory per instance and reset on restart.
- Tables are capped at 2,000 characters, about 40 rows.
- WhatsApp sharing opens WhatsApp with the advisory text filled in; the user still picks who to send it to.
- Not built: audio playback of the advisory, maps or live sensor feeds.

## How it was built

A solo three-hour build for Google PromptWars, directed by a product designer. Antigravity (Planning Mode) built the app (`main.py`, `ai.py`, `logic.py`, `validation.py`) and the WhatsApp share. Claude Code did the UX and visual pass on `templates/` and `static/`, wrote `tests/` (which found and fixed two bugs), checked the live service, and wrote the README and `docs/`. Both agents followed the rules in [`AGENTS.md`](AGENTS.md) and the skills in [`.agents/skills/`](.agents/skills/). The prompts are logged in [`docs/prompts.md`](docs/prompts.md).
