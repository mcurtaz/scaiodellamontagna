# Step 2 — Networking & IAM

Part of `DEPLOYMENT_PLAN.md`. Builds on `DEPLOYMENT_STEP_1_FOUNDATIONS.md`'s
providers/variables. No custom VPC — the account's default VPC/subnets are
used as data sources; a dedicated VPC is unnecessary complexity for a single
instance.

## 1. Default VPC data sources

`terraform/network.tf`:

```hcl
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
```

## 2. Security group

`terraform/security_groups.tf` — one SG for the instance:

```hcl
resource "aws_security_group" "app" {
  name        = "scaio-app"
  description = "Scaio della Montagna app server"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH from admin IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  ingress {
    description = "HTTP (Let's Encrypt HTTP-01 + CloudFront)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS (CloudFront -> Caddy)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Feature = "network"
    Name    = "scaio-app"
  }
}
```

80/443 are open to the world on purpose: CloudFront doesn't originate from a
fixed, easily-allowlisted IP range for this kind of setup, and Let's Encrypt's
HTTP-01 challenge needs port 80 reachable from the public internet too.

## 3. Elastic IP

Allocated here, associated to the instance in Step 4 (kept in this file
since it's a networking resource, tagged `Feature = "network"`):

```hcl
resource "aws_eip" "app" {
  domain = "vpc"

  tags = {
    Feature = "network"
    Name    = "scaio-app"
  }
}
```

Note: AWS bills a small flat rate per public IPv4 address regardless of
whether it's attached to a running or stopped instance (2024 pricing) — this
doesn't change based on the EC2 power-control variable in Step 4, and isn't
worth working around for a few cents/month.

## 4. EC2 IAM role & instance profile

`terraform/iam.tf` — the role the instance assumes, granting exactly what it
needs and nothing else:

```hcl
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "scaio-app"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    Feature = "compute"
    Name    = "scaio-app"
  }
}

resource "aws_iam_instance_profile" "app" {
  name = "scaio-app"
  role = aws_iam_role.app.name

  tags = {
    Feature = "compute"
    Name    = "scaio-app"
  }
}
```

The actual permission policy (SSM read on `/scaio/*`, S3 read/write on the
three app buckets, `cloudfront:CreateInvalidation` on the astro
distribution) is attached here but references resources created in later
steps (Steps 3, 5, 7) — write it as a single `aws_iam_role_policy` once those
ARNs exist, rather than half-defining it now. Come back to this file at the
end of Step 7 to fill in:

```hcl
data "aws_iam_policy_document" "app" {
  statement {
    sid       = "ReadSecrets"
    actions   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
    resources = ["arn:aws:ssm:${var.aws_region}:*:parameter/scaio/*"]
  }

  statement {
    sid     = "AppBuckets"
    actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [
      aws_s3_bucket.astro_static.arn, "${aws_s3_bucket.astro_static.arn}/*",
      aws_s3_bucket.directus_uploads.arn, "${aws_s3_bucket.directus_uploads.arn}/*",
      aws_s3_bucket.db_backups.arn, "${aws_s3_bucket.db_backups.arn}/*",
    ]
  }

  statement {
    sid       = "InvalidateAstroCdn"
    actions   = ["cloudfront:CreateInvalidation"]
    resources = [aws_cloudfront_distribution.astro_static.arn]
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "scaio-app"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}
```

## Done when

- `terraform plan` shows the SG, EIP, IAM role/instance profile as
  to-be-created (the `aws_iam_role_policy` block stays commented out /
  deferred until Step 7's resources exist).
- No SSH access exists yet at this point — that's Step 4.
