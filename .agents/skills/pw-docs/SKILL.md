---
name: pw-docs
description: Write README.md and docs/prompts.md from the real code and BRIEF.md. Use in the Claude Code lane once the app is deployed.
---

Write `README.md` (under 150 lines), factual and pointing to files for each claim, in this order:
1. Product name and one-line promise; live URL; how to try it in 30 seconds (which example to load, and the demo sign-in if there is one).
2. The problem: the challenge text word for word, then the user and their pain in two sentences.
3. What it does: the golden path in 3 steps.
4. How it works: one-line flow diagram, "the AI decides, the code computes", the fallback chain.
5. Google services used: a table of service, what for, file.
6. Evaluation notes: a table of the seven scored areas, what was done, evidence file.
7. Run locally, tests, deploy (commands from `AGENTS.md`).
8. Honest limits.
9. How it was built: Antigravity Planning Mode plus Claude Code, prompts in `docs/prompts.md`.

Also write `docs/submission.md` for the submission form: **Brief** (what it does, for whom, the flow, the demo sign-in if any, under 1,000 characters) and **GenAI services used and where** (model, what each call does, file and function, under 1,000 characters).

Write `docs/prompts.md` as an ordered log of the prompts used, what each produced, and what the owner changed. Only touch `README.md` and `docs/`.
