---
name: pw-xfactor
description: Choose, then build, one X factor that removes the user's hardest barrier and is demoable in 10 seconds (speak instead of type, hear the answer in Hindi, point the camera, visible sources, hand it to family). Use during /pw-plan to choose, and after the first deploy (minute 95 to 115) to build. Antigravity builds it; Claude Code tests and documents it.
---

An X factor is one thing the room remembers. It must remove the user's hardest barrier from `BRIEF.md` (can't type, can't read English, can't read small print, doesn't trust AI, needs family to act). If it only decorates, cut it.

## Rules

- **One** X factor. A second only if it costs nothing (option E or F) and there's time.
- Demoable in 10 seconds on stage, with one tap.
- At most one Gemini call per use. The free key has about 20 calls a day.
- Has a fallback and fails safe: if it breaks, the golden path still works and nothing reassuring is shown by mistake.
- Built on top of a **deployed** app. If it isn't working by **minute 120**, hide it and move on.

## Menu (all tested on 13 Nov in project `pw-bhopal-1114`)

**A. Speak instead of type.** Browser Web Speech API (`window.SpeechRecognition || window.webkitSpeechRecognition`, `lang` `hi-IN` or `en-IN`). No key, no quota. A mic button beside the main field fills the field; the user still presses the main button. Hide the mic if the API is missing. Works best in Chrome. Keep example chips for a noisy hall.

**B. Hear the answer.** Google Cloud Text-to-Speech, enabled in the project and paid from the Cloud trial credit, so no Gemini quota.
- Voices tested: `hi-IN-Chirp3-HD-Achernar`, `hi-IN-Chirp3-HD-Alnilam` (natural). Also available: `en-IN`, `bn-IN`, `gu-IN`, `kn-IN`, `ml-IN`, `mr-IN`, `pa-IN`, `ta-IN`, `te-IN`, `ur-IN`.
- REST: `POST https://texttospeech.googleapis.com/v1/text:synthesize` with `{"input":{"text":...},"voice":{"languageCode":"hi-IN","name":...},"audioConfig":{"audioEncoding":"MP3"}}`; the reply's `audioContent` is base64 MP3.
- Auth on Cloud Run: `google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])` with `google.auth.transport.requests.AuthorizedSession`. The runtime service account already has access; no key. Pin `requests==2.34.2` in `requirements.txt` if imported.
- Locally without credentials: fall back to the browser's `speechSynthesis`, or hide the button. Never crash.
- A server route returns `audio/mpeg`. Cap text at 600 characters, cache by text hash, never autoplay. A "Listen" button plus an `<audio controls>` element.

**C. Point the camera.** Gemini reads a photo of a bill, medicine strip, letter or SMS screenshot.
- Tested: `gemini-3.5-flash-lite` read a sample bill in 2.8 s and returned JSON (amount, due date, one Hindi sentence).
- `types.Part.from_bytes(data=..., mime_type=...)` plus a `response_schema`.
- `<input type="file" accept="image/*" capture="environment">` opens the phone camera.
- Accept JPG, PNG or WebP only, 4 MB max, check the file's magic bytes, keep it in memory, never store or log it.
- Numbers it reads go through `logic.py`: for example, days until the due date is computed in code, not by the AI.
- Ship one sample image in `static/` so the demo works with one tap.

**D. Trust you can see.** Answers come only from a small `sample_data.json` of real official facts (helplines, schemes, rules), each with an ID and an official link. The model must cite IDs; the code checks every cited ID was sent. If not, it says "I don't know" and links the official source. Show "Checked against N official sources". (Gemini's Google Search grounding is untested on this free key; test it once before relying on it.)

**E. Hand it to family.** No keys, no quota, Google and Indian everyday tools:
- WhatsApp: `https://wa.me/?text=` plus the URL-encoded summary.
- Google Calendar: `https://calendar.google.com/calendar/render?action=TEMPLATE&text=...&dates=YYYYMMDDTHHMMSSZ/YYYYMMDDTHHMMSSZ&details=...` (dates computed in `logic.py`).
- Google Maps: `https://www.google.com/maps/search/?api=1&query=...`

**F. Their language.** An English and Hindi switch: Gemini answers in the chosen language through the system instruction; UI labels come from a small dictionary.

## Pairings that fit past briefs

- Seniors, low literacy, documents: **C + B**: "point the phone, hear it in Hindi". Zero typing, zero reading.
- Workers on the move: **A + E**: speak it, send it on WhatsApp.
- Safety, money, health: **D**, plus the fail-safe rule.
- Travel and culture: **E** (Maps) **+ B** (a local storyteller's voice).

## Avoid on the day

Image generation (slow, costly, rarely solves the pain), real-time voice conversation (too risky in 3 hours), the Maps JavaScript API (needs a key and billing), login or a database, and anything not on this list unless you've tested it.

## How to run this skill

**During planning (minute 15 to 25):** read `BRIEF.md`. Propose the best two options for this user, each with: the barrier it removes, the 10-second demo moment, the risk, the minutes to build. Stop. The owner picks one and writes it under `## X factor` in `BRIEF.md`. Add it to the plan as the step after the first deploy.

**After the first deploy (minute 95 to 115):** build only the chosen option, in the Antigravity lane, behind its fallback. Run it locally, then `/pw-deploy`, then try it on a phone. Tell the owner the exact tap sequence for the demo.

**Then, in the Claude Code lane:** tests with Text-to-Speech and Gemini mocked (no network); the README's Google services table gets a row for any new service with its file; one sentence in the README on why this X factor matters for this user.

**Pitch line:** one sentence that ties it to the user's barrier, for example: "Kamla ji can't read the small print, so she points her phone at the bill and hears it in Hindi."
