# Retention

*Owner: Marty. 2026-09-16. Rewritten the same day after Patrick set the bundle
contents — the old version leaned on a variable surprise piece that no longer
exists.*

Acquisition gets the attention; churn decides whether this is a business. At 8%
monthly churn the average subscriber lasts 12.5 months. At 4%, 25 months. Same
product, same spend, double the company. Nothing in the channel plan is worth as
much as halving churn.

Category benchmarks (checked 2026-09-16): consumer subscription ecommerce runs
5–8% monthly; curated lifestyle boxes 7–10%; best-in-class under 3%.
**Our target: under 5% monthly by month 6.**

## What we're retaining with

Four fixed items every month: a relief print, a cocktail card, a letter, a
sticker. All flat, all paper, all in an envelope. Patrick ruled out coasters,
matchbooks and tea towels on weight and cost, so the retention plan can't lean on
objects that get used up and replaced. It has to lean on the **collection** and
the **relationship**.

## The four reasons people will cancel us

### 1. They ran out of wall
The structural risk, and it got worse when the surprise piece died. Someone
subscribes to fill a space, fills it in four months, and has no reason to
continue. The old answer was that the third piece would skew toward usable
objects — coasters, tea towels, menus. That answer is gone.

**The answer is now the cocktail card, and it has to carry more weight than it
was designed to.** It's the only piece that isn't wall-destined: it's a collected
object, filed and used at the bar cart, and an unfinished set is a reason not to
cancel. So it ships every month without gaps, and we sell the *collection*
explicitly, not the card — "month seven of your cocktail book" is the message,
not "this month's drink."

Two things that follow, both of which I want built:
- **Something to keep the cards in.** A box, a slipcase, a binder, sent at month
  three or six. It turns a stack of cards into an object with visible gaps in it,
  which is the whole psychology. Costs one design and one print run.
- **Sell frames, or a simple hanging system, in month two.** Removing the
  friction between "received a print" and "it's on the wall" is a retention
  intervention disguised as an upsell — and it buys wall space back by making
  rotation easy.

If the month-6 cohort still cliffs after both, the wall ceiling is real and the
product needs something that gets consumed. That's a Patrick conversation about
weight, not a marketing fix.

### 2. The month wasn't for them
Someone who loves cocktails gets a month about bread. Variety is the product, but
it guarantees misses.

**Patrick's letter already is the answer**, which is the best thing about it. He
writes why he chose the subject and what's new in the studio, in the envelope,
every month. People forgive a subject they don't love if they understand the
thinking. Back it with the monthly "what's shipping and why" email so the
explanation arrives before the bundle does, not with it.

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

## The photo loop

Patrick's letter asks subscribers to send photos of where their pieces ended up.
That request goes in **every** letter with one place to send to. It does two jobs
at once: it gives us real customers' walls and bar carts to post, and a
subscriber who has sent us a photo of their own bar cart is materially less
likely to cancel — they've put themselves in the thing. Reply to every single
one, in Patrick's voice, because he actually wants to.

## The anti-cancel playbook

In priority order, all to be built before we have anything to retain:

1. **Dunning + card-update flow.** Launch requirement. Non-negotiable.
2. **Pause, prominently, in the cancel flow.** Launch requirement.
3. **The monthly "what's shipping and why" email.** Launch requirement. Sends the
   week the bundle mails.
4. **A designed mailer.** Anticipation is a retention mechanic; a package that
   looks like a gift keeps people subscribed.
5. **The card case or slipcase**, shipped at month 3 or 6. The collection needs a
   home to have visible gaps.
6. **Cancel survey, one question, free text.** We will learn more from the first
   20 cancels than from any research we could buy.
7. **Month-3 and month-6 touchpoints.** Handwritten note or a surprise extra at
   the two most common churn cliffs.
8. **Quarterly subject vote.** Month 4+.
9. **Loyalty by tenure, not discount.** Every print is already signed and
   numbered, so tenure has to be marked some other way — first pick of a
   misprint, an extra card, a print not in the run.
10. **Win-back at 60 days post-cancel.** One email, the print they missed, no
    discount.

## Cohort discipline

From the first subscriber, track retention by **signup cohort**, not aggregate.
Aggregate churn hides everything that matters. Specifically watch:
- Month-1 → month-2 retention. The single most predictive number we'll have.
- Month-6 retention. Where the wall-space ceiling would show up, and where the
  all-flat-paper bundle is most exposed.
- Gift-subscription conversion at expiry. Free money if it works.

Schema in `data/metrics-schema.md`, values in `data/metrics.json`.

## What I'd cut before I'd cut retention work

All of it. Every tactic in `channels.md` and `guerrilla.md` is worth less than
getting churn from 8% to 4%.

## Sources

- Churn by category — https://eightx.co/blog/average-subscription-churn-rate-by-category (checked 2026-09-16)
- Voluntary vs. involuntary churn split — https://www.subscriptionboxcalculator.us/benchmarks (checked 2026-09-16)
