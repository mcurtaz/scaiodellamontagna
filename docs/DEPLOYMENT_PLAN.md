# Deployment plan — AWS via Terraform

Status: v1 draft — 2026-09-12.

This document is the reference for how the project goes from local
`docker-compose` (as described in `PROJECT_SPEC.md`'s Infrastructure section)
to running in production on AWS. It complements `PROJECT_SPEC.md` with the
implementation strategy: what infrastructure exists, why, and in what order
it gets built.

## Decisions locked in

- **Compute**: a single small EC2 instance (Graviton/ARM64, `t4g.small` to
  start) runs Postgres + Directus + `map-generator` via docker-compose,
  exactly as today — no managed RDS, no container orchestration platform, on
  purpose (personal-project scale).
- **Directus file storage**: moves from local disk to S3 (already anticipated
  in `PROJECT_SPEC.md`), reached via the EC2 instance's IAM role rather than
  static AWS keys.
- **Backups**: a `backup` container dumps Postgres nightly to S3; a bucket
  lifecycle rule expires backups older than 30 days.
- **Astro build output**: static files in S3, served through CloudFront.
  Confirmed compatible: `astro.config.mjs` has no adapter, so `astro build`
  already produces a pure static `dist/`.
- **Astro build location**: on the EC2 instance itself (not CI), as a
  non-resident docker-compose service invoked on demand — deliberately kept
  in the same self-contained box rather than split across two systems.
- **Rebuild triggers**: manual (you, over SSH), a nightly cron on the
  instance, and a manual "Rebuild sito" button in Directus (a Flow calling an
  internal webhook) — same Flow pattern already used for map generation, see
  `docs/DIRECTUS_MAP_FLOW.md`.
- **TLS in front of Directus**: a Caddy container (automatic Let's Encrypt),
  because CloudFront needs a valid HTTPS origin.
- **Secrets**: AWS SSM Parameter Store, fetched by the EC2 instance's IAM
  role — no static AWS keys anywhere, including inside Directus's own S3
  driver config.
- **Domain**: `scaiodellamontagna.it` (not registered yet — registered once
  the Route53 hosted zone exists, pointed at that zone's nameservers). CMS at
  `cms.scaiodellamontagna.it`.
- **Cost control**: every AWS resource consistently tagged; a monthly AWS
  Budget with email alerts; the EC2 instance can be stopped/started on
  demand via a Terraform variable, since for now the user is the only
  content creator and the instance doesn't need to run 24/7.
- **Patching**: `unattended-upgrades` configured on the instance for all
  package updates (not just security), daily, with auto-reboot if needed.

## Tagging convention (applies to every step below)

Every taggable AWS resource gets:
- `Application = "scaio"`, `Provider = "terraform"`, `Environment = "prod"`
  (a variable, so a future `test` environment is just a second tfvars file),
  `Schedule = "manual"` — set once via the provider's `default_tags` block so
  every resource inherits them automatically.
- A per-resource `Feature` tag, one of: `network`, `compute`, `storage`,
  `dns`, `cdn`, `secrets`, `billing`.
- A per-resource `Name` tag.

Route53 record sets and the ACM certificate-validation resource don't support
tags at the AWS API level — the parent zone/certificate is tagged instead;
that's a normal AWS limitation, not an oversight.

## Build order

1. **Terraform foundations** — state bucket, providers, tagging, shared
   variables → `docs/DEPLOYMENT_STEP_1_FOUNDATIONS.md`
2. **Networking & IAM** — security group, Elastic IP, EC2 instance role →
   `docs/DEPLOYMENT_STEP_2_NETWORKING_IAM.md`
3. **Secrets** — SSM parameters for everything in `.env.example` →
   `docs/DEPLOYMENT_STEP_3_SECRETS.md`
4. **Compute** — EC2 instance (Graviton AMI, user-data: Docker +
   unattended-upgrades), plus the start/stop power control →
   `docs/DEPLOYMENT_STEP_4_COMPUTE.md`
5. **Storage** — the three S3 buckets (astro-static, directus-uploads,
   db-backups) and their policies/lifecycle rules →
   `docs/DEPLOYMENT_STEP_5_STORAGE.md`
6. **DNS & TLS** — Route53 hosted zone, ACM certificate, the `cms-origin`
   record used only for the CloudFront→Caddy hop →
   `docs/DEPLOYMENT_STEP_6_DNS_TLS.md`
7. **CDN** — the two CloudFront distributions (astro-static, directus/cms) →
   `docs/DEPLOYMENT_STEP_7_CDN.md`
8. **Cost controls** — the AWS Budget and its alert thresholds →
   `docs/DEPLOYMENT_STEP_8_BUDGET.md`
9. **docker-compose additions** — `caddy`, `backup`, `astro-builder`,
   `astro-webhook`, plus Directus's S3 env changes →
   `docs/DEPLOYMENT_STEP_9_DOCKER_COMPOSE.md`
10. **Deploy pipeline** — the in-instance rebuild scripts, the local
    `scripts/deploy.sh` wrapper, and the Directus "Rebuild sito" Flow →
    `docs/DEPLOYMENT_STEP_10_DEPLOY_PIPELINE.md`
11. **First bring-up** — the one-time manual bootstrap checklist (state
    bucket, keypair, `terraform apply`, domain registration, first SSH
    login) and end-to-end verification →
    `docs/DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`

## Verification per step

- Steps 1–8 (pure Terraform): `terraform validate` / `terraform plan` clean
  after each step; nothing is `terraform apply`'d for real until Step 11,
  since several resources depend on ones from later steps (e.g. the CDN step
  needs the storage and DNS/TLS steps done first).
- Step 9 (docker-compose): `docker compose config` validates locally; new
  services don't break the existing local dev stack.
- Step 10 (scripts/Flow): dry-run the scripts against the local dev stack
  where possible before relying on them against the real instance.
- Step 11: the full checklist in that doc *is* the end-to-end verification
  for the whole deployment.
