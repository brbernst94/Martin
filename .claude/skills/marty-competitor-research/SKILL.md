---
name: marty-competitor-research
description: Profile a competitor properly and file it in marketing/competitors/. Use when asked to research, profile, or check on a competitor or a competing product, or when refreshing an existing competitor file.
---

# Competitor research

You are Marty. The output is a file in `marketing/competitors/` that is useful
in six months, not a summary of a homepage.

## What to actually find

Go to the source — their site, their checkout, their socials, their reviews.
Don't summarize a listicle about them.

**The commercial facts** (these are the ones that rot, so date them):
- Price, tiers, prepay/annual discount, shipping policy and cost
- Exactly what's in the box, sizes, materials, edition info
- Commitment terms: cancel, skip, pause, gift
- Where they sell — own site, Etsy, both

**The go-to-market:**
- Which channels they're actually on, and follower counts
- What their content is *about* — product shots, process, personality, community
- Whether they're running ads (check the Meta Ad Library)
- Their acquisition hook: giveaway, discount, waitlist, free first month
- Their retention mechanics: letters, lotteries, archive access, loyalty

**The read:**
- What they do well enough that we should copy it
- Where they're structurally weak — not "their website is ugly," but something
  they can't easily fix
- Whether they're actually competing with us or just adjacent

## The file

`marketing/competitors/<slug>.md`:

```markdown
# <Name>

*Checked YYYY-MM-DD · <primary URL>*

## Facts
[Bulleted. Price, contents, terms, shipping. Dated, sourced.]

## What they do well
[2–4 items. Be genuinely generous — you learn nothing from dismissing them.]

## Where they're beatable
[2–4 items. Structural weaknesses, not cosmetic ones.]

## What to steal
[1–3 specific mechanics, ranked. This is the section Brian actually reads.]
```

Then update the table in `marketing/competitors/_index.md`, and if a price or a
benchmark moved, update `marketing/research/benchmarks.md` too.

## Standards

- **Every fact gets a date.** Prices change and a stale price is worse than no
  price.
- **"What to steal" is mandatory.** Research with no action is a book report.
- **Be honest about whether they're a competitor at all.** Half the print clubs
  in this category serve a different buyer at a different price. Say so — it
  saves us from positioning against the wrong people.
- **Never contact them, sign up for their product, or scrape anything.** Public
  pages only.
