# Martin — the marketing org for a monthly art bundle

This repo *is* the marketing department. It holds the brand context, the living
strategy, the competitive research, the experiment backlog, the metrics, and the
agent that works on all of it.

**Marty** is the CMO. He is an agent defined in `.claude/agents/marty.md`. He
researches, writes strategy, ships campaign briefs, files a morning update, and
owns the metrics dashboard.

## Cast

| Who | Role |
| --- | --- |
| Brian Bernstein | CEO. Business, ops, fulfillment, pricing, final call on spend. |
| Patrick Selner | Founder / Artist. Every piece of art in every bundle. |
| Marty | CMO (agent). Strategy, research, channels, campaigns, metrics. |

## Map

```
company/          Who we are. Read this first — everything else assumes it.
  business-brief.md   The product, the model, the economics
  brand.md            Positioning, voice, naming, visual guardrails
  icp.md              Who buys this, and why
  open-questions.md   Decisions Marty needs from Brian or Patrick
  knowledge.md        Facts Brian and Patrick have stated, dated and attributed
  decisions.md        Every call, and why
  naming.md           The name, and why the others lost
  glossary.md         Plain-English definitions of every term in this repo
marketing/
  strategy.md         The living master strategy. The one doc to read.
  channels.md         Per-channel plan, owner, cadence, kill criteria
  paid-media.md       When paid turns on, budgets, guardrails
  guerrilla.md        Offline / unconventional tactics
  retention.md        Churn, LTV, the anti-cancel playbook
  experiments.md      The backlog. Everything is a test with a stated bet.
  calendar.md         What ships when
  competitors/        One file per competitor + an index
  research/           Benchmarks, market notes, technique watch
  briefs/             Dated morning updates (YYYY-MM-DD.md)
data/
  metrics.json        Source of truth for the dashboard
  metrics-schema.md   What each metric means and where it comes from
dashboard/
  index.html          The dashboard. Reads data/metrics.json.
.claude/
  agents/marty.md     The CMO
  skills/             Marty's repeatable procedures
```

## Working with Marty

In a Claude Code session in this repo:

- `Ask Marty for today's brief` → runs the `marty-morning-brief` skill
- `Marty, research <competitor>` → `marty-competitor-research`
- `Marty, update the dashboard with <numbers>` → `marty-metrics`
- `Marty, brief me a campaign for <thing>` → `marty-campaign-brief`

Marty commits his own work. Every strategy change lands as a commit with a
reason in the message.

## House rules

1. **No invented numbers.** Every metric in `data/metrics.json` is real,
   sourced, and dated — or it is explicitly `null`. Benchmarks from the web are
   labeled as benchmarks, never as our numbers.
2. **Every tactic has a bet, a cost, and a kill date.** See `experiments.md`.
3. **Brian approves spend.** Marty proposes, Brian signs off. Nothing gets
   bought without a line in `paid-media.md` marked APPROVED.
4. **Patrick's time is the scarcest resource in the company.** Any tactic that
   asks for new art gets costed in hours before it gets proposed.
