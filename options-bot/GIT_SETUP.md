# Git + daily auto-push — setup

Three `.bat` files. You run two of them once, ever. The third runs itself.

## What you need first

**Git for Windows** — https://git-scm.com/download/win

Accept every default. The one that matters is **Git Credential Manager**, which is enabled by default; it's what remembers your GitHub login so the daily push doesn't need a password. After installing, close any open Command Prompt windows — new ones pick up the changed PATH.

## Step 1 — create the GitHub repo

1. https://github.com/new
2. Name it whatever you like (`quant-system` is fine)
3. **Private**
4. **Do not** tick "Add a README" — the repo must be completely empty
5. Create it, then copy the `https://github.com/...` URL

You already have `dcorbin07/quant_bots`. You can point at that instead if you'd rather — but it isn't empty, so the first push would be rejected. Cleanest is a new empty repo covering everything (bots + screener + backtests in one place), which is also what makes a single daily push sensible.

## Step 2 — run `setup_git.bat`

Double-click it. It asks for the URL you just copied, then:

- creates the repository in this folder
- **checks that no `.env` is about to be committed and aborts if one is**
- makes the first commit
- pushes

A browser window opens once, asking you to sign in to GitHub. That's Credential Manager. Sign in and it won't ask again.

## Step 3 — run `setup_daily_push.bat`

Double-click it. It asks what time to run (default 18:00) and registers a Windows scheduled task called **Porkbelly Daily GitHub Push**.

The task runs as you, while you're logged in. If the laptop is off at 18:00, Windows runs it the next time you're on. That's the right behavior for a laptop — no stored password, no surprises.

## After that

| Want to | Do |
|---|---|
| Push right now | double-click `push_to_github.bat` |
| See what happened | open `push_log.txt` |
| Check the task exists | `schtasks /query /tn "Porkbelly Daily GitHub Push"` |
| Run the task now | `schtasks /run /tn "Porkbelly Daily GitHub Push"` |
| Change the time | run `setup_daily_push.bat` again |
| Stop the daily push | `schtasks /delete /tn "Porkbelly Daily GitHub Push" /f` |

`push_to_github.bat` is safe to run when nothing has changed — it says "No changes to push" and exits.

## The secrets guard

Both `setup_git.bat` and `push_to_github.bat` stage everything, then check the staged list for any file named `.env` before committing. If one appears they unstage everything and abort without pushing. `.env.example` is explicitly allowed through — it's a blank template and belongs in the repo.

That's a backstop, not the primary defence. The primary defence is `.gitignore`, which excludes `.env`, `*.key`, `*.pem`, `oracle_keys/`, all `data/` runtime directories, logs, `venv/`, and `__pycache__`.

**Verified in a scratch repo**: with real `.env` files present in both `quant_bots/` and `screener/`, plus a `data/sim/` book, service logs, and a stray zip — 136 files stage, zero secrets, both `.env.example` templates included. Force-adding a `.env` triggers the abort.

Worth knowing anyway: if a secret ever does reach GitHub, deleting it in a later commit does **not** remove it — it stays in the history and must be treated as leaked. Rotate the key immediately rather than trying to scrub it.

## If the push fails

Almost always an expired GitHub sign-in. Double-click `push_to_github.bat` by hand and sign in when the browser opens; the scheduled task resumes working after that.

Anything else — send me the contents of `push_log.txt`.

## What this does not do

It pushes your **local** folder. The Oracle box is separate and stays on the zip-and-scp flow from §7 of the handoff. If you'd rather deploy by pulling from GitHub on the box, say so — it's a real improvement over uploading zips through Cloud Shell, and it's about ten minutes of setup.
