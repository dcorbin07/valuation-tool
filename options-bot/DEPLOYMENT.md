# Deployment — is there something better than Oracle Cloud?

Short answer: **the host isn't your problem, the deploy pipeline is.** Fix that and Oracle is fine. But there are two real Oracle risks worth five minutes each.

---

## The two Oracle risks, and what to do about them

### 1. Idle reclamation — you are squarely exposed

Verified today from [Oracle's own docs](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), quoted verbatim:

> "Idle Always Free compute instances may be reclaimed by Oracle. Oracle will deem virtual machine and bare metal compute instances as idle if, during a 7-day period, the following are true:
> - CPU utilization for the 95th percentile is less than 20%
> - Network utilization is less than 20%
> - Memory utilization is less than 20% *(applies to A1 shapes only)*"

Your bots run ~13 times a day for well under a minute each. Your 95th-percentile CPU is approximately zero.

And there's a twist that works against you: the **memory** criterion applies only to Ampere A1 shapes. All conditions must be true simultaneously — so your AMD E2.1.Micro is judged on **CPU and network alone**. Fewer conditions to satisfy means *easier* to be flagged. An A1 owner can escape by keeping memory occupied; you have no such lever.

The thresholds have tightened over time — 10% in early 2023, 15% in April 2023, 20% now.

**The fix, and it's free: convert the Oracle account to Pay As You Go.** Always Free resources stay free on a PAYG account, and the policy explicitly scopes to *"Idle **Always Free** compute instances."* Oracle's own reclamation email says: *"You can keep idle compute instances from being stopped by converting your account to Pay As You Go."*

Two honest caveats. That email quote is from 2023 and the current docs page doesn't restate the exemption — it's well-supported, not iron-clad. And the most consistently identified trigger for the account terminations below is **payment-card verification failure**, so if you go PAYG, keep the card current and don't use a virtual card that might fail a $0.01 authorization.

Reclamation *stops* the instance rather than terminating it (boot volume survives), with roughly 7 days' warning — though that comes from Oracle's notification email, not the docs, which say only "reclaimed."

### 2. Your state exists in exactly one place

This matters more than the host. Every documented Oracle free-tier termination story ends identically: no warning, no reason, no appeal, and **no successful data recovery in any case I found**. There were ~10 well-documented instances across 2025-26 on Oracle's own forums.

Counter-evidence is substantial — a large 2025 survey thread is overwhelmingly positive, with users reporting 3-6 years of continuous use and zero terminations, and I found no first-hand idle-reclamation report from 2025 or 2026 at all. Nobody has a base rate and complainants self-select. The risk is real but probably small.

That's exactly the shape of risk you handle with a backup rather than a migration. `deploy/backup_state.sh` mirrors `data/` to a second private repo nightly. Twenty minutes, and it converts "catastrophic and unrecoverable" into "annoying, one hour."

One more thing worth knowing about who you're dealing with: on **15 June 2026 Oracle silently halved the Ampere A1 free allocation** from 4 OCPU/24GB to 2 OCPU/12GB — no blog post, no changelog, no customer email. It doesn't touch your AMD instance. It does tell you how much notice you'd get if the AMD tier changed.

---

## What I'd actually do

**Stay on Oracle.** Not because it's the best host — it isn't — but because for a $0-revenue SIM project the operational pain you've been feeling is entirely in the *deploy flow*, not the host. Moving to a $6/mo box and keeping the zip-through-Cloud-Shell dance would fix nothing.

Three actions, roughly 30 minutes total:

1. Convert the Oracle account to **Pay As You Go** (removes the reclamation risk; still $0)
2. Set up **git-pull deployment** (below) — deletes every gotcha in §7 of the handoff
3. Set up **nightly state backup** to a second private repo

If Oracle ever does give you trouble, the migration is then a 20-minute job: spin up a box anywhere, clone, restore state, run `install_services.sh`.

### If you'd rather just leave

For reference, with current (July 2026) pricing:

| Option | Real cost | Notes |
|---|---|---|
| **DigitalOcean Basic** | **$6.00/mo** | 1 vCPU / 1GB / 25GB. The boring correct answer. Real support, a usable control panel, no reclamation policy. |
| AWS Lightsail | $5.00/mo | 512MB is tight. 3 months free. The $3.50 tier is IPv6-only. |
| Akamai/Linode Nanode | $5.00/mo | 1GB. Solid. |
| GCP e2-micro | $0 + ~$3.65 IPv4 | Still free, us-west1/central1/east1 only, 1GB/mo egress cap. |
| Hetzner (US) | **$20.49/mo** | Was $6.99 in May. Two price rises in 2026. No longer competitive in the US; the €5.49 CX23 is EU-only. |

**Not GitHub Actions.** I looked at it seriously — your ~273 runs/month fit the free tier comfortably, and committing state back to the repo is a legitimate pattern. It fails on timing. GitHub's own docs say scheduled runs "can be delayed during periods of high loads" and that **"some queued jobs may be dropped."** Measured reports show 9-22 minute delays routinely, and one open issue tracks a job degrading to ~4.5 hours average delay. A 10:45 ET rebalance that lands at 11:07 — or silently vanishes — is a data-quality bug you'd never notice.

---

## Setting up git-pull deployment

Replaces: download zip → verify size → delete old → upload via Cloud Shell → `scp` → `ssh` → disable bracketed paste → stop services → `cd ~` → `unzip -o` (from HOME, never from inside the folder) → pip → tests → install services.

With this: **one command.**

### One-time, on the box

```bash
ssh -i ~/ssh-key-2026-05-29.key ubuntu@141.148.45.115

# 1. Generate a deploy key
ssh-keygen -t ed25519 -C "quant-bots oracle box" -f ~/.ssh/id_ed25519_quantbots -N ""
cat ~/.ssh/id_ed25519_quantbots.pub          # copy this whole line

# 2. Trust github.com — VERIFY the fingerprint, don't blindly accept
ssh-keyscan -t ed25519 github.com > /tmp/gh_key
ssh-keygen -lf /tmp/gh_key
#    must print exactly:
#    SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU
cat /tmp/gh_key >> ~/.ssh/known_hosts && rm /tmp/gh_key
```

### One-time, on GitHub

Your repo → **Settings → Deploy keys → Add deploy key** → paste the public key → title it "oracle box" → **leave "Allow write access" UNCHECKED.**

Read-only is the point. If the box is ever compromised, the attacker gets read access to one repo — not write access to your code, and not a shell that GitHub can invoke.

### One-time, back on the box

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile /home/ubuntu/.ssh/id_ed25519_quantbots
    IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

`IdentitiesOnly yes` matters — without it, ssh offers every key it can find, GitHub matches the wrong one, and you get a baffling "Repository not found."

Now convert the existing directory into a clone. Your `.env` and `data/` are NOT in the repo, so they survive:

```bash
cd ~
cp -a quant_bots quant_bots_backup_$(date +%F)     # belt and braces
sudo systemctl stop trend-bot momentum-bot options-bot reversion-bot

cd ~/quant_bots
git init -b main
git remote add origin git@github.com:YOURNAME/YOURREPO.git
git fetch origin
git reset --hard origin/main        # code now matches GitHub; .env and data/ untouched (gitignored)
ls -la .env && ls data/sim/          # confirm both survived

python3 -m venv venv 2>/dev/null || true
source venv/bin/activate && pip install -r requirements.txt
bash deploy/install_services.sh
```

### From then on

From Windows, without logging in:

```
ssh -i ~/ssh-key-2026-05-29.key ubuntu@141.148.45.115 "bash ~/quant_bots/deploy/deploy.sh"
```

`deploy.sh` refuses to proceed if the working tree is dirty, fast-forwards only (never merges), installs dependencies and **runs both test suites before touching a single service** — so a bad commit stops the deploy while the old bots are still running happily. It reports the commit range it deployed and the resulting service status.

Full flow becomes: edit locally → `push_to_github.bat` → one ssh command. Nothing to upload, nothing to unzip, no bracketed paste, no way to nest `quant_bots/quant_bots/`.

---

## One thing to fix while you're in there

**Move `data/` out of the repo working tree.** It's gitignored, but that is not protection: `git clean -fdx` deletes ignored files, and it's precisely the command you'll reach for when a pull goes wrong. Systemd's `StateDirectory=` is the clean answer — it creates the directory, sets ownership, and exports `$STATE_DIRECTORY` to the service.

I haven't done this yet because it requires changing every service unit and the path handling in `sim_paths()` / the journal, and I'd rather do it deliberately than as a footnote. It's on the list.

---

## Sources

- [Oracle Always Free resources — reclamation policy](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Oracle Free Tier FAQ](https://www.oracle.com/cloud/free/faq/) (30-day idle-account language, which contradicts the 60 days in the OCI docs)
- [Oracle community: reclamation of idle compute instances](https://community.oracle.com/customerconnect/discussion/671904/reclamation-of-idle-compute-instances)
- [InfoQ: Oracle quietly cuts free-tier Ampere resources](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
- [LowEndTalk: do you still use Oracle free tier?](https://lowendtalk.com/discussion/210471/do-you-still-use-oracle-cloud-free-tier-if-yes-how-long-have-you-been-using-it) (the positive counter-evidence)
- [GitHub Actions: events that trigger workflows — schedule delays](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [actions/runner#4468 — scheduled workflow delay tracking](https://github.com/actions/runner/issues/4468)
- [Hetzner price adjustments 2026](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
