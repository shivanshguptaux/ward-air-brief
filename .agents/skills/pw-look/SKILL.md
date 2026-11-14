---
name: pw-look
description: UX and visual pass to industry standard. Apply the visual system from AGENTS.md, follow the owner's sketch and reference screenshots if attached, and fix the screen against a UX checklist. Use right after the golden path works with the stub, or when the UI looks unpolished.
---

Run in Claude Code at minute 60, when it holds `templates/` and `static/` (see the handover table in `AGENTS.md`). Do not change behaviour, routes or the AI. Only templates, CSS, front-end JS for motion, and front-end copy. Keep every class, id and form field name that Python or JS relies on.

## 1. Inputs, in order of authority
1. The owner's paper sketch, if attached: follow its layout and order.
2. Reference screenshots, if attached: borrow the **pattern** (structure, hierarchy, how the result is presented), never the brand, colours, logo or wording.
3. The "Visual system" section of `AGENTS.md`: every value as a CSS custom property in `static/styles.css`, no stray hex values or pixel sizes elsewhere. Tune the accent and mood to the user in `BRIEF.md` (for example larger type and a warmer tone for older users), keeping AA contrast.

## 2. UX checklist (fix each one that fails)
- **Layout matches the "Device" in `BRIEF.md`** (rules in `AGENTS.md`). Phone: 480 px column centred on wide screens, sticky header, primary action in a sticky bottom bar; bottom tabs only if there are 2 to 4 real destinations that all work. Desk: top bar, two columns from 1024 px, one column under 768 px. Either way it must work at 360 px.
- **One job per screen.** One primary button, full width on phones, within thumb reach at the bottom of the form. Secondary actions are text buttons.
- **The answer first.** The result opens with the single most useful line in large type (the "moment of value" from `BRIEF.md`), then two or three short labelled sections. No paragraphs over three lines.
- **Familiar patterns** the user already knows from Google Pay, Google Lens or WhatsApp: a card with a clear status at the top, a big primary action, plain labels.
- **Every state designed:** empty (one sentence of what to do plus 2 or 3 example chips), loading (a short status line in plain words, not a spinner alone), result, error (what happened in plain words plus a "Try again" button), and the X factor's fallback.
- **Plain language** at a reading age of about 12, in the user's words from `BRIEF.md`. Hindi text in Devanagari, not transliterated. Labels say what to do ("Take a photo of the leaf"), not what the field is ("Image upload").
- **Trust is visible:** where a number or fact comes from, a "not professional advice" line where it matters, and estimates labelled as estimates.
- **Touch and type:** controls at least 44 px tall, 16 px body minimum (18 px or more for older users), line height 1.5, comfortable spacing between tappable items.
- **No noise:** no emoji as icons, no gradients, no stock images, no shadows. Icons only if inline SVG with a text label.

## 3. Motion
Apply the "Motion" line of the visual system in `AGENTS.md`. Add it last, after the layout is right.

## 4. Check
Run the app locally (`.venv/bin/flask --app main run --port 8080`) and look at it in the browser: 360 px wide and 1280 px, then 200% zoom, then with reduced motion on. Take a screenshot of each, fix anything cut off, crowded, jumpy or needing sideways scrolling, and show the owner the 360 px and 1280 px screenshots.

## 5. Hand back
Commit, say which files you touched, and hand `templates/` and `static/` back to Antigravity at minute 95.

List what changed in one short list, then name the one thing you'd still improve with 10 more minutes.
