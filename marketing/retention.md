# Retention

*Owner: Marty. 2026-09-16.*

Acquisition gets the attention; churn decides whether this is a business. At 8%
monthly churn the average subscriber lasts 12.5 months. At 4%, 25 months. Same
product, same spend, double the company. Nothing in the channel plan is worth as
much as halving churn.

Category benchmarks (checked 2026-09-16): consumer subscription ecommerce runs
5–8% monthly; curated lifestyle boxes 7–10%; best-in-class under 3%.
**Our target: under 5% monthly by month 6.**

## The four reasons people will cancel us

### 1. They ran out of wall
The structural risk. Someone subscribes to fill a space, fills it in four
months, and has no reason to continue.

**The answer is the third piece.** It's the only element that isn't
wall-destined, and it should deliberately skew toward things that get *used* and
*replaced* — coasters, matchbooks, recipe cards, tea towels, menus, labels. A
subscriber whose bundle keeps producing usable objects never hits the ceiling.

Also: sell frames, or a simple hanging system, in month two. Removing the
friction between "received a print" and "it's on the wall" is a retention
intervention disguised as an upsell.

### 2. The month wasn't for them
Someone who loves cocktails gets a month about bread. Variety is the product, but
it guarantees misses.

**The answer is telling them what's coming, and why.** The monthly email that
explains the *idea* behind the month converts a miss into a story. People forgive
a subject they don't love if they understand the thinking. They don't forgive a
box that shows up unexplained.

Longer-term: let subscribers vote on one upcoming subject per quarter. Voting is
the cheapest retention mechanic that exists — it manufactures anticipation and
makes cancelling feel like leaving early.

### 3. Money got tight
Unavoidable and seasonal.

**The answer is a pause button that's easier to find than the cancel button.** A
pause is a retained customer; a cancel is a new CAC. Offer 1–3 month pauses
prominently in the cancel flow. Also offer a downgrade before you offer a
goodbye.

### 4. The card expired
Involuntary churn is 25–40% of all churn in consumer subscription and it's the
only kind that's purely an engineering problem.

**The answer:** dunning. Card-expiry warnings at 30 and 7 days, retries on a
schedule, and a one-click update link. This is the cheapest retention work
available and it must exist at launch, not after the first failed charge.

## The anti-cancel playbook

In priority order, all to be built before we have anything to retain:

1. **Dunning + card-update flow.** Launch requirement. Non-negotiable.
2. **Pause, prominently, in the cancel flow.** Launch requirement.
3. **The monthly "what's shipping and why" email.** Launch requirement. Sends the
   week the bundle mails.
4. **A designed mailer.** Anticipation is a retention mechanic; a package that
   looks like a gift keeps people subscribed.
5. **Cancel survey, one question, free text.** We will learn more from the first
   20 cancels than from any research we could buy.
6. **Month-3 and month-6 touchpoints.** Handwritten note or a surprise extra at
   the two most common churn cliffs.
7. **Quarterly subject vote.** Month 4+.
8. **Loyalty by tenure, not discount.** At month 12, the print is signed and
   numbered. Costs nothing, can't be bought, and makes leaving feel like losing
   status.
9. **Win-back at 60 days post-cancel.** One email, the print they missed, no
   discount.

## Cohort discipline

From the first subscriber, track retention by **signup cohort**, not aggregate.
Aggregate churn hides everything that matters. Specifically watch:
- Month-1 → month-2 retention. The single most predictive number we'll have.
- Month-6 retention. Where the wall-space ceiling would show up.
- Gift-subscription conversion at expiry. Free money if it works.

Schema in `data/metrics-schema.md`, values in `data/metrics.json`.

## What I'd cut before I'd cut retention work

All of it. Every tactic in `channels.md` and `guerrilla.md` is worth less than
getting churn from 8% to 4%.

## Sources

- Churn by category — https://eightx.co/blog/average-subscription-churn-rate-by-category (checked 2026-09-16)
- Voluntary vs. involuntary churn split — https://www.subscriptionboxcalculator.us/benchmarks (checked 2026-09-16)
