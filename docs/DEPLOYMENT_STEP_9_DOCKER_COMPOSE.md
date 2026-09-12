# Step 9 — docker-compose additions

Part of `DEPLOYMENT_PLAN.md`. Everything from here on is application-repo
changes, not Terraform — this is where the infrastructure from Steps 1–8
gets used by the actual stack. Builds on the existing `docker-compose.yml`
(`postgres`, `directus`, `map-generator` services already defined).

## 1. Directus — move to S3

```yaml
  directus:
    environment:
      # ...existing vars unchanged...
      PUBLIC_URL: https://cms.scaiodellamontagna.it
      STORAGE_LOCATIONS: s3
      STORAGE_S3_DRIVER: s3
      STORAGE_S3_BUCKET: scaio-directus-uploads
      STORAGE_S3_REGION: eu-south-1
      # No STORAGE_S3_KEY / STORAGE_S3_SECRET — the EC2 instance role
      # (Step 2) supplies credentials via the AWS SDK's default chain.
```

Drop the `STORAGE_LOCAL_ROOT` env var and the
`./.directus-data/uploads:/directus/uploads` volume mount — no longer needed.

## 2. `caddy` — TLS termination in front of Directus

New `Caddyfile` at repo root:

```
cms-origin.scaiodellamontagna.it {
	reverse_proxy directus:8055
}
```

`docker-compose.yml` addition:

```yaml
  caddy:
    image: caddy:2
    container_name: scaio_caddy
    restart: unless-stopped
    depends_on:
      - directus
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
```

Caddy issues its own Let's Encrypt certificate for `cms-origin...` the first
time it starts (needs port 80 reachable, per Step 2's security group) — this
is separate from the ACM certificate CloudFront uses for the public `cms.`
hostname (see `DEPLOYMENT_STEP_6_DNS_TLS.md`).

## 3. `backup` — nightly `pg_dump` to S3

New `backup/` directory, mirroring the existing `map-generator/` layout:

`backup/Dockerfile`:

```dockerfile
FROM postgres:16-alpine
RUN apk add --no-cache aws-cli dcron
COPY dump-and-upload.sh /usr/local/bin/dump-and-upload.sh
RUN chmod +x /usr/local/bin/dump-and-upload.sh
COPY crontab /etc/crontabs/root
CMD ["crond", "-f", "-l", "2"]
```

`backup/dump-and-upload.sh`:

```bash
#!/bin/sh
set -eu
FILE="scaio-$(date +%Y%m%d-%H%M%S).sql.gz"
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h postgres -U directus -d directus | gzip > "/tmp/$FILE"
aws s3 cp "/tmp/$FILE" "s3://scaio-db-backups/$FILE"
rm "/tmp/$FILE"
```

`backup/crontab` (one line — nightly at 03:00, before the unattended-upgrades
04:00 reboot window from `DEPLOYMENT_STEP_4_COMPUTE.md`):

```
0 3 * * * /usr/local/bin/dump-and-upload.sh >> /var/log/backup.log 2>&1
```

`docker-compose.yml` addition:

```yaml
  backup:
    build: ./backup
    container_name: scaio_backup
    restart: unless-stopped
    depends_on:
      - postgres
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

(Relies on the instance role for S3 write access — no AWS keys in this
container's env either.)

## 4. `astro-builder` — the build, on-demand only

New top-level `profiles` usage so this never starts with a plain `docker
compose up -d`:

```yaml
  astro-builder:
    build:
      context: ./astro
    profiles: ["tools"]
    environment:
      DIRECTUS_URL: http://directus:8055
      DIRECTUS_TOKEN: ${DIRECTUS_TOKEN}
      PUBLIC_SITE_URL: ${PUBLIC_SITE_URL}
    volumes:
      - ./astro/dist:/app/dist
    command: ["npm", "run", "build"]
```

New `astro/Dockerfile` (build-only, not a runtime server):

```dockerfile
FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
```

Invoked only as `docker compose --profile tools run --rm astro-builder` —
see `DEPLOYMENT_STEP_10_DEPLOY_PIPELINE.md`.

## 5. `astro-webhook` — internal-only rebuild trigger

New `deploy/webhook/` directory — built from source (not a pulled image),
specifically so architecture (Graviton/arm64, per
`DEPLOYMENT_STEP_4_COMPUTE.md`) is a non-issue:

`deploy/webhook/app.py`:

```python
import subprocess
from flask import Flask

app = Flask(__name__)

@app.post("/rebuild-astro")
def rebuild_astro():
    result = subprocess.run(["/bin/sh", "/deploy/rebuild-astro.sh"], capture_output=True, text=True)
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}, \
           (200 if result.returncode == 0 else 500)
```

`deploy/webhook/Dockerfile`:

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir flask gunicorn
WORKDIR /app
COPY app.py .
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
```

`docker-compose.yml` addition — **no `ports:` entry**, so it's unreachable
from outside the compose network:

```yaml
  astro-webhook:
    build: ./deploy/webhook
    container_name: scaio_astro_webhook
    restart: unless-stopped
    volumes:
      - ./deploy:/deploy:ro
      - /var/run/docker.sock:/var/run/docker.sock # needed to shell out to docker compose
```

Directus reaches it at `http://astro-webhook:8080/rebuild-astro` (Step 10's
Flow).

## Done when

- `docker compose config` validates locally with all four new services
  present.
- Locally, `docker compose --profile tools run --rm astro-builder` produces
  `astro/dist/` without needing it in the default `up -d` set.
- The existing local dev workflow (`STORAGE_LOCATIONS: local`, no S3) still
  works unchanged when these env vars are left at their `.env.example`
  defaults — production-only values (S3 storage, Caddy, backup, webhook)
  only take effect via the production `.env` rendered from SSM
  (`DEPLOYMENT_STEP_3_SECRETS.md`).
