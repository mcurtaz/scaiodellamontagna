# Step 10 — Deploy pipeline

Part of `DEPLOYMENT_PLAN.md`. Builds on Step 9's docker-compose services.
Two rebuild scripts live **in the repo**, run on the EC2 instance, so
manual-SSH, nightly cron, and the Directus webhook (Step 9's
`astro-webhook`) all execute the exact same code — no logic duplicated
across triggers.

## 1. In-instance scripts

`deploy/rebuild-backend.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/app
git pull
docker compose up -d --build
```

`deploy/rebuild-astro.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/app
git pull
docker compose --profile tools run --rm astro-builder
aws s3 sync astro/dist s3://scaio-astro-static --delete
aws cloudfront create-invalidation --distribution-id "$ASTRO_CLOUDFRONT_DISTRIBUTION_ID" --paths '/*'
```

`ASTRO_CLOUDFRONT_DISTRIBUTION_ID` comes from Step 7's Terraform output,
added as a plain (non-secret) line in the rendered `.env`
(`DEPLOYMENT_STEP_3_SECRETS.md`'s `render-env-from-ssm.sh` — append it there
once Step 7 is applied and its distribution id is known) and sourced before
running this script, or exported directly in the instance's shell profile.

## 2. Local convenience wrapper

`scripts/deploy.sh` (run from your machine — this is "the script you run
manually"):

```bash
#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:?usage: deploy.sh backend|astro}"
EC2_HOST="ubuntu@<elastic-ip-or-cms-origin-hostname>"

case "$TARGET" in
  backend) ssh "$EC2_HOST" 'bash /home/ubuntu/app/deploy/rebuild-backend.sh' ;;
  astro)   ssh "$EC2_HOST" 'bash /home/ubuntu/app/deploy/rebuild-astro.sh' ;;
  *) echo "unknown target: $TARGET" >&2; exit 1 ;;
esac
```

## 3. Nightly cron (on the instance, not in Terraform)

A crontab entry added during first bring-up
(`DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`), not baked into `user_data` (keeps
`user_data` focused on one-time provisioning, not ongoing app-repo state
that changes independently of the instance):

```
0 2 * * * /bin/bash /home/ubuntu/app/deploy/rebuild-astro.sh >> /home/ubuntu/rebuild-astro.log 2>&1
```

Runs at 02:00, before the backup (03:00) and unattended-upgrades reboot
window (04:00) from Steps 4 and 9 — the three nightly jobs don't overlap.

## 4. Directus "Rebuild sito" Flow

New `docs/DIRECTUS_REBUILD_FLOW.md`, written in the same step-by-step style
as the existing `docs/DIRECTUS_MAP_FLOW.md`:

1. Settings → Flows → Create Flow.
2. Name: `Rebuild sito`.
3. Trigger: **Manual** (not scoped to any collection — shows as a standalone
   button in the Directus admin, e.g. under a "Rebuild" panel).
4. Single **Webhook / Request URL** operation: `POST
   http://astro-webhook:8080/rebuild-astro`.
5. Save.

This deliberately does **not** fire automatically on every `articoli`/
`itinerari` save (autosave/draft edits would trigger a rebuild per keystroke
session) — editors press the button when a piece of content is actually
ready to go live. The nightly cron (above) is the safety net for anything
not manually triggered.

## Done when

- Both `deploy/rebuild-*.sh` scripts are executable and free of syntax
  errors (`bash -n`).
- `scripts/deploy.sh astro` run against the real instance (once Steps 1–9
  are applied) produces a working `https://scaiodellamontagna.it`.
- `scripts/deploy.sh backend` run after a docker-compose change picks it up
  without downtime beyond the affected container's restart.
- The nightly cron entry exists (`crontab -l` on the instance) and a manual
  test run of `rebuild-astro.sh` succeeds before trusting the schedule.
- Pressing "Rebuild sito" in the Directus admin triggers a rebuild and the
  site updates within a couple of minutes.
