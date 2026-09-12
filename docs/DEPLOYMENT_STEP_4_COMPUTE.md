# Step 4 — Compute (EC2)

Part of `DEPLOYMENT_PLAN.md`. Builds on the SG/EIP/IAM from
`DEPLOYMENT_STEP_2_NETWORKING_IAM.md`.

## 1. AMI — Ubuntu 24.04 LTS, arm64

```hcl
data "aws_ami" "ubuntu_arm64" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*"]
  }
  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}
```

`t4g.small` (the default from Step 1's `instance_type` variable) is
Graviton/ARM64 — cheaper than the equivalent `t3` (x86) instance for the same
spec. All Docker images this project uses (postgres, directus, python, caddy,
node, aws-cli) publish official multi-arch manifests including `arm64`, so no
image changes are needed anywhere else in the stack for this to work — the
one thing that does need a change is the webhook listener, addressed in
`DEPLOYMENT_STEP_9_DOCKER_COMPOSE.md` (built from source there instead of
pulled as a prebuilt image, specifically to sidestep this).

## 2. Key pair

```hcl
resource "aws_key_pair" "app" {
  key_name   = "scaio-app"
  public_key = var.ssh_public_key

  tags = {
    Feature = "compute"
    Name    = "scaio-app"
  }
}
```

(Only the public key is a Terraform-managed resource/state attribute — the
private key is generated and kept locally, see
`DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`.)

## 3. `user_data` — Docker + unattended-upgrades

```hcl
locals {
  user_data = <<-EOF
    #!/bin/bash
    set -euo pipefail

    # Docker + compose plugin
    apt-get update
    apt-get install -y ca-certificates curl gnupg git awscli jq
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
      https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    usermod -aG docker ubuntu

    # unattended-upgrades: all updates (not just -security), daily, auto-reboot
    apt-get install -y unattended-upgrades
    cat > /etc/apt/apt.conf.d/51scaio-unattended-upgrades <<'CONF'
    Unattended-Upgrade::Origins-Pattern {
      "origin=*";
    };
    Unattended-Upgrade::Automatic-Reboot "true";
    Unattended-Upgrade::Automatic-Reboot-Time "04:00";
    CONF
    cat > /etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
    APT::Periodic::Update-Package-Lists "1";
    APT::Periodic::Unattended-Upgrade "1";
    CONF
  EOF
}
```

`Origins-Pattern { "origin=*"; }` is the part that widens Ubuntu's
out-of-the-box unattended-upgrades (security-only) to *all* package updates,
per the user's requirement.

Cloning the private repo and populating `.env` is **not** done in
`user_data` — it needs a repo credential (a deploy key), which is a
documented first-login step (`DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`), not
something to bake into an instance's boot script.

## 4. The instance

```hcl
resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu_arm64.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name
  key_name               = aws_key_pair.app.key_name
  user_data              = local.user_data

  root_block_device {
    volume_type = "gp3"
    volume_size = 30 # Docker images + Postgres data + Node build add up
  }

  tags = {
    Feature = "compute"
    Name    = "scaio-app"
  }
}

resource "aws_eip_association" "app" {
  instance_id   = aws_instance.app.id
  allocation_id = aws_eip.app.id
}
```

## 5. Power control — stop/start without destroying anything

Rather than a `count`/destroy-recreate trick, use the dedicated
`aws_ec2_instance_state` resource, which just calls the EC2
start/stop API against the existing instance:

```hcl
resource "aws_ec2_instance_state" "app" {
  instance_id = aws_instance.app.id
  state       = var.ec2_running ? "running" : "stopped"
}
```

Flipping `ec2_running = false` in `terraform.tfvars` and re-applying stops
the instance; flipping it back starts it. The `aws_instance` resource, its
EBS root volume, and the Elastic IP are untouched either way — nothing is
reprovisioned, no data is lost, and the box comes back exactly as it was.

## Done when

- `terraform plan` shows the AMI data source resolving to an arm64 Ubuntu
  24.04 image, the key pair, instance, EIP association, and instance-state
  resource.
- (After Step 11's first apply) `ssh ubuntu@<eip> 'docker --version && docker
  compose version'` succeeds.
- A day after first boot, `/var/log/unattended-upgrades/unattended-upgrades.log`
  on the instance shows a run.
- Toggling `ec2_running` and re-applying actually stops/starts the instance
  (verify in the EC2 console or `aws ec2 describe-instances`).
