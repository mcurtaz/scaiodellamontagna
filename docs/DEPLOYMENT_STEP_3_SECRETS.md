# Step 3 — Secrets (SSM Parameter Store)

Part of `DEPLOYMENT_PLAN.md`. Every secret currently in `.env.example`
becomes an `aws_ssm_parameter` (type `SecureString`), so `terraform apply`
provisions the secrets store in the same step as the infrastructure —
there's no separate manual `aws ssm put-parameter` bootstrapping.

## 1. Parameters

`terraform/ssm.tf`:

```hcl
locals {
  ssm_secrets = {
    postgres_password                = var.postgres_password
    directus_secret                  = var.directus_secret
    directus_admin_email             = var.directus_admin_email
    directus_admin_password          = var.directus_admin_password
    directus_token                   = var.directus_token
    directus_token_map_generator     = var.directus_token_map_generator
    maptiler_key                     = var.maptiler_key
    directus_map_generator_folder_id = var.directus_map_generator_folder_id
  }
}

resource "aws_ssm_parameter" "secret" {
  for_each = local.ssm_secrets

  name  = "/scaio/${each.key}"
  type  = "SecureString"
  value = each.value

  tags = {
    Feature = "secrets"
    Name    = "scaio-${each.key}"
  }
}
```

This is what Step 2's `ReadSecrets` IAM statement (`/scaio/*`) grants the
instance role read access to.

## 2. Fetching secrets into `.env` on the instance

A small script, `scripts/render-env-from-ssm.sh` (repo-tracked, run once on
first login and again any time a secret changes — see
`DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`):

```bash
#!/usr/bin/env bash
set -euo pipefail

PARAMS=$(aws ssm get-parameters-by-path \
  --path /scaio/ --with-decryption --query 'Parameters[]' --output json)

echo "$PARAMS" | jq -r '.[] | "\(.Name | ltrimstr("/scaio/") | ascii_upcase)=\(.Value)"' > .env

# PUBLIC_URL / DIRECTUS_URL / STORAGE_* aren't secrets — appended as plain values
cat >> .env <<'EOF'
DIRECTUS_URL=http://directus:8055
PUBLIC_SITE_URL=https://scaiodellamontagna.it
STORAGE_LOCATIONS=s3
STORAGE_S3_BUCKET=scaio-directus-uploads
STORAGE_S3_REGION=eu-south-1
EOF

echo "Wrote .env from SSM (${PARAMS_COUNT:-$(echo "$PARAMS" | jq length)} secrets + static values)."
```

Note the uppercase transform only produces the right key names because the
SSM parameter names (`postgres_password`, `directus_secret`, ...) already
match the lowercase form of the `.env.example` keys — keep that
correspondence if new secrets are added later.

## Done when

- `terraform plan` shows 8 `aws_ssm_parameter` resources to create.
- `scripts/render-env-from-ssm.sh` exists and is executable
  (`chmod +x`), even though it can't be tested until an instance with the
  IAM role exists (Step 4) and the parameters have been applied.
