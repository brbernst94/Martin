# Marty on Slack

Marty runs as a small Python service on Railway. He reads the strategy repo,
answers in Slack, searches the web, and commits decisions back to GitHub.

Socket Mode — no public URL, no webhook to register, nothing to re-point when
Railway redeploys.

## What he can do from Slack

- Answer from the repo (`read_file`, `list_files`, `search_repo`)
- **Commit changes** (`write_file`) — updates a strategy doc and pushes it
- Live web research (Anthropic's server-side web search)
- Run the morning brief, on a schedule or on demand

He still can't spend money, post publicly, or email anyone outside the company.

---

## 1. Create the Slack app (5 minutes)

1. https://api.slack.com/apps → **Create New App** → **From an app manifest**
2. Pick your workspace, then paste the manifest. **The editor opens on the JSON
   tab** — either paste `slack-app-manifest.json`, or click the YAML tab first
   and paste `slack-app-manifest.yml`. Pasting YAML into the JSON tab fails with
   `Expecting 'STRING','NUMBER',... got: 'INVALID'`. Create.
3. **Basic Information → App-Level Tokens** → Generate Token and Scopes.
   Name it `railway`, add the `connections:write` scope, generate.
   Copy the `xapp-…` token → this is `SLACK_APP_TOKEN`.
4. **Install App** → Install to Workspace. Copy the Bot User OAuth Token
   (`xoxb-…`) → this is `SLACK_BOT_TOKEN`.
5. In Slack, create a private channel (`#marty`) and invite him:
   `/invite @Marty`. He also takes DMs.

## 2. GitHub token

A fine-grained personal access token scoped to **this repo only**, with
**Contents: Read and write**. https://github.com/settings/tokens?type=beta

## 3. Deploy to Railway

```bash
railway login
railway init            # or: railway link, into an existing project
railway up              # from the service/ directory
```

Or point Railway at the GitHub repo and set **Root Directory** to `service`.

### Variables

Set every one of these in Railway → Variables (`.env.example` is the template):

| Variable | Value |
| --- | --- |
| `ANTHROPIC_API_KEY` | from console.anthropic.com |
| `SLACK_BOT_TOKEN` | `xoxb-…` |
| `SLACK_APP_TOKEN` | `xapp-…` |
| `GITHUB_TOKEN` | fine-grained PAT, contents read/write |
| `GITHUB_REPO` | `brbernst94/Martin` |
| `GITHUB_BRANCH` | `main` |
| `REPO_DIR` | `/data/repo` |
| `MARTY_BRIAN_ID` | your Slack user ID — briefed as CEO |
| `MARTY_PATRICK_ID` | Patrick's Slack user ID — briefed as the artist |
| `MARTY_ALLOWED_USERS` | anyone else allowed to talk to him (optional) |
| `MARTY_MODEL` | `claude-opus-5` |
| `MARTY_EFFORT` | `high` |
| `BRIEF_CRON` | **leave empty for now** |
| `BRIEF_CHANNEL` | the channel ID for `#marty` |
| `BRIEF_TZ` | `America/Denver` |

**Set `MARTY_BRIAN_ID` and `MARTY_PATRICK_ID`.** They control two things: who's
allowed to talk to Marty at all, and how he briefs them. Without them anyone in
the workspace can spend your Anthropic credits and commit to the repo.

To find an ID, DM Marty **`whoami`** and he replies with it. That works before
you're on the allowlist — which is the point, since it's how you get on it. The
manual route is profile → **⋮** → **Copy member ID**.

Marty talks to Brian as a CEO — money, dates, decisions, no craft vocabulary —
and to Patrick as the artist: the work, his own printmaking vocabulary, and no
marketing metrics. Anyone else gets a plain register with no jargon in either
direction.

### Volume (optional)

Railway → project canvas → **Cmd+K → "volume"**, or right-click the empty canvas.
It's a canvas-level object, not a service setting, which is why it's hard to
find — and it needs a Hobby plan or above.

**Skip it if it's in the way.** Without a volume `/data` is ordinary ephemeral
container disk: everything works, Marty just re-clones the repo when the
container restarts. The repo is a few hundred KB, so that's about two seconds
at boot. If `REPO_DIR` turns out to be genuinely unwritable the service falls
back to `/tmp` rather than crash-looping.

## 4. Turning the morning brief on

It's off. When you want it, set `BRIEF_CRON` and redeploy:

```
BRIEF_CRON=0 7 * * 1-5     # 7am Denver, weekdays
BRIEF_TZ=America/Denver
BRIEF_CHANNEL=C0XXXXXXX
```

APScheduler reads the cron in `BRIEF_TZ`, so write it in local time — no UTC
conversion needed.

## Using him

- **DM** — anything. He replies in the DM.
- **`@Marty` in a channel** — he answers in a thread and stays in that thread.
- **`reset`** in a thread — clears his memory of it.
- **`whoami`** — replies with your Slack member ID and which register he's using
  for you. Works for anyone, configured or not.

Threads keep context for 3 days or 40 messages, whichever comes first, and now
survive a restart (persisted next to the repo checkout).

## Answer first, file second

Answering and recording are two separate passes.

**Pass one** answers you, with read-only tools. No writes, because every tool
call is a full model round trip — letting Marty file paperwork mid-answer added
about a minute per file while you watched a status line.

**Pass two** runs in the background once the reply is on screen, at low effort,
with writes enabled. It records anything durable and pushes it as one commit. If
there was nothing worth recording it does nothing and says nothing.

You'll see a quiet `_filed a1b2c3d: company/knowledge.md_` under his reply when
something landed, and a visible warning if the push failed.

The morning brief is the exception — writing the brief *is* the job, so it keeps
writes inline.

## If Marty can't commit

A **public** repo clones fine with a bad, expired, or read-only token, so a
successful clone proves nothing about write access. At boot Marty runs a real
`git push --dry-run` and logs a loud block naming the problem if it fails.

It has to be a dry-run push specifically. An earlier version asked the REST API
instead and reported success while git was still being rejected — the API takes
a Bearer token over `api.github.com`, git takes Basic auth over `github.com`.
Verifying one tells you nothing about the other. Check the path you actually use.

The fix is almost always a fine-grained token missing **Repository permissions →
Contents → Read and write**, or one whose **Repository access** doesn't list this
repo. A classic token needs the `repo` scope. The boot message reports the token
type and length, so a stray newline shows up as a wrong length.

Credentials go in an `Authorization: Basic` header passed per-command, never in
the remote URL — so the token is never written into `.git/config` on the
volume.

## How Marty remembers

Two layers, deliberately:

- **Short-term** — the live conversation. Capped, expiring, on disk.
- **Long-term — the repo.** `company/knowledge.md` holds facts Brian and Patrick
  have stated, dated and attributed. `company/decisions.md` holds every call and
  *why*. Both load into his prompt on every single message.

There's no vector database and there shouldn't be. The repo is versioned,
human-readable, and correctable — a separate memory store would give you two
sources of truth that drift, and one of them you can't audit.

**When a fact changes**, Marty doesn't just append. He strikes the old fact,
logs the reversal with its reason, greps the repo for the old value, and rewrites
every file that carried it — then says what else it broke. A new price changes
the CAC math in `pricing.md`; a new launch date rebuilds `calendar.md`. A repo
that contradicts itself is worse than no repo.

Facts from Brian and Patrick outrank anything Marty found on the web. They're the
experts on this business.

## Costs

Three things keep this affordable, and all three were learned the expensive way.

**The stable half of the prompt comes first and carries the cache breakpoint.**
Identity, the repo map and the always-loaded docs are identical for every
person and every pass, so they cache once and are read back at a tenth of the
price. Anything that varies — who is talking, which pass — goes in a second
block *after* it. Putting the variable content first, which is how this started,
gives every combination its own cache entry and each one pays full price for the
same 6k tokens.

**Only three documents are preloaded.** `marty.md`, `business-brief.md` and
`knowledge.md`. Everything else he opens with `read_file` when it's relevant.
Preloading eight documents cost ~14k tokens on *every* API call, and a tool loop
makes several per exchange.

**Capture runs on Sonnet.** Deciding what to file is much easier than deciding
what to think. Opus on both roughly doubled the bill for no gain.

Every turn logs what it cost:

```
answer: 3 call(s), 2 cached, $0.042
capture: 2 call(s), 2 cached, $0.008
```

If `cached` is 0 across a whole conversation, caching is broken — check whether
something varying slipped into the stable block.

**A Haiku gate decides whether capture runs at all.** Most exchanges are
questions or chatter and produce no writes; running a full Sonnet tool loop to
discover that was the most wasteful thing here. One ~$0.0004 call answers YES or
NO first. On failure it answers YES — losing a fact is worse than a wasted call.

**The message history is cached too**, not just the system prompt, and the
system block holds a 1-hour TTL. Slack messages arrive minutes apart, and the
default 5-minute cache expired in every gap.

Roughly $0.08 an exchange, $0.11 when something gets recorded.

### What's left

Input is largely solved; **output is now the dominant cost**, and thinking
tokens bill as output. So `MARTY_EFFORT` is the real remaining lever:

- `medium` — the default for chat. Right for most questions.
- `low` — noticeably cheaper, and fine for lookups and quick calls. Costs
  judgment on anything strategic.
- `high` — worth it for the morning brief, where research and synthesis are the
  whole point.

Other knobs: `MARTY_CAPTURE_MODEL` (default `claude-sonnet-5`), `MARTY_GATE_MODEL`
(default `claude-haiku-4-5`), and `MARTY_MODEL` if you ever want to drop the
answering model — I'd keep that on Opus. It's where the judgment lives, and it's
no longer where the money goes.

## Running locally

```bash
cd service
pip install -r requirements.txt
cp .env.example .env     # fill it in
set -a && source .env && set +a
python app.py
```

## Layout

```
app.py              Slack wiring, message routing, scheduler, health endpoint
marty/agent.py      The Claude loop — tools, system prompt, pause_turn handling
marty/repo.py       Git working copy: clone, pull, read, write, commit, push
marty/memory.py     Per-thread conversation state
```

## Guardrails in the code

- `MARTY_ALLOWED_USERS` gates every inbound message.
- Repo writes are path-checked — nothing outside the repo, and `.git/`,
  `.github/workflows/`, and `service/.env` are refused outright.
- The GitHub token is scrubbed from any error text before it reaches Slack.
- Push retries rebase onto origin rather than force-pushing.
- Tool loop caps at 20 turns and 5 `pause_turn` resumes so a runaway research
  session can't bill indefinitely.
