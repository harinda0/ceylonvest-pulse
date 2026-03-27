Deploy the current changes to Railway via GitHub.

Steps:
1. Run `git status` to check for uncommitted changes
2. Run `git diff --stat` to review what changed
3. If there are changes, stage and commit with a descriptive message
4. Push to GitHub: `git push origin HEAD`
5. Check that the push succeeded
6. Remind: Railway auto-deploys from the main branch — if on a feature branch, merge to main first or push to main

Important:
- Never commit `.env`, `data/pulse.db`, or `data/test_*.png`
- Never force push
- If on a feature branch, suggest creating a PR instead of pushing directly to main
