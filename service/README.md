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
| `MARTY_ALLOWED_USERS` | your + Patrick's Slack user IDs, comma-separated |
| `MARTY_MODEL` | `claude-opus-5` |
| `MARTY_EFFORT` | `high` |
| `BRIEF_CRON` | **leave empty for now** |
| `BRIEF_CHANNEL` | the channel ID for `#marty` |
| `BRIEF_TZ` | `America/Denver` |

**Set `MARTY_ALLOWED_USERS`.** Without it anyone in the workspace who can see
Marty can spend your Anthropic credits and commit to the repo. Find a user ID in
Slack: profile → ⋮ → Copy member ID.

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

Threads keep context for 3 days or 40 messages, whichever comes first, and now
survive a restart (persisted next to the repo checkout).

## Answer first, file second

Marty replies before he writes anything. Repo writes are staged during the turn
and committed in a single push *after* the reply is sent, so git never sits
between a question and its answer — and a turn that touches four files is one
commit, not four.

You'll see a quiet `_pushed a1b2c3d: company/knowledge.md_` under his reply when
something landed.

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

Opus 5 at `high` effort. The repo context is cached, so a follow-up in the same
thread costs a fraction of the first message. Expect roughly $0.10–0.40 per
exchange depending on how much research he does. A full morning brief with web
research is closer to $1–2.

To cut it: `MARTY_EFFORT=medium` for everyday chat, or `MARTY_MODEL=claude-sonnet-5`.
Both trade judgment for cost — I'd leave it on Opus for strategy work.

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
