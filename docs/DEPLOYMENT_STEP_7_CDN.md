# Step 7 — CDN (CloudFront)

Part of `DEPLOYMENT_PLAN.md`. Builds on the storage buckets (Step 5) and the
ACM cert + `cms-origin` record (Step 6). Two distributions — one static, one
in front of the dynamic Directus app.

## 1. Astro static site distribution

Origin Access Control (OAC), not the older OAI, since it's the current
AWS-recommended way to let CloudFront read a private bucket:

```hcl
resource "aws_cloudfront_origin_access_control" "astro_static" {
  name                              = "scaio-astro-static"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "astro_static" {
  enabled             = true
  default_root_object = "index.html"
  aliases             = [var.domain_name, "www.${var.domain_name}"]

  origin {
    domain_name              = aws_s3_bucket.astro_static.bucket_regional_domain_name
    origin_id                = "astro-static"
    origin_access_control_id = aws_cloudfront_origin_access_control.astro_static.id
  }

  default_cache_behavior {
    target_origin_id       = "astro-static"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods          = ["GET", "HEAD"]
    cache_policy_id         = "658327ea-f89d-4fab-a63d-7e88639e58f6" # AWS managed "CachingOptimized"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.cdn.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Feature = "cdn"
    Name    = "scaio-astro-static"
  }
}
```

Bucket policy granting only this distribution's OAC read access (added to
`s3.tf` from Step 5, referencing the distribution created here):

```hcl
data "aws_iam_policy_document" "astro_static_oac" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.astro_static.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.astro_static.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "astro_static" {
  bucket = aws_s3_bucket.astro_static.id
  policy = data.aws_iam_policy_document.astro_static_oac.json
}
```

## 2. Directus/CMS distribution

Custom origin at `cms-origin.scaiodellamontagna.it` (Step 6), HTTPS only.
Cache policy: honor whatever `Cache-Control` Directus itself sets (per
`PROJECT_SPEC.md`'s asset-cache section, Directus already sets
`ASSETS_CACHE_TTL` correctly) rather than imposing CloudFront's own TTLs;
forward cookies + `Authorization` (needed for the admin panel/API) and all
query strings (needed for `?width=&quality=` asset transforms).

```hcl
resource "aws_cloudfront_cache_policy" "directus" {
  name        = "scaio-directus"
  default_ttl = 0
  max_ttl     = 31536000
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "all"
    }
    headers_config {
      header_behavior = "whitelist"
      headers { items = ["Authorization", "Host"] }
    }
    query_strings_config {
      query_string_behavior = "all"
    }
  }
}

resource "aws_cloudfront_distribution" "directus" {
  enabled = true
  aliases = ["${var.cms_subdomain}.${var.domain_name}"]

  origin {
    domain_name = "cms-origin.${var.domain_name}"
    origin_id   = "directus"
    custom_origin_config {
      http_port              = 80
      https_port              = 443
      origin_protocol_policy  = "https-only"
      origin_ssl_protocols    = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "directus"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods          = ["GET", "HEAD"]
    cache_policy_id         = aws_cloudfront_cache_policy.directus.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.cdn.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Feature = "cdn"
    Name    = "scaio-directus"
  }
}
```

## 3. DNS records pointing at both distributions

Back in `route53.tf` (Step 6's file), now that the distributions exist:

```hcl
resource "aws_route53_record" "apex" {
  zone_id = aws_route53_zone.root.zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.astro_static.domain_name
    zone_id                = aws_cloudfront_distribution.astro_static.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.root.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.astro_static.domain_name
    zone_id                = aws_cloudfront_distribution.astro_static.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "cms" {
  zone_id = aws_route53_zone.root.zone_id
  name    = "${var.cms_subdomain}.${var.domain_name}"
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.directus.domain_name
    zone_id                = aws_cloudfront_distribution.directus.hosted_zone_id
    evaluate_target_health = false
  }
}
```

## 4. Close the loop on Step 2's IAM policy

Now that `aws_s3_bucket.astro_static`, `aws_s3_bucket.directus_uploads`,
`aws_s3_bucket.db_backups`, and `aws_cloudfront_distribution.astro_static`
all exist, uncomment/finish the `aws_iam_role_policy.app` block from
`DEPLOYMENT_STEP_2_NETWORKING_IAM.md` — its resource references now resolve.

## Done when

- `terraform plan` shows both distributions, the OAC + bucket policy, the
  custom cache policy, and the three DNS alias records.
- (After apply + DNS propagation) `https://scaiodellamontagna.it` and
  `https://cms.scaiodellamontagna.it` both resolve through CloudFront with a
  valid cert (even before real content is deployed — Step 5's empty bucket
  will just 403/404, and Directus needs Step 9's Caddy running first).
