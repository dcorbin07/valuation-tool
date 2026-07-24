# Push this to a private GitHub repo

**Yes — make it private.** It's commercial code with a monetization plan. Secrets
are already git-ignored (`.env`, the SQLite DBs), but the *source itself* is your
IP, so keep the repo private. This folder is already a git repo with an initial
commit, so you only need to create the remote and push.

## Option A — GitHub CLI (easiest, if you have `gh`)
```bash
cd path\to\valuation-tool
gh auth login            # once, if you haven't
gh repo create valuation-tool --private --source=. --remote=origin --push
```
Done — that creates the private repo and pushes `main` in one step.

## Option B — GitHub website + git
1. github.com → **New repository**. Name it (e.g. `valuation-tool`), set **Private**,
   and do **NOT** add a README/.gitignore/license (this repo already has commits).
2. Back in the folder, add the remote and push:
   ```bash
   cd path\to\valuation-tool
   git remote add origin https://github.com/<your-username>/valuation-tool.git
   git branch -M main
   git push -u origin main
   ```
3. **Auth:** for HTTPS, GitHub asks for a username + a **Personal Access Token**
   (Settings → Developer settings → Personal access tokens → *Fine-grained*, repo
   scope) as the "password". Or use SSH if you've set up a key. (Same flow as your
   On The Steps `git_push.bat`.)

## After the first push
- Day-to-day: `git add -A && git commit -m "…" && git push`
- Before every commit, confirm no secrets snuck in: `git status` should never show
  `.env`. It won't — it's ignored — but check after adding new config files.
- **Deploy hooks in:** Render's Blueprint (`render.yaml`) reads directly from this
  repo, so once it's on GitHub you can point Render at it and it deploys on push.

## Safety note
Never commit real API keys or Stripe secrets. They live only in `.env` locally and
in your host's environment-variable settings (Render dashboard) — never in the repo.
