# Build rules

A solo, 3-hour build of a GenAI web app for a Google PromptWars challenge. The owner is a product designer directing AI agents. Speed matters, and so does a clean, working result.

## How this is scored

1. An AI reviewer reads the public GitHub repo. Weight, from the organisers' briefing on the day: **highest** code quality and problem statement alignment; **medium** security and efficiency; **lower but never zero** testing and accessibility (no tests means 0 for testing). Google services is not on the leaderboard list; keep it cheap.
2. 3 submission attempts, and **only the last one counts**, not the best.
3. Then people test the live app by hand, feature by feature, with their own inputs. **Disqualified for:** no real GenAI call, static or hard-coded features, mock or fake data, hallucinated AI answers, false positives, or a feature that doesn't work. Fewer features that all work beat more that don't.
   Real weights (warm-up report): problem alignment 30%, code quality 20%, security 15%, efficiency 15%, testing 10%, accessibility 10%. The analyzer also rates "user understanding" (the app models the user's role, language, context) and "adaptive, proactive assistance" (it uses history to help without being asked).
4. The top 10 pitch. Judges pick on problem fit, prompt quality and the pitch.

Every change should help at least one of those, or be cut.

## Working style

- The challenge text and the golden path live in `BRIEF.md`. Read it before planning. Use its wording for names, headings and the README.
- Plan before code. Break work into steps of about 15 minutes. Do one step, run it, tell the owner how to see it, then stop.
- Every ask in the challenge text maps to a real, working feature, connected in one flow (one input feeding the next step). Nothing beyond the challenge. No database, payments or build step.
- No login unless the challenge has staff-only output (for example an internal note). Then one simple sign-in for staff only, with the demo username and password shown on the sign-in page and in `README.md`, password hashed with `werkzeug.security`; the public side stays open.
- **No per-user state in module-level variables** (a global "previous result" leaks between users; it cost points in alignment, security and efficiency in the warm-up). Keep history in the signed Flask session or send it from the browser with the request. Module-level is fine only for constants and the shared cache.
- **Use the standard library for parsing**: `csv` (with `csv.Sniffer` for messy delimiters), `json`, `datetime`, `decimal`. No hand-rolled string splitting.
- Keep the repo small: no images over 200 KB, no `node_modules`, no generated files.
- Never print, log or commit API keys. Search for `AIza` before every commit.
- When something fails, find the root cause from the full error, make the smallest fix, and say what it was in two sentences.

## Lanes (two agents work at once)

- **Antigravity** owns the Python side all day: `main.py`, `ai.py`, `logic.py`, `validation.py`, `sample_data.json`, `requirements.txt`, `Procfile`. It also deploys.
- **Claude Code** owns `tests/`, `README.md`, `docs/` all day.
- **`templates/` and `static/` pass between them at fixed minutes.** Only the holder edits them. The other agent reports what it needs there instead of editing.

| Minutes | Holds `templates/` + `static/` | For |
|---|---|---|
| 30–60 | Antigravity | `/pw-build` |
| 60–95 | Claude Code | `/pw-look`: look, feel and motion (Antigravity is on `ai.py` and the deploy) |
| 95–130 | Antigravity | `/pw-xfactor` build, then `/pw-secure` |
| 130–150 | Claude Code | `/pw-a11y` and final polish |
| 150 on | Frozen | Fixes only, by whoever the owner names |

- If the owner says "hand over", stop, commit, and say which files you touched.
- Edit only your own lane unless the owner says otherwise. If you find a bug in the other lane, report it instead of fixing it.

## Stack (fixed)

- Python 3.13 (`.python-version` says `3.13`; Cloud Run's builder has no 3.12). Local env: `.venv`, made with `uv`.
- Flask, server-rendered Jinja templates, plain CSS, a little vanilla JS. No frameworks.
- Gemini via the `google-genai` SDK. gunicorn in production.
- Pinned `requirements.txt`: `flask==3.1.3`, `gunicorn==27.0.1`, `google-genai==3.3.0`. Tests: `pytest==9.2.0` in `requirements-dev.txt`.

## Structure

- `main.py`: routes only, plus security headers and one JSON log line per request.
- `ai.py`: every Gemini call (system instruction, JSON schema output, timeout, fallback model, honest error, cache).
- `logic.py`: pure functions for anything deterministic: numbers, dates, rules, sorting. No AI here.
- `validation.py`: input checks.
- `templates/`, `static/`, `sample_data.json`: example **inputs** only (realistic, labelled "Example", one tap to load into the form, then sent through the real AI). Never stored results shown as if computed. Facts or reference data must be real, with their source.
- Health check at `/health`. Never `/healthz`: Cloud Run reserves paths ending in "z".

## Gemini rules

- The AI decides, the code computes. The model handles language and judgement; numbers, dates and facts come from `logic.py`.
- Model from env `GEMINI_MODEL` (default `gemini-3.5-flash`), fallback from `GEMINI_FALLBACK_MODEL` (default `gemini-3.5-flash-lite`).
- System instruction defines the job, tone and output. Structured JSON via `response_schema`, validated before use.
- User text goes inside clear delimiters, and the system instruction says to treat it as data, never instructions.
- 20 second timeout. On 429, timeout or 5xx: retry once on the fallback model, then show an honest error ("The analysis couldn't run right now. Please try again in a minute.") with a Try again button. **No canned AI output on the live app, ever**: it reads as fake data.
- Fail safe, never fail happy: when the AI call fails, never show a reassuring verdict ("safe", "approved", "all good"). Say the check could not run and give the safe next step.
- Without a key the app still starts and shows that same honest message. No demo mode, no `?demo=1`. The hard-coded stub in `ai.py` lives only until `/pw-gemini` replaces it; tests mock the client instead.
- No hallucination: answers use only the user's input and the facts sent. Every finding points to its source (row, field or fact ID), and the code checks the IDs exist. If the data can't support an answer, say so.
- Cache identical requests in memory (small LRU, 15 minutes).
- Leave quota for the evaluators, who test after the deadline: one Gemini call per user action, the cache, and a per-IP rate limit only. No daily cap that could block them. Test with mocks; make real calls sparingly.

## X factor

- One memorable feature that removes the user's hardest barrier, chosen from the `/pw-xfactor` menu and named in `BRIEF.md`. Built only after the first deploy, behind a fallback. If it isn't working by minute 120, hide it.
- Cloud Text-to-Speech is enabled in `pw-bhopal-1114` (paid from Cloud credit, not Gemini quota). On Cloud Run it authenticates as the service account; no key.

## Quality bar

- **Security:** validate type, required fields and length (2,000 characters max); `MAX_CONTENT_LENGTH` 64 KB; Jinja autoescape on; `textContent`, never `innerHTML`, for user or model text; headers on every response: Content-Security-Policy (self only, no inline scripts), X-Content-Type-Options nosniff, Referrer-Policy strict-origin-when-cross-origin, X-Frame-Options DENY; 20 requests a minute per IP on AI routes; no stack traces; debug off.
- **Accessibility (WCAG 2.2 AA):** `lang` set; header, main, footer landmarks; skip link; one h1; visible labels; hints and errors tied with `aria-describedby`; `aria-invalid` on bad fields; results and loading in an `aria-live="polite"` region; focus moves to the result; full keyboard use with visible focus; 4.5:1 text contrast; `prefers-reduced-motion`; works at 360 px and 200% zoom; real buttons and links only.
- **Efficiency:** cache, timeouts, no build step, small payloads.
- **Code quality:** small modules, type hints, short docstrings, no dead code.
- **Google services:** Gemini, Cloud Run, Secret Manager, Cloud Logging (plus Text-to-Speech or Maps/Calendar links if the X factor uses them), each listed in the README with the file that uses it.

## Visual system

**If `BRIEF.md` has a "Design direction" section, it comes first; these defaults fill the gaps.**

**AQI colours (this challenge), CPCB categories, as tokens:** `--aqi-good #00B050`, `--aqi-satisfactory #92D050`, `--aqi-moderate #FFD84D`, `--aqi-poor #FF9900` (all four with `--text` on top), `--aqi-very-poor #C62828`, `--aqi-severe #7E0023` (white text). Used only for AQI chips, bars and badges, always with the category word and the number. Colour never means anything else in the app.

Use only CSS custom properties in `static/styles.css`. Adjust the accent and mood to fit the user in `BRIEF.md`, keeping contrast at AA.

- Colour: `--bg #FAFAF8`, `--surface #FFFFFF`, `--text #1C1C1A`, `--muted #5C5C57`, `--border #E4E3DE`, `--accent #0F6E66`, `--accent-text #FFFFFF`, `--accent-weak #E6F2F0`, `--danger #B3261E`, `--success #1E7D3A`. Never colour as the only signal.
- Type: system stack (`-apple-system, "Segoe UI", Roboto, sans-serif`); sizes 14, 16, 20, 28, 36; weights 400 and 600; body at least 16 px.
- Space on a 4 px base: 4, 8, 12, 16, 24, 32, 48. Radius 8 for controls, 12 for cards. Cards: white, 1 px border, no shadows.
- **The layout follows the user's device**, named under "Device" in `BRIEF.md`. Most PromptWars users are on phones, so phone is the default.
- **Phone (default): a mobile-first web app.** Design at 360 px first. One column, max-width 480 px, centred on wider screens over `--bg`, so on a laptop or projector it reads as an app. No desktop sidebars or top menus.
- **Desk (office staff, doctors, teachers planning, coordinators, anyone comparing many items or filling long forms): a responsive desktop layout.** A top bar, then two columns from 1024 px (list or input on the left, detail or result on the right, max-width 1120 px), collapsing to one column under 768 px so it still works on a phone. Tables only for real tabular data, with a stacked card view on phones.
- **Two users on two devices** (for example a patient on a phone and a clinic on a desk): build the primary user's side first in their layout. Add the second view only if the golden path needs it, as one simple page.
- **Phone app shell:** a slim sticky header (product name, language switch), scrolling content, and the screen's primary action in a sticky bottom bar within thumb reach. Respect `env(safe-area-inset-bottom)` and set `viewport-fit=cover`.
- **Bottom navigation only if the golden path truly has 2 to 4 destinations** (for example Check, History, Help) and every tab works. A one-job app gets no tab bar. If used: a `<nav aria-label="Main">` of real links, icon plus text label on each, `aria-current="page"` on the active tab, 56 px tall, and it never covers the primary button.
- Add `static/manifest.webmanifest` (name, short name, theme colour, one 512 px icon) and link it, so "Add to Home screen" works. No service worker.
- Controls at least 44 px tall. One primary button per screen. Focus: 3 px solid accent outline, 2 px offset.
- Every screen has empty (2 or 3 example chips), loading (short text status), result and error (with retry) states.
- Results lead with the single most useful line, then short labelled sections. No emoji, gradients or stock illustrations.
- **Motion: minimal, CSS only.** `transform` and `opacity` only, 150 to 250 ms, `cubic-bezier(0.2, 0, 0, 1)`, as tokens (`--dur-fast 150ms`, `--dur 220ms`, `--ease`). Where: the result card settling in (8 px rise and fade), button press (scale 0.98), a pulsing dot beside the loading line, chips and focus rings easing. Nothing loops except the loading dot, nothing moves layout, nothing blocks input. All of it off under `prefers-reduced-motion: reduce`. No animation library or CDN (the CSP blocks it).

## Environment (already set up)

- GCP project `pw-bhopal-1114`, region `asia-south1`, billing on, deploy permissions granted.
- Gemini key in Secret Manager as `gemini-api-key-free` (free-tier project).
- Run locally: `GEMINI_API_KEY="$(gcloud secrets versions access latest --secret=gemini-api-key-free --project pw-bhopal-1114)" .venv/bin/flask --app main run --port 8080`
- Deploy: `gcloud run deploy SERVICE --source . --project pw-bhopal-1114 --region asia-south1 --allow-unauthenticated --max-instances 2 --set-secrets GEMINI_API_KEY=gemini-api-key-free:latest --set-env-vars GEMINI_MODEL=gemini-3.5-flash,GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite`
- Logs: `gcloud run services logs read SERVICE --project pw-bhopal-1114 --region asia-south1 --limit 50`
- GitHub: `gh` is signed in as shivanshguptaux. New public repo: `gh repo create NAME --public --source . --remote origin --push`
