# Metrics schema

*Owner: Marty. `data/metrics.json` is the single source of truth for
`dashboard/index.html`. This file says what each number means, where it comes
from, and who is responsible for it.*

## Rules

1. **`null` means "not measured."** It never means zero. Do not put `0` in a
   field to make a chart look tidy.
2. **Every non-null value needs a `source` and the file needs an `as_of`.**
   Source is where the number came from: "Shopify Analytics", "Meta Ads
   Manager", "manual count". If you can't name it, don't write it.
3. **`benchmark` is the category benchmark from
   `marketing/research/benchmarks.md`.** It is not our number and it is never
   presented as ours.
4. **`target` is what we're aiming at.** Set deliberately, not aspirationally.
5. **Projections do not live here.** They live in `marketing/strategy.md`,
   clearly labeled.
6. **Append to `history`, never overwrite.** One snapshot per month so cohort
   and trend analysis is possible later.

## The metrics

### North star
**`active_subscribers`** — paying, non-paused subscriptions on the last day of
the month. The only number that matters. Paused subscribers are counted
separately, not here.

### Funnel
| Field | Definition | Where it comes from |
| --- | --- | --- |
| `site_visits` | Sessions on the site, monthly | Storefront analytics |
| `unique_visitors` | Distinct visitors, monthly | Storefront analytics |
| `waitlist_signups` | Cumulative emails captured pre-launch | Email platform |
| `visit_to_signup_rate` | signups ÷ unique visitors | Calculated |
| `signup_to_subscriber_rate` | Of waitlist emails, % who became paying | Calculated at launch |
| `checkout_start` | Began checkout | Storefront |
| `checkout_completion_rate` | Completed ÷ started | Calculated |

### Acquisition
| Field | Definition |
| --- | --- |
| `new_subscribers` | First-time paying subscribers in the month |
| `cac_blended` | All marketing spend ÷ all new subscribers |
| `cac_paid` | Paid spend ÷ subscribers attributed to paid |
| `cac_organic` | Organic cost (mostly hours, valued at $0 cash) ÷ organic subscribers |
| `marketing_spend` | Cash out the door. Includes printing for guerrilla tactics. |

**Attribution warning.** Platform-reported conversions are directional at best
for a business this size. The primary source of truth is the post-purchase "how
did you hear about us?" question. Build it into checkout at launch — it is the
cheapest analytics we will ever have.

### Revenue
| Field | Definition |
| --- | --- |
| `mrr` | active_subscribers × arpu |
| `arpu` | Average revenue per user per month, net of discounts |
| `price_point` | List price |
| `gross_margin` | (revenue − COGS − shipping) ÷ revenue. Patrick's labor counted at a real hourly rate, not zero. |
| `ltv` | arpu × gross_margin × (1 ÷ monthly_churn) |
| `ltv_cac_ratio` | ltv ÷ cac_blended. Below 3:1 means the model isn't working. |

### Retention
| Field | Definition |
| --- | --- |
| `monthly_churn` | Cancels ÷ subscribers at start of month |
| `voluntary_churn` | Customer actively cancelled |
| `involuntary_churn` | Payment failed. Fixable with dunning. |
| `month_2_retention` | % of a cohort still active in month 2. **The most predictive number we will have.** |
| `month_6_retention` | Where a wall-space ceiling would show up |
| `avg_subscriber_lifetime_months` | 1 ÷ monthly_churn |
| `pause_rate` | % choosing pause instead of cancel. Higher is good. |
| `gift_conversion_at_expiry` | % of gift subs converting to self-pay |

### Channels
Per channel: `status` (`not_live` / `testing` / `live` / `off` / `killed`),
platform-native reach metrics, `signups_attributed`, and `spend`.

`signups_attributed` comes from the post-purchase survey, not the platform.

### Cohorts
One object per signup month:
```json
{ "cohort": "2026-11", "size": 100, "retained": { "m1": 100, "m2": null, "m3": null } }
```
Aggregate churn hides everything. Always read cohorts.

### History
One snapshot per month, appended:
```json
{ "month": "2026-11", "active_subscribers": null, "mrr": null, "new_subscribers": null, "churn": null, "cac": null }
```

## Instrumentation Marty needs at launch

Not optional, and all of it is cheap if built before the first customer:

1. **Post-purchase "how did you hear about us?"** — single question, free text
   plus options. The most valuable attribution we will have.
2. **Unique short links / QR codes per guerrilla tactic.** A coaster drop with no
   tracking link teaches us nothing.
3. **Analytics on the storefront** with UTM discipline on every link we post.
4. **Cancel survey** — one free-text question. Read every response personally.
5. **Cohort export** from the subscription platform, monthly.
