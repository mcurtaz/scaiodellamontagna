# Step 5 — Storage (S3)

Part of `DEPLOYMENT_PLAN.md`. Three application buckets — the fourth bucket
mentioned in the plan (`scaio-terraform-state`) is deliberately **not**
managed here (or anywhere in this config): a backend bucket can't be created
by the config that uses it as its own backend. It's created once, manually,
in `DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`.

## 1. `scaio-astro-static`

Private bucket; CloudFront reads it via Origin Access Control (configured in
`DEPLOYMENT_STEP_7_CDN.md`, which also supplies the bucket policy that grants
that OAC read access — added to this file once Step 7 exists).

```hcl
resource "aws_s3_bucket" "astro_static" {
  bucket = "scaio-astro-static"

  tags = {
    Feature = "storage"
    Name    = "scaio-astro-static"
  }
}

resource "aws_s3_bucket_public_access_block" "astro_static" {
  bucket                  = aws_s3_bucket.astro_static.id
  block_public_acls       = true
  block_public_policy     = false # CloudFront OAC policy is attached here
  ignore_public_acls      = true
  restrict_public_buckets = false
}
```

## 2. `scaio-directus-uploads`

Private; Directus's S3 storage driver reaches it through the EC2 instance
role (Step 2's IAM policy), so `STORAGE_S3_KEY`/`STORAGE_S3_SECRET` are never
set anywhere — the AWS SDK picks up instance-metadata credentials
automatically when they're absent.

```hcl
resource "aws_s3_bucket" "directus_uploads" {
  bucket = "scaio-directus-uploads"

  tags = {
    Feature = "storage"
    Name    = "scaio-directus-uploads"
  }
}

resource "aws_s3_bucket_public_access_block" "directus_uploads" {
  bucket                  = aws_s3_bucket.directus_uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "directus_uploads" {
  bucket = aws_s3_bucket.directus_uploads.id
  versioning_configuration {
    status = "Enabled" # protects against accidental delete/overwrite; no separate backup job needed for uploads
  }
}
```

Existing locally-uploaded files still need a one-time `aws s3 sync` copy into
this bucket after it exists (Directus stores just the file id in the DB, not
the storage path, so this is a plain file copy — see `PROJECT_SPEC.md`).

## 3. `scaio-db-backups`

Private, 30-day lifecycle expiry (only Postgres needs this job — uploaded
files are already covered by the bucket versioning above).

```hcl
resource "aws_s3_bucket" "db_backups" {
  bucket = "scaio-db-backups"

  tags = {
    Feature = "storage"
    Name    = "scaio-db-backups"
  }
}

resource "aws_s3_bucket_public_access_block" "db_backups" {
  bucket                  = aws_s3_bucket.db_backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "db_backups" {
  bucket = aws_s3_bucket.db_backups.id

  rule {
    id     = "expire-after-30-days"
    status = "Enabled"
    filter {}
    expiration {
      days = 30
    }
  }
}
```

## Done when

- `terraform plan` shows all three buckets, their public-access blocks, the
  uploads bucket's versioning, and the backups bucket's lifecycle rule.
- (Later, once objects exist) an object older than 30 days in
  `scaio-db-backups` is actually gone — worth testing once with the rule
  temporarily set to 1 day, then reverting to 30, per
  `DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`'s verification checklist.
