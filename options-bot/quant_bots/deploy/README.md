# deploy/ — systemd services, timers, and one-command install

These define how the bots run autonomously on the Oracle box. They live here
(shipped in the zip) so you never lose them — if you rebuild the box, recreate
everything with one command.

## Files
- `trend-bot.service`, `momentum-bot.service`, `options-bot.service`
  — the three bots as always-on services (start on boot, restart on crash)
- `daily-summary.timer` + `.service` — end-of-day Discord summary, Mon-Fri 21:30 UTC
- `weekly-report.timer` + `.service` — weekly correlation report, Sun 17:00 UTC
- `install_services.sh` — installs all of the above in one command

## Rebuilding the box from scratch
After getting the code onto a fresh box:

```bash
cd ~/quant_bots
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# create ~/quant_bots/.env with your Tradier keys + Discord webhook
bash deploy/install_services.sh
```

That's the whole deployment. The install script is safe to re-run.

## Timezone note
Timers run in UTC. The daily summary fires at 21:30 UTC, which is 5:30pm EDT
(daylight, Mar–Nov) and 4:30pm EST (standard, Nov–Mar) — safely after the 4pm
ET close in both, so it never runs mid-session. No seasonal adjustment needed.
