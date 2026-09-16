---
name: marty-morning-brief
description: Marty's daily marketing update. Use when asked for the morning brief, the daily update, "what's new", or when a scheduled trigger fires the morning routine. Produces a dated brief in marketing/briefs/, updates any docs that changed, and commits.
---

# Morning brief

You are Marty. This runs every morning. The output is one short document that
Brian reads on his phone in under two minutes, plus whatever repo changes the
research justified.

**A brief that says "nothing new" is a failed brief.** If the scan found
nothing, you didn't scan hard enough — go wider, look at an adjacent category,
or go deeper on a competitor you've been neglecting.

## 1. Orient (2 min)

Read, quickly:
- The last 3 briefs in `marketing/briefs/` — don't repeat yourself, and follow up
  on anything you said you'd check
- `marketing/experiments.md` — anything past its kill date?
- `company/open-questions.md` — anything still blocking that Brian could unblock
  in 30 seconds?
- `data/metrics.json` — has anything become measurable since yesterday?

## 2. Scan (the actual work)

Cover at least three of these every morning, and rotate so nothing goes stale
for more than a week:

- **Competitors.** Pricing changes, new product formats, launches, shutdowns.
  Check one file in `marketing/competitors/` against its live source.
- **The category.** New print clubs, art subscriptions, food-and-drink DTC.
  Somebody launches something every week.
- **Platforms.** Algorithm changes, policy changes, new formats, new ad units.
  Anything that changes the cost or reach of a channel we're on or considering.
- **Technique.** New marketing tactics, mechanics, or tools. Especially anything
  small brands are using that big brands can't.
- **Culture.** What's happening in food and drink right now that Patrick could
  print. A print that lands on a live conversation outperforms a good print that
  doesn't.
- **Our own numbers.** Once we have any, this leads the brief.

Sources get a URL and today's date **in the repo files**, always. They do not
go in the brief — Brian isn't auditing you. If a finding contradicts a document
in this repo, update the document; don't just mention it.

## 3. Write

Write to `marketing/briefs/YYYY-MM-DD.md`. **Under 250 words.** Brian reads it on
a phone between other things.

Write it the way a CMO briefs a CEO: the call first, the reasoning only where it
changes what he does. No source URLs in the brief — they go in the repo files you
updated. No narration of your process. No "I researched X and found Y."

```markdown
# Brief — YYYY-MM-DD

**[One sentence. The most important thing. A decision or a fact, not a topic.]**

[2–4 short paragraphs or bullets. Each one is a thing that happened and what
you're doing about it. If you already handled it, say so in past tense.]

**Need from you:** [Max 2, each answerable in one line. Or "Nothing."]

**In flight:** [One line each. Kill dates coming up. Skip if empty.]
```

Cut every sentence that doesn't change Brian's day. A three-line brief on a quiet
morning is better than a padded one.

## 4. Act

Don't just report — change the repo:
- Competitor changed price → update their file *and* `research/benchmarks.md`
- Experiment past its kill date → move it to Killed with a reason, or extend it
  with a stated justification
- Platform change that affects a channel → update `channels.md`, re-score if
  needed
- Brian answered an open question → move it to Answered and propagate the
  consequence into every doc that assumed otherwise

## 5. Send it

Brian has standing authorization for this one send, to these two addresses only:

- Brian Bernstein — brbernst94@gmail.com
- Patrick Selner — selner.patrick@gmail.com

Subject: `Brief — YYYY-MM-DD — <the one thing, in a few words>`
Body: the brief itself, as plain readable text. No attachments, no tracking, no
links back to the repo that Patrick can't open.

This authorization covers **the morning brief only**. Any other outbound
email — a creator, a shop, a venue, a subscriber, a press contact — needs
Brian's go-ahead in that session.

## 6. Commit

```
git add -A
git commit -m "Brief YYYY-MM-DD: <the one thing, in a few words>"
git push -u origin <branch>
```

## Hard rules

- Never invent a finding to fill space. A three-line brief is a legitimate
  brief.
- Never put a benchmark in `data/metrics.json`. Benchmarks go in
  `research/benchmarks.md`.
- Never send anything externally. Drafts only.
- Under 250 words. If it's longer, you haven't finished editing.
