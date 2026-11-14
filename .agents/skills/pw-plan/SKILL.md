---
name: pw-plan
description: Plan the app from BRIEF.md in 15-minute build steps, with no code. Use at the start of the main build, after the brief is written and checked.
---

Read `BRIEF.md` and `AGENTS.md`. Plan only; write no code yet.

Give:
1. The file list (follow the structure in `AGENTS.md`).
2. The routes, each with one line on what it returns.
3. The Gemini design: the system instruction text and the JSON response schema.
4. What `logic.py` computes deterministically.
5. The build order as 4 steps of about 15 minutes each. Step 1 is always the full golden path working with a stubbed AI response.
6. Anything not needed for the golden path, flagged so the owner can cut it.
7. The X factor: if `BRIEF.md` names one, add it as the step right after the first deploy. If not, propose the best two from the `/pw-xfactor` menu for this user, one line each.

Then stop and wait for "Approved".
