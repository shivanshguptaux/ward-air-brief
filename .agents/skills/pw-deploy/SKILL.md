---
name: pw-deploy
description: Check the repo, push to GitHub and deploy to Cloud Run, then verify the live URL. Use for the first deploy around minute 90 and for every redeploy.
---

1. Check: `.python-version` is `3.13`; `requirements.txt` is pinned; `.gitignore` and `.gcloudignore` exist; `/health` exists. Run `git grep -n "AIza" || echo clean` and stop if anything is found.
2. Commit with a short message describing what now works. If there is no GitHub remote yet: `gh repo create NAME --public --source . --remote origin --push` (ask the owner for NAME). Otherwise `git push`.
3. Deploy with the command in `AGENTS.md` (ask the owner for the service name the first time).
4. Verify on the live URL: `/health` returns ok, the home page loads, and one real request works with the example input. Never deploy with the stub still in `ai.py`.
5. Report the live URL and the repo URL.

If the deploy fails, read `gcloud builds list --limit 3` and the failing log, then fix the root cause.
