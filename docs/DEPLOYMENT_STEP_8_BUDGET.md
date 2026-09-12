# Step 8 — Cost controls (AWS Budget)

Part of `DEPLOYMENT_PLAN.md`. One AWS Budgets resource, no SNS topic needed —
`aws_budgets_budget` supports emailing subscribers directly.

## 1. Budget + notifications

```hcl
resource "aws_budgets_budget" "monthly" {
  name         = "scaio-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}
```

Defaults from Step 1: `budget_limit_usd = 20`, `budget_alert_email =
"mcurtaz@gmail.com"`. `aws_budgets_budget` doesn't currently support the
provider's `default_tags`/resource `tags` argument in the same way other
resources do (a Budgets API limitation) — no `Feature`/`Name` tag block here,
consistent with the tagging note in `DEPLOYMENT_PLAN.md` about resources the
AWS API itself doesn't let you tag.

## Done when

- `terraform plan` shows the budget resource with both notifications.
- After `apply`, AWS emails `mcurtaz@gmail.com` a subscription-confirmation
  message — **it must be confirmed** before any alert will actually be
  delivered (this is standard AWS Budgets/SNS-style opt-in behavior, not a
  bug). Confirm it as part of `DEPLOYMENT_STEP_11_FIRST_BRINGUP.md`'s
  checklist.
- The budget shows up in Billing → Budgets in the console with the $20 limit
  and both thresholds visible.
