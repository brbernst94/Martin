# Pricing

*Owner: Marty. 2026-09-16. Built on Brian's Current State Breakeven Analysis.*

## The recommendation

**$32/month.** Annual prepay at $320 — two months free, cash up front, zero
involuntary churn for a year.

Not $15. $15 is the number the cost model permits, not the number the business
needs.

## What the cost model actually says

Per-unit variable cost, from Brian's sheet:

| Line | Per unit |
| --- | --- |
| Paper | $0.80 |
| Ink | $0.65 |
| Sticker | $0.75 |
| Envelope | $0.45 |
| Shipping | $0.82 |
| Card processing (2.9% + $0.30) | varies with price |

Fixed monthly: website $23, relief blocks $10, parchment $10 = **$43/month.**

Non-processing variable cost is **$3.47/unit**. Fixed costs are trivial. That
means breakeven is four or five subscribers *at any price in the $15–32 range* —
the cost structure does not pick the price. Positioning and CAC do.

## Why $15 is the wrong number

**1. It puts us in the saturated band.** Ravi Zupa is $10 and Andrea Jacobsen is
$12, both with a signed print and free worldwide shipping. At $15 we are not a
different category, we're a 25% price premium on the same shelf — the worst
place to stand.

**2. It kills paid acquisition permanently.** At $15, contribution per unit is
$10.80. Category-average CAC is ~$72. That's a **seven-month payback**, before
Patrick is paid anything. No paid channel ever clears. We'd be capped at whatever
organic produces, forever.

At $32, contribution is $26.63. CAC payback drops to **under three months** and
LTV:CAC clears 3:1 comfortably at target churn. That's the whole difference
between a business that can scale and one that can't.

**3. It doesn't pay Patrick.** At $15 and 50 subscribers, the sheet shows $497/month
profit. If making and packing 50 bundles is 40 hours, that's **$12/hour** for a
professional printmaker and graphic designer. At $32 the same month clears
~$1,290 — about $32/hour. That's still under his market rate, but it's a
business rather than an expensive hobby.

**4. The price is the positioning.** The strategy is "a working printmaker's
studio practice, delivered." A $15 price argues against that in a way no
amount of copy can fix. Three cocktails in Denver costs more than the bundle;
that comparison should feel obviously favourable, not suspiciously cheap.

## Contribution at each price

| Price | Processing | Total variable | Contribution | Margin | CAC payback @ $72 |
| --- | --- | --- | --- | --- | --- |
| $15 | $0.74 | $4.21 | $10.79 | 72% | 6.7 months |
| $20 | $0.88 | $4.35 | $15.65 | 78% | 4.6 months |
| $25 | $1.03 | $4.50 | $20.50 | 82% | 3.5 months |
| **$32** | **$1.23** | **$4.70** | **$27.30** | **85%** | **2.6 months** |
| $38 | $1.40 | $4.87 | $33.13 | 87% | 2.2 months |

Why not $38: it crosses the line where a subscription box starts getting judged
against genuine luxury goods, and we have no brand equity yet to survive that
comparison. Revisit at month 12 with a track record.

## Two numbers in the sheet I don't believe

**Shipping at $0.82 is almost certainly wrong, and it's the one that matters.**
That's roughly a one-ounce first-class stamp. A rigid mailer carrying a print, a
sticker, a letter and a third piece will not weigh one ounce and will not be
machinable. Realistic is **$1.50–$2.50** as a large flat, or **$4–5** if it goes
rigid via Ground Advantage.

At $32 a $4 shipping cost is survivable — margin drops from 85% to 75%. At $15 it
eats a third of the contribution. **The cheaper the price, the more this error
hurts**, which is itself an argument for the higher number.

*Action for Brian: weigh a mocked-up bundle in its actual mailer and price it at
the counter before we commit to anything.*

**Patrick's labour is not in the model at all.** That's fine for a breakeven
sheet and fatal for a pricing decision. `data/metrics-schema.md` requires gross
margin to count his hours at a real rate, and the numbers above don't yet. We
need a studio-hours-per-bundle figure — it's also the growth ceiling
(`company/open-questions.md` #3).

## Structure

- **$32/month**, cancel anytime.
- **$320/year** — two months free. Push this hard at launch: it's cash up front,
  it removes twelve months of card-failure churn, and it converts the people most
  likely to have stayed anyway.
- **No launch discount.** Discount-acquired subscribers churn at 2–3x. If we need
  an incentive it's an *extra piece* — a second print, a founding-member
  something — never a lower price.
- **Gift: 3 months $96, 6 months $186.** Must exist before November.
- Shipping included in the price. The category expects it and a separate
  shipping line at checkout is a conversion killer.

## What would change my mind

- Shipping lands above $5/unit → the bundle needs to get lighter or the price
  needs to go to $38, not down.
- Patrick's per-bundle time exceeds ~50 minutes → we're capacity-bound long
  before we're demand-bound, and the price should go *up* to ration it.
- The Denver waitlist won't convert above $25 → that's real data and it beats
  this analysis. We'll know by launch.
