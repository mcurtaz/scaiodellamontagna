# Step 1 — Terraform foundations

Part of `DEPLOYMENT_PLAN.md`. Everything else lives in a new `terraform/`
directory at repo root and builds on the provider/backend/tagging/variables
set up here.

## 1. State backend

Terraform's own state can't be stored by the same config that creates its
bucket, so the state bucket is created once, manually, before anything else
(see `DEPLOYMENT_STEP_11_FIRST_BRINGUP.md` for the exact command). Once it
exists:

`terraform/backend.tf`:

```hcl
terraform {
  backend "s3" {
    bucket       = "scaio-terraform-state"
    key          = "prod/terraform.tfstate"
    region       = "eu-south-1"
    use_lockfile = true # native S3 locking (Terraform >= 1.9) — no DynamoDB table needed
  }
}
```

## 2. Providers, pinned versions, default tags

`terraform/versions.tf`:

```hcl
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

`terraform/providers.tf`:

```hcl
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Application = "scaio"
      Provider    = "terraform"
      Environment = var.environment
      Schedule    = "manual"
    }
  }
}

# ACM certs used by CloudFront must live in us-east-1 regardless of the main region
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Application = "scaio"
      Provider    = "terraform"
      Environment = var.environment
      Schedule    = "manual"
    }
  }
}
```

Every resource created in later steps only needs to add its own `Feature`/
`Name` tags — `Application`/`Provider`/`Environment`/`Schedule` come from
`default_tags` automatically.

## 3. Shared variables

`terraform/variables.tf` (the full set referenced across every later step —
declared once here so each step doc below only calls out the variables it
actually reads):

```hcl
variable "aws_region" {
  default = "eu-south-1"
}

variable "environment" {
  default = "prod" # a future "test" env is a second tfvars file
}

variable "domain_name" {
  default = "scaiodellamontagna.it"
}

variable "cms_subdomain" {
  default = "cms"
}

variable "instance_type" {
  default = "t4g.small" # Graviton/ARM64
}

variable "ec2_running" {
  type    = bool
  default = true
}

variable "allowed_ssh_cidr" {
  description = "Your IP, as a /32 CIDR. No default on purpose."
  type        = string
}

variable "ssh_public_key" {
  type = string
}

variable "budget_limit_usd" {
  default = 20
}

variable "budget_alert_email" {
  default = "mcurtaz@gmail.com"
}

# Sensitive — every secret currently in .env.example
variable "postgres_password" { sensitive = true }
variable "directus_secret" { sensitive = true }
variable "directus_admin_email" { sensitive = true }
variable "directus_admin_password" { sensitive = true }
variable "directus_token" { sensitive = true }
variable "directus_token_map_generator" { sensitive = true }
variable "maptiler_key" { sensitive = true }
variable "directus_map_generator_folder_id" { sensitive = true }
```

Actual values (except the defaults above) go in a gitignored
`terraform/terraform.tfvars` — add `terraform/terraform.tfvars` and
`terraform/.terraform/` to `.gitignore` alongside the existing `.env` entry.

## Done when

- `terraform/versions.tf`, `providers.tf`, `backend.tf`, `variables.tf` exist.
- `terraform init` succeeds against the (manually pre-created) state bucket.
- `terraform validate` passes with no resources defined yet.
