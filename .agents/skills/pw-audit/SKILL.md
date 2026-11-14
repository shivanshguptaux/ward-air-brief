---
name: pw-audit
description: Act as the automated PromptWars reviewer and score the repo on the seven dimensions with the cheapest fixes. Use around minute 140, or any time the owner asks how the repo would score.
---

Read the whole repo and `BRIEF.md`. Do not edit anything.

Score each out of 10, with one line of evidence (file and line):
1. Problem statement alignment (against the challenge text in `BRIEF.md`)
2. Code quality
3. Security
4. Efficiency
5. Testing
6. Accessibility
7. Google services usage

Then list the 5 fixes that would raise the total most, each under 10 minutes, ranked by score gain per minute, each with the exact prompt to paste into the right agent's lane.
