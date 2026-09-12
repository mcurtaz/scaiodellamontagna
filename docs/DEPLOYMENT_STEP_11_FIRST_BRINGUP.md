# Step 11 — First bring-up

Part of `DEPLOYMENT_PLAN.md`. The one-time manual checklist to go from
"Terraform + repo changes exist" to "site is live" — everything before this
step is provisioning code; this step is where it's actually run for the
first time, in order.

## 1. Terraform state bucket (manual, predates everything else)

```bash
aws s3 mb s3://scaio-terraform-state --region eu-south-1
aws s3api put-bucket-versioning \
  --bucket scaio-terraform-state \
  --versioning-configuration Status=Enabled
```

Must exist before `terraform init` in Step 1, since it's the backend itself
— it's the one resource in this whole plan deliberately kept outside
Terraform's own management.

## 2. SSH keypair

```bash
ssh-keygen -t ed25519 -f ~/.ssh/scaio-app -C "scaio-app"
```

Public key (`~/.ssh/scaio-app.pub`) goes into `terraform/terraform.tfvars`
as `ssh_public_key`. Private key stays local, never touches Terraform state.

## 3. `terraform/terraform.tfvars`

Gitignored. Populate every sensitive variable from Step 1
(`postgres_password`, `directus_secret`, etc. — generate fresh random values
for anything that's currently a placeholder in the local `.env`), plus
`allowed_ssh_cidr = "<your IP>/32"` and `ssh_public_key`.

## 4. Apply

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Creates everything from Steps 1–8: networking, IAM, secrets, the EC2
instance, storage, DNS zone + ACM cert, CloudFront, and the budget.

## 5. Register the domain

Take `terraform output route53_nameservers` and register
`scaiodellamontagna.it` (wherever the user chooses to register it),
pointing it at those nameservers. DNS propagation can take up to 48 hours,
though usually much less.

## 6. Confirm the budget subscription

Check `mcurtaz@gmail.com` for an AWS Budgets subscription-confirmation email
and confirm it — alerts won't deliver otherwise (see
`DEPLOYMENT_STEP_8_BUDGET.md`).

## 7. First SSH login

```bash
ssh -i ~/.ssh/scaio-app ubuntu@$(terraform output -raw ec2_public_ip)
```

On the instance:

```bash
# Deploy key for the private repo — add its public half as a GitHub deploy key first
git clone git@github.com:<you>/scaiodellamontagna.git app
cd app

# Render .env from SSM (Step 3) — needs the ASTRO_CLOUDFRONT_DISTRIBUTION_ID
# appended once (see DEPLOYMENT_STEP_10_DEPLOY_PIPELINE.md)
bash scripts/render-env-from-ssm.sh

docker compose up -d
```

## 8. One-time data migration

- Existing locally-uploaded Directus files: `aws s3 sync .directus-data/uploads/
  s3://scaio-directus-uploads/` (per `PROJECT_SPEC.md` — a file copy, not a
  DB migration).
- First Astro deploy: `scripts/deploy.sh astro` from your machine.

## 9. Nightly cron

```bash
crontab -e
# add: 0 2 * * * /bin/bash /home/ubuntu/app/deploy/rebuild-astro.sh >> /home/ubuntu/rebuild-astro.log 2>&1
```

## End-to-end verification

- `curl -I https://cms.scaiodellamontagna.it` returns a Directus response
  through CloudFront/Caddy with a valid certificate.
- `curl -I https://scaiodellamontagna.it` returns the Astro static site.
- Log into the Directus admin at `https://cms.scaiodellamontagna.it/admin`.
- Press "Rebuild sito" (`DEPLOYMENT_STEP_10_DEPLOY_PIPELINE.md`'s Flow) and
  confirm the live site updates within a couple of minutes.
- Confirm a nightly backup lands in `scaio-db-backups` (can trigger
  `deploy/dump-and-upload.sh` manually to avoid waiting for 03:00) and that
  the 30-day lifecycle rule actually expires an old object (temporarily set
  to 1 day to test, then revert to 30 in `s3.tf`, `terraform apply` again).
- Flip `ec2_running = false` in `terraform.tfvars`, `terraform apply`,
  confirm the instance stops without losing data; flip back to `true` and
  confirm the whole stack (`docker compose ps`) comes back up on its own —
  add `restart: unless-stopped` (already the case for every service in
  `docker-compose.yml`) is what makes this automatic on instance boot.
- A day after first boot, check
  `/var/log/unattended-upgrades/unattended-upgrades.log` on the instance for
  a completed run.
- Update `docs/PROJECT_SPEC.md`'s Infrastructure section to point at this
  plan as the implemented (not just researched) direction, once everything
  above is verified.
