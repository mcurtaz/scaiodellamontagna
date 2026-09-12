# Step 6 — DNS & TLS

Part of `DEPLOYMENT_PLAN.md`. Covers the Route53 hosted zone and the ACM
certificate used by CloudFront. The actual DNS records pointing at
CloudFront are added in `DEPLOYMENT_STEP_7_CDN.md` (they need the
distributions to exist first) — this step creates the zone, the
`cms-origin` record (which does *not* depend on CloudFront), and the cert.

## Why `cms-origin` is a separate hostname from `cms`

CloudFront needs to reach Directus over HTTPS with a cert that's actually
valid for whatever hostname the origin request uses. If the public
`cms.scaiodellamontagna.it` record pointed at CloudFront (as it must, so
browsers can reach the CMS), and CloudFront's *origin* domain were also
`cms.scaiodellamontagna.it`, that's circular — the origin lookup would just
hit CloudFront again.

So: `cms.scaiodellamontagna.it` → alias to the directus CloudFront
distribution (public-facing, Step 7). `cms-origin.scaiodellamontagna.it` →
plain A record straight to the EC2 Elastic IP — this is the hostname Caddy
requests its own separate Let's Encrypt certificate for (not the ACM cert
below), and what CloudFront's custom-origin config points at in Step 7.

## 1. Hosted zone

Created fresh — the domain isn't registered yet.

```hcl
resource "aws_route53_zone" "root" {
  name = var.domain_name

  tags = {
    Feature = "dns"
    Name    = "scaio-root"
  }
}
```

The zone's nameservers (`aws_route53_zone.root.name_servers`, exposed as a
Terraform output) are what get handed to the domain registrar once the
domain is actually registered — see `DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`.

## 2. `cms-origin` record

```hcl
resource "aws_route53_record" "cms_origin" {
  zone_id = aws_route53_zone.root.zone_id
  name    = "cms-origin.${var.domain_name}"
  type    = "A"
  ttl     = 300
  records = [aws_eip.app.public_ip]
}
```

## 3. ACM certificate (us-east-1, for CloudFront)

Covers the two public-facing hostnames CloudFront will serve — **not**
`cms-origin` (Caddy gets its own cert for that one directly from Let's
Encrypt, unrelated to ACM).

```hcl
resource "aws_acm_certificate" "cdn" {
  provider          = aws.us_east_1
  domain_name       = var.domain_name
  subject_alternative_names = [
    "www.${var.domain_name}",
    "${var.cms_subdomain}.${var.domain_name}",
  ]
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Feature = "dns"
    Name    = "scaio-cdn"
  }
}

resource "aws_route53_record" "cdn_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cdn.domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }

  zone_id = aws_route53_zone.root.zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 300
  records = [each.value.value]
}

resource "aws_acm_certificate_validation" "cdn" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.cdn.arn
  validation_record_fqdns = [for r in aws_route53_record.cdn_cert_validation : r.fqdn]
}
```

## Done when

- `terraform plan` shows the hosted zone, the `cms-origin` A record, the ACM
  cert (3 SANs), its validation CNAME records, and the validation resource.
- (After apply, once the domain is registered and nameservers updated at the
  registrar) `dig NS scaiodellamontagna.it` resolves to the zone's Route53
  nameservers, and the ACM certificate's status moves from "Pending
  validation" to "Issued" in the console within a few minutes.
